# hong-share 📦

**多终端文件共享技能**——通过一个私有 Git 仓库，让 Mac / Windows / Linux / 手机之间随时中转文件。

> 把 GitHub 私有仓库当免费云盘用：任一设备 push 文件，其他设备 pull 即可获取。

## 能做什么

| 功能 | 说明 |
|---|---|
| 📤 **上传** | 把文件/文件夹推到共享仓库 |
| 📥 **拉取** | 从共享仓库取文件到本机 |
| 🗑️ **清空** | 一键清空仓库（保留历史记录） |
| 🔀 **多端互通** | 任意数量的设备连同一个仓库即可互传 |

## 工作原理

```
设备A ──push──> GitHub 私有仓库 ──pull──> 设备B / 设备C / ...
```

## 快速开始

### 1. 创建私有仓库

在 GitHub（或 Gitee）新建一个仓库，命名为 `share`，**选择 Private**，不要勾选 README。

### 2. 本地初始化（每台设备一次）

```bash
# 创建 share 目录
mkdir -p ~/Desktop/share && cd ~/Desktop/share

# 初始化并关联远程仓库
git init
git remote add origin <你的仓库地址>
git fetch origin
git branch -M master
git pull origin master
```

### 3. 配置 config.json

```json
{
  "share_dir": "~/Desktop/share",
  "remote": "origin",
  "branch": "master",
  "platform": "auto",
  "username": "你的名字"
}
```

## 使用方式

### 通过 AI 助手对话（推荐）

直接说人话即可：

```text
把 /Users/hong/Desktop/report.pdf 上传到 share
```

```text
获取一下 share 的 report.pdf
```

```text
清空一下 share
```

> ⚠️ **重要**：AI 只在你说出明确指令时才会操作 share。日常聊天、改技能文件等**不会**自动同步。

### 手动操作

```bash
cd ~/Desktop/share

# 上传
git add .
git commit -m "upload files"
git push origin master

# 拉取
git pull origin master
```

### 使用脚本

```bash
# Mac / Linux
./scripts/share.sh upload file1.csv file2.csv
./scripts/share.sh fetch
./scripts/share.sh clean

# Windows (PowerShell)
./scripts/share.ps1 upload file1.csv file2.csv
./scripts/share.ps1 fetch
./scripts/share.ps1 clean
```

## 分支管理

- 默认操作在 `master` 分支
- 需要其他分支时**明确指定**："把文件传到 dev 分支"
- 用完后**立即切回 master**

## 冲突处理

推送冲突时以**本地上传的版本**为准：

```bash
git pull -X ours origin master
git push origin master
```

## 常见问题

**Q: push 被拒绝？**
A: 先拉取再推送：`git pull -X ours origin master && git push origin master`

**Q: Git 认证失败？**
A: 用个人访问令牌（Settings → Developer settings → Personal access tokens），然后：
```bash
git remote set-url origin https://<token>@github.com/用户名/share.git
```

**Q: 大文件传不上？**
A: Git 单文件上限 100MB，大文件先压缩再传。

**Q: 多设备同时改同一个文件冲突？**
A: 先 `git pull -X ours origin master` 再推送，以本地版本为准。

## 目录结构

```
hong-share/
├── SKILL.md           # AI 执行文档（给 AI 看）
├── README.md          # 本文件（给人看）
├── config.json        # 配置（每台设备不同）
└── scripts/
    ├── share.sh       # Mac / Linux 脚本
    └── share.ps1      # Windows 脚本
```

## 许可

MIT License
