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

### 前置条件：Git 账号配置

**这是最关键的一步，必须优先完成！**

#### 检查是否已配置

```bash
# 检查 git 是否安装
git --version

# 检查是否配置过用户名
git config --global user.name
git config --global user.email

# 检查是否能连接 GitHub
ssh -T git@github.com
```

**判断结果**：
- 如果 `git --version` 无输出 → 未安装 git，需要先安装
- 如果 `user.name` 或 `user.email` 为空 → 未配置，需要配置
- 如果 `ssh -T` 返回 `Hi xxx! You've successfully authenticated` → 已配置成功

#### 情况一：未安装 Git

**Windows**：
1. 打开 https://git-scm.com/download/win
2. 下载安装包
3. 双击运行，一路点 "Next" 即可
4. 安装完成后重启终端

**Mac**：
```bash
xcode-select --install
```
点击 "安装" 等待完成

**Linux (Ubuntu/Debian)**：
```bash
sudo apt update
sudo apt install git -y
```

#### 情况二：未配置 Git 账号

```bash
# 设置用户名（填你的 GitHub 用户名）
git config --global user.name "你的用户名"

# 设置邮箱（填你的 GitHub 邮箱）
git config --global user.email "你的邮箱@example.com"
```

**询问用户**：请提供你的 GitHub/Gitee 用户名和邮箱

#### 情况三：未配置 SSH 密钥

**方式一：使用 SSH（推荐，更安全）**

1. 生成 SSH 密钥：

```bash
# 生成密钥（一路回车即可）
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 查看公钥
# Windows:
cat ~/.ssh/id_ed25519.pub
# Mac/Linux:
open ~/.ssh/id_ed25519.pub  # Mac 会自动打开
# 或者
cat ~/.ssh/id_ed25519.pub    # Linux
```

2. 复制公钥内容

3. 添加到 GitHub：
   - 打开 https://github.com/settings/keys
   - 点击 "New SSH key"
   - Title 填 "我的电脑"
   - Key 粘贴刚才复制的公钥
   - 点击 "Add SSH key"

4. 测试连接：

```bash
ssh -T git@github.com
```

成功会显示：`Hi 用户名! You've successfully authenticated...`

**方式二：使用 HTTPS + Token（简单但每次要输密码）**

1. 生成 Personal Access Token：
   - 打开 https://github.com/settings/tokens
   - 点击 "Generate new token"
   - Note 填 "share"
   - Expiration 选 "No expiration"
   - 勾选 `repo` 权限
   - 点击 "Generate token"
   - **立即复制 token（只显示一次！）**

2. 使用 token 替代密码：

```bash
# 将远程地址改为带 token 的格式
git remote set-url origin https://<token>@github.com/用户名/share.git
```

#### 验证配置完成

```bash
# 测试 SSH 连接
ssh -T git@github.com

# 成功输出：Hi 用户名! You've successfully authenticated...
```

**只有看到以上成功输出，才能继续下一步！**

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

### 第二步：自动检测默认值

在询问用户之前，先尝试获取默认值：

```bash
# 获取系统用户名
echo $USER  # Mac/Linux
echo %USERNAME%  # Windows

# 检测操作系统
uname -s  # Mac/Linux
ver  # Windows

# 检测桌面路径
ls ~/Desktop 2>/dev/null && echo "桌面存在"
```

**自动填充以下配置**：
- `username`：默认使用系统用户名
- `share_dir`：默认 `~/Desktop/share`（Mac/Linux）或 `C:/Users/用户名/Desktop/share`（Windows）
- `platform`：自动检测（auto）

### 第三步：创建远程仓库

引导用户在 GitHub/Gitee 创建仓库：

1. 打开 https://github.com 或 https://gitee.com
2. 点击 "New repository"
3. 仓库名填 `share`
4. 选择 **Private**（私有，避免文件泄露）
5. 不要勾选 "Add a README file"
6. 点击 "Create repository"
7. 复制仓库地址（格式如 `https://github.com/用户名/share.git`）

**询问用户**：请提供远程仓库地址（如 `https://github.com/xxx/share.git`）

### 第四步：本地初始化

**确认配置**（重要）：

```
请确认以下配置：

本地目录：~/Desktop/share
远程仓库：https://github.com/xxx/share.git

确认无误请回复"是"，否则请告诉我需要修改的内容
```

用户确认后，执行以下命令：

```bash
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

### 第五步：写入配置

**确认配置**（重要）：

```
最终配置如下：

{
  "share_dir": "~/Desktop/share",
  "remote": "origin",
  "branch": "master",
  "platform": "auto",
  "username": "zhangsan"
}

确认无误请回复"是"，否则请告诉我需要修改的内容
```

用户确认后，写入 `config.json`

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

## 初始化配置流程

首次使用时，按以下流程获取配置：

### 自动检测

先尝试自动获取默认值：
- `username`：从系统获取（`$USER` 或 `%USERNAME%`）
- `share_dir`：默认桌面下的 share 目录
- `platform`：自动检测操作系统

### 二次确认

以下重要配置需要用户确认：

1. **share_dir（本地目录）**
   - 显示默认值
   - 询问："是否使用此路径？"

2. **远程仓库地址**
   - 用户必须提供
   - 显示完整地址
   - 询问："确认此地址正确？"

3. **最终配置**
   - 显示完整的 config.json 内容
   - 询问："确认配置无误？"

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
5. 冲突策略：使用 `git pull -X ours`，冲突时以本地上传的文件为准
6. 返回上传结果

### 2. 清空 share

1. 用户明确说"清空"时直接执行，无需二次确认
2. 执行对应平台的清空脚本
3. 清空逻辑：删除所有文件 → 创建空提交 → 强制推送（保留历史记录）
4. 返回清空结果

### 3. 获取文件

1. 执行对应平台的拉取脚本
2. 在 `share_dir` 中搜索用户指定的文件
3. 找到则返回完整路径，未找到则返回当前文件列表

## 平台脚本

每个平台一个脚本，通过参数区分操作：

| 平台 | 脚本 | 用法 |
|------|------|------|
| Windows | `scripts/share.ps1` | `./share.ps1 upload file.txt` |
| Mac/Linux | `scripts/share.sh` | `./share.sh upload file.txt` |

### 操作示例

```bash
# 上传文件
./share.ps1 upload file1.txt file2.csv      # Windows
./share.sh upload file1.txt file2.csv       # Mac/Linux

# 拉取最新
./share.ps1 fetch                            # Windows
./share.sh fetch                             # Mac/Linux

# 清空（保留历史）
./share.ps1 clean                            # Windows
./share.sh clean                             # Mac/Linux
```

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
- 清空操作会保留历史记录，只是添加一个空提交
- 多终端同时操作时建议先拉取再推送
- 首次使用需要用户手动创建远程仓库
