#!/usr/bin/env python3
"""
下载所有商品缩略图
"""

import os
import json
import requests
import time
from urllib.parse import urlparse


def download_image(url, save_path, retries=3):
    """下载图片"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://books.rakuten.co.jp/'
    }
    
    for i in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return True
        except Exception as e:
            if i < retries - 1:
                time.sleep(0.5)
    return False


def main():
    base_dir = '/Users/hong/Desktop/日本商品'
    images_dir = os.path.join(base_dir, '缩略图')
    json_file = os.path.join(base_dir, '商品数据_基础.json')
    
    # 创建图片目录
    os.makedirs(images_dir, exist_ok=True)
    
    # 加载商品数据
    with open(json_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"共 {len(products)} 个商品")
    print(f"保存到: {images_dir}\n")
    
    # 下载统计
    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, product in enumerate(products):
        product_id = product.get('id', 'unknown')
        thumbnail_url = product.get('thumbnail_url', '')
        
        if not thumbnail_url:
            failed += 1
            continue
        
        # 文件名
        filename = f"{product_id}.jpg"
        filepath = os.path.join(images_dir, filename)
        
        # 跳过已下载的
        if os.path.exists(filepath):
            skipped += 1
            continue
        
        # 下载
        print(f"[{i+1}/{len(products)}] {product.get('title', '')[:30]}...")
        
        if download_image(thumbnail_url, filepath):
            downloaded += 1
        else:
            failed += 1
        
        time.sleep(0.1)
        
        # 每100个保存进度
        if (i + 1) % 100 == 0:
            print(f"  --- 进度: 已下载 {downloaded} | 跳过 {skipped} | 失败 {failed}")
    
    print(f"\n{'=' * 50}")
    print(f"下载完成！")
    print(f"  成功: {downloaded}")
    print(f"  跳过: {skipped}")
    print(f"  失败: {failed}")
    print(f"  保存位置: {images_dir}")


if __name__ == '__main__':
    main()
