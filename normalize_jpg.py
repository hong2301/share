#!/usr/bin/env python3
"""把 items.csv 引用的所有图片统一转为真 JPEG，文件名后缀统一 .jpg，并同步更新 items.csv 路径。

- 内容非 JPEG（PNG/WEBP/GIF 等）→ 转成 JPEG（透明 PNG 贴白底）
- 文件名后缀不标准（如 xxx_D_00.jpg.png / xxx_M_05.jpg.webp）→ 重命名为 xxx_D_00.jpg
- 已规范（真 JPEG + .jpg 后缀）的文件跳过，可重复运行（幂等）
- 每次运行自动读取 items.csv 并回写更新后的路径

用法：
  python3 normalize_jpg.py            # 处理 items.csv 引用的图片
  python3 normalize_jpg.py --all      # 额外处理 imgs 目录中未被引用的图片
"""
import csv
import io
import os
import re
import sys

import requests
from PIL import Image

CSV_PATH = "items.csv"
IMGS_DIR = "imgs"
JPEG_QUALITY = 92


def to_jpeg_bytes(img) -> bytes:
    """把 PIL Image 转为 JPEG 字节（RGBA/RGBA 贴白底，GIF 取首帧）"""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


def standard_name(path: str) -> str:
    """规范文件名：统一以 .jpg 结尾。
    imgs/xxx_D_00.jpg.png -> imgs/xxx_D_00.jpg
    imgs/xxx_M_05.jpg.webp -> imgs/xxx_M_05.jpg
    已是 .jpg 结尾的保持不变
    """
    base = os.path.basename(path)
    stem = re.sub(r"\.(jpg|jpeg|png|webp|gif)(\.[a-zA-Z0-9]+)*$", "", base, flags=re.I)
    return os.path.join(os.path.dirname(path), stem + ".jpg")


def process_file(path: str, dry: bool = True):
    """处理单个文件，返回 (新路径 or None, 报告)"""
    if not os.path.exists(path):
        return None, f"缺失 {path}"
    size = os.path.getsize(path)
    if size == 0:
        return None, f"空文件 {path}"

    # 读实际格式
    try:
        with Image.open(path) as im:
            fmt = im.format
            im.seek(0)
            im.load()
    except Exception as e:
        return None, f"无法解码 {path}: {e}"

    new_path = standard_name(path)
    need_convert = fmt != "JPEG"
    need_rename = new_path != path

    if not need_convert and not need_rename:
        return None, None  # 已规范，跳过

    # 目标路径冲突检查
    if new_path != path and os.path.exists(new_path):
        return None, f"目标已存在 {new_path} (跳过 {path})"

    if dry:
        action = "转JPEG" if need_convert else ""
        if need_rename:
            action += "+重命名" if action else "重命名"
        return new_path, f"{action}: {path} -> {new_path}"

    # 执行（顺序很重要：先 rename 旧文件，再写入转换内容，避免旧文件覆盖新内容）
    try:
        data = None
        if need_convert:
            with Image.open(path) as im:
                data = to_jpeg_bytes(im)
        if need_rename and new_path != path:
            os.rename(path, new_path)
        if need_convert:
            with open(new_path, "wb") as f:
                f.write(data)
        return new_path, f"{'转换' if need_convert else ''}{'+重命名' if need_rename else ''}: {path} -> {new_path}"
    except Exception as e:
        return None, f"失败 {path}: {e}"


def main():
    dry = "--dry-run" in sys.argv
    do_all = "--all" in sys.argv

    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

    # 收集所有引用路径 -> 需要更新的 (row, 旧路径)
    targets = []  # (row, old_path)
    for row in rows:
        for p in row["img_paths"].split("|"):
            p = p.strip()
            if p:
                targets.append((row, p))

    print(f"items.csv 引用 {len(targets)} 个路径")

    # 处理并记录路径映射
    mapping = {}  # old_path -> new_path
    report = []
    for row, old_path in targets:
        if old_path in mapping:
            continue
        new_path, msg = process_file(old_path, dry=dry)
        if msg:
            report.append(msg)
        if new_path:
            mapping[old_path] = new_path

    # 同步更新 items.csv
    updated_rows = 0
    if not dry:
        for row in rows:
            parts = [p.strip() for p in row["img_paths"].split("|") if p.strip()]
            changed = False
            for i, p in enumerate(parts):
                if p in mapping:
                    parts[i] = mapping[p]
                    changed = True
            if changed:
                row["img_paths"] = " | ".join(parts)
                updated_rows += 1
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # 可选：处理 imgs 目录中未被引用的图片
    if do_all:
        referenced = set(mapping.keys())
        for row in rows:
            for p in row["img_paths"].split("|"):
                p = p.strip()
                if p:
                    referenced.add(p)
        others = [f for f in os.listdir(IMGS_DIR)
                  if not f.startswith(".") and os.path.join(IMGS_DIR, f) not in referenced]
        extra = []
        for fn in others:
            p = os.path.join(IMGS_DIR, fn)
            new_path, msg = process_file(p, dry=dry)
            if msg and "跳过" not in msg:
                extra.append(msg)
        report += extra
        print(f"额外处理未引用图片 {len(others)} 个")

    # 输出报告
    changed = [m for m in report if "转换" in m or "重命名" in m or "->" in m]
    skipped = [m for m in report if m and "->" not in m and "转换" not in m]
    print(f"\n{'[DRY-RUN] ' if dry else ''}需要处理 {len(mapping)} 个文件")
    for m in changed[:15]:
        print(f"  ✓ {m}")
    if len(changed) > 15:
        print(f"  ... 等共 {len(changed)} 个")
    if skipped:
        print(f"\n跳过/异常 {len(skipped)} 个:")
        for m in skipped[:8]:
            print(f"  ⚠ {m}")
    if not dry:
        print(f"\n✓ items.csv 已同步更新 {updated_rows} 行")


if __name__ == "__main__":
    main()
