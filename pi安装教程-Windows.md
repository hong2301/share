# Pi 安装教程（Windows）

> Pi 是一个运行在终端里的 AI 编程助手（coding agent）。
> 本文档适用于 **Windows 10/11**。

---

## 一、前置条件

### 1. 安装 Node.js（含 npm）

Pi 通过 npm 安装，需要 Node.js 18+。

- 下载地址：https://nodejs.org/
- 选择 **LTS 版本** 下载，双击安装，一路 Next
- 安装完打开终端验证：

```bash
node -v
npm -v
```

### 2. 安装 Git for Windows（提供 bash）

**重要**：Pi 在 Windows 上要求有 bash shell，推荐用 Git Bash。

- 下载地址：https://git-scm.com/download/win
- 双击安装，一路 Next（默认选项即可）
- 安装完验证：

```bash
git --version
```

Pi 会按顺序查找 bash：
1. `~/.pi/agent/settings.json` 里自定义的 `shellPath`
2. Git Bash（`C:\Program Files\Git\bin\bash.exe`）
3. PATH 里的 `bash.exe`（Cygwin / MSYS2 / WSL）

---

## 二、安装 Pi

### 方式一：npm 全局安装（推荐）

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

> `--ignore-scripts` 跳过依赖的生命周期脚本，pi 正常安装不需要它。

### 方式二：官方安装脚本

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

> Windows 下在 Git Bash 里执行。

### 验证安装

```bash
pi --version
```

---

## 三、配置 AI Provider

### 方式 A：设置环境变量

```powershell
# PowerShell 临时设置
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# 永久设置
setx ANTHROPIC_API_KEY "sk-ant-..."
```

```bash
# Git Bash / WSL
export ANTHROPIC_API_KEY=sk-ant-...
```

### 方式 B：使用其他 Provider

Pi 支持多种 provider（Anthropic / OpenAI / OpenRouter / DeepSeek 等）。

用 OpenRouter：

```bash
$env:OPENROUTER_API_KEY = "sk-or-..."
```

用 DeepSeek（示例，需按实际配置）：

```bash
$env:DEEPSEEK_API_KEY = "sk-..."
```

也可以用 `pi` 的 `/provider` 命令或编辑 `~/.pi/agent/settings.json` 选择默认 provider 和模型：

```json
{
  "defaultProvider": "opencode-go",
  "defaultModel": "deepseek-v4-flash"
}
```

---

## 四、启动 Pi

```bash
pi
```

首次启动会询问是否信任当前项目文件夹（`~/.pi/agent/trust.json` 会记住选择）。

常用操作：

| 操作 | 说明 |
|------|------|
| 直接对话 | 输入文字回车，pi 会调用工具完成任务 |
| `!命令` | 执行 bash 命令并把输出发给 AI |
| `!!命令` | 只执行命令，不发给 AI |
| `/compact` | 手动压缩上下文 |
| `@文件` | 引用项目文件 |
| `Ctrl+G` | 打开外部编辑器（Windows 默认记事本） |

---

## 五、安装技能 / 扩展 / 包

```bash
# npm 包
pi install npm:@foo/pi-tools

# Git 仓库（技能/扩展）
pi install git:github.com/user/repo
pi install https://github.com/user/repo

# 卸载
pi uninstall npm:@foo/pi-tools
```

技能目录：`~/.pi/agent/skills/`（手写 SKILL.md 放入即可）

---

## 六、常见问题

### Q: 提示找不到 bash
**A**: 安装 Git for Windows，或手动指定：
```json
{
  "shellPath": "C:\\Program Files\\Git\\bin\\bash.exe"
}
```

### Q: npm 安装报权限错误
**A**: 用管理员 PowerShell 执行，或设置 npm 全局目录。

### Q: 启动后无法连接模型
**A**: 检查 API Key 是否正确、网络能否访问对应 provider。

### Q: 想换模型
**A**: 会话内 `/models` 查看列表，`/provider` 切换 provider。

---

## 七、官方文档

- 完整文档：`C:\Users\Administrator\AppData\Roaming\npm\node_modules\@earendil-works\pi-coding-agent\docs\`
- Windows 专属说明：`docs/windows.md`
- 官方站点：https://pi.dev

---

*本教程由 hong-daemon 整理，2026-08-01*
