# -*- coding: utf-8 -*-
"""生成 Instagram 采集交付数据模版（多 sheet Excel + 说明）。

对比基准：客户先前采集件 `_agentgirl_.xlsx`（79 行 × 57 列，IG 帖子接口扁平化）。
本模版为其超集：保留客户全部 57 列，另加推导列 + 原始 JSON 落盘路径列。

用法：
    python make_template.py
输出：
    template/IG采集-数据模版_<日期>.xlsx
    template/IG采集-数据模版说明.md
    template/示例_每帖JSON.json
"""
from __future__ import annotations

import datetime as dt
import json
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "template")
TODAY = "20261015"
WINDOW_START = "2025-10-15"
CLIENT_XLSX = r"D:\share\_agentgirl_.xlsx"

HEAD_FILL = PatternFill("solid", fgColor="4472C4")
HEAD_FONT = Font(bold=True, color="FFFFFF")
RESERVE_FILL = PatternFill("solid", fgColor="FFF2CC")   # 预留列（用户后续填写）
ADD_FILL = PatternFill("solid", fgColor="E2EFDA")       # 我方新增列
SEC_FONT = Font(bold=True, size=12)
LINK_FONT = Font(color="0563C1", underline="single")

# ---------------------------------------------------------------- 列定义
# 客户端原有 57 列（保持同名同序，便于与其历史件对齐）
CLIENT_COLS = [
    "accessibility_caption", "ad_id", "affiliate_info", "boosted_status", "caption",
    "caption_is_edited", "carousel_media_count", "clips_attribution_info", "clips_metadata",
    "coauthor_producers", "code", "comment_count", "crosspost_metadata", "display_uri",
    "explore", "facepile_top_likers", "fb_like_count", "has_audio", "headline", "id",
    "image_versions2", "inventory_source", "invited_coauthor_producers", "is_dash_eligible",
    "is_paid_partnership", "like_count", "link", "location", "media_overlay_info", "media_type",
    "number_of_qualities", "open_carousel_submission_state", "pk", "product_type", "sponsor_tags",
    "taken_at", "thumbnails", "title", "user", "usertags", "video_versions", "view_count",
    "user_id", "first_video_url", "caption_text", "audio_type", "audio_title", "artist_username",
    "audio_asset_id", "sponsor_username", "sponsor_id", "sponsor_full_name", "sponsor_pic_url",
    "owner_profile_pic_url", "tagged_usernames", "tagged_user_ids", "tagged_user_fullnames",
]

# 我方新增列（帖子明细）
POST_ADD_COLS = [
    "source_username",      # 名单里的账号（校对归属，防止串号）
    "post_url",             # https://www.instagram.com/p/<code>/
    "taken_at_utc",         # 帖子的 ISO 时间（UTC）
    "taken_at_local",       # ISO 时间（UTC+8）
    "in_window",            # 1=落在采集窗口（>=2025-10-15）, 0=窗口外
    "media_count_actual",   # 实际媒体数（轮播展开后的真实条数）
    "image_count",          # 本条帖子里的图片数（含轮播每一张）
    "image_urls",           # 【核心】图片链接数组，JSON 数组字符串
    "video_count",
    "video_urls",           # 视频链接数组，JSON 数组字符串
    "location_pk", "location_name", "location_lat", "location_lng",
    "is_video", "is_carousel",
    "collect_time",         # 采集时刻（ISO，UTC+8）
    "collect_batch",        # 批次号
    "raw_json_path",        # 该帖原始 JSON 的相对路径
    "raw_json_sha256",      # 原文校验（可证明未被改动）
]

# 账号总表追加列
ACC_ADD_COLS = [
    "采集状态",        # 待采集 / 成功 / 失败 / 私密跳过
    "近一年帖数",      # 落在窗口内的帖子数
    "已采图片数",
    "最近发帖时间",
    "数据目录",        # raw_json/<username>/
    "采集时间",
    "错误信息",
    "照片链接数组",    # 【预留】用户后续自行填照片链接数组
]

# 图片链接表：一行一图，只存链接（下载文件信息只落在每帖 JSON 里，不进此表）
IMAGE_COLS = [
    "source_username", "post_code", "post_url", "taken_at_local", "media_index",
    "image_url", "width", "height",
]

LOG_COLS = [
    "时间戳", "source_username", "阶段", "事件", "post_code", "http_status",
    "本次帖子数", "累计帖子", "累计图片", "本次下载图片数", "耗时ms", "风控标记", "备注",
]

FIELD_DOC = [
    # sheet, 字段, 中文名, 来源, 说明
    ("02_帖子明细", "code", "短码", "IG API", "帖子短码，post_url 由它拼出"),
    ("02_帖子明细", "pk / id", "帖子ID", "IG API", "pk 为数字ID；id 为 <pk>_<user_id> 复合ID"),
    ("02_帖子明细", "taken_at", "发布时间戳", "IG API", "UTC 秒级时间戳（客户件同名字段）"),
    ("02_帖子明细", "taken_at_utc", "发布时间UTC", "推导", "由 taken_at 转 ISO 8601"),
    ("02_帖子明细", "taken_at_local", "发布时间北京", "推导", "UTC+8；跨时区口径以此为准"),
    ("02_帖子明细", "in_window", "是否在窗口", "推导", f"1 = taken_at >= {WINDOW_START}（北京时区）"),
    ("02_帖子明细", "media_type", "媒体类型", "IG API", "1=图片 2=视频 8=轮播"),
    ("02_帖子明细", "product_type", "作品类型", "IG API", "feed / clips / igtv / carousel_container"),
    ("02_帖子明细", "caption / caption_text", "正文", "IG API", "caption 为原始结构体；caption_text 为纯文本"),
    ("02_帖子明细", "carousel_media_count", "轮播张数", "IG API", "仅轮播帖有值；单图/视频帖为空"),
    ("02_帖子明细", "media_count_actual", "实际媒体数", "推导", "轮播=carousel_media_count，单帖=1"),
    ("02_帖子明细", "image_urls", "图片链接数组", "推导", "【核心】JSON 数组；轮播每张一条，取每张的最大分辨率候选"),
    ("02_帖子明细", "video_urls", "视频链接数组", "推导", "JSON 数组；图片帖为空数组"),
    ("02_帖子明细", "location / location_*", "定位", "IG API", "原始结构体 + 拆出的 pk/名称/经纬度"),
    ("02_帖子明细", "usertags / tagged_*", "标记用户", "IG API", "原始结构体 + 拆出的用户名/ID/昵称"),
    ("02_帖子明细", "like_count", "点赞数", "IG API", "采集时刻快照，非最终值"),
    ("02_帖子明细", "comment_count", "评论数", "IG API", "采集时刻快照（显示值）"),
    ("02_帖子明细", "view_count", "播放量", "IG API", "视频/Reels 有值，图片帖为空"),
    ("02_帖子明细", "image_versions2 / display_uri", "图片候选URL", "IG API", "客户件形态（已扁平化），我方仅作兼容列"),
    ("02_帖子明细", "raw_json_path", "原始JSON路径", "推导", "全字段零丢失的落盘位置，每帖一个文件"),
    ("02_帖子明细", "raw_json_sha256", "原始JSON校验", "推导", "防篡改/去重"),
    ("02_帖子明细", "collect_time", "采集时间", "推导", "UTC+8，精确到秒"),
    ("01_账号总表", "username", "账号", "名单", "973 个账号，唯一"),
    ("01_账号总表", "pk / id", "账号ID", "名单", "pk 为数字ID"),
    ("01_账号总表", "follower_count", "粉丝数", "名单", "名单快照，非采集时刻实时值"),
    ("01_账号总表", "media_count", "历史帖子总数", "名单", "含全部历史，不限窗口"),
    ("01_账号总表", "is_private", "是否私密", "名单", "=True 无法公开采集，标为「私密跳过」"),
    ("01_账号总表", "采集状态", "采集状态", "我方", "待采集 / 成功 / 失败 / 私密跳过"),
    ("01_账号总表", "近一年帖数", "窗口内帖数", "我方", "落在 2025-10-15 起的帖子数"),
    ("01_账号总表", "数据目录", "数据目录", "我方", "raw_json/<username>/"),
    ("01_账号总表", "照片链接数组", "照片链接数组", "【预留】", "客户自行填写用，采集器不写入"),
    ("03_图片链接表", "media_index", "媒体序号", "推导", "轮播内顺序，从 1 开始"),
    ("03_图片链接表", "image_url", "图片链接", "IG API", "带签名，含 oe= 过期参数；此表只存链接"),
    ("03_图片链接表", "width / height", "宽/高", "IG API", "取自该帖所用候选图"),
    ("04_采集日志", "风控标记", "风控标记", "推导", "正常 / 限速 / challenge / 登录失效"),
    ("04_采集日志", "阶段", "阶段", "推导", "主页 / 翻页 / 帖子 / 图片"),
]


def load_roster() -> pd.DataFrame:
    df = pd.read_excel(os.path.join(ROOT, "instagram_usrinfo.xlsx"))
    df.columns = [c if not str(c).startswith("Unnamed") else f"col_{i}_未命名" for i, c in enumerate(df.columns)]
    return df


def sample_post_row() -> dict:
    """从客户件取一行做示例，映射到我方字段。"""
    row = pd.read_excel(CLIENT_XLSX).iloc[0].to_dict()
    ts = int(row.get("taken_at") or 0)
    code = row.get("code")
    img = row.get("display_uri") or row.get("image_versions2")
    row.update({
        "source_username": row.get("user"),
        "post_url": f"https://www.instagram.com/p/{code}/",
        "taken_at_utc": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "taken_at_local": dt.datetime.fromtimestamp(ts + 8 * 3600, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+08:00"),
        "in_window": 0 if ts < 1760544000 else 1,
        "media_count_actual": int(row.get("carousel_media_count") or 1),
        "image_count": 1,
        "image_urls": json.dumps([img] if img else [], ensure_ascii=False),
        "video_count": 1 if row.get("first_video_url") else 0,
        "video_urls": json.dumps([row["first_video_url"]], ensure_ascii=False) if row.get("first_video_url") else "[]",
        "is_video": 1 if row.get("media_type") == 2 else 0,
        "is_carousel": 1 if row.get("media_type") == 8 else 0,
        "collect_time": "2026-10-15 18:00:00",
        "collect_batch": "sample",
        "raw_json_path": f"raw_json/{row.get('user')}/{code}.json",
        "raw_json_sha256": "-",
    })
    return row


def write_sheet(wb, title, cols, rows, widths=None, mark=(), note=None):
    ws = wb.create_sheet(title)
    if note:
        ws.append([note])
        ws["A1"].font = Font(italic=True, color="808080")
    ws.append(cols)
    hr = ws.max_row
    for i, c in enumerate(cols, 1):
        cell = ws.cell(hr, i)
        cell.font = HEAD_FONT
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        if c in mark:
            cell.fill = RESERVE_FILL
            cell.font = Font(bold=True, color="833C00")
        elif c in POST_ADD_COLS or c in ACC_ADD_COLS[:7]:
            cell.fill = ADD_FILL
            cell.font = Font(bold=True, color="1F4E1F")
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    for i, c in enumerate(cols, 1):
        w = (widths or {}).get(c, 16)
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(hr + 1, 1)
    ws.auto_filter.ref = f"A{hr}:{get_column_letter(len(cols))}{ws.max_row}"
    return ws


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    roster = load_roster()

    wb = Workbook()
    wb.remove(wb.active)

    # ------------------------------------------------------------ 00_说明
    ws = wb.create_sheet("00_说明")
    info = [
        ["Instagram 采集数据交付 — 数据模版", ""],
        ["", ""],
        ["生成时间", "2026-10-15"],
        ["模版版本", "v1（待用户确认后定稿）"],
        ["采集对象", "名单内 973 个 Instagram 账号（其中 2 个私密账号无法公开采集）"],
        ["采集窗口", "近一年：2025-10-15 起（按发帖时间，北京时区 UTC+8）"],
        ["对比基准", "客户先前采集件 _agentgirl_.xlsx（79 行 × 57 列）"],
        ["本模版定位", "客户件的超集：保留其全部 57 列并同名同序，另加推导列 + 原始 JSON 路径列"],
        ["", ""],
        ["【sheet 一览】", ""],
        ["01_账号总表", "973 行，一行一账号；名单 82 列 + 采集状态/近一年帖数 + 预留「照片链接数组」"],
        ["02_帖子明细", "一行一帖（含轮播帖）；客户 57 列 + 22 列新增（含核心 image_urls）"],
        ["03_图片链接表", "一行一图（轮播展开），只存链接；与帖子、账号表分离"],
        ["04_采集日志", "实时追加；每抓一条记一行，含风控标记与下载计数"],
        ["05_字段说明", "全字段字典：字段 → 中文名 → 来源 → 说明"],
        ["", ""],
        ["【数据分层】", ""],
        ["唯一数据源", "JSON。Excel 只是派生视图，布局可随时灵活调整，不承载过程状态"],
        ["账号级", "01_账号总表（含预留「照片链接数组」列，供客户后续填写）"],
        ["帖子级", "02_帖子明细（一行一帖）+ raw_json/<username>/*.json（全字段零裁剪）"],
        ["图片级", "03_图片链接表（只存链接）；图片文件下载信息不进此表"],
        ["", ""],
        ["【实时落盘口径】", ""],
        ["落盘时机", "每获取到一条帖子数据即写一个 JSON 文件（不等批次结束），满足「实时记录」要求"],
        ["目录结构", "raw_json/<username>/<taken_at>_<code>.json"],
        ["原子写入", "先写 .tmp 再 os.replace，避免中断产生半截文件"],
        ["边记录边下载", "图片下载与元数据同步进行；文件落 images/<username>/<code>_<i>.jpg，下载路径/大小/校验写在每帖 JSON 的 images[] 里"],
        ["日志", "_collect_log.jsonl（每行一条，追加式）+ 04_采集日志 sheet"],
        ["汇总层", "Excel 可随时由 raw_json 全量重建，不依赖过程状态"],
        ["", ""],
        ["【颜色约定】", ""],
        ["黄色表头", "预留列，采集器不写入，留给客户自行填写"],
        ["绿色表头", "我方相对客户件新增的列"],
        ["", ""],
        ["【已确认】", ""],
        ["数据源", "先存 JSON，后续灵活整理为 xlsx"],
        ["照片链接数组", "账号级；放在 01_账号总表 最后一列（预留，采集器不写入）"],
        ["表分离", "账号表 / 帖子表 / 图片链接表 各自独立"],
        ["图片链接表", "只存链接；正式采集时一边记录一边下载，下载信息只进 JSON"],
    ]
    for r in info:
        ws.append(r)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 100
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and (c.value.startswith("【") or c.value.startswith("Instagram")):
                c.font = SEC_FONT
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    # ------------------------------------------------------- 01_账号总表
    acc_cols = list(roster.columns) + ACC_ADD_COLS
    rows = roster.to_dict("records")
    for r in rows:
        r["采集状态"] = "私密跳过" if r.get("is_private") is True else "待采集"
        r["数据目录"] = f"raw_json/{r.get('username')}/"
    write_sheet(wb, "01_账号总表", acc_cols, rows,
                widths={"biography": 40, "full_name": 22, "profile_pic_url": 30,
                        "hd_profile_pic_url_info_url": 30, "数据目录": 34, "错误信息": 30,
                        "照片链接数组": 34, "username": 20, "category": 18, "采集状态": 12},
                mark=("照片链接数组",),
                note="一行一账号；973 行名单已填好。黄色表头＝预留列（账号级照片链接数组，客户自行填写），绿色表头＝我方新增列。")

    # ------------------------------------------------------- 02_帖子明细
    post_cols = CLIENT_COLS + POST_ADD_COLS
    write_sheet(wb, "02_帖子明细", post_cols, [sample_post_row()],
                widths={"caption": 45, "caption_text": 45, "image_urls": 50, "video_urls": 40,
                        "clips_metadata": 30, "usertags": 30, "location": 24, "image_versions2": 30,
                        "display_uri": 30, "raw_json_path": 40, "post_url": 38, "owner_profile_pic_url": 26},
                note="一行一帖（含轮播帖，轮播在 03_图片链接表 逐张展开）。下方 1 行为示例行，正式采集时替换。绿色表头＝我方新增列。")

    # ------------------------------------------------------- 03_图片链接表
    write_sheet(wb, "03_图片链接表", IMAGE_COLS,
                [{"source_username": "_agentgirl_", "post_code": "DNaCw0ruhDl",
                  "post_url": "https://www.instagram.com/p/DNaCw0ruhDl/",
                  "taken_at_local": "2025-08-16 15:07:13+08:00", "media_index": 1,
                  "image_url": "https://scontent-xxx.cdninstagram.com/v/t51.2885-15/xxx_n.jpg?...&oe=68F1A2B3",
                  "width": 1080, "height": 1350}],
                widths={"image_url": 60, "post_url": 38, "source_username": 20, "post_code": 16},
                note="一行一图（轮播逐张展开），只存链接。示例行仅示意格式。图片文件落盘信息在每帖 JSON 的 images[] 里，不在此表。")

    # ------------------------------------------------------- 04_采集日志
    write_sheet(wb, "04_采集日志", LOG_COLS,
                [{"时间戳": "2026-10-15 18:00:00", "source_username": "cristiano", "阶段": "帖子",
                  "事件": "写入JSON", "post_code": "ABC123", "http_status": 200,
                  "本次帖子数": 12, "累计帖子": 120, "累计图片": 168, "本次下载图片数": 168, "耗时ms": 1830,
                  "风控标记": "正常", "备注": "示例行"}],
                widths={"时间戳": 20, "source_username": 20, "事件": 26, "备注": 40, "风控标记": 14},
                note="实时追加。每抓一条记一行，用于断点续跑、风控举证与速率核算。")

    # ------------------------------------------------------- 05_字段说明
    write_sheet(wb, "05_字段说明", ["sheet", "字段", "中文名", "来源", "说明"],
                [{"sheet": a, "字段": b, "中文名": c, "来源": d, "说明": e} for a, b, c, d, e in FIELD_DOC],
                widths={"sheet": 16, "字段": 30, "中文名": 18, "来源": 10, "说明": 70},
                note="字段字典；「来源」= IG API 原始 / 名单 / 推导 / 我方新增。")

    path = os.path.join(OUT, f"IG采集-数据模版_{TODAY}.xlsx")
    wb.save(path)
    print("->", path)
    print("sheets:", wb.sheetnames)
    print("帖子明细列数:", len(post_cols), "（客户 57 + 新增", len(POST_ADD_COLS), "）")
    print("账号总表列数:", len(acc_cols), "=", len(roster.columns), "+", len(ACC_ADD_COLS))


if __name__ == "__main__":
    main()
