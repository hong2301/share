#!/usr/bin/env python3
"""阶段一：从政策语料提取候选术语（种子词构建）"""
import jieba
import jieba.analyse
import glob
import os
import re
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(BASE, "..", "语料库")
OUTPUT = os.path.join(BASE, "..", "输出")

os.makedirs(OUTPUT, exist_ok=True)

# 领域停用词（功能词、通用词）
STOPWORDS = set("""的 了 和 与 及 或 在 是 为 对 于 从 到 向 以 等 而 但 其 之 一个 该 各 两 三 应 要 将 并 由 通过 进行 提供 开展 加强 促进 推动 支持 建立 完善 落实 实施 引导 鼓励 规范 发展 建设 服务 管理 工作 相关 有关 方面 领域 情况 问题 重点 主要 进一步 不断 积极 有效 加快 深化 优化 提升 强化 坚持 按照 根据 切实 健全 发挥 确保 统筹 推进 着力 依托 围绕 结合 借鉴 探索 创新 应用 实现 形成 明确 落实 提升 建立 完善 促进 支持 保障 加强 推动 发展 建设 服务 管理 经营 企业 机构 部门 单位 平台 系统 政府 市场 社会 国家 地方 全国 我国 中央 国务院 人民银行 银保监会 金融监管总局 各省 自治区 直辖市 有关 通知 意见 文件 规定 要求 办法 措施 工作 部门 相关 各 大 中 小 微 数量 情况 时间 方面 内容 标准 基础 环节 手段 方式 渠道 领域 范围 水平 能力 机制 体系 制度 政策 环境 条件 需求 供给 结构 质量 效率 效益 成果 效果 问题 风险 责任 义务 权利 利益 关系 过程 结果 目标 任务 计划 方案 项目 工程 平台 中心 基地 试点 示范 试验 经验 模式 路径 方向 思路 部署 安排 布局 规划 目标 任务 要求 标准 规范 管理 监督 检查 考核 评估 验收 评价 执法 处罚 责任 追究 组织 领导 协调 配合 联动 协同 共享 公开 透明 公正 公平 合法 合规 安全 稳定 有序 健康 持续 快速 准确 完整 及时 全面 深入 切实 有力 有效 高效 便捷 灵活 积极 主动 稳妥 审慎 逐步 有序 合理 适当 必要 重要 重大 关键 核心 基础 基本 具体 明确 清晰 详细 充分 广泛 普遍 一般 特殊 正常 异常 总体 整体 全局 局部 宏观 微观 产业 行业 领域 市场 主体 行为 活动 事项 业务 项目 产品 服务 技术 模式 工具 手段 方式 方法 途径 渠道 环节 流程 链条 环节 阶段 步骤 内容 要素 资源 资产 资本 资金 货币 信贷 融资 投资 收益 成本 利润 收入 支出 费用 价格 价值 风险 收益 回报 损失 违约 不良 逾期 呆账 坏账 贷款 借款 存款 理财 保险 证券 债券 基金 信托 担保 抵押 质押 保证 承兑 贴现 结算 清算 支付 转账 汇兑 交易 签约 履行 违约 纠纷 诉讼 仲裁 调解 执行 保全 查封 扣押 冻结 划拨 拍卖 变卖 偿还 归还 清偿 追偿 索赔 理赔 承保 核保 理赔 精算 准备金 偿付 资本 充足 杠杆 流动性 系统性 区域性 传染 交叉 关联 集中 分散 对冲 套期 保值 投机 套利 监管 审批 备案 登记 报告 披露 审计 检查 处罚 罚款 警告 暂停 撤销 吊销 取缔 禁止 限制 约束 规范 规制 治理 管控 防控 防范 预警 监测 跟踪 排查 整改 处置 应对 化解 缓释 隔离 防火墙""".split())

# 领域种子词（数智供应链金融核心概念，理论框架映射）
SEED_TERMS = [
    # 数字化技术
    "数字化", "智能化", "人工智能", "大数据", "区块链", "物联网", "云计算",
    "金融科技", "数字技术", "信息技术", "系统集成", "数据要素", "算法",
    # 供应链管理
    "供应链", "产业链", "价值链", "物流", "仓储", "核心企业", "上下游",
    "供应链网络", "产业协同", "供应链管理", "全链条", "生态圈",
    # 金融服务
    "供应链金融", "应收账款", "应付账款", "票据", "保理", "质押", "抵押",
    "信用贷款", "授信", "融资", "信贷", "供应链票据", "动产融资",
    "仓单", "订单融资", "存货融资", "预付款融资", "脱核模式",
    # 数据与信息
    "四流合一", "信息流", "资金流", "物流", "商流", "数据信用", "物的信用",
    "信息归集", "数据安全", "隐私保护", "征信",
    # 监管与规范
    "风险防控", "合规", "风险监测", "全口径债务", "授信管理", "尽职调查",
    "贷前", "贷中", "贷后", "贸易背景", "虚构贸易", "资金用途",
    # 产业应用
    "中小企业", "实体经济", "制造业", "科技创新", "绿色发展", "新质生产力",
    "五篇大文章", "产业集群", "特色产业", "乡村振兴",
]


def clean_text(text):
    # 去除非中文字符（保留中文、数字、%）
    text = re.sub(r'[^\u4e00-\u9fff0-9%]', ' ', text)
    return text


def main():
    # 加载停用词到 jieba
    for w in SEED_TERMS:
        jieba.add_word(w)

    # 合并所有政策语料
    all_text = ""
    for f in glob.glob(os.path.join(CORPUS_DIR, "*.txt")):
        with open(f, encoding='utf-8') as fh:
            all_text += fh.read() + "\n"

    print(f"语料总长度: {len(all_text)}")

    # 用 jieba.analyse 提取关键词（TF-IDF）
    top_kw = jieba.analyse.extract_tags(all_text, topK=200, withWeight=False)

    # 同时用词频统计
    words = jieba.cut(all_text)
    counter = Counter()
    for w in words:
        w = w.strip()
        if len(w) < 2 or len(w) > 10:
            continue
        if w in STOPWORDS:
            continue
        if not re.match(r'^[\u4e00-\u9fff]+$', w):
            continue
        counter[w] += 1

    # 输出 TF-IDF 关键词
    print("\n=== TF-IDF Top 100 关键词 ===")
    for i, kw in enumerate(top_kw, 1):
        print(f"{i}. {kw} ({counter.get(kw, 0)})")

    # 保存词频统计
    with open(os.path.join(OUTPUT, "阶段1_词频统计.txt"), 'w', encoding='utf-8') as f:
        f.write("=== 高频词统计 ===\n")
        for w, c in counter.most_common(300):
            f.write(f"{w}\t{c}\n")

    with open(os.path.join(OUTPUT, "阶段1_TFIDF关键词.txt"), 'w', encoding='utf-8') as f:
        for i, kw in enumerate(top_kw, 1):
            f.write(f"{i}. {kw}\n")

    print(f"\n已保存到 {OUTPUT}")


if __name__ == "__main__":
    main()
