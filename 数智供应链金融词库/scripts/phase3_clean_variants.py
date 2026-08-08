#!/usr/bin/env python3
"""阶段三：变体词清洗与校验
从语料回溯产生的变体词中，筛选有效领域术语
"""
import re
from collections import Counter

OUTPUT = "/Users/hong/Desktop/ck/数智供应链金融词库/输出"

# 读取变体词汇总
variants = Counter()
with open(f"{OUTPUT}/阶段2_变体词汇总.txt", encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) == 2:
            variants[parts[0]] = int(parts[1])

# 过滤规则
STOP_SUFFIX = [
    "股份有限公司", "有限公司", "责任公司", "集团股份", "集团有限",
    "银行股份有限公司", "供应链股份",
]

VERB_PATTERNS = [
    r'^[的是一在于把被让给以将要从向为对和与或及]',  # 以虚词开头
    r'^[进行开展加强促进推动支持建立完善落实实施引导鼓励规范发展建设服务管理提升强化确保统筹推进]',  # 以动词开头
    r'^[积极有效不断加快深化优化坚持按照根据切实健全发挥]',
]

def is_valid_term(term, freq):
    """判断是否为有效领域术语"""
    if len(term) < 4 or len(term) > 12:
        return False
    # 过滤公司全名
    for s in STOP_SUFFIX:
        if s in term:
            return False
    # 过滤截断词（以常见截断字结尾：有/及/与/和/供/管/售/通/务/货等）
    if term.endswith(('及', '与', '和', '有', '供', '管', '售', '通', '务', '货', '额', '度', '的', '为', '在', '了', '等', '中')) and len(term) < 8:
        return False
    # 过滤以单字开头且非术语的（如 度、天、关、们、级、售、通、销、本、他）
    if term[0] in '度天关们级售通销本他上届央行发准贷或近金从' and len(term) < 7:
        return False
    # 过滤含"及""和""与"连接的长短语
    if len(term) > 8 and any(c in term for c in "及和与"):
        return False
    # 过滤以虚词/动词开头
    for p in VERB_PATTERNS:
        if re.match(p, term):
            return False
    # 过滤句子片段（含多个'的'或过长）
    if term.count('的') > 1 and len(term) > 6:
        return False
    # 过滤纯数字/英文
    if not re.search(r'[\u4e00-\u9fff]', term):
        return False
    # 词频过滤
    if freq < 3 and len(term) > 7:
        return False
    return True


valid = {t: c for t, c in variants.items() if is_valid_term(t, c)}

# 排序输出
sorted_valid = sorted(valid.items(), key=lambda x: -x[1])

print(f"=== 清洗后有效变体词: {len(sorted_valid)} 个 ===\n")
with open(f"{OUTPUT}/阶段3_有效变体词.txt", 'w', encoding='utf-8') as f:
    for term, freq in sorted_valid:
        f.write(f"{term}\t{freq}\n")
        print(f"{term} ({freq})")
