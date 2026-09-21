# Bark Notify Skill

🔔 Bark 推送通知 Skill - 将消息推送到 iPhone

## 简介

这是一个完整的 Bark 推送通知封装，支持：

- 📱 命令行直接推送
- 🎵 30+ 种内置铃声
- 🔢 角标动态设置
- 📊 推送级别控制（穿透专注模式）
- 🎯 智能参数推断
- ⚙️ 配置文件管理

## 快速开始

### 1. 配置 Key

从 Bark App 复制你的 device key，编辑 `config.json`：

```json
{
  "server": "https://api.day.app",
  "key": "你的key",
  "default_sound": "calypso",
  "default_group": "Pi"
}
```

### 2. 发送推送

```bash
# 简单推送
node scripts/bark.js notify "标题" "内容"

# 带铃声和分组
node scripts/bark.js notify -s alarm -g 监控 "告警" "CPU 过高"

# 穿透专注模式
node scripts/bark.js notify --time-sensitive "紧急" "需要立即处理"
```

### 3. 测试

```bash
node scripts/bark.js test
```

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `notify` | 发送推送 | `notify "标题" "内容"` |
| `badge` | 设置角标 | `badge 5` |
| `sound` | 设置默认铃声 | `sound alarm` |
| `config` | 查看/修改配置 | `config default_sound bell` |
| `sounds` | 列出所有铃声 | `sounds` |
| `badges` | 列出角标预设 | `badges` |
| `test` | 测试推送 | `test` |

## 参数说明

### 推送选项

| 选项 | 简写 | 说明 |
|------|------|------|
| `--sound` | `-s` | 铃声名称 |
| `--group` | `-g` | 消息分组 |
| `--level` | `-l` | 推送级别 |
| `--time-sensitive` | | 时效性通知 |
| `--icon` | | 自定义图标 URL |
| `--url` | | 点击跳转链接 |
| `--image` | | 推送图片 URL |
| `--subtitle` | | 副标题 |
| `--copy` | | 复制到剪贴板 |
| `--markdown` | | Markdown 正文 |

### 推送级别

| 级别 | 说明 |
|------|------|
| `active` | 默认，亮屏显示 |
| `timeSensitive` | 时效性，穿透专注模式 |
| `passive` | 仅通知列表，不亮屏 |
| `critical` | 重要警告，静音也响 |

## 铃声列表

### 警报类
- `alarm` - 警报声
- `sharp` - 尖锐音效
- `riser` - 上升音效
- `tritone` - 三全音
- `phone` - 电话铃声

### 通知类
- `calypso` - 默认铃声
- `bell` - 铃声
- `chime` - 风铃声
- `glass` - 玻璃声
- `pulse` - 脉冲声
- `sonar` - 声纳音效

### 成功类
- `complete` - 完成提示音
- `hero` - 英雄音效
- `victory` - 胜利音效
- `payment` - 支付提示音

## Python 集成

```python
import subprocess

BARK = '/Users/hong/mac/巧克力加工厂/skills/bark-notify/scripts/bark.js'

def send_bark(title, body, sound='calypso', group='Pi'):
    cmd = ['node', BARK, 'notify', '-s', sound, '-g', group, title, body]
    return subprocess.run(cmd, capture_output=True, timeout=20).returncode == 0

# 使用
send_bark('完成', '任务已完成', sound='complete')
```

## 文件结构

```
bark-notify/
├── SKILL.md           # Skill 主文档
├── README.md          # 本文件
├── config.json        # 配置文件（含 key）
├── config.example.json # 配置示例
├── sounds.json        # 铃声库
├── badges.json        # 角标库
└── scripts/
    └── bark.js        # 主脚本
```

## 获取 Key

1. App Store 搜索「Bark」安装
2. 打开 App
3. 点击「测试推送」复制 URL
4. URL 格式：`https://api.day.app/{key}/...`
5. 复制 `{key}` 部分到 `config.json`

## 常见问题

**Q: 推送没有声音？**
- 检查 iPhone 静音模式
- 确认 App 通知权限
- 使用 `level: critical` 突破静音

**Q: 如何穿透专注模式？**
```bash
node scripts/bark.js notify --time-sensitive "标题" "内容"
```

**Q: 如何清除角标？**
```bash
node scripts/bark.js badge 0
```

## 相关链接

- [Bark 官方文档](https://bark.day.app)
- [Bark GitHub](https://github.com/Finb/Bark)
- [参数详解](https://bark.day.app/#/params)

## License

MIT
