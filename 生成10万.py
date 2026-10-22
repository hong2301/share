# -*- coding: utf-8 -*-
"""
生成 桌面/10万.xlsx : 交付2 的 109,570 条项目数据, 表头/列顺序与 20万.xlsx 完全一致。
- 主体字段来自 交付2/project_meta_api 的 JSON(同 交付2/生成表格.py 规则)
- 新增的 9 个 abstract 字段从
  "08-24十万条数据能用的前几个字段（需要和全样本匹配）.csv" 按 link 匹配补齐
- 评论文件名/实际评论采集值 按 comments_out_api 匹配
"""
import csv
import json
import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm

BASE = Path('/Users/hong/Desktop/indiegogo/交付2')
PROJECT_DIR = BASE / "project_meta_api"
COMMENTS_DIR = BASE / "comments_out_api"
CSV_PATH = '/Users/hong/Desktop/08-24十万条数据能用的前几个字段（需要和全样本匹配）.csv'
OUTPUT_FILE = Path('/Users/hong/Desktop/10万.xlsx')

# 与 20万.xlsx 完全一致的 43 列顺序
COLUMNS = [
    'abstractTitle', 'abstractCreator', 'abstractCreatorWebsiteLink', 'abstractKeyword',
    'categories', 'abstractVideoAmount', 'abstractVideoLink', 'abstractPictureAmount',
    'abstractPictureLink',
    'projectID', 'phase', 'status', 'campaignOutcome', 'campaignStart', 'campaignEnd',
    'mj', 'backers', 'wcMj', 'rewards', 'tags', 'medias', 'mediaUrls', 'updates', 'FAQ',
    'currency', 'statusText', 'rewardData', 'tagTexts', 'shortDescription', 'projectStory',
    'expected_count', 'url', 'cjStatus', 'error',
    'totalFundsGathered', 'totalBackersCount', 'backersCount', 'fundsGathered',
    'campaignGoal', 'completionRate',
    '实际评论采集值', '评论文件名', 'projectStory_续',
]


def status_text_short(status_text):
    if not status_text:
        return ""
    for line in str(status_text).split("\n"):
        line = line.strip()
        if line:
            return line
    return ""


def url_to_filename(url):
    if not url:
        return None
    name = re.sub(r"^https?://", "", url)
    name = re.sub(r"^[^/]+/", "", name)
    name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]", "", name)
    name = name.strip("-")
    return name if name else None


def extract_raw_fields(raw_data):
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


def to_int(v):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return 0


def split_list(v):
    v = (v or '').strip()
    if not v:
        return []
    return [x.strip() for x in v.split('\n') if x.strip()]


def load_csv_map():
    m = {}
    with open(CSV_PATH, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            link = (row.get('link') or '').strip()
            if not link:
                continue
            m[link] = {
                'abstractTitle': row.get('Abstract_title') or '',
                'abstractCreator': row.get('Abstract_creator') or '',
                'abstractCreatorWebsiteLink': row.get('Abstract_creator_website_link') or '',
                'abstractKeyword': row.get('Abstract_keyword') or '',
                'categories': row.get('categories') or '',
                'abstractVideoAmount': to_int(row.get('Abstract_video_amount')),
                'abstractVideoLink': split_list(row.get('Abstract_video_link')),
                'abstractPictureAmount': to_int(row.get('Abstract_picture_amount')),
                'abstractPictureLink': split_list(row.get('Abstract_picture_link')),
            }
    return m


def main():
    print("读取 CSV 匹配表...")
    csv_map = load_csv_map()
    print(f"CSV 映射条数: {len(csv_map):,}")

    print("处理 JSON...")
    rows = []
    matched = 0
    for f in tqdm(sorted(PROJECT_DIR.glob("*.json")), desc="JSON"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue
        if not d.get("url"):
            continue
        row = {}
        for key, value in d.items():
            if key == "raw":
                continue
            row[key] = status_text_short(value) if key == "statusText" else value
        row.update(extract_raw_fields(d.get("raw", {})))
        url = d.get("url")
        row["_url"] = url
        row["实际评论采集值"] = None
        row["评论文件名"] = None
        a = csv_map.get(url)
        if a:
            matched += 1
            row.update(a)
        else:
            row.update({'abstractTitle': '', 'abstractCreator': '', 'abstractCreatorWebsiteLink': '',
                        'abstractKeyword': '', 'categories': '', 'abstractVideoAmount': 0,
                        'abstractVideoLink': [], 'abstractPictureAmount': 0, 'abstractPictureLink': []})
        rows.append(row)
    print(f"成功 {len(rows):,} 行 | CSV 匹配上: {matched:,}")

    df = pd.DataFrame(rows)

    # projectStory 超长拆分
    if "projectStory" in df.columns:
        _st = df["projectStory"].fillna("")
        df["projectStory"] = _st.apply(lambda s: s[:32767] if isinstance(s, str) else s)
        df["projectStory_续"] = _st.apply(lambda s: s[32767:] if isinstance(s, str) and len(s) > 32767 else "")

    # 评论匹配
    print("匹配评论文件...")
    for idx in tqdm(df.index, desc="评论"):
        url = df.at[idx, "_url"]
        fid = url_to_filename(url.strip()) if url else None
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

    # 列顺序对齐 20万.xlsx
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS]

    # 清理非法字符
    def clean_string(v):
        if isinstance(v, str):
            return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v)
        return v
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(clean_string)

    print(f"保存到 {OUTPUT_FILE}...")
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"完成! {len(df)} 行, {len(df.columns)} 列")


if __name__ == "__main__":
    main()