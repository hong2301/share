# hong-share

多终端文件共享技能，通过 Git 仓库实现跨设备临时文件中转。

## 功能

- 📤 上传文件到共享仓库
- 📥 从共享仓库拉取文件
- 🗑️ 清空共享仓库

## 支持平台

- Windows（PowerShell）
- macOS（Bash）
- Linux（Bash）

## 快速开始

### 1. 创建远程仓库

在 GitHub 或 Gitee 创建一个私有仓库，获取仓库地址。

### 2. 本地初始化

```bash
# 创建 share 目录
mkdir -p ~/Desktop/share && cd ~/Desktop/share

# 初始化并关联远程仓库
git init
git remote add origin <仓库地址>
git fetch origin
git branch -M master
```

### 3. 配置技能

编辑 `config.json`：

```json
{
  "share_dir": "~/Desktop/share",
  "remote": "origin",
  "branch": "master",
  "platform": "auto"
}
```

## 使用方式

### 通过 Pi AI 助手

直接对话即可：

- "把 xxx 上传到 share"
- "获取一下 share 的 xxx"
- "清空一下 share"

### 手动操作

```bash
cd ~/Desktop/share

# 推送
git add .
git commit -m "upload files"
git push origin master

# 拉取
git pull origin master
```

## 目录结构

```
hong-share/
├── SKILL.md           # AI 执行文档
├── README.md          # 人类阅读文档
├── config.json        # 配置文件
└── scripts/
    ├── share.ps1      # Windows 脚本
    └── share.sh       # Mac/Linux 脚本
```

## 常见问题

### Git 认证失败

使用个人访问令牌替代密码：

```bash
git remote set-url origin https://<token>@github.com/用户名/share.git
```

### 推送冲突

先拉取再推送：

```bash
git pull --rebase origin master
git push origin master
```

### 大文件上传失败

Git 单文件限制 100MB，建议压缩后传输。

## 许可

MIT License
