#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 交付2/项目数据.xlsx
- 遍历 project_meta_api 下的 json
- 除 raw 外所有字段作列
- 从 raw 提取 6 个字段(totalFundsGathered/totalBackersCount/backersCount/fundsGathered/campaignGoal/completionRate)
- statusText 转换：只取首行状态词(如 Closed/Funded/Late Pledge Ended...)
- projectStory 超长拆分：第一列≤32767字符，超出放 projectStory_续
- 实际评论采集值：按 file_id 对应 comments_<file_id>.csv 数据行数
- 评论文件名：同样按 file_id 匹配，输出 comments_<file_id>.csv 文件名

用法：cd /Users/hong/Desktop/indiegogo/交付2 && python3 生成表格.py
"""
import json
import re
import os
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

BASE = Path(__file__).resolve().parent
PROJECT_DIR = BASE / "project_meta_api"
COMMENTS_DIR = BASE / "comments_out_api"
OUTPUT_FILE = BASE / "项目数据.xlsx"


def status_text_short(status_text):
    """statusText 转换：取首行状态词，去掉后续说明文案"""
    if not status_text:
        return ""
    lines = [s.strip() for s in str(status_text).split("\n") if s.strip()]
    return lines[0] if lines else ""


def url_to_filename(url):
    if not url:
        return None
    name = re.sub(r"^https?://", "", url)
    name = re.sub(r"^[^/]+/", "", name)
    name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]", "", name)
    return name.strip("-") if name.strip("-") else None


def extract_raw_fields(raw_data):
    """从 raw 提取 6 个字段"""
    result = {}
    if not raw_data:
        return result
    stats = raw_data.get("projectState", {}).get("statistics", {})
    result["totalFundsGathered"] = stats.get("totalFundsGathered")
    result["totalBackersCount"] = stats.get("totalBackersCount")
    result["backersCount"] = stats.get("backersCount")
    result["fundsGathered"] = stats.get("fundsGathered")
    ctx = raw_data.get("projectContext", {}).get("project", {})
    result["campaignGoal"] = ctx.get("campaignGoal")
    funds = result.get("fundsGathered")
    goal = result.get("campaignGoal")
    if funds is not None and goal and goal > 0:
        result["completionRate"] = f"{(funds / goal * 100):.2f}%"
    else:
        result["completionRate"] = None
    return result


def main():
    print("开始处理...")
    project_files = sorted(PROJECT_DIR.glob("*.json"))
    print(f"共找到 {len(project_files)} 个项目文件")

    rows = []
    for f in tqdm(project_files, desc="处理项目文件"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if not data.get("url"):
                continue
            row = {}
            for key, value in data.items():
                if key == "raw":
                    continue
                if key == "statusText":  # statusText 转换：取首行
                    row[key] = status_text_short(value)
                else:
                    row[key] = value
            raw = data.get("raw", {})
            row.update(extract_raw_fields(raw))
            row["_url"] = data.get("url")
            row["实际评论采集值"] = None
            row["评论文件名"] = None
            rows.append(row)
        except Exception as e:
            print(f"错误 {f.name}: {e}")
            continue

    print(f"\n成功处理 {len(rows)} 条数据")
    df = pd.DataFrame(rows)

    # 本次采集新增字段(abstract 系列 + categories)放到最左边
    new_cols = [c for c in df.columns if c.startswith('abstract') or c == 'categories']
    if new_cols:
        other_cols = [c for c in df.columns if c not in new_cols]
        df = df[new_cols + other_cols]
        print(f"新增字段列放最左: {new_cols}")

    # projectStory 超长拆分
    print("\n拆分超长 projectStory...")
    if "projectStory" in df.columns:
        _st = df["projectStory"].fillna("")
        df["projectStory"] = _st.apply(lambda s: s[:32767] if isinstance(s, str) else s)
        df["projectStory_续"] = _st.apply(
            lambda s: s[32767:] if isinstance(s, str) and len(s) > 32767 else ""
        )

    # 评论数量：按 file_id 对应 comments_<file_id>.csv
    print("\n匹配评论数量...")
    for idx in tqdm(df.index, desc="匹配评论"):
        url = df.at[idx, "_url"]
        if url:
            fid = url_to_filename(url.strip())
            if fid:
                cf = COMMENTS_DIR / f"comments_{fid}.csv"
                if cf.exists():
                    df.at[idx, "评论文件名"] = cf.name
                    try:
                        with open(cf, "r", encoding="utf-8-sig", newline="") as fp:
                            df.at[idx, "实际评论采集值"] = max(sum(1 for _ in fp) - 1, 0)
                    except Exception:
                        pass

    df = df.drop(columns=["_url"])

    # 清理不支持的字符
    def clean_string(v):
        if isinstance(v, str):
            return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v)
        return v

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(clean_string)

    print(f"\n保存到 {OUTPUT_FILE}...")
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"完成！共 {len(df)} 行，{len(df.columns)} 列")


if __name__ == "__main__":
    main()