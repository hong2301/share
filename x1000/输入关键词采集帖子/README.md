# X350 - X(Twitter) 帖子采集工具

基于 DrissionPage 的 X 平台帖子批量采集脚本。

## 快速开始

### 1. 准备 `input.csv`

每行一个搜索链接 + 可选关键词，格式：

```csv
url,关键词
https://x.com/search?q=from%3ABeijingEvening%20since%3A2026-01-01%20until%3A2026-01-31&src=typed_query,
https://x.com/search?q=Beijing%20since%3A2026-01-01%20until%3A2026-01-31&src=typed_query,Beijing
https://x.com/search?q=%23beijingtravel%20since%3A2026-01-01%20until%3A2026-01-31&src=typed_query,#beijingtravel
```

支持的链接类型：

| 类型 | 示例 | 关键词列 |
|------|------|----------|
| 按账号 + 日期 | `from%3A{账号}%20since%3A...until%3A...` | 留空 |
| 按关键词 + 日期 | `{关键词}%20since%3A...until%3A...` | 填关键词 |
| 按标签 + 日期 | `%23{标签}%20since%3A...until%3A...` | 填标签 |

### 2. 运行

```bash
python main.py
```

需要先打开 Chrome 调试端口（2728），脚本会自动接管浏览器逐个打开链接采集。

### 3. 输出 `output.csv`

| 发布者 | 发布时间 | 正文 | 点赞数 | 回复数 | 转发数 | 浏览量 | 话题标签 | 关键词 | 链接 |
|--------|----------|------|--------|--------|--------|--------|----------|--------|------|

- **关键词**列：对应 `input.csv` 中填写的关键词，账号采集则为空
- **话题标签**：自动从正文提取 `#xxx`

## 采集控制逻辑

- **每条链接最多采集 15 条帖子**，达到上限后自动进入下一条链接
- **连续 5 轮未发现新帖子则提前停止**，避免页面无新内容时无限等待
- 每发现一条新帖子会重置计数，确保只统计连续空窗
