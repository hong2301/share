#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并4个子文件夹的comments_out_api和project_meta_api
冲突时保留较大的文件
"""

import os
import shutil
from pathlib import Path

# 源文件夹列表
SOURCE_FOLDERS = ['0-10000', '10001-20000', '20001-30000', '30001-40000']

# 要合并的子目录
SUB_DIRS = ['comments_out_api', 'project_meta_api']

# 合并目标文件夹
MERGE_DIR = 'merged'

def get_file_size(filepath):
    """获取文件大小"""
    return os.path.getsize(filepath)

def count_files(folder_path):
    """统计文件夹中的文件数量"""
    count = 0
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            count += 1
    return count

def merge_folder(src_folder, dst_folder, sub_dir):
    """合并单个子目录"""
    src_path = os.path.join(src_folder, sub_dir)
    dst_path = os.path.join(dst_folder, sub_dir)
    
    if not os.path.exists(src_path):
        return 0, 0
    
    # 创建目标目录
    os.makedirs(dst_path, exist_ok=True)
    
    # 统计文件数量
    files = [f for f in os.listdir(src_path) if os.path.isfile(os.path.join(src_path, f))]
    total = len(files)
    copied = 0
    skipped = 0
    
    for i, filename in enumerate(files, 1):
        src_file = os.path.join(src_path, filename)
        dst_file = os.path.join(dst_path, filename)
        
        if not os.path.exists(dst_file):
            # 目标不存在，直接复制
            shutil.copy2(src_file, dst_file)
            copied += 1
        else:
            # 目标存在，比较文件大小
            src_size = get_file_size(src_file)
            dst_size = get_file_size(dst_file)
            
            if src_size > dst_size:
                # 源文件更大，覆盖
                shutil.copy2(src_file, dst_file)
                copied += 1
            else:
                skipped += 1
        
        # 显示进度
        progress = i / total * 100
        print(f"\r  进度: {i}/{total} ({progress:.1f}%) - 复制: {copied}, 跳过: {skipped}", end='', flush=True)
    
    print()  # 换行
    return copied, skipped

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    merge_path = os.path.join(base_dir, MERGE_DIR)
    
    # 创建合并目录
    os.makedirs(merge_path, exist_ok=True)
    
    print("=" * 60)
    print("开始合并文件夹")
    print("=" * 60)
    
    total_copied = 0
    total_skipped = 0
    
    for sub_dir in SUB_DIRS:
        print(f"\n{'='*60}")
        print(f"合并 {sub_dir}")
        print(f"{'='*60}")
        
        for folder in SOURCE_FOLDERS:
            src_folder = os.path.join(base_dir, folder)
            if not os.path.exists(src_folder):
                print(f"\n[跳过] {folder} 不存在")
                continue
            
            print(f"\n处理: {folder}")
            copied, skipped = merge_folder(src_folder, merge_path, sub_dir)
            total_copied += copied
            total_skipped += skipped
    
    print(f"\n{'='*60}")
    print("合并完成!")
    print(f"总复制: {total_copied} 文件")
    print(f"总跳过: {total_skipped} 文件 (保留较大版本)")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
