---
name: hong-share
description: 多终端通过本地 Git 仓库临时共享文件。支持任意数量的 PC/Mac/Linux 终端互通，只要能连接到该仓库即可。当用户说"把...上传到 share"、"清空一下 share"或"获取一下 share 的..."时触发。
---

# hong-share

用于多终端之间临时中转文件的 Git 共享仓库工作流。

## 工作原理

```
终端A ──推送──> 远程仓库 ──拉取──> 终端B
```

每个终端将文件推送到同一个远程 Git 仓库，其他终端拉取即可获取。

## 首次使用搭建流程

当用户首次使用此技能时，按以下步骤引导：

### 第一步：环境检查

执行以下检查，确认本机具备基本条件：

```bash
# 检查 git 是否安装
git --version
```

- **成功**：显示版本号（如 `git version 2.x.x`）
- **失败**：提示用户安装 git
  - Windows：下载 https://git-scm.com/download/win
  - Mac：执行 `xcode-select --install`
  - Linux：执行 `sudo apt install git`（Ubuntu/Debian）

### 第二步：创建远程仓库

引导用户在 GitHub/Gitee 创建仓库：

1. 打开 https://github.com 或 https://gitee.com
2. 点击 "New repository"
3. 仓库名填 `share`
4. 选择 **Private**（私有，避免文件泄露）
5. 不要勾选 "Add a README file"
6. 点击 "Create repository"
7. 复制仓库地址（格式如 `https://github.com/用户名/share.git`）

**询问用户**：请提供远程仓库地址（如 `https://github.com/xxx/share.git`）

### 第三步：本地初始化

用户提供仓库地址后，执行以下命令：

```bash
# 选择 share 目录位置（默认桌面）
# Windows: C:/Users/用户名/Desktop/share
# Mac/Linux: ~/Desktop/share

# 创建目录
mkdir -p ~/Desktop/share
cd ~/Desktop/share

# 初始化 git
git init

# 关联远程仓库（替换为用户提供的地址）
git remote add origin <用户提供的仓库地址>

# 拉取远程内容
git fetch origin

# 创建并切换到主分支
git branch -M master
git pull origin master || true
```

### 第四步：配置技能

将以下内容写入 `config.json`：

```json
{
  "share_dir": "本机share目录的绝对路径",
  "remote": "origin",
  "branch": "master",
  "platform": "auto"
}
```

`platform` 可选值：
- `auto`：自动检测
- `win`：Windows
- `mac`：Mac
- `linux`：Linux

### 第五步：验证联通

执行拉取测试，确认配置正确：

```bash
cd <share_dir>
git status
git pull origin master
```

**成功标志**：
- `git status` 显示 "On branch master"
- `git pull` 无报错

**失败处理**：
- "fatal: remote origin already exists" → 远程已配置，跳过 `git remote add`
- "error: failed to push some refs" → 先执行 `git pull --rebase origin master`
- "fatal: could not read Username" → 仓库地址需要认证，引导用户配置 token

## 自检流程

每次执行操作前，自动执行以下检查：

| 检查项 | 命令 | 成功标志 |
|--------|------|----------|
| 配置文件 | 读取 `config.json` | 存在且 `share_dir` 非空 |
| 目录存在 | `ls <share_dir>` | 无报错 |
| Git 仓库 | `ls <share_dir>/.git` | 目录存在 |
| Git 状态 | `cd <share_dir> && git status` | 显示分支信息 |
| 远程配置 | `cd <share_dir> && git remote -v` | 显示远程地址 |

**任一检查失败时**：
1. 告知用户哪一步失败
2. 提供具体的修复命令
3. 修复后重新自检

## 触发条件

用户出现以下任意意图时触发：

1. **上传文件到 share**
   - "把 xxx 上传到 share"
   - "传 xxx 到 share"
   - "share 里放 xxx"

2. **清空 share**
   - "清空一下 share"
   - "把 share 清空"
   - "clean share"

3. **从 share 获取文件**
   - "获取一下 share 的 xxx"
   - "从 share 拿 xxx"
   - "share 里有没有 xxx"

4. **初始化/配置 share**
   - "配置 share"
   - "设置 share"
   - "share 怎么用"

## 执行规则

### 1. 上传文件

1. 自检通过后，解析用户给出的文件/目录路径
2. 检查源文件是否存在，不存在则告知用户并停止
3. 复制文件到 `share_dir`（保留原文件名，已存在则覆盖）
4. 执行对应平台的上传脚本
5. 返回上传结果

### 2. 清空 share

1. 用户明确说"清空"时直接执行，无需二次确认
2. 执行对应平台的清空脚本
3. 返回清空结果

### 3. 获取文件

1. 执行对应平台的拉取脚本
2. 在 `share_dir` 中搜索用户指定的文件
3. 找到则返回完整路径，未找到则返回当前文件列表

## 平台脚本映射

| 操作 | Windows | Mac/Linux |
|------|---------|-----------|
| 上传 | `scripts/share-upload.ps1` | `scripts/share-upload.sh` |
| 拉取 | `scripts/share-fetch.ps1` | `scripts/share-fetch.sh` |
| 清空 | `scripts/share-clean.ps1` | `scripts/share-clean.sh` |

## 常见问题

### Q: 提示 "fatal: remote origin already exists"
**A**: 远程已配置，跳过添加步骤，直接执行 `git fetch origin`

### Q: 提示 "error: failed to push some refs"
**A**: 本地与远程有冲突，执行：
```bash
git pull --rebase origin master
git push origin master
```

### Q: 提示 "fatal: could not read Username"
**A**: 需要认证，使用个人访问令牌：
```bash
# GitHub: Settings → Developer settings → Personal access tokens
# 生成 token 后，将地址改为：
git remote set-url origin https://<token>@github.com/用户名/share.git
```

### Q: 推送大文件失败
**A**: Git 限制单个文件不超过 100MB，建议压缩后传输

### Q: 多终端同时修改同一文件冲突
**A**: 先拉取再推送：
```bash
git pull origin master
# 解决冲突（如有）
git push origin master
```

## 注意事项

- 该仓库只用于临时中转，不要传大文件或敏感文件
- 清空操作会强制推送，会重写分支历史
- 多终端同时操作时建议先拉取再推送
- 首次使用需要用户手动创建远程仓库
