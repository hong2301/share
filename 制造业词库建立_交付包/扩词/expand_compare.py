# -*- coding: utf-8 -*-
"""
扩词实验：Word2Vec vs BERT
- 语料：第二次输出中文语料（4份政策 + 9篇文献，18.7万字符）
- 种子词：词典.xlsx 的 47 个词
- 方法1：Word2Vec (Skip-gram, 从头训练)
- 方法2：BERT (bert-base-chinese 预训练模型，contextual embedding)
"""
import os, json, re, sys
import jieba
import numpy as np

BASE = r'C:\Users\Administrator\Desktop\ck\制造业词库建立'
CORPUS = os.path.join(BASE, '第二次输出', '语料_中文全量.txt')
DICT_XLSX = os.path.join(BASE, '第三次输出', '词典.xlsx')

# ---------- 1. 读取种子词 ----------
import openpyxl
wb = openpyxl.load_workbook(DICT_XLSX, data_only=True)
ws = wb.active
seeds = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[2]:
        for w in str(row[2]).replace('，', ',').replace('、', ',').split(','):
            w = w.strip()
            if w and w not in seeds:
                seeds.append(w)
print('种子词:', len(seeds))

# ---------- 2. 读取语料 ----------
with open(CORPUS, encoding='utf-8') as f:
    corpus = f.read()
print('语料字符数:', len(corpus))

# ---------- 3. jieba 分词（种子词加入自定义词典防切散） ----------
for s in seeds:
    jieba.add_word(s)
# 语料按句切分
sentences_raw = re.split(r'[。！？；\n]', corpus)
sentences_raw = [s.strip() for s in sentences_raw if len(s.strip()) >= 5]

# 分词结果（tokenized sentences）
tokenized = [list(jieba.cut(s)) for s in sentences_raw]
print('句子数:', len(tokenized))
print('示例:', tokenized[0][:30])

# 全量词表与词频
from collections import Counter
vocab_counter = Counter()
for toks in tokenized:
    vocab_counter.update(toks)
# 过滤：纯符号/纯数字/单字（保留二字以上中文词）
candidate_words = []
for w, c in vocab_counter.items():
    if re.fullmatch(r'[\u4e00-\u9fff]{2,}', w) and c >= 2:
        candidate_words.append(w)
print('候选词(≥2字, 频次≥2):', len(candidate_words))

# ---------- 4. Word2Vec 训练 ----------
from gensim.models import Word2Vec
w2v = Word2Vec(tokenized, vector_size=100, window=5, min_count=1,
               sg=1, epochs=30, workers=1, seed=42)
print('Word2Vec 词表:', len(w2v.wv))

def w2v_expand(seed, topk=10):
    if seed not in w2v.wv:
        return []
    sims = w2v.wv.most_similar(seed, topn=topk)
    return [(w, round(float(s), 4)) for w, s in sims]

# ---------- 5. BERT 词向量 ----------
print('加载 BERT (bert-base-chinese)...')
from transformers import AutoTokenizer, AutoModel
import torch
tok = AutoTokenizer.from_pretrained('bert-base-chinese')
model = AutoModel.from_pretrained('bert-base-chinese')
model.eval()

def get_bert_embeddings(sentences_batch, max_len=64):
    enc = tok(sentences_batch, padding=True, truncation=True,
              max_length=max_len, return_tensors='pt')
    with torch.no_grad():
        out = model(**enc)
    return enc, out.last_hidden_state

# 对每个句子：jieba 分词得到词列表，BERT 得到 char token embeddings，
# 词向量 = 其覆盖的 char token embedding 的均值（BERT 中文为字级）
word_embs = {}
word_cnt = {}
BATCH = 32
for i in range(0, len(sentences_raw), BATCH):
    batch = sentences_raw[i:i+BATCH]
    enc, hidden = get_bert_embeddings(batch)
    input_ids = enc['input_ids']
    for b in range(len(batch)):
        ids = input_ids[b]
        h = hidden[b]  # (L, H)
        chars = tok.convert_ids_to_tokens(ids)  # 中文每个字一个 token
        # 用 jieba 切词（与位置对齐：纯中文部分按字对齐）
        sent = batch[b]
        toks = list(jieba.cut(sent))
        # 建立 词 -> (起始token位置, 长度) 映射
        pos = 1  # 跳过 [CLS]
        for tk in toks:
            if pos >= len(chars) - 1:
                break
            if not re.fullmatch(r'[\u4e00-\u9fff]+', tk):
                # 非纯中文（标点/数字/英文），跳过对应 token
                pos += len(tk) if re.fullmatch(r'[\u4e00-\u9fff]+', '') else max(len(tk), 1)
                # 简化：非中文token按字符数推进（英文/数字BERT也可能切子词，此处近似）
                continue
            L = len(tk)
            if pos + L > len(chars):
                break
            if all(chars[pos+j] == tk[j] for j in range(L) if j < len(chars)-pos):
                emb = h[pos:pos+L].mean(dim=0).numpy()
                if tk not in word_embs:
                    word_embs[tk] = []
                    word_cnt[tk] = 0
                word_embs[tk].append(emb)
                word_cnt[tk] += 1
            pos += L
    if (i // BATCH) % 20 == 0:
        print(f'  BERT 编码进度: {i}/{len(sentences_raw)} 已收集词: {len(word_embs)}')

# 平均词向量
bert_vec = {}
for w, embs in word_embs.items():
    if word_cnt[w] >= 2:  # 出现≥2次
        bert_vec[w] = np.mean(np.stack(embs), axis=0)
print('BERT 可用词向量(≥2次):', len(bert_vec))

# 归一化 + 余弦相似度
def cosine_sim(a, b):
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(a @ b)

def bert_expand(seed, topk=10):
    if seed not in bert_vec:
        return []
    sv = bert_vec[seed]
    sims = [(w, cosine_sim(sv, v)) for w, v in bert_vec.items() if w != seed]
    sims.sort(key=lambda x: -x[1])
    return [(w, round(s, 4)) for w, s in sims[:topk]]

# ---------- 6. 对比输出 ----------
results = []
for seed in seeds:
    w2 = w2v_expand(seed)
    be = bert_expand(seed)
    results.append({
        'seed': seed,
        'w2v': w2,
        'bert': be,
        'w2v_in_vocab': seed in w2v.wv,
        'bert_in_vocab': seed in bert_vec,
    })

# 输出报告
out_txt = os.path.join(BASE, '第三次输出', '扩词对比_Word2Vec_vs_BERT.txt')
with open(out_txt, 'w', encoding='utf-8') as f:
    f.write('='*100 + '\n')
    f.write('扩词实验对比：Word2Vec vs BERT\n')
    f.write('语料：4份政策 + 9篇文献（%.1f万字）\n' % (len(corpus)/10000))
    f.write('种子词数：%d\n' % len(seeds))
    f.write('='*100 + '\n\n')
    for r in results:
        f.write(f'【{r["seed"]}】\n')
        f.write(f'  Word2Vec: ' + (' | '.join(f'{w}({s})' for w, s in r['w2v'][:8]) if r['w2v'] else '（词不在词表中）') + '\n')
        f.write(f'  BERT    : ' + (' | '.join(f'{w}({s})' for w, s in r['bert'][:8]) if r['bert'] else '（词不在语料中）') + '\n')
        f.write('\n')
    # 统计
    w2_ok = sum(1 for r in results if r['w2v'])
    be_ok = sum(1 for r in results if r['bert'])
    f.write('='*100 + '\n')
    f.write(f'种子词覆盖率：Word2Vec {w2_ok}/{len(seeds)}，BERT {be_ok}/{len(seeds)}\n')
print('结果已保存:', out_txt)

# 终端打印前10个种子词的对比
for r in results[:10]:
    print(f'\n【{r["seed"]}】')
    print('  W2V:', [w for w, _ in r['w2v'][:6]])
    print('  BERT:', [w for w, _ in r['bert'][:6]])
