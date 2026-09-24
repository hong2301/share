# 评论接口监听探测成果（2026-09-25）

## 通道
接管 7746 端口 Chrome（复用登录态），监听浏览器自发的评论接口请求，原始响应全量落盘。

## 两个评论接口
| 接口 | 目录 | 说明 |
|---|---|---|
| `/api/sns/web/v2/comment/page` | 一级评论page/ | 一级评论分页（含内嵌二级 sub_comments） |
| `/api/sns/web/v2/comment/sub/page` | 二级评论sub_page/ | 二级评论分页（URL 带 root_comment_id=所属一级） |
| SSR 笔记详情 | ssr_note.json | 笔记基础数据（window.__INITIAL_STATE__） |

## 本次探测（笔记 6a9bf1a7... 算了跟你们不养猫的讲不清楚）
- 监听抓取：127 条评论（一级 88 / 二级 39），与页面显示一致
- 一级 9 个分页包 + 二级 6 个分页包
- 汇总：result_api_test.csv（39 字段逐行评论，含 commentId/parentCommentId/commentLevel/likeCount/ipLocation/createTime 等）

## 说明
浏览器监听 == 平台接口采集 同源接口（comment/page + sub/page），数据口径一致；
监听方式的优势：浏览器登录态稳定 + 天然网页展示顺序。
