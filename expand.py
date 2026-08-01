import csv
import json
import os
import re

INPUT_CSV = "/Users/hong/Desktop/天猫/items.csv"
OUTPUT_CSV = "/Users/hong/Desktop/天猫/天猫潮玩商品数据.csv"


def classify_imgs(img_paths_str):
    """根据 img_paths 返回 (main_count, desc_count)"""
    paths = [p.strip() for p in img_paths_str.split(" | ") if p.strip()]
    m = sum(1 for p in paths if "_M_" in os.path.basename(p))
    d = sum(1 for p in paths if "_D_" in os.path.basename(p))
    if m == 0 and d == 0 and paths:
        m = len(paths)
    return m, d


# ========== 第一步：读取 + 收集所有列名 ==========
rows = []
all_param_keys = set()
all_sku_keys = set()
max_main = 0
max_desc = 0

with open(INPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # 参数
        params_raw = row.get("params", "")
        try:
            params = json.loads(params_raw) if params_raw else {}
        except:
            params = {}
        row["_params"] = params
        all_param_keys.update(params.keys())

        # SKU keys（从 combos 收集）
        sku_raw = row.get("sku", "")
        combos = []
        if sku_raw:
            try:
                sku_data = json.loads(sku_raw)
                combos = sku_data.get("combos", [])
            except:
                pass
        for c in combos:
            for k in c:
                if not k.startswith("_"):
                    all_sku_keys.add(k)
        row["_combos"] = combos

        # 图片
        m, d = classify_imgs(row.get("img_paths", ""))
        max_main = max(max_main, m)
        max_desc = max(max_desc, d)

        rows.append(row)

# ========== 第二步：构建列 ==========
param_keys = sorted(all_param_keys)
sku_keys = sorted(all_sku_keys)

img_cols = [f"主图{i+1}" for i in range(max_main)] + \
           [f"详情图{i+1}" for i in range(max_desc)]

columns = ["店铺名称", "商品链接", "商品名"] \
    + [f"SKU-{k}" for k in sku_keys] \
    + ["价格(原价)"] \
    + [f"参数-{k}" for k in param_keys] \
    + img_cols \
    + ["图片本地路径"]


def extract_price(combo_price_str):
    """从 _combo_price 中提取最后的价格金额"""
    if not combo_price_str:
        return ""
    # 格式: "款式描述=xxx | 大小=xxx | ￥89" 或 "key=xxx | ￥89"
    parts = [p.strip() for p in combo_price_str.split(" | ")]
    for p in reversed(parts):
        if "￥" in p or "¥" in p or re.search(r'\d+\.?\d*', p):
            return p
    return parts[-1] if parts else ""


# ========== 第三步：展开数据 ==========
output_rows = []

for row in rows:
    combos = row["_combos"]
    if not combos:
        combos = [{}]

    # 解析图片链接
    img_urls = [u.strip() for u in row.get("img_urls", "").split(" | ") if u.strip()]
    img_paths_raw = row.get("img_paths", "")
    paths = [p.strip() for p in img_paths_raw.split(" | ") if p.strip()]

    main_urls, desc_urls = [], []
    m_i = 0
    d_i = 0
    for p in paths:
        fn = os.path.basename(p)
        if "_D_" in fn:
            # 详情图：无对应 URL（旧数据未采集），用本地路径填充
            desc_urls.append(p)
            d_i += 1
        else:
            if m_i < len(img_urls):
                main_urls.append(img_urls[m_i])
            m_i += 1
    if not main_urls and not desc_urls and img_urls:
        main_urls = img_urls

    for combo in combos:
        out = {}
        out["店铺名称"] = row.get("shop_name", "")
        out["商品链接"] = row.get("item_url", "")
        out["商品名"] = row.get("title", "")

        # SKU 拆列
        for sk in sku_keys:
            val = ""
            if sk in combo and isinstance(combo[sk], dict):
                val = combo[sk].get("selected", "")
            elif sk in combo:
                val = str(combo[sk])
            out[f"SKU-{sk}"] = val

        # 价格
        combo_price = combo.get("_combo_price", row.get("origin_price", ""))
        out["价格(原价)"] = extract_price(combo_price)

        # 参数
        for pk in param_keys:
            out[f"参数-{pk}"] = row["_params"].get(pk, "")

        # 图片链接展开
        for i in range(max_main):
            out[f"主图{i+1}"] = main_urls[i] if i < len(main_urls) else ""
        for i in range(max_desc):
            out[f"详情图{i+1}"] = desc_urls[i] if i < len(desc_urls) else ""

        out["图片本地路径"] = row.get("img_paths", "")

        output_rows.append(out)

# ========== 第四步：写 CSV ==========
with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"完成！输出: {OUTPUT_CSV}")
print(f"共 {len(output_rows)} 行，SKU列 {len(sku_keys)} 个，参数列 {len(param_keys)} 个")
print(f"主图 {max_main} 张，详情图 {max_desc} 张")

# ========== 检查多余图片（移动到 imgs1） ==========
IMGS_DIR = "/Users/hong/Desktop/天猫/imgs"
IMGS1_DIR = "/Users/hong/Desktop/天猫/imgs1"
if os.path.isdir(IMGS_DIR):
    recorded = set()
    for row in rows:
        for p in row.get("img_paths", "").split(" | "):
            p = p.strip()
            if p:
                recorded.add(os.path.basename(p))
    orphan = [f for f in os.listdir(IMGS_DIR) if f not in recorded and not f.startswith(".")]
    if orphan:
        os.makedirs(IMGS1_DIR, exist_ok=True)
        moved = 0
        for fname in orphan:
            src = os.path.join(IMGS_DIR, fname)
            dst = os.path.join(IMGS1_DIR, fname)
            if os.path.exists(dst):
                # 目标已存在则加序号，避免覆盖
                stem, ext = os.path.splitext(fname)
                i = 1
                while os.path.exists(dst):
                    dst = os.path.join(IMGS1_DIR, f"{stem}_{i}{ext}")
                    i += 1
            os.rename(src, dst)
            moved += 1
        print(f"移动 {moved} 张孤儿图片到 imgs1")
        print(f"  示例: {orphan[:5]}")
    else:
        print("无多余图片")
