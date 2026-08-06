# say-tts 技能部署文档

## 功能简介

say-tts 是一个文字转语音（TTS）技能，支持：
- 将文字转换为语音并播放
- 通过 Bark 推送通知到 iPhone
- 跨平台支持（Windows/Mac/Linux）

## 前置条件

### 1. 安装 Python

检查 Python 是否已安装：

```bash
python --version
```

如果未安装：
- **Windows**: 下载 https://www.python.org/downloads/
- **Mac**: `brew install python` 或从官网下载
- **Linux**: `sudo apt install python3 python3-pip`（Ubuntu/Debian）

### 2. 安装 Node.js（用于 Bark 通知）

检查 Node.js 是否已安装：

```bash
node --version
```

如果未安装：
- **Windows/Mac/Linux**: 下载 https://nodejs.org/

### 3. 安装 Python 依赖

```bash
pip install edge-tts pygame
```

## 部署步骤

### 第一步：创建技能目录

```bash
# 创建目录结构
mkdir -p ~/.pi/agent/skills/say-tts/scripts
mkdir -p ~/.pi/agent/skills/say-tts/docs
cd ~/.pi/agent/skills/say-tts
```

### 第二步：创建配置文件

创建 `config.json`：

```json
{
  "voice": "zh-CN-XiaoxiaoNeural",
  "bark_enabled": true
}
```

### 第三步：创建 say.py 脚本

创建 `scripts/say.py`：

```python
#!/usr/bin/env python3
import sys
import os
import asyncio
import tempfile
import pygame
import edge_tts

VOICE = "zh-CN-XiaoxiaoNeural"
TEXT = sys.argv[1] if len(sys.argv) > 1 else "晚上好，我是 hamster"

async def main():
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await edge_tts.Communicate(TEXT, VOICE).save(tmp_path)
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
```

### 第四步：创建 bark 通知脚本

创建 `scripts/notify.py`：

```python
#!/usr/bin/env python3
"""
Bark 推送通知脚本
用法: python notify.py "标题" "内容"
"""
import sys
import json
import urllib.request
import urllib.parse

CONFIG_PATH = os.path.expanduser("~/.config/bark/config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def send_bark(title, body, sound="calypso", group="Pi"):
    config = load_config()
    server = config["server"].rstrip("/")
    key = config["key"]
    
    payload = json.dumps({
        "title": title,
        "body": body,
        "sound": sound,
        "group": group
    }).encode()
    
    url = f"{server}/{key}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        if result.get("code") == 200:
            print(f"[bark] 已推送: {title}")
            return True
    except Exception as e:
        print(f"[bark] 推送失败: {e}")
        return False

if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "通知"
    body = sys.argv[2] if len(sys.argv) > 2 else "任务完成"
    send_bark(title, body)
```

### 第五步：配置 Bark 推送

#### 5.1 安装 Bark App

在 iPhone 上安装 Bark App：
- App Store 搜索 "Bark"
- 或访问 https://github.com/Finb/Bark

#### 5.2 获取推送地址

打开 Bark App，会显示一个推送地址，格式如：
```
https://api.day.app/xxxxxxxxxxxxxx
```

#### 5.3 创建配置文件

创建目录和配置文件：

```bash
mkdir -p ~/.config/bark
```

创建 `~/.config/bark/config.json`：

```json
{
  "server": "https://api.day.app",
  "key": "你的Bark Key",
  "sound": "calypso",
  "group": "Pi"
}
```

**重要**：将 `你的Bark Key` 替换为 Bark App 中显示的 Key。

#### 5.4 测试推送

```bash
node ~/.pi/agent/bin/bark.js "测试" "Bark 推送配置成功"
```

如果 iPhone 收到通知，说明配置成功。

### 第六步：创建 SKILL.md

创建 `SKILL.md`：

```markdown
---
name: say-tts
description: 将文字通过 edge-tts 转成语音并播放，支持单次朗读和重复朗读。触发词：say、tts、朗读、播放文字。
---

# say-tts

将文本转为语音并通过本地扬声器播放。

## 何时使用

当用户希望 AI 把一段文字读出来，或调用本地 TTS 能力时。

## 环境要求

- Python 3.8+
- 已安装依赖：`edge-tts`、`pygame`

安装依赖：

```bash
pip install edge-tts pygame
```

## 运行方式

### 单次朗读

```bash
python scripts/say.py "晚上好，我是 hamster"
```

### 推送通知

```bash
python scripts/notify.py "任务完成" "数据采集已完成"
```

## 触发词

以下任意表达都会触发 TTS：

- 直接朗读：`说...`、`朗读...`、`播放...`
- 讲述内容：`讲...`
- 描述性请求：`把...读出来`

## 回应规则

- 只要脚本正常执行，就默认用户已经听到声音
- 运行成功后，不要反问"你听到了吗"
- 只用极简短的方式确认已执行
```

## 验证部署

### 测试 TTS 功能

```bash
cd ~/.pi/agent/skills/say-tts
python scripts/say.py "你好，我是你的 AI 助手"
```

如果听到语音，说明 TTS 功能正常。

### 测试 Bark 推送

```bash
node ~/.pi/agent/bin/bark.js "测试" "部署成功"
```

如果 iPhone 收到通知，说明 Bark 推送正常。

## 常见问题

### Q: 提示 "No module named 'edge_tts'"

**A**: 安装依赖：

```bash
pip install edge-tts
```

### Q: 提示 "No module named 'pygame'"

**A**: 安装依赖：

```bash
pip install pygame
```

### Q: 没有声音

**A**: 检查：
1. 音频输出设备是否正常
2. 音量是否开启
3. Python 版本是否为 3.8+

### Q: Bark 推送失败

**A**: 检查：
1. `~/.config/bark/config.json` 是否存在
2. Key 是否正确
3. 网络是否正常

### Q: 提示 "config not found"

**A**: 创建配置文件：

```bash
mkdir -p ~/.config/bark
cat > ~/.config/bark/config.json << 'EOF'
{
  "server": "https://api.day.app",
  "key": "你的Bark Key",
  "sound": "calypso",
  "group": "Pi"
}
EOF
```

## 目录结构

```
~/.pi/agent/skills/say-tts/
├── SKILL.md           # 技能说明文档
├── config.json        # 配置文件
├── README.md          # 说明文档
├── docs/
│   └── DEPLOY.md      # 部署文档（本文件）
└── scripts/
    ├── say.py         # TTS 主脚本
    ├── say10.py       # 重复朗读脚本
    ├── notify.py      # Bark 推送脚本
    └── say.bat        # Windows 批处理
```

## 自动化集成

在 AI 任务完成后自动发送通知：

```bash
# 任务完成后
python ~/.pi/agent/skills/say-tts/scripts/notify.py "任务完成" "数据采集已完成"
```

或使用 bark.js：

```bash
node ~/.pi/agent/bin/bark.js "任务完成" "数据采集已完成"
```
