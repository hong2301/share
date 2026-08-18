"""
按商品链接采集京东商品详情：只采集 商品名称、产品规格(每个规格对应价格)、好评数量、价格
输入：input.csv (sku,商品链接)
输出：jd_goods_detail.csv (sku,商品名称,产品规格,好评数量,价格)
"""
import csv
import os
import random
import time
from DrissionPage import Chromium, ChromiumOptions

# ============ 变量区 ============
tabPort = 9349

# 每个商品采集完后的随机等待秒数（模拟人工，防封）
MIN_WAIT = 10
MAX_WAIT = 15

def random_wait():
    t = random.uniform(MIN_WAIT, MAX_WAIT)
    print(f"随机等待 {t:.1f} 秒...")
    time.sleep(t)

co = ChromiumOptions()
co.set_local_port(tabPort)
dp = Chromium(addr_or_opts=co)
tab1 = dp.new_tab()  # 商品详情页
# tab1.ele("@class=asdf",timeout=0.1).click()

# ============ CSV 配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "input.csv")
CSV_PATH = os.path.join(BASE_DIR, "jd_goods_detail.csv")
HEADERS = ["sku", "商品名称", "产品规格", "好评数量", "价格"]


def collect_detail(detail_tab):
    """采集：商品名称、好评数量、规格(每个规格点击后取价格，失败留空)、价格"""
    data = {}

    # ---------- 商品名称 ----------
    data["title"] = ""
    try:
        title_ele = detail_tab.ele("@class=sku-title-name", timeout=1)
        data["title"] = title_ele.text.strip()
    except Exception as e:
        print("提取商品名称失败:", e)

    # ---------- 好评数量 ----------
    data["reviews"] = ""
    try:
        reviews_ele = detail_tab.ele("@class=comment-title", timeout=1)
        data["reviews"] = reviews_ele.text.strip()
    except Exception as e:
        print("提取好评数量失败:", e)

    # ---------- 默认价格（兜底） ----------
    default_price = ""
    try:
        price_ele = detail_tab.ele("@class=product-price--main", timeout=1)
        default_price = price_ele.text.strip()
    except Exception as e:
        print("提取默认价格失败:", e)
    data["price"] = default_price

    # ---------- 规格：遍历每个规格项，click(by_js=True) 后取价格，失败留空 ----------
    data["spec"] = ""
    try:
        specBox = detail_tab.ele("@class=specification-group-content", timeout=1)
        spec_items = specBox.children()
        if spec_items:
            spec_names = []
            spec_prices = []
            for it in spec_items:
                # 规格名
                try:
                    spec_names.append(it.text.strip())
                except Exception:
                    spec_names.append("")

                # 点击规格项（优先点其可点击内容区），等待价格刷新
                try:
                    it.click(by_js=True)
                    time.sleep(0.8)  # 等待价格刷新
                    price_ele = detail_tab.ele("@class=product-price--main", timeout=1)
                    spec_prices.append(price_ele.text.strip())
                except Exception as e:
                    print("获取规格价格失败:", e)
                    spec_prices.append("")  # 失败留空

            # 每个规格带它的价格，如：规格A:¥xx、规格B:¥xx
            data["spec"] = "、".join(
                (f"{n}:{p}" if p else f"{n}:" if n else "")
                for n, p in zip(spec_names, spec_prices)
            )
            # 价格列 = 每个规格的价格（失败位置留空段）
            data["price"] = "、".join(spec_prices)
        else:
            # 无规格项：仅拼接规格文本，价格保持默认
            txt = ""
            for sc in specBox.children():
                try:
                    if sc.text:
                        txt += sc.text.strip() + "、"
                except Exception:
                    continue
            data["spec"] = txt.rstrip("、")
            data["price"] = default_price
    except Exception as e:
        print("提取规格失败:", e)
        data["price"] = default_price

    return data


def get_existing_skus(path):
    """读取已采集 CSV 中的 sku 集合"""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return {row["sku"] for row in reader if row.get("sku")}


def load_input_items(path):
    """读取 input.csv，返回 [{sku, url}]"""
    items = []
    if not os.path.exists(path):
        print("找不到 input.csv:", path)
        return items
    with open(path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sku = (row.get("sku") or "").strip()
            if not sku:
                continue
            url = (row.get("商品链接") or "").strip()
            if not url:
                url = f"https://item.jd.com/{sku}.html"
            items.append({"sku": sku, "url": url})
    return items


# ============ 主流程 ============
input_items = load_input_items(INPUT_PATH)
print("从 input.csv 载入商品数:", len(input_items))

if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=HEADERS).writeheader()

existing_skus = get_existing_skus(CSV_PATH)
print("已采集、可跳过的 sku 数:", len(existing_skus))
get_count = 0

for item in input_items:
    try:
        if item["sku"] in existing_skus:
            print("已存在，跳过:", item["sku"])
            continue

        tab1.get(item["url"])
        get_count += 1
        if get_count >= 25:
            input(f"已执行 {get_count} 次详情页请求，请按回车继续...")
            get_count = 0
        time.sleep(5)

        detail = collect_detail(tab1)

        row = {
            "sku": item["sku"],
            "商品名称": detail.get("title", ""),
            "产品规格": detail.get("spec", ""),
            "好评数量": detail.get("reviews", ""),
            "价格": detail.get("price", ""),
        }
        with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow(row)

        existing_skus.add(item["sku"])
        print("已写入:", item["sku"], detail.get("title", ""))

        random_wait()  # 每个商品采集完后随机等 10-15 秒再采集下一个
    except Exception as e:
        print("解析失败:", e)

print("全部完成，CSV 路径:", CSV_PATH)
