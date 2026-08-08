#!/usr/bin/env python3
"""阶段二：语料回溯补充（变体扩展）
以种子词为锚点，在年报语料中检索变体表达
"""
import glob
import os
import re
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from seed_word_table import SEED_WORDS

ANNUAL_DIR = os.path.join(BASE, "..", "年报文本")
OUTPUT = os.path.join(BASE, "..", "输出")
os.makedirs(OUTPUT, exist_ok=True)

# 收集所有种子词
all_seeds = []
for dim, subs in SEED_WORDS.items():
    for sub, words in subs.items():
        all_seeds.extend(words)


def load_corpus():
    """加载所有年报文本"""
    texts = []
    for f in glob.glob(os.path.join(ANNUAL_DIR, "*.txt")):
        with open(f, encoding='utf-8') as fh:
            texts.append(fh.read())
    return "\n".join(texts)


def extract_variants(corpus, seed):
    """检索种子词上下文，提取相邻词汇作为变体候选"""
    variants = Counter()
    # 找出所有种子词出现位置，提取前后文
    for m in re.finditer(re.escape(seed), corpus):
        start = max(0, m.start() - 30)
        end = min(len(corpus), m.end() + 30)
        context = corpus[start:end]
        # 提取包含种子词的词组（种子词+前后名词）
        # 模式：种子词可能被 前/后缀 扩展
        extended = re.findall(r'[\u4e00-\u9fff]{0,6}' + re.escape(seed) + r'[\u4e00-\u9fff]{0,8}', context)
        for e in extended:
            if len(e) >= 4 and len(e) <= 20:
                variants[e] += 1
    return variants


def main():
    print("加载年报语料...")
    corpus = load_corpus()
    print(f"语料长度: {len(corpus)}")

    all_variants = Counter()
    seed_stats = []

    for seed in all_seeds:
        variants = extract_variants(corpus, seed)
        if variants:
            # 去掉和种子词完全相同的
            real_variants = {k: v for k, v in variants.items() if k != seed}
            if real_variants:
                # 按频率排序，取前 20 个
                top = sorted(real_variants.items(), key=lambda x: -x[1])[:20]
                seed_stats.append((seed, top))
                for v, c in top:
                    all_variants[v] += c

    # 输出结果
    print(f"\n=== 变体扩展结果（{len(seed_stats)} 个种子词有变体） ===")
    with open(os.path.join(OUTPUT, "阶段2_语料回溯变体.txt"), 'w', encoding='utf-8') as f:
        for seed, variants in seed_stats:
            f.write(f"\n【{seed}】\n")
            for v, c in variants:
                f.write(f"  {v} ({c})\n")
                print(f"  {seed} → {v} ({c})")

    print(f"\n=== 变体词总数: {len(all_variants)} ===")
    with open(os.path.join(OUTPUT, "阶段2_变体词汇总.txt"), 'w', encoding='utf-8') as f:
        for v, c in all_variants.most_common(500):
            f.write(f"{v}\t{c}\n")


if __name__ == "__main__":
    main()
