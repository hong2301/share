# Bark 推送通知使用指南

Bark 是一款 iOS 推送通知工具，可以将消息推送到 iPhone。支持命令行、API、脚本等多种调用方式。

## 目录

- [快速开始](#快速开始)
- [配置文件](#配置文件)
- [命令行使用](#命令行使用)
- [API 调用](#api-调用)
- [请求参数详解](#请求参数详解)
- [实用示例](#实用示例)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 安装 Bark App

从 App Store 搜索「Bark」安装，打开 App 复制你的推送 Key。

### 2. 配置本地环境

配置文件位置：`~/.config/bark/config.json`

```json
{
  "server": "https://api.day.app",
  "key": "你的推送key",
  "sound": "calypso",
  "group": "Pi"
}
```

### 3. 发送第一条推送

```bash
/Users/hong/.pi/agent/bin/bark "测试" "Hello from Mac!"
```

---

## 配置文件

**路径：** `~/.config/bark/config.json`

| 字段 | 说明 | 示例 |
|------|------|------|
| `server` | API 服务器地址 | `https://api.day.app` |
| `key` | 设备推送 Key | `eaYaBtin3RaFix4VXMjcEV` |
| `sound` | 默认铃声 | `calypso` |
| `group` | 默认分组 | `Pi` |

### 常用铃声

- `calypso`（默认）
- `alarm`
- `minuet`
- `complete`
- `bell`
- `chime`
- `glass`
- `sonar`
- `hero`
- `note`
- `pulse`
- `riser`
- `sharp`
- `multiway`
- `bellows`

---

## 命令行使用

**路径：** `/Users/hong/.pi/agent/bin/bark`

### 基础用法

```bash
# 简单推送（标题 + 正文）
bark "任务完成" "数据采集已完成"

# 等效写法
bark -t "任务完成" -b "数据采集已完成"
```

### 完整参数

```bash
bark [选项] [标题] [正文]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `-t` | 推送标题 | `-t "警告"` |
| `-b` | 推送正文 | `-b "磁盘空间不足"` |
| `-s` | 铃声 | `-s alarm` |
| `-g` | 分组 | `-g "监控"` |
| `-l` | 自动复制正文到剪贴板 | `-l` |
| `--level` | 推送级别 | `--level timeSensitive` |
| `--icon` | 自定义图标 URL | `--icon https://xxx.png` |
| `--url` | 点击跳转链接 | `--url https://example.com` |
| `--time-sensitive` | 时效性通知（穿透专注模式） | `--time-sensitive` |

### 推送级别

| 级别 | 说明 |
|------|------|
| `active` | 默认，亮屏显示 |
| `timeSensitive` | 时效性通知，专注模式下显示 |
| `passive` | 仅通知列表，不亮屏 |
| `critical` | 重要警告，静音也响铃（需 App 授权） |

### 使用示例

```bash
# 带自定义铃声和分组
bark -s alarm -g "服务器" "宕机告警" "nginx 进程停止"

# 时效性通知
bark --time-sensitive "紧急任务" "客户投诉需要立即处理"

# 带跳转链接
bark -t "日报" "点击查看" --url "https://report.example.com"

# 自动复制到剪贴板
bark -l "复制内容" "已复制到剪贴板"
```

---

## API 调用

### URL 格式

```
https://api.day.app/{key}/{title}/{body}
```

或简化版：

```
https://api.day.app/{key}/{body}
```

### GET 请求

```bash
curl "https://api.day.app/your_key/推送内容?group=分组&sound=alarm"
```

### POST 表单

```bash
curl -X POST "https://api.day.app/your_key" \
     -d 'body=推送内容&title=标题&group=分组'
```

### POST JSON（推荐）

```bash
curl -X POST "https://api.day.app/your_key" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d '{
  "title": "监控告警",
  "body": "CPU 使用率超过 90%",
  "sound": "alarm",
  "group": "服务器",
  "level": "timeSensitive"
}'
```

### JSON 请求（Key 在请求体）

```bash
curl -X POST "https://api.day.app/push" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d '{
  "device_key": "your_key",
  "title": "测试",
  "body": "Hello"
}'
```

---

## 请求参数详解

### 内容

| 参数 | 说明 |
|------|------|
| `title` | 推送标题，显示在通知卡片第一行 |
| `subtitle` | 推送副标题，显示在标题下方 |
| `body` | 推送正文，主要内容 |
| `markdown` | Markdown 格式正文（忽略 body） |

### 设备

| 参数 | 说明 |
|------|------|
| `device_key` | 设备 key（JSON 请求时使用） |
| `device_keys` | 批量推送，key 数组（公共服务器最多 10 个） |

### 展示与分组

| 参数 | 说明 |
|------|------|
| `group` | 消息分组 |
| `icon` | 自定义通知图标 URL（iOS 15+） |
| `image` | 推送图片 URL |
| `badge` | App 角标数字（0 清除角标） |

### 提醒与铃声

| 参数 | 说明 |
|------|------|
| `level` | 推送级别：`active`/`timeSensitive`/`passive`/`critical` |
| `volume` | 重要警告音量 0-10（仅 critical 生效） |
| `call` | 重复响铃 |
| `sound` | 自定义铃声名 |

### 复制与跳转

| 参数 | 说明 |
|------|------|
| `copy` | 指定复制内容 |
| `url` | 点击跳转地址 |
| `action` | 点击操作弹窗 |

### 保存与管理

| 参数 | 说明 |
|------|------|
| `isArchive` | 是否保存到历史（默认 true） |
| `ttl` | 保存有效期（秒） |
| `id` | 通知唯一标识 |
| `delete` | 删除通知 |

---

## 实用示例

### 1. 监控脚本告警（Python）

```python
import subprocess
import json

BARK = '/Users/hong/.pi/agent/bin/bark'

def send_alert(title, message, level='active'):
    """发送 Bark 告警"""
    cmd = [BARK, '-t', title, '-b', message]
    if level != 'active':
        cmd.extend(['--level', level])
    subprocess.run(cmd, timeout=20)

# 使用示例
send_alert('⚠️ 服务宕机', 'nginx 进程停止运行', level='timeSensitive')
```

### 2. 批量推送（API）

```python
import requests
import json

SERVER = 'https://api.day.app'
KEYS = ['key1', 'key2', 'key3']  # 最多 10 个

def batch_push(title, body, keys):
    """批量推送到多台设备"""
    url = f"{SERVER}/push"
    payload = {
        "device_keys": keys,
        "title": title,
        "body": body
    }
    resp = requests.post(url, json=payload)
    return resp.json()

result = batch_push("全员通知", "系统维护中", KEYS)
```

### 3. 定时任务通知（Shell）

```bash
#!/bin/bash
# backup.sh - 备份完成后发送通知

BACKUP_DIR="/data/backup"
DATE=$(date +%Y%m%d)

# 执行备份
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" /important/data

if [ $? -eq 0 ]; then
    /Users/hong/.pi/agent/bin/bark "✅ 备份完成" "$DATE 备份成功，大小: $(du -h $BACKUP_DIR/backup_$DATE.tar.gz | cut -f1)"
else
    /Users/hong/.pi/agent/bin/bark -s alarm "❌ 备份失败" "$DATE 备份出错，请检查"
fi
```

### 4. MCP 集成（Claude Code）

```sh
claude mcp add bark --transport http https://api.day.app/mcp/{your_key}
```

---

## 常见问题

### 1. 推送没有声音

- 检查 iPhone 是否开启了静音模式
- 确认 Bark App 通知权限已开启
- 使用 `--level critical` 可以突破静音（需授权）

### 2. 推送延迟

- 公共服务器可能有排队，自建服务器更快
- 检查网络连接

### 3. URL 编码问题

手动拼接 GET 请求时，特殊字符需要 URL 编码：

```bash
# 中文内容需要编码
curl "https://api.day.app/your_key/$(python3 -c 'import urllib.parse; print(urllib.parse.quote("推送内容"))')"
```

### 4. 通知分组

同一 `group` 的推送会在通知中心归组，可长按横幅选择静音某分组。

### 5. 清除角标

```bash
bark -t "清除" --badge 0
```

---

## 相关资源

- 官方文档：https://bark.day.app
- GitHub：https://github.com/Finb/Bark
- 本机配置：`~/.config/bark/config.json`
- 本机命令：`/Users/hong/.pi/agent/bin/bark`

---

*最后更新：2025-01*
