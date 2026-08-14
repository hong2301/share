#!/usr/bin/env python3
"""
遍历 products.csv 文件，并访问每个商品链接
"""
import csv
import os
import time
import re
import requests
from DrissionPage import Chromium, ChromiumOptions

CSV_FILE = '/Users/hong/Desktop/日本商品2/采集数据/products.csv'
DATA_FILE = '/Users/hong/Desktop/日本商品2/采集数据/data.csv'
IMAGES_DIR = '/Users/hong/Desktop/日本商品2/采集数据/images'
os.makedirs(IMAGES_DIR, exist_ok=True)

# 浏览器端口
tabPort = 5564
co = ChromiumOptions()
co.set_local_port(tabPort)
dp = Chromium(addr_or_opts=co)
tab = dp.get_tab()
# tab.ele("@class=asdf",timeout=0.1).click()

def init_data_csv():
    """初始化data.csv，不存在则创建表头"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['商品URL', '商品ID', '层级', '名称', '价格', '红色标注', '描述', '图片链接', '图片路径'])

def write_data(row_data):
    """追加写入data.csv"""
    with open(DATA_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(row_data)

init_data_csv()

# 读取data.csv中已处理过的商品ID，用于跳过已处理商品
done_ids=set()
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        for drow in reader:
            if len(drow) >= 2 and drow[1]:
                done_ids.add(drow[1])
print(f"已处理 {len(done_ids)} 个商品")

with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    next(reader)  # 跳过表头
    rows = list(reader)

print(f"共 {len(rows)} 条数据")

for i, row in enumerate(rows):
    url = row[1]
    print(f"\n[{i+1}/{len(rows)}]")
    try:
        # 提取商品ID
        pid_match = re.search(r'pid=(\d+)', url)
        pid = pid_match.group(1) if pid_match else str(i+1)

        # 已在data.csv中处理过则跳过
        if pid in done_ids:
            print(f"  {pid} 已处理，跳过")
            continue

        tab.get(url)

        cjText=''
        productName=''
        price=''
        ptValue=''
        msText=''

        # 层级
        cjEles=tab.eles("@class=pankuzu_lists inline container",timeout=1)
        for cjEleItem in cjEles:
            # 去除换行符后拼接
            cjText+=cjEleItem.text.replace('\n','').replace('\r','')+'\n'
        print(cjText)

        # 名称
        nameEle=tab.ele("@class=product_name",timeout=1)
        if nameEle:
            productName=nameEle.text
        print(productName)

        priceEle=tab.ele("@class=product_price_area",timeout=1)
        if priceEle:
            price=priceEle.text
        print(price)

        spans=tab.eles("@tag()=span",timeout=1)
        for spanItem in spans:
            if 'color : #ff0000;' == spanItem.attr('style'):
                ptValue=spanItem.text
                break
        print(ptValue)

        msEle=tab.ele("@class=product_explain",timeout=1)
        if msEle:
            msText=msEle.text
        print(msText)

        # 图片：保存链接 + 下载主图
        imgLinks=[]
        imgPaths=[]
        imgBox=tab.ele("@class=product_img_thumb",timeout=1)
        if imgBox:
            imgs=imgBox.eles("@tag()=img",timeout=1)
            for n, imgItem in enumerate(imgs):
                imgUrl=imgItem.attr('src')
                if imgUrl:
                    imgLinks.append(imgUrl)
                    # 主图命名格式：商品id_M_序号.jpg
                    filename=f"{pid}_M_{n}.jpg"
                    filepath=os.path.join(IMAGES_DIR, filename)
                    try:
                        resp=requests.get(imgUrl, timeout=30)
                        resp.raise_for_status()
                        with open(filepath,'wb') as f:
                            f.write(resp.content)
                        imgPaths.append(filepath)
                        print(f"  图片已保存: {filename}")
                    except Exception as e:
                        print(f"  图片下载失败: {e}")
            print(f"  图片链接数: {len(imgLinks)}")

        # 即刻写入data.csv（所有数据完整才写入）
        imgLinksText='|'.join(imgLinks)
        imgPathsText='|'.join(imgPaths)
        if cjText and productName and price and ptValue and msText and imgLinks and imgPaths:
            write_data([url, pid, cjText, productName, price, ptValue, msText, imgLinksText, imgPathsText])
            done_ids.add(pid)  # 写入后标记为已处理
            print(f"  已写入data.csv")
        else:
            print(f"  数据不完整，跳过写入（缺少: {[k for k,v in {'层级':cjText,'名称':productName,'价格':price,'红色标注':ptValue,'描述':msText,'图片链接':imgLinks,'图片路径':imgPaths}.items() if not v]}）")

        time.sleep(1)
    except Exception as e:
        pass
