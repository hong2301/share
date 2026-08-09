#!/usr/bin/env python3
"""
补充抓取商品详情页信息
"""

import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup


def get_page(url, retries=3):
    """获取页面内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
    }
    
    for i in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if i < retries - 1:
                time.sleep(1)
    return None


def parse_product_page(html):
    """解析商品详情页面"""
    soup = BeautifulSoup(html, 'html.parser')
    details = {}
    
    # 商品情报
    categories = soup.find_all('span', class_='category')
    for cat in categories:
        key = cat.text.strip()
        parent = cat.find_parent()
        if parent:
            value_span = parent.find('span', class_='categoryValue')
            if value_span:
                value = value_span.text.strip()
                
                if '発売日' in key:
                    details['detail_release_date'] = value
                elif '販売元' in key:
                    details['seller'] = value
                elif '対応機種' in key:
                    details['device'] = value
                elif 'JAN' in key:
                    details['detail_jan'] = value
    
    # 商品说明
    h2 = soup.find('h2', string=re.compile('商品説明'))
    if h2:
        next_elem = h2.find_next_sibling()
        while next_elem and next_elem.name not in ['h2', 'h3']:
            if next_elem.name in ['div', 'p']:
                text = next_elem.get_text(strip=True)
                if text:
                    details['description'] = text[:1500]
                    break
            next_elem = next_elem.find_next_sibling()
    
    # 提取ラインナップ
    desc = details.get('description', '')
    lineup_matches = re.findall(r'(\d+)\.\s*([^\d\n]+)', desc)
    if lineup_matches:
        details['lineup'] = [f"{num}.{name.strip()}" for num, name in lineup_matches]
    
    # 详情页图片URL
    detail_images = []
    product_imgs = soup.find_all('img', src=lambda x: x and ('shop.r10s.jp/book/cabinet' in str(x) or 'tshop.r10s.jp/book/cabinet' in str(x)) if x else False)
    for img in product_imgs:
        src = img.get('src', '')
        if src and src not in detail_images:
            if src.startswith('//'):
                src = 'https:' + src
            src = src.split('?')[0]
            detail_images.append(src)
    details['detail_images'] = detail_images
    
    return details


def main():
    base_dir = '/Users/hong/Desktop/日本商品'
    json_file = os.path.join(base_dir, '商品数据_基础.json')
    output_file = os.path.join(base_dir, '商品数据_完整.json')
    
    # 加载基础数据
    with open(json_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"加载了 {len(products)} 个商品")
    
    # 检查是否已有完整数据
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            completed = json.load(f)
        completed_ids = {p.get('id') for p in completed}
        print(f"已有 {len(completed)} 个完成的商品")
    else:
        completed = []
        completed_ids = set()
    
    # 处理每个商品
    total = len(products)
    for i, product in enumerate(products):
        product_id = product.get('id')
        
        # 跳过已完成的
        if product_id in completed_ids:
            continue
        
        print(f"[{i+1}/{total}] {product.get('title', '')[:40]}...")
        
        # 获取详情页
        url = product.get('url')
        if url:
            time.sleep(0.2)
            html = get_page(url)
            if html:
                details = parse_product_page(html)
                product.update(details)
        
        completed.append(product)
        completed_ids.add(product_id)
        
        # 每50个商品保存一次
        if len(completed) % 50 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(completed, f, ensure_ascii=False, separators=(',', ':'))
            print(f"  已保存 {len(completed)} 个商品")
    
    # 最终保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(completed, f, ensure_ascii=False, separators=(',', ':'))
    
    print(f"\n完成！共 {len(completed)} 个商品")
    print(f"保存到: {output_file}")


if __name__ == '__main__':
    main()
