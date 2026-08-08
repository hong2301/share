#!/usr/bin/env python3
"""下载供应链金融相关上市公司年报（东方财富公告 API）"""
import urllib.request
import json
import os
import time

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "年报语料")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 供应链金融/数智化供应链相关上市公司
STOCKS = {
    "002183": "怡亚通",      # 供应链服务龙头
    "000001": "平安银行",    # 供应链金融业务
    "300226": "上海钢联",    # 大宗商品供应链金融
    "600036": "招商银行",    # 供应链金融
    "002415": "海康威视",    # 数字化
}

HEADERS = {"User-Agent": "Mozilla/5.0"}


def search_annual(stock_code):
    """查找 2024/2025 年报"""
    results = []
    for y, (start, end) in {
        "2024": ("2025-03-01", "2025-05-31"),
        "2025": ("2026-03-01", "2026-05-31"),
    }.items():
        url = (f"https://np-anotice-stock.eastmoney.com/api/security/ann?"
               f"sr=-1&page_size=50&page_index=1&ann_type=A&client_source=web"
               f"&stock_list={stock_code}&f_node=0&s_node=0"
               f"&begin_time={start}&end_time={end}")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read().decode('utf-8'))
            for a in data.get('data', {}).get('list', []):
                title = a.get('title', '')
                if '年度报告' in title and '摘要' not in title:
                    results.append((y, a['art_code'], title))
        except Exception as e:
            print(f"  ❌ {stock_code} {y}: {e}")
        time.sleep(0.5)
    return results


def get_pdf_url(art_code):
    url = f"https://np-cnotice-stock.eastmoney.com/api/content/ann?art_code={art_code}&client_source=web&page_index=1"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('data', {}).get('attach_url_web') or data.get('data', {}).get('attach_url')
    except Exception as e:
        print(f"  ❌ 获取PDF链接 {art_code}: {e}")
        return None


def download_pdf(url, filepath):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=60)
        with open(filepath, 'wb') as f:
            f.write(resp.read())
        size = os.path.getsize(filepath) / 1024
        print(f"  ✅ {os.path.basename(filepath)}: {size:.0f} KB")
        return True
    except Exception as e:
        print(f"  ❌ 下载失败 {url}: {e}")
        return False


for code, name in STOCKS.items():
    print(f"=== {name}({code}) ===")
    anns = search_annual(code)
    for year, art_code, title in anns:
        print(f"  找到: {title} ({year})")
        pdf_url = get_pdf_url(art_code)
        if pdf_url:
            filepath = os.path.join(OUTPUT_DIR, f"{name}_{year}年报.pdf")
            download_pdf(pdf_url, filepath)
        time.sleep(0.5)
    time.sleep(1)

print("\n完成！")
