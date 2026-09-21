---
name: bark-notify
description: |
  当用户想要通过 Bark 推送通知到 iPhone 时触发。支持命令行和 API 调用，
  包含自定义铃声、角标、分组、推送级别、加密推送、批量推送等完整功能。
  支持 MCP 集成、自建服务器部署。
---

# Bark 推送通知 Skill

这个 skill 把「通过 Bark 推送通知到 iPhone」的完整流程封装成可复用指令。

## 触发场景

用户说类似以下的话时触发：

- "发个通知到手机"
- "用 Bark 推送"
- "手机收到通知"
- "发个铃声通知"
- "推送告警到 iPhone"
- "发个消息提醒我"
- "bark 推送"
- "发个通知"
- "手机通知我"
- "给我发个推送"
- "发个消息到手机"
- "发个提醒"
- "推送到 iPhone"
- "手机提醒我"
- "发个通知提醒"
- "批量推送"
- "加密推送"
- "自建 bark 服务器"

## 环境要求

- Node.js 环境
- 配置文件 `config.json` 存在且包含有效的 `key`
- 若 config.json 缺失，引导用户从 App 复制 key 并配置

---

## 核心概念

### 推送架构

```
发送端 → Bark 服务器 → 苹果 APNs 服务器 → iPhone 设备 → Bark App
```

### 推送参数完整说明

#### 内容相关

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `title` | string | 是 | 标题，显示在通知卡片第一行 | "任务完成" |
| `body` | string | 是 | 正文，通知的主要内容 | "备份成功，共处理 1024 个文件" |
| `subtitle` | string | 否 | 副标题，显示在标题下方、正文上方的小字位置，适合放来源、状态等补充信息 | "来自服务器-01" |
| `markdown` | string | 否 | Markdown 格式正文，传了会忽略 body。支持：加粗、斜体、删除线、链接、行内代码、代码块、1-6级标题、引用、有序/无序列表、任务列表 | "**重要** 请查看" |

#### 设备相关

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `device_key` | string | 否 | 推送目标设备的 key，用于 JSON 请求时在请求体中指定设备 | "your_key" |
| `device_keys` | array | 否 | key 数组，一次推送给多台设备，仅支持 JSON 请求，公共服务器最多 10 个，自建服务器无上限 | ["key1", "key2"] |

#### 展示与分组

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `group` | string | 否 | 消息分组，同一 group 的推送在通知中心和历史记录里会归到一组。支持长按/下拉横幅选择静音某分组 | "监控", "Pi", "服务器" |
| `icon` | string | 否 | 自定义通知图标 URL，替换默认 Bark 图标。图标会自动缓存，同一 URL 只下载一次，首次下载超 10 秒退回默认。需 iOS 15+ | "https://example.com/icon.png" |
| `image` | string | 否 | 推送图片 URL，收到推送后展开通知即可看到大图。图片会缓存，下载超 10 秒不带图片显示 | "https://example.com/image.jpg" |
| `badge` | number | 否 | App 图标上的角标数字，直接设置为传入值（不累加）。传 0 清除角标并清掉通知中心里该 App 的通知 | 0, 1, 5, 99 |

#### 提醒与铃声

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `level` | string | 否 | 推送级别，见下方详细说明 | "active", "timeSensitive" |
| `volume` | number | 否 | 重要警告（level=critical）的音量，范围 0-10，默认 5。仅 critical 生效，普通推送音量由系统控制 | 5, 8, 10 |
| `call` | string | 否 | 传 "1" 时铃声循环播放 30 秒（默认只响一次），用于强提醒场景。配合 sound 和 volume 使用 | "1" |
| `sound` | string | 否 | 自定义铃声名，App 内置铃声和自己导入的铃声都可以用。导入的铃声需是 .caf 格式、时长不超过 30 秒 | "alarm", "calypso" |

#### 复制与跳转

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `copy` | string | 否 | 指定复制内容，长按通知可复制。不传时复制正文 | "复制的文本" |
| `url` | string | 否 | 点击跳转地址，支持 URL Scheme 和 Universal Link。http/https 链接优先用 Universal Link 打开，失败用 Safari | "https://example.com" |
| `action` | string | 否 | 传 "alert" 时点击推送弹出操作弹窗（可复制/分享）。传 "none" 时只打开 App 不跳转。同时传 url 时优先按 url 跳转 | "alert", "none" |

#### 加密相关

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `ciphertext` | string | 否 | 加密推送的密文，推送内容对服务器和 APNs 都不可见，只有本机 App 能解密 | - |
| `iv` | string | 否 | 加密时使用的随机 IV 值，需一并传给服务器 | - |

#### 保存与管理

| 参数 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `isArchive` | string | 否 | 是否保存到历史记录。传 "1" 保存，其他值不保存。不传按 App 设置决定，默认保存 | "1" |
| `ttl` | number | 否 | 保存有效期（秒），过期自动删除历史记录和通知中心对应推送。适合验证码、临时告警 | 3600, 86400 |
| `id` | string | 否 | 通知唯一标识。使用相同 id 时新推送会替换旧通知，不会重复堆叠。需 Bark v1.5.2+、bark-server v2.2.5+ | "order-123" |
| `delete` | string | 否 | 传 "1" 时删除指定通知（需搭配 id）。通过静默推送下发，需开启「后台 App 刷新」 | "1" |

### 推送级别详解

| 级别 | 说明 | 场景 | 要求 |
|------|------|------|------|
| `active` | 默认值，系统会立即亮屏显示通知 | 日常通知、任务完成、普通提醒 | 无 |
| `timeSensitive` | 时效性通知，专注模式下也能显示 | 紧急任务、重要告警、需要立即处理 | iOS 15+ |
| `passive` | 仅将通知添加到通知列表，不会亮屏提醒 | 低优先级通知、日志记录、后台同步 | 无 |
| `critical` | 重要警告，静音模式下也会响铃 | 服务器宕机、安全告警、紧急维修 | iOS 15+，需 App 授权「重要警告」 |

**critical 级别特殊说明：**
- 需要在 Bark App 里授权「重要警告」权限
- 未授权时降级为普通通知
- 铃声音量由 `volume` 参数控制（0-10）
- 适合服务器宕机、安全入侵等极端场景

### 铃声分类详解

| 类别 | 说明 | 推荐场景 | 示例铃声 |
|------|------|----------|----------|
| `alert` | 警报类，声音急促、醒目 | 紧急告警、安全警告、宕机通知 | alarm, sharp, riser, tritone, phone |
| `notification` | 通知类，声音适中 | 日常消息、状态更新、任务提醒 | calypso, bell, chime, glass, pulse, sonar |
| `success` | 成功类，声音欢快 | 任务完成、备份成功、部署成功 | complete, hero, victory, payment |
| `default` | 默认，通用 | 不确定时使用 | calypso |

**场景 → 铃声推荐：**

| 场景 | 推荐铃声 | 理由 |
|------|----------|------|
| 服务器宕机 | alarm | 急促警报，立即引起注意 |
| CPU/内存告警 | sharp | 尖锐刺耳，表示异常 |
| 磁盘空间不足 | riser | 上升音效，表示问题升级 |
| 备份完成 | complete | 完成提示音，表示成功 |
| 部署成功 | hero | 英雄音效，表示成就 |
| 监控心跳 | pulse | 脉冲声，表示持续监控 |
| 扫描完成 | sonar | 声纳音效，表示检测完成 |
| 日常提醒 | calypso | 默认铃声，通用友好 |
| 紧急呼叫 | phone | 电话铃声，表示紧急 |
| 收款通知 | payment | 支付提示音，表示交易 |

---

## 命令行用法

### 发送推送

```bash
# 基础用法 - 标题 + 正文
node scripts/bark.js notify "标题" "内容"

# 指定铃声和分组
node scripts/bark.js notify -s alarm -g 监控 "告警" "CPU使用率超过90%"

# 时效性通知（穿透专注模式）
node scripts/bark.js notify --time-sensitive "紧急" "客户投诉需要立即处理"

# 重要警告（静音也响）
node scripts/bark.js notify -l critical "服务器宕机" "nginx进程停止运行"

# 带跳转链接
node scripts/bark.js notify --url "https://grafana.example.com" "日报" "点击查看详细监控"

# 带副标题
node scripts/bark.js notify --subtitle "来自生产环境" "告警" "数据库连接池耗尽"

# Markdown 格式正文
node scripts/bark.js notify --markdown "## 告警详情\n\n- **服务器**: prod-01\n- **CPU**: 95%\n- **时间**: 2024-01-01 12:00" "告警" "详情见下方"

# 自定义图标
node scripts/bark.js notify --icon "https://example.com/alert.png" "告警" "自定义图标通知"

# 推送图片
node scripts/bark.js notify --image "https://example.com/screenshot.png" "截图" "服务器状态截图"

# 复制到剪贴板
node scripts/bark.js notify --copy "订单号: ORDER-123456" "订单" "已复制订单号"

# 循环响铃 30 秒
node scripts/bark.js notify --call "紧急" "请立即处理"

# 有效期 1 小时（适合验证码）
node scripts/bark.js notify --ttl 3600 "验证码" "123456"

# 不保存到历史记录
node scripts/bark.js notify --archive 0 "临时通知" "无需保存"

# 组合多个参数
node scripts/bark.js notify -s alarm -g 监控 --time-sensitive --url "https://dashboard.example.com" --subtitle "生产环境" "⚠️ 紧急告警" "数据库主从同步延迟超过30秒，请立即检查"
```

### 设置角标

```bash
# 设置角标数字
node scripts/bark.js badge 5

# 清除角标
node scripts/bark.js badge 0

# 根据文件数量设置角标
FILE_COUNT=$(ls /path/to/files/*.json 2>/dev/null | wc -l)
node scripts/bark.js badge $FILE_COUNT
```

### 配置管理

```bash
# 查看当前配置
node scripts/bark.js config

# 修改默认铃声
node scripts/bark.js config default_sound alarm

# 修改默认分组
node scripts/bark.js config default_group 监控

# 修改服务器地址（自建服务器时）
node scripts/bark.js config server https://your-bark-server.com

# 修改设备 Key
node scripts/bark.js config key your_new_key
```

### 查看资源

```bash
# 列出所有铃声（按类别分组）
node scripts/bark.js sounds

# 列出角标预设
node scripts/bark.js badges
```

### 测试

```bash
# 发送测试推送（使用默认配置）
node scripts/bark.js test
```

---

## API 调用

### URL 格式

```
https://api.day.app/{key}/{title}/{body}
https://api.day.app/{key}/{body}
```

### GET 请求

```bash
# 简单推送
curl "https://api.day.app/your_key/推送内容"

# 带参数
curl "https://api.day.app/your_key/标题/正文?sound=alarm&group=监控&level=timeSensitive"

# URL 编码（中文特殊字符）
curl "https://api.day.app/your_key/$(python3 -c 'import urllib.parse; print(urllib.parse.quote("推送内容"))')"
```

### POST 表单

```bash
curl -X POST "https://api.day.app/your_key" \
     -d 'body=推送内容&title=标题&group=分组&sound=alarm'
```

### POST JSON（推荐）

```bash
curl -X POST "https://api.day.app/your_key" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d '{
  "title": "监控告警",
  "body": "CPU 使用率超过 90%，当前 95.2%",
  "sound": "alarm",
  "group": "服务器",
  "level": "timeSensitive",
  "url": "https://grafana.example.com/d/cpu",
  "icon": "https://example.com/alert-icon.png"
}'
```

### JSON 请求（Key 在请求体）

```bash
curl -X POST "https://api.day.app/push" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d '{
  "device_key": "your_key",
  "title": "测试",
  "body": "Hello from API",
  "sound": "complete"
}'
```

### 批量推送

```bash
# 公共服务器最多 10 个设备，自建服务器无上限
curl -X POST "https://api.day.app/push" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d '{
  "device_keys": ["key1", "key2", "key3"],
  "title": "全员通知",
  "body": "系统维护中，预计 30 分钟后恢复",
  "sound": "alarm",
  "group": "全员"
}'
```

### 加密推送

```bash
#!/bin/bash
# 加密推送示例

deviceKey='your_device_key'
json='{"body": "加密内容", "sound": "alarm", "group": "加密"}'

# 16 位密钥和 IV
key='1234567890123456'
iv='1234567890123456'

# 转换为 hex 编码
key_hex=$(printf $key | xxd -ps -c 200)
iv_hex=$(printf $iv | xxd -ps -c 200)

# 加密
ciphertext=$(echo -n $json | openssl enc -aes-128-cbc -K $key_hex -iv $iv_hex | base64)

# 发送
curl --data-urlencode "ciphertext=$ciphertext" \
     --data-urlencode "iv=$iv" \
     https://api.day.app/$deviceKey
```

### 删除通知

```bash
# 需要搭配 id 使用，需开启「后台 App 刷新」
curl -X POST "https://api.day.app/your_key" \
     -d 'delete=1&id=order-123'
```

### 更新通知（使用相同 id）

```bash
# 第一次发送
curl -X POST "https://api.day.app/your_key" \
     -H 'Content-Type: application/json' \
     -d '{"id":"task-123","title":"任务进度","body":"处理中... 30%"}'

# 第二次发送（相同 id 会替换）
curl -X POST "https://api.day.app/your_key" \
     -H 'Content-Type: application/json' \
     -d '{"id":"task-123","title":"任务进度","body":"已完成 100%"}'
```

---

## MCP 集成

### VS Code

```json
{
  "servers": {
    "bark": {
      "type": "http",
      "url": "https://api.day.app/mcp/{your_key}"
    }
  }
}
```

### Claude Code

```bash
claude mcp add bark --transport http https://api.day.app/mcp/{your_key}
```

或配置文件：

```json
{
  "mcpServers": {
    "bark": {
      "type": "http",
      "url": "https://api.day.app/mcp/{your_key}"
    }
  }
}
```

---

## Python 集成

### 基础调用

```python
import subprocess

BARK_SCRIPT = '/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js'

def send_bark(title, body, sound='calypso', group='Pi', level='active'):
    """发送 Bark 推送"""
    cmd = ['node', BARK_SCRIPT, 'notify', '-s', sound, '-g', group]
    if level != 'active':
        cmd.extend(['--level', level])
    cmd.extend([title, body])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return result.returncode == 0

# 使用示例
send_bark('⚠️ 告警', '磁盘空间不足', sound='alarm', group='服务器')
send_bark('✅ 完成', '备份成功', sound='complete')
send_bark('紧急', '需要立即处理', level='timeSensitive')
```

### 直接 API 调用

```python
import requests
import json

def send_bark_api(title, body, key, server='https://api.day.app', **kwargs):
    """通过 API 直接发送"""
    url = f"{server}/{key}"
    payload = {
        "title": title,
        "body": body,
        **kwargs
    }
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()

# 使用
result = send_bark_api(
    title='测试',
    body='Hello',
    key='your_key',
    sound='alarm',
    group='test'
)
```

### 监控脚本示例

```python
import subprocess
import time
import os

BARK_SCRIPT = '/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js'
WATCH_DIR = '/path/to/monitor'

def send_alert(title, body, sound='alarm'):
    """发送告警"""
    cmd = ['node', BARK_SCRIPT, 'notify', '-s', sound, '-g', '监控', title, body]
    subprocess.run(cmd, timeout=20)

def check_disk():
    """监控磁盘空间"""
    while True:
        # 获取磁盘使用率
        usage = os.popen("df -h / | tail -1 | awk '{print $5}'").read().strip().replace('%', '')
        
        if int(usage) > 90:
            send_alert('⚠️ 磁盘告警', f'磁盘使用率: {usage}%', sound='alarm')
        
        time.sleep(300)  # 每5分钟检查一次

if __name__ == '__main__':
    check_disk()
```

### 批量推送示例

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
        "body": body,
        "sound": "alarm",
        "group": "全员"
    }
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()

result = batch_push("全员通知", "系统维护中", KEYS)
print(result)
```

### 进度通知示例（使用相同 id）

```python
import requests
import time

def send_progress(task_id, progress, title="任务进度"):
    """发送进度通知（会替换之前的通知）"""
    url = f"https://api.day.app/your_key"
    payload = {
        "id": task_id,
        "title": title,
        "body": f"进度: {progress}%",
        "sound": "pulse" if progress < 100 else "complete"
    }
    requests.post(url, json=payload)

# 模拟长时间任务
for i in range(101):
    send_progress("task-001", i)
    time.sleep(1)
```

---

## Shell 脚本集成

### 定时任务通知

```bash
#!/bin/bash
# backup.sh - 备份完成后发送通知

BACKUP_DIR="/data/backup"
DATE=$(date +%Y%m%d)
BARK="/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js"

# 执行备份
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" /important/data

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_DIR/backup_$DATE.tar.gz" | cut -f1)
    node $BARK notify -s complete -g 备份 "✅ 备份完成" "$DATE 备份成功，大小: $SIZE"
else
    node $BARK notify -s alarm -g 备份 "❌ 备份失败" "$DATE 备份出错，请检查日志"
fi
```

### 监控目录变化

```bash
#!/bin/bash
# monitor.sh - 监控目录文件数量变化

WATCH_DIR="/path/to/files"
BARK="/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js"
LAST_COUNT=0

while true; do
    COUNT=$(ls "$WATCH_DIR"/*.json 2>/dev/null | wc -l)
    
    if [ $COUNT -ne $LAST_COUNT ] && [ $LAST_COUNT -ne 0 ]; then
        node $BARK notify -s pulse -g 监控 "文件变化" "当前 $COUNT 个文件（之前 $LAST_COUNT）"
    fi
    
    LAST_COUNT=$COUNT
    sleep 60
done
```

### 服务状态监控

```bash
#!/bin/bash
# check_service.sh - 检查服务是否运行

SERVICE="nginx"
BARK="/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js"

if ! pgrep -x "$SERVICE" > /dev/null; then
    node $BARK notify --time-sensitive -s alarm -g 服务 "⚠️ 服务宕机" "$SERVICE 进程未运行"
    # 尝试重启
    sudo systemctl start $SERVICE
    if [ $? -eq 0 ]; then
        node $BARK notify -s complete -g 服务 "✅ 服务已重启" "$SERVICE 已自动重启"
    else
        node $BARK notify -l critical -s alarm -g 服务 "❌ 重启失败" "$SERVICE 重启失败，请手动处理"
    fi
fi
```

---

## 配置文件

**路径：** `config.json`

```json
{
  "server": "https://api.day.app",
  "key": "your_device_key",
  "default_sound": "calypso",
  "default_group": "Pi",
  "default_level": "active"
}
```

### 字段说明

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `server` | string | API 服务器地址 | `https://api.day.app` |
| `key` | string | 设备推送 Key（必填） | - |
| `default_sound` | string | 默认铃声 | `calypso` |
| `default_group` | string | 默认分组 | `Pi` |
| `default_level` | string | 默认推送级别 | `active` |

### 获取 Key

1. App Store 搜索「Bark」安装
2. 打开 App
3. 点击「测试推送」
4. 复制 URL 中的 key 部分
   - URL 格式：`https://api.day.app/{key}/...`
   - 复制 `{key}` 部分
5. 填入 config.json 的 `key` 字段

### 自建服务器

如果需要自建 Bark 服务器：

```bash
# Docker 部署
docker run -dt --name bark -p 8080:8080 -v `pwd`/bark-data:/data finab/bark-server

# Docker-Compose 部署
mkdir bark && cd bark
curl -sL https://git.io/JvSRl > docker-compose.yaml
docker-compose up -d

# 手动部署
./bark-server_linux_amd64 -addr 0.0.0.0:8080 -data ./bark-data
```

修改 config.json 的 `server` 为你的服务器地址：
```json
{
  "server": "https://your-bark-server.com",
  "key": "your_key"
}
```

**自建服务器优势：**
- 无批量推送数量限制
- 无请求频率限制
- 更好的隐私保护
- 支持多 APNS Clients 提升 QPS

**QPS 参考（美西 VPS）：**

| 核心数 | 内存 | QPS |
|--------|------|-----|
| 1 | 3.75 GB | 4,023 |
| 4 | 16 GB | 21,413 |
| 16 | 64 GB | 64,516 |
| 64 | 256 GB | 105,263 |

---

## 全链路流程

```
用户触发 → 意图识别 → 参数提取 → 配置读取 → 参数映射 → 构建 Payload → 发送请求 → 校验结果 → 反馈用户
```

### 1. 意图识别

**关键词 → 行为映射：**

| 关键词 | 动作 |
|--------|------|
| 告警、警告、错误、宕机、异常 | 使用 `alarm` 铃声 |
| 完成、成功、搞定 | 使用 `complete` 铃声 |
| 紧急、立即、马上、 ASAP | 使用 `timeSensitive` 级别 |
| 重要、关键、严重 | 使用 `critical` 级别 |
| 监控、检测、心跳 | 使用 `monitor` 分组 |
| 静默、后台、低调 | 使用 `passive` 级别 |
| 验证码、临时 | 设置 `ttl` 有效期 |

### 2. 参数映射

```python
# 关键词 → 铃声映射
SOUND_MAP = {
    '告警': 'alarm',
    '警告': 'alarm',
    '错误': 'sharp',
    '宕机': 'alarm',
    '异常': 'riser',
    '完成': 'complete',
    '成功': 'hero',
    '搞定': 'victory',
    '紧急': 'phone',
    '立即': 'phone',
    '监控': 'pulse',
    '心跳': 'sonar',
    '日常': 'calypso',
    '提醒': 'chime'
}

# 关键词 → 级别映射
LEVEL_MAP = {
    '紧急': 'timeSensitive',
    '立即': 'timeSensitive',
    '马上': 'timeSensitive',
    'asap': 'timeSensitive',
    '重要': 'critical',
    '关键': 'critical',
    '严重': 'critical',
    '静默': 'passive',
    '后台': 'passive',
    '低调': 'passive'
}

# 关键词 → 分组映射
GROUP_MAP = {
    '监控': '监控',
    '服务器': '服务器',
    '备份': '备份',
    '部署': '部署',
    '订单': '订单',
    '用户': '用户'
}
```

### 3. 智能推断规则

| 用户输入 | 推断结果 |
|----------|----------|
| "发个通知" | 询问内容，使用默认铃声和分组 |
| "发个告警" | 使用 `alarm` 铃声，`monitor` 分组 |
| "发个完成通知" | 使用 `complete` 铃声 |
| "紧急通知" | 使用 `timeSensitive` 级别 |
| "发个监控告警" | 使用 `alarm` 铃声，`monitor` 分组 |
| "静默通知" | 使用 `passive` 级别 |
| "验证码 123456" | 设置 `ttl` 为 300 秒（5分钟） |

### 4. 完整处理流程

```python
def process_bark_request(user_input):
    """处理用户的 Bark 推送请求"""
    
    # 1. 解析意图
    intent = parse_intent(user_input)
    
    # 2. 提取参数
    title = intent.get('title', '通知')
    body = intent.get('body')
    
    if not body:
        return "请提供要推送的内容"
    
    # 3. 智能匹配铃声
    sound = 'calypso'  # 默认
    for keyword, s in SOUND_MAP.items():
        if keyword in user_input:
            sound = s
            break
    
    # 4. 智能匹配级别
    level = 'active'  # 默认
    for keyword, l in LEVEL_MAP.items():
        if keyword in user_input:
            level = l
            break
    
    # 5. 智能匹配分组
    group = 'Pi'  # 默认
    for keyword, g in GROUP_MAP.items():
        if keyword in user_input:
            group = g
            break
    
    # 6. 特殊处理：验证码
    if '验证码' in user_input:
        # 提取验证码数字
        import re
        code = re.search(r'\d{4,6}', user_input)
        if code:
            body = f"验证码: {code.group()}"
            ttl = 300  # 5分钟有效期
    
    # 7. 发送推送
    return send_bark(title, body, sound=sound, group=group, level=level)
```

---

## 自检

发送测试推送验证配置：

```bash
node scripts/bark.js test
```

成功会收到通知并显示 `✅ 推送成功`。

---

## 注意事项

### 限流与封禁

- 公共服务器有频率限制，高频发送可能被拦截
- 5 分钟内超过 1000 次错误请求（HTTP 400/404/500）IP 会被封禁 24 小时
- 5 分钟内超过 5 次 405 错误请求会被封禁
- 建议：单次推送间隔 > 1秒
- 自建服务器无此限制

### 权限

- `critical` 级别需要在 App 里授权「重要警告」
- 未授权时降级为普通通知
- 授权路径：Bark App → 设置 → 重要警告
- `call` 参数（循环响铃）需配合 sound 和 volume 使用

### 图片/图标

- 自定义图标/图片首次下载有 10 秒超时
- 图标会自动缓存，同一 URL 只下载一次
- 超时后退回默认图标
- 需要 iOS 15+

### 安全

- Key 是敏感信息，不要上传到公开仓库
- `.gitignore` 已配置保护 `config.json`
- 可使用加密推送保护隐私
- 自建服务器可完全掌控数据

### 长度

- 单条推送建议不超过 1000 字符
- Markdown 正文图片会降级为链接文本
- `title` 建议不超过 50 字符

### 通知管理

- 使用相同 `id` 可以替换通知（不会重复堆叠）
- `delete` 参数需搭配 `id` 使用
- 删除通知需开启「后台 App 刷新」
- `isArchive=0` 可不保存到历史记录
- `ttl` 可设置自动过期时间

### 多设备

- 同一个 Key 只能一台设备使用
- 只有最后打开的 APP 会收到推送
- 多设备推送需使用 `device_keys` 数组

---

## 常见问题

### Q: 推送没有声音？

- 检查 iPhone 是否开启静音模式
- 确认 Bark App 通知权限已开启
- 使用 `level: critical` 可突破静音（需授权）
- 检查是否对该分组静音
- 检查 Device Token 是否正常（App 设置中查看）

### Q: 推送延迟？

- 公共服务器有排队，可自建服务器
- 检查网络连接
- 检查是否触发限流
- 设备进入后台可能导致网络请求超时

### Q: 如何穿透专注模式？

使用 `--time-sensitive` 或 `level: timeSensitive`，需 iOS 15+。如无效尝试重启设备。

### Q: 如何清除角标？

```bash
node scripts/bark.js badge 0
```

### Q: 如何给多台设备推送？

使用批量推送 API：
```bash
curl -X POST "https://api.day.app/push" \
     -H 'Content-Type: application/json' \
     -d '{"device_keys":["key1","key2"],"title":"全员","body":"通知内容"}'
```

公共服务器最多 10 个设备，自建服务器无上限。

### Q: 如何删除通知？

需要指定通知 id：
```bash
curl -X POST "https://api.day.app/your_key" \
     -d 'delete=1&id=order-123'
```

需开启「后台 App 刷新」。

### Q: 如何更新/替换通知？

使用相同 id 发送新通知即可替换：
```bash
curl -X POST "https://api.day.app/your_key" \
     -H 'Content-Type: application/json' \
     -d '{"id":"task-123","title":"进度","body":"100%"}'
```

### Q: Markdown 支持哪些格式？

支持：加粗、斜体、删除线、链接、行内代码、代码块、1-6级标题、引用、有序/无序列表、任务列表。图片会降级为链接文本。

### Q: 如何静音某个分组？

在收到推送时，长按或下拉系统推送横幅，选择对某个分组静音。

### Q: DeviceToken 显示未知？

- 设备可能没有正常连接到苹果服务器
- 可能伴随 iMessage 不可用、其他 App 推送也收不到
- 尝试切换网络、重启手机
- 如果翻墙代理了 Apple 服务可以关闭翻墙工具
- 此问题是用户设备与苹果服务器的连接问题

### Q: 莫名收到未知推送？

可能原因：
1. Safari 输入网址时自动补全成 Bark API URL，预加载触发推送
2. 聊天软件（如微信）不定时请求 URL 触发推送
3. 推送 Key 泄露，推荐重置 Key

### Q: 自动复制推送失效？

iOS 14.5 之后因权限收紧，不能在收到推送时自动复制。可下拉推送或在锁屏界面左滑推送查看即可自动复制。

### Q: 推送特殊字符导致失败？

URL 编码问题，特殊字符需要 URL 编码。建议无脑套一层 URL 编码。

### Q: 多台设备使用同一个 key？

同一个 Key 只能一台设备使用，只有最后打开的 APP 会收到推送。

---

## 隐私安全

### 推送路线

```
发送端 → Bark 服务器 → 苹果 APNs 服务器 → iPhone → Bark App
```

**可能泄露隐私的地方：**
1. 发送端未使用 HTTPS 或使用公共服务器（作者会看到请求日志）
2. Bark App 本身不安全，上传到 App Store 的版本经过修改

### 解决方案

1. **自建服务器**：使用开源后端代码自行部署，开启 HTTPS
2. **加密推送**：使用自定义秘钥加密推送内容，对服务器和 APNs 都不可见
3. **验证 App**：在 Bark App 设置内查看 GitHub Run Id，验证构建来源

### 加密推送原理

- 使用 AES-128-CBC 加密
- 密钥和 IV 由用户自定义
- 推送内容对服务器和 APNs 都不可见
- 只有本机 App 能解密
- 解密失败时显示 `Decryption Failed`

---

## 相关资源

- 官方文档：https://bark.day.app
- 参数详解：https://bark.day.app/#/params
- GitHub：https://github.com/Finb/Bark
- 服务端 GitHub：https://github.com/Finb/bark-server
- 本机脚本：`/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js`
- 配置文件：`/Users/hong/mac/巧克力加工厂/skills/bark-notify/config.json`
- 铃声库：`/Users/hong/mac/巧克力加工厂/skills/bark-notify/sounds.json`
- 角标库：`/Users/hong/mac/巧克力加工厂/skills/bark-notify/badges.json`

---

## 支持的应用程序和插件

- [SmsForwarder](https://github.com/pppscn/SmsForwarder) - 监控 Android 手机短信、来电、APP通知，转发到 Bark
- [acme.sh](https://github.com/acmesh-official/acme.sh/wiki/notify#16-set-notification-for-ios-bark) - 证书生成通知
- [Uptime-Kuma](https://github.com/louislam/uptime-kuma) - 自托管监控工具，支持 Bark 告警
- [Apprise](https://github.com/caronc/apprise) - 多平台通知，支持 Bark
- [浏览器扩展](https://github.com/ij369/bark-sender) - 将网页内容发送到手机
- [RevenueBell](https://github.com/woxiqingxian/RevenueBell) - 苹果订阅收入事件推送
