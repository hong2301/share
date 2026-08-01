# -*- coding: utf-8 -*-
"""
合并 indiegogo / indiegogo2 / indiegogo3 三个目录：

1. links.csv：按 projectID 合并，状态优先级 done(3) > no_comments(2) > error(1) > pending(0)
   - pending 是待处理，其余都是处理过的；同优先级按目录顺序 dir1 > dir2 > dir3 取靠前者
2. comments_out_api / project_meta_api / indiegogo_main_api_progress：
   同名文件（同一 projectID）在多个目录存在时，取该 projectID 状态优先级最高
   目录中的文件；该目录没有对应文件时，按优先级降序在其他目录中寻找。

输出：/Users/hong/Desktop/indiegogo_total/
"""

import csv
import os
import shutil
from pathlib import Path

BASE = Path("/Users/hong/Desktop")
DIRS = ["indiegogo", "indiegogo2", "indiegogo3"]
OUT = BASE / "indiegogo_total"
SUBS = ["comments_out_api", "project_meta_api", "indiegogo_main_api_progress"]

STATUS_PRIORITY = {"done": 3, "no_comments": 2, "error": 1, "pending": 0}
# 目录排序：先按状态优先级降序，再按目录编号升序（dir1 > dir2 > dir3）
dir_rank = {d: i for i, d in enumerate(DIRS)}


def load_links(d):
    with open(BASE / d / "links.csv", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return {row["projectID"]: row for row in reader}


def main():
    # ---------- 1. 读入三个 links.csv ----------
    rows = {d: load_links(d) for d in DIRS}
    all_ids = list(rows[DIRS[0]].keys())
    for d in DIRS[1:]:
        for k in rows[d]:
            if k not in rows[DIRS[0]]:
                print(f"[warn] {d} 有额外 projectID: {k}")
                all_ids.append(k)

    # ---------- 2. 合并 links：每个 projectID 选优先级最高的行 ----------
    merged = {}
    per_dir_winner = {d: 0 for d in DIRS}
    status_count = {}
    for pid in all_ids:
        # 按 (状态优先级, 目录排名) 取最优行
        best = None
        for d in DIRS:
            row = rows[d].get(pid)
            if row is None:
                continue
            key = (STATUS_PRIORITY.get(row["status"], 0), -dir_rank[d])
            if best is None or key > best[0]:
                best = (key, row, d)
        _, row, winner = best
        merged[pid] = row
        per_dir_winner[winner] += 1
        st = row["status"]
        status_count[st] = status_count.get(st, 0) + 1

    # 保持原顺序输出（与 dir1 顺序一致）
    out_rows = [merged[pid] for pid in all_ids]

    # ---------- 3. 输出合并后的 links.csv ----------
    OUT.mkdir(exist_ok=True)
    fieldnames = list(out_rows[0].keys())
    with open(OUT / "links.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"[links] 已写入 {OUT / 'links.csv'} 共 {len(out_rows)} 行")
    print(f"[links] 状态分布: {status_count}")
    print(f"[links] 每目录胜出行数: {per_dir_winner}")

    # ---------- 4. 合并 api 目录 ----------
    for sub in SUBS:
        out_sub = OUT / sub
        out_sub.mkdir(exist_ok=True)
        # 收集三目录所有文件: pid -> [(目录排名, 路径)]
        files = {}
        for d in DIRS:
            sub_path = BASE / d / sub
            if not sub_path.exists():
                continue
            for name in os.listdir(sub_path):
                m = name.rsplit("_", 1)
                pid = m[1].rsplit(".", 1)[0]
                files.setdefault(pid, []).append((dir_rank[d], sub_path / name))
        copied = 0
        for pid in all_ids:
            # 该 projectID 的目录优先级排序
            rank_order = sorted(DIRS, key=lambda d: (-STATUS_PRIORITY.get(rows[d].get(pid, {}).get("status", "pending"), 0), dir_rank[d]))
            src = None
            for d in rank_order:
                candidates = [p for r, p in files.get(pid, []) if r == dir_rank[d]]
                if candidates:
                    src = candidates[0]  # 同目录同 pid 只有一个文件
                    break
            if src is None:
                continue
            dst = out_sub / src.name
            shutil.copy2(src, dst)
            copied += 1
        print(f"[{sub}] 已合并 {copied} 个文件 → {out_sub}")

    # ---------- 5. 汇总报告 ----------
    print("\n===== 汇总 =====")
    for sub in SUBS:
        print(f"{sub}: {len(list((OUT / sub).iterdir()))} 个文件")
    # done 状态但没有 comments 文件的项目（仅提示）
    no_c = sum(1 for pid, r in merged.items() if r["status"] == "done" and not (OUT / "comments_out_api" / f"comments_{pid}.csv").exists())
    print(f"done 但无 comments 文件: {no_c} 个")


if __name__ == "__main__":
    main()
