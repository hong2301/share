#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 运行包/评论数对照表.xlsx
- 遍历 project_meta_api 全部 208,200 个 JSON(不依赖 links.csv)
- expected：json 的 expected_count（应有评论数）
- actual：对应 comments_<fid>.csv 的数据行数（实际评论数）
- 差异 = expected - actual
- 评论文件名：comments_<fid>.csv 的文件名（无则空）

输出列：link, cjStatus, 应有评论数(expected), 实际评论数(actual), 差异(应有-实际), 评论文件名
"""
import json
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROJECT_DIR = BASE / "project_meta_api"
COMMENTS_DIR = BASE / "comments_out_api"
OUTPUT_FILE = BASE / "评论数对照表.xlsx"


def url_to_filename(url):
    if not url:
        return None
    name = re.sub(r"^https?://", "", url)
    name = re.sub(r"^[^/]+/", "", name)
    name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]", "", name)
    return name.strip("-") if name.strip("-") else None


def count_rows(path):
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except Exception:
        return 0


def main():
    files = sorted(PROJECT_DIR.glob("*.json"))
    print(f"JSON 共 {len(files)} 个")

    rows = []
    for i, f in enumerate(files):
        if i and i % 20000 == 0:
            print(f"  ... 已处理 {i}", flush=True)
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue
        link = d.get("url") or ""
        exp = d.get("expected_count")
        cj = d.get("cjStatus") or ""
        fid = url_to_filename(link)
        cfile = None
        act = 0
        if fid:
            cf = COMMENTS_DIR / f"comments_{fid}.csv"
            if cf.exists():
                cfile = cf.name
                act = count_rows(cf)
        diff = "" if exp is None else int(exp) - act
        rows.append([link, cj, "" if exp is None else int(exp), act, diff, cfile or ""])

    print(f"整理完成, {len(rows)} 行, 写入 xlsx...")
    try:
        import pandas as pd
        df = pd.DataFrame(rows, columns=[
            "link", "cjStatus", "应有评论数(expected)", "实际评论数(actual)",
            "差异(应有-实际)", "评论文件名",
        ])
        df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    except Exception:
        # pandas/openpyxl 不可用时退化为 csv(仍含文件名列)
        import csv
        with open(str(OUTPUT_FILE).replace('.xlsx', '.csv'), "w", encoding="utf-8-sig", newline="") as fo:
            w = csv.writer(fo)
            w.writerow(["link", "cjStatus", "应有评论数(expected)", "实际评论数(actual)",
                        "差异(应有-实际)", "评论文件名"])
            w.writerows(rows)
    print(f"已保存: {OUTPUT_FILE} | {len(rows)} 行")


if __name__ == "__main__":
    main()