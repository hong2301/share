import csv
import json
import os
import re
import time
import requests
from DrissionPage import Chromium, ChromiumOptions

# ========== items.csv 统一状态+数据管理 ==========
ITEMS_CSV = "items.csv"
COLUMNS = ["title", "url", "shop_url", "status",
           "shop_name", "item_url", "item_id", "sku",
           "origin_price", "params", "img_urls", "img_paths"]

IMGS_DIR = "imgs"


def read_items():
    """读取 items.csv，返回列表 [{...}, ...]"""
    if not os.path.exists(ITEMS_CSV):
        return []
    with open(ITEMS_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_items(rows):
    """全量覆写 items.csv"""
    with open(ITEMS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def check_or_skip(title, url):
    """
    查 title+url 是否存在：
    - 不存在 → 新增 pending 行，返回 "new"
    - 存在 & status=pending/error → 返回 "retry"
    - 存在 & status=done → 返回 "skip"
    """
    rows = read_items()
    for row in rows:
        if row["title"] == title and row["url"] == url:
            return "retry" if row["status"] in ("pending", "error") else "skip"
    # 新建 pending 行
    rows.append({c: "" for c in COLUMNS})
    rows[-1]["title"] = title
    rows[-1]["url"] = url
    rows[-1]["status"] = "pending"
    write_items(rows)
    return "new"


def save_item(title, url, shop_url, data, status):
    """更新指定行的全部数据字段 + status"""
    rows = read_items()
    for row in rows:
        if row["title"] == title and row["url"] == url:
            row["shop_url"] = shop_url
            row["status"] = status
            for k in ("shop_name", "item_url", "item_id", "sku", "origin_price", "img_urls", "img_paths"):
                row[k] = data.get(k, "")
            row["params"] = json.dumps(data.get("params", {}), ensure_ascii=False)
            break
    write_items(rows)


def check_data_complete(data):
    """检查关键字段是否都非空，返回 (完整, 缺失字段列表)"""
    required = ["shop_name", "item_url", "item_id", "title", "sku", "origin_price", "img_urls", "img_paths"]
    empty = [k for k in required if not data.get(k)]
    if not data.get("params"):
        empty.append("params")
    return len(empty) == 0, empty


# ========== 图片下载 ==========
def getBigImg(tab, item_id, index, img_type="M", img_url=None):
    """下载图片到 imgs/{item_id}_{M|D}_{index:02d}.jpg，返回 (url, 本地路径)。
    img_url 为 None 时从 mainPic 元素获取，否则直接用传入的 URL。"""
    try:
        if img_url is None:
            img_ele = tab.ele("@@tag()=img@@class=mainPic--zxTtQs0P", timeout=1)
            if not img_ele:
                return "", ""
            img_url = img_ele.link

        if not img_url:
            return "", ""

        img_url = re.sub(r'_\d+x\d+.*?(\..+?)$', r'\1', img_url)
        img_url = re.sub(r'\.jpg_.*', '.jpg', img_url)

        os.makedirs(IMGS_DIR, exist_ok=True)
        filename = f"{item_id}_{img_type}_{index:02d}.jpg"
        filepath = os.path.join(IMGS_DIR, filename)

        ok = False
        try:
            tab.download(img_url, IMGS_DIR, filename)
            ok = True
        except:
            pass
        if not ok:
            try:
                resp = requests.get(img_url, headers={
                    "Referer": "https://detail.tmall.com/",
                    "User-Agent": "Mozilla/5.0"
                }, timeout=30)
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                ok = True
            except:
                pass

        if not ok:
            return img_url, ""
        return img_url, f"{IMGS_DIR}/{filename}"
    except Exception as e:
        print(f"getBigImg 错误: {e}")
        return "", ""

def getPrice(tab):
    try:
        priceEle = tab.ele("@@class=leftWrap--IJTfJ3mp", timeout=1)
        if not priceEle:
            priceEle = tab.ele("@@class=priceWrap--R3TrPIS6", timeout=1)
        if not priceEle:
            priceEle = tab.ele("@@class=block2--MLcO9YdF", timeout=1)
        if priceEle:
            return priceEle.text
    except Exception as e:
        print('getPrice',e)
    return 0

# ========== 工具函数 ==========
def is_product_page(url):
    return "detail.tmall.com/item.htm" in url or "item.taobao.com/item.htm" in url


def extract_item_id(url):
    m = re.search(r'[?&]id=(\d+)', url)
    return m.group(1) if m else None


# ========== 详情页数据采集 ==========
def getData(tab):
    data = {
        "shop_name": "",
        "item_url": "",
        "item_id": "",
        "title": "",
        "sku": "",
        "origin_price": "",
        "params": {},
        "img_urls": "",
        "img_paths": "",
    }
    try:
        shopNameEle = tab.ele("@class=shopName--cSjM9uKk f-els-1", timeout=1)
        if shopNameEle:
            data["shop_name"] = shopNameEle.text

        item_id = extract_item_id(tab.url) or ""
        data["item_url"] = f"https://detail.tmall.com/item.htm?id={item_id}" if item_id else tab.url
        data["item_id"] = item_id

        titleEle = tab.ele("@class=mainTitle--R75fTcZL", timeout=1)
        if titleEle:
            data["title"] = titleEle.text

        # sku 选择 + 价格（笛卡尔积遍历所有组合）
        import itertools

        all_combos = []

        # 第一步：收集所有 SKU 维度
        skuEles = tab.eles("@class=skuItem--Z2AJB9Ew ", timeout=1)
        sku_meta = []  # [{name, count}]
        for skuEle in skuEles:
            skuName = ""
            nameEle = skuEle.ele("@class=ItemLabel--psS1SOyC", timeout=1)
            if nameEle:
                skuName = nameEle.text
            if skuName in ("数量", ""):
                continue
            valEles = skuEle.eles("@class=valueItemText--T7YrR8tO f-els-1", timeout=1)
            sku_meta.append({"name": skuName, "count": len(valEles)})

        # 第二步：生成所有索引组合（笛卡尔积）
        if sku_meta:
            idx_ranges = [range(m["count"]) for m in sku_meta]
            index_combos = list(itertools.product(*idx_ranges))
        else:
            index_combos = [()]

        # 第三步：逐个组合点击并采集
        for indices in index_combos:
            skuEles = tab.eles("@class=skuItem--Z2AJB9Ew ", timeout=1)
            sku_dict = {}
            for si, skuEle in enumerate(skuEles):
                skuName = ""
                skuNameEle = skuEle.ele("@class=ItemLabel--psS1SOyC", timeout=1)
                if skuNameEle:
                    skuName = skuNameEle.text
                if skuName in ("数量", ""):
                    continue

                all_values = []
                selected_text = ""
                skuValueELes = skuEle.eles("@class=valueItemText--T7YrR8tO f-els-1", timeout=1)
                target_index = indices[si] if si < len(indices) else 0

                for vi, skuValueELe in enumerate(skuValueELes):
                    text = skuValueELe.text
                    all_values.append(text)
                    parent = skuValueELe.parent()
                    is_selected = parent and "isSelected" in (parent.attr("class") or "")
                    is_disabled = parent and "disabled" in (parent.attr("class") or "").lower()

                    if not is_disabled and vi == target_index:
                        if is_selected:
                            selected_text = text
                        else:
                            skuValueELe.click()
                            time.sleep(1)
                            selected_text = text
                        break

                sku_dict[skuName] = {"values": all_values, "selected": selected_text}

            combo = " | ".join(f"{k}={v['selected']}" for k, v in sku_dict.items())
            price = getPrice(tab)
            print(f"  组合: {combo} | 价格: {price}")
            sku_dict["_combo_price"] = f"{combo} | {price}"
            all_combos.append(sku_dict.copy())

        # 多级存储
        sku_data = {"combos": all_combos} if all_combos else {}
        data["sku"] = json.dumps(sku_data, ensure_ascii=False)
        data["origin_price"] = " || ".join(c["_combo_price"] for c in all_combos)

        # 主图
        img_urls = []
        img_paths = []
        imgBox = tab.ele("@class=thumbnails--v976to2t", timeout=1)
        if imgBox:
            imgEles = imgBox.children()
            for imgIndex, imgEle in enumerate(imgEles):
                try:
                    imgEle.click(by_js=True)
                except:
                    thumb_url = imgEle.link or ""
                    img_urls.append(thumb_url)
                    img_paths.append("")
                    continue
                time.sleep(0.5)
                url, path = getBigImg(tab, item_id, imgIndex, "M")
                if url:
                    img_urls.append(url)
                if path:
                    img_paths.append(path)

        # 详情图
        xqImgs = tab.eles("@class=descV8-singleImage-image lazyload", timeout=1)
        for di, xqImgItem in enumerate(xqImgs):
            try:
                xqImgItem.scroll.to_see()
            except Exception as e:
                pass
            time.sleep(0.5)

            
            xq_url = xqImgItem.link
            if xq_url:
                url, path = getBigImg(tab, item_id, di, "D", img_url=xq_url)
                if url:
                    img_urls.append(url)
                if path:
                    img_paths.append(path)
        data["img_urls"] = " | ".join(img_urls)
        data["img_paths"] = " | ".join(img_paths)

        # 大参数 (Title=value, SubTitle=key)
        bigParamEles = tab.eles("@@class=emphasisParamsInfoItem--H5Qt3iog  emphasisParamsInfoItem2or4--TswMCmzk ", timeout=1)
        for item in bigParamEles:
            val_ele = item.ele("@@class=emphasisParamsInfoItemTitle--IGClES8z", timeout=0)
            key_ele = item.ele("@@class=emphasisParamsInfoItemSubTitle--Lzwb8yjJ", timeout=0)
            if key_ele and val_ele:
                data["params"][key_ele.text.strip()] = val_ele.text.strip()

        # 小参数 (Title=key, SubTitle=value)
        smallParamEles = tab.eles("@@class=generalParamsInfoItem--qLqLDVWp", timeout=1)
        for item in smallParamEles:
            key_ele = item.ele("@@class=generalParamsInfoItemTitle--Fo9kKj5Z", timeout=0)
            val_ele = item.ele("@@class=generalParamsInfoItemSubTitle--S4pgp6b9", timeout=0)
            if key_ele and val_ele:
                data["params"][key_ele.text.strip()] = val_ele.text.strip()
    except Exception as e:
        print("getData错误", e)
    return data


# ========== 商品入口 ==========
def getSpData(title, current_url, ele):
    try:
        try:
            ele.scroll.to_see()
        except Exception as e:
            pass
        ele.click()
        tab = dp.get_tab()
        nowUrl = tab.url

        if is_product_page(nowUrl):
            item_id = extract_item_id(nowUrl)
            print(f"进入商品详情页，item_id={item_id}")

            data = getData(tab)
            print(json.dumps(data, ensure_ascii=False, indent=2))

            complete, empty_fields = check_data_complete(data)
            if complete:
                save_item(title, current_url, current_url, data, "done")
                print(f"✅ {item_id} 数据完整，已写入")
            else:
                save_item(title, current_url, current_url, data, "error")
                print(f"❌ {item_id} 字段缺失: {empty_fields}")
                # 保存详情页 HTML 供人工排查
                os.makedirs("htmls", exist_ok=True)
                html_path = f"htmls/{item_id}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(tab.html)
                print(f"  详情页 HTML 已保存: {html_path}")
                input("人工查看，按回车继续...")
        else:
            raise Exception(f"未进入商品详情页，当前 URL: {nowUrl}")
    except Exception as e:
        print(f"getSpData 出错: {e}")
    tab.close()


# ========== 可配置项 ==========
import random
DELAY_MIN = 5        # 每个商品之间最小等待秒数
DELAY_MAX = 10       # 每个商品之间最大等待秒数
PAUSE_EVERY = 100     # 每采集多少个后暂停等人工确认

# ========== 主流程 ==========
tabPort = 4519
co = ChromiumOptions()
co.set_local_port(tabPort)
dp = Chromium(addr_or_opts=co)
tab = dp.get_tab()
# tab.ele("@class=sadf",timeout=0.1).click()

# data = getData(tab)
# print(json.dumps(data, ensure_ascii=False, indent=2))
# input()

spEles = tab.eles("@class=cardContainer--CwazTl0O", timeout=1)
count = 0
for spEleItem in spEles:
    try:
        title = ""
        titleEle = spEleItem.ele("@class=title--GExDBPUi", timeout=1)
        if titleEle:
            title = titleEle.text

        current_url = tab.url
        action = check_or_skip(title, current_url)

        if action == "skip":
            print(f"跳过（已完成）: {title}")
            continue
        elif action == "retry":
            print(f"重试（之前 pending/error）: {title}")
        else:
            print(f"新增（pending）: {title}")

        getSpData(title, current_url, spEleItem)

        count += 1
        if count % PAUSE_EVERY == 0:
            input(f"已采集 {count} 个，按回车继续...")

        delay = random.randint(DELAY_MIN, DELAY_MAX)
        print(f"等待 {delay} 秒...")
        time.sleep(delay)

    except Exception as e:
        print("商品循环", e)
        input("!")
