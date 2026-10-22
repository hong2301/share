# 小红书帖子基础数据采集（浏览器监听 + SSR 双通道）

不依赖 cookie 鉴权 / JS 签名解密，直接复用浏览器已登录状态与自身请求。

## 原理

```
tab.listen.start('api/sns/web')   # 挂载网络监听
tab.get(url)                      # 浏览器自动加载页面（自带真实 cookie 与签名）
```

- **主通道**：读页面 SSR 数据 `window.__INITIAL_STATE__.note.noteDetailMap`（浏览器已解好密的真实数据）
- **兜底通道**：监听 `api/sns/web/v1/feed` 接口响应（SSR 缺失/加密笔记时浏览器会自发 feed 请求）

## 依赖

- Python 3.8+
- DrissionPage（实测 4.1.1.2）：`pip install DrissionPage`
- 浏览器需已启动并登录小红书，端口默认 7746（main.py 变量区 `tabPort` 可改）

## 使用

input.csv 格式（标题行 `url` + 每行一个链接）：
```
url
https://www.xiaohongshu.com/discovery/item/xxx?xsec_token=...
```

运行：
```bash
python main.py                 # 全量采集
python main.py --start 2 --end 50   # 只采第 2~50 条
```

## 输出

- `result/postData/<noteId>.json`：每条帖子的采集结果，统一结构：
  ```json
  {
    "noteId": "...",
    "url": "...",
    "collectedAt": "时间",
    "status": "success|fail",
    "msg": "ok 或失败原因",
    "data": { title, type, desc, tags, cover, images, videoUrl,
              videoDuration, likedCount, collectedCount, commentCount,
              shareCount, authorNickname, authorUserId, ipLocation,
              publishTime, xsecToken }
  }
  ```
- `api_raw/<noteId>/note_info_ssr.json`（或 `_feed.json`）：接口/SSR 原始数据全量备份
- `log/main_时间戳.log`：运行日志（终端 + 文件双写）

## 说明

- 成功失败都会在 `result/postData/` 落盘一份 json，`status`/`msg` 记录结果与原因
- `api_raw/`、`result/`、`log/` 为运行产物，按需清理或加入 .gitignore