# -*- coding: utf-8 -*-
"""
把 jd_goods_detail.csv 整理为 京东.xlsx，格式对齐 淘宝整理.xlsx
列：销量排名 | 产品名称 | 已售数量 | 规格名称 | 规格到手价 | 商品链接 | 平台
- 每个规格拆为一行
- 已售数量 = 评价数量展示（如 200+ / 1万+）
- 规格到手价 = 纯数字（去掉 ¥，按规格对应）
- 销量排名按已售数量降序（同名次跳过式）
- 平台 = 京东
"""
import csv
import os
import re

from openpyxl import Workbook

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, "根据关键词查询商品", "jd_goods_detail.csv")
DST = os.path.join(BASE_DIR, "京东.xlsx")

HEADERS = ["销量排名", "产品名称", "已售数量", "规格名称", "规格到手价", "商品链接", "平台"]


def sales_display(review_text):
    """'买家评价(200+)' -> '200+'；'买家评价(1万+)' -> '1万+'"""
    if not review_text:
        return ""
    m = re.search(r"(\d[\d,，]*(?:\.\d+)?万?\+?)", review_text)
    return m.group(1) if m else ""


def sales_number(display):
    """把展示文本转成可排序的数值：'1万+' -> 10000, '200+' -> 200"""
    if not display:
        return 0
    m = re.search(r"([\d.]+)", display.replace(",", "").replace("，", ""))
    n = float(m.group(1)) if m else 0
    if "万" in display:
        n *= 10000
    return int(n)


def competition_rank(sorted_values):
    """降序销量 -> {销量值: 名次}（相同值同名次，跳过式 1,1,3）"""
    ranks = {}
    prev = None
    rank = 1
    for i, v in enumerate(sorted_values, start=1):
        if prev is None or v != prev:
            rank = i
            prev = v
        ranks.setdefault(v, rank)
    return ranks


def split_spec(seg):
    """把 '规格名:¥274.18' 拆成 (规格名, 纯数字价格)；拆不出价格则价格留空"""
    spec_name = seg
    spec_price = ""
    m = re.search(r":\s*(¥?\d+(?:\.\d+)?)\s*$", seg)
    if m:
        spec_price = clean_price(m.group(1))
        spec_name = seg[:m.start()].rstrip(":")
    elif seg.endswith(":"):
        spec_name = seg[:-1]
    return spec_name, spec_price


def clean_price(p):
    """'¥274.18' -> 274.18（数字）；无法解析则原样"""
    if not p:
        return ""
    m = re.search(r"\d+(?:\.\d+)?", p)
    if m:
        try:
            return float(m.group(0))
        except Exception:
            return m.group(0)
    return p


def prices_list(price_col):
    """价格列 '¥274.18、¥432.18' -> [274.18, 432.18]"""
    if not price_col:
        return []
    return [clean_price(x) for x in price_col.split("、")]


def main():
    if not os.path.exists(SRC):
        print("找不到源文件:", SRC)
        return

    with open(SRC, "r", encoding="utf-8-sig") as f:
        rows = [dict(r) for r in csv.DictReader(f) if r.get("sku", "").strip()]

    for r in rows:
        r["_disp"] = sales_display(r.get("好评数量", ""))
        r["_num"] = sales_number(r["_disp"])

    sales_sorted = sorted([r["_num"] for r in rows], reverse=True)
    rank_map = competition_rank(sales_sorted)

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet"
    ws.append(HEADERS)

    for r in sorted(rows, key=lambda x: x["_num"], reverse=True):
        sku = r.get("sku", "")
        spec_segs = (r.get("产品规格", "") or "").split("、")
        prices = prices_list(r.get("价格", ""))
        if spec_segs == [""]:
            spec_segs = []

        n = max(len(spec_segs), len(prices))
        if n == 0:
            n = 1

        for i in range(n):
            seg = spec_segs[i] if i < len(spec_segs) else ""
            name, p1 = split_spec(seg)
            p2 = prices[i] if i < len(prices) else ""
            price = p1 if p1 != "" else p2  # 规格内价格优先，否则用价格列

            ws.append([
                rank_map.get(r["_num"], ""),    # 销量排名
                r.get("商品名称", ""),          # 产品名称
                r["_disp"],                     # 已售数量（200+ / 1万+）
                name,                           # 规格名称
                price,                          # 规格到手价（纯数字）
                f"https://item.jd.com/{sku}.html",  # 商品链接
                "京东",                         # 平台
            ])

    wb.save(DST)
    print("已生成:", DST)
    print("共写入数据行(含规格拆分):", ws.max_row - 1)


if __name__ == "__main__":
    main()
