---
name: hong-share
description: 多终端（Mac/Windows/Linux）通过本地 Git 仓库临时共享文件。当用户说"把...上传到 share"、"清空一下 share"或"获取一下 share 的..."时触发。只有用户明确要求才操作，禁止自动同步。
---

# hong-share

多终端通过同一个远程 Git 仓库（GitHub/Gitee）临时中转文件。任一端 push，其他端 pull 即可获取。

## 配置

- 配置文件：`<技能目录>/config.json`
- 本地 share 目录：`/Users/hong/mac/share`
- 脚本：`scripts/share.sh`（Mac/Linux）、`scripts/share.ps1`（Windows）

```json
{
  "share_dir": "/Users/hong/mac/share",
  "remote": "origin",
  "branch": "master",
  "platform": "mac",
  "username": "hong"
}
```

## 触发条件

用户明确表达以下意图时触发：

1. **上传**："把 xxx 上传到 share"、"传 xxx 到 share"、"share 里放 xxx"
2. **清空**："清空一下 share"、"把 share 清空"、"clean share"
3. **获取**："获取一下 share 的 xxx"、"从 share 拿 xxx"、"share 里有没有 xxx"
4. **配置**："配置 share"、"设置 share"、"share 怎么用"

## 禁止自动操作（重要）

**只有用户明确说要操作 share 时才执行任何 Git 操作。**

没有明确说时，绝对不要：
- 自动 commit / push / pull / fetch
- 修改技能文件后顺手同步到 share
- 因为"上次用过"就执行 Git 操作

不确定用户意图时，先询问确认。

## 分支规则

- 默认操作在 `master` 分支
- 其他分支**可用**，但必须用户**明确指定**（如"把文件传到 dev 分支"）才切换
- 用完后必须**立即切回 master**
- 分支名从 config.json 的 `branch` 读取

## 自检（每次操作前）

1. `config.json` 存在且 `share_dir` 非空
2. share 目录存在且有 `.git`
3. 在 `master` 分支（用户指定其他分支时除外）
4. `git remote -v` 显示远程地址

失败时：告知用户 + 给修复命令。

## 执行规则

统一调用脚本：`scripts/share.sh <action> <files...>`

### 上传
1. 自检通过，默认 master 分支
2. 解析文件路径，检查存在
3. 调用 `share.sh upload <path...>`（脚本内完成：复制 → pull -X ours → commit → push）
4. 返回结果

### 清空
1. 用户明确说清空，无需二次确认
2. 调用 `share.sh clean`（删除文件 → 空提交 → 强制推送，保留历史）

### 获取
1. 调用 `share.sh fetch` 拉取
2. 在 share_dir 中搜索目标文件
3. 找到返回完整路径；未找到返回文件列表

## 冲突策略

脚本默认 `git pull -X ours`：冲突时**以本地上传的为准**。

## 常见问题

- **push 被拒**：先 `git pull -X ours origin master` 再 push
- **分支偏离**：`git fetch && git reset --hard origin/master`（会丢本地差异）
- **认证失败**：配 token，`git remote set-url origin https://<token>@github.com/用户名/share.git`
- **大文件**：单文件 ≤100MB，大文件先压缩

## 注意事项

- 临时中转用，不传大文件/敏感文件
- 清空保留历史（空提交）
- 多终端同时操作时先拉取再推送
