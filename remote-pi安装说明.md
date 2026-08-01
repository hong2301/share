# 用 Pi 安装 remote-pi 说明

> remote-pi 是 Pi coding agent 的扩展包，提供两大功能：
> 1. **本地 Agent 网络（mesh）**：同一台机器上多个 Pi 实例互相通信
> 2. **手机远程控制**：通过手机 App 远程给 Pi 发指令、看实时输出
>
> 版本：remote-pi 0.5.3

---

## 一、前置条件

- **Node.js 20+**（安装教程见桌面 `pi安装教程-Windows.md`）
- **已安装 Pi**（`npm install -g --ignore-scripts @earendil-works/pi-coding-agent`）

---

## 二、安装 remote-pi（一行命令）

在 Pi 终端里执行：

```text
pi install npm:remote-pi
```

安装内容：
- 注册 `/remote-pi` 斜杠命令
- 部署 agent 技能（教 LLM 使用 `agent_send` / `agent_request` 工具）

验证是否装好：

```text
/remote-pi config
```

正常会打印当前 relay 地址和来源（env / config / default）。

---

## 三、首次启动（向导）

```text
/remote-pi
```

第一次运行会问三个问题：
1. **Agent name** — 其他 agent 怎么称呼你（默认=目录名）
2. **Default session** — agent 网络的房间名（同一目录的多终端默认同房间）
3. **Auto-start relay?** — 是否自动连接 relay（手机控制需要选 Yes）

之后每次运行 `/remote-pi` 都会自动加入会话并启动 relay，无需再配置。

---

## 四、本地 Agent 网络（多终端互聊）

在同一目录开 **两个** Pi 终端，各自运行 `/remote-pi`，然后直接对话：

```
谁在我们的 agent 会话里？列出他们。
```

LLM 会自动调用 `agent_send` → broker → 返回其他 agent 名称。

常用命令：

| 命令 | 作用 |
|------|------|
| `/remote-pi join [name]` | 加入（或创建）一个会话 |
| `/remote-pi leave` | 离开当前会话 |
| `/remote-pi sessions` | 列出本地会话 |
| `/remote-pi rename <新名>` | 改名 |
| `/remote-pi status` | 查看 mesh + relay 状态 |
| `/remote-pi stop` | 停止本终端的 mesh + relay |

> 第一个进入会话的 agent 成为 leader（托管 broker），leader 退出后 follower 自动接管。

---

## 五、手机远程控制

### 1. 下载 App

所有下载渠道（Google Play / App Store / 直装包）：
`https://remote-pi.jacobmoura.work/#get-the-app`

### 2. 配对

relay 起来后（`/remote-pi relay status` 显示 started/paired）：

```text
/remote-pi pair
```

终端会打印 **二维码**，用 App 扫码即可。配对是**每台机器一次**，之后所有 Pi 进程都接受。

### 3. 管理已配对设备

```text
/remote-pi devices        # 列出
/remote-pi revoke <shortid>   # 撤销（shortid = devices 显示的前 8 位）
```

---

## 六、Relay（中继）选择

### 方式 A：社区公共 relay（默认，零配置）

`https://relay-rp1.jacobmoura.work`

- 共享基础设施，可用性 best-effort
- 中继只看到连接元数据，**消息内容端到端加密**

### 方式 B：自建 relay（注重隐私）

```bash
docker run -d \
  --name remote-pi-relay \
  -p 3000:3000 \
  --restart unless-stopped \
  ghcr.io/jacobaraujo7/remote-pi-relay:latest
```

推荐挂到 Tailscale / WireGuard VPN 后面，只有自己的设备能访问。

指定自己的 relay：

```text
/remote-pi relay url https://relay.yourdomain.tld
```

> URL 必须是 `http://` 或 `https://`（`ws://`/`wss://` 会被拒绝）。

优先级：环境变量 `REMOTE_PI_RELAY` > `~/.pi/remote/config.json` > 默认值。

---

## 七、守护进程模式（后台常驻 Pi）

适合让 Pi 24 小时后台运行、处理手机指令 / cron 定时任务。

### 一次性设置

```bash
# 全局安装 CLI（pi install 只装扩展，不暴露 CLI 命令）
npm install -g remote-pi

# 安装系统服务（Linux=systemd user，macOS=launchd）
remote-pi install
```

### 每个文件夹的流程

```bash
cd ~/某个目录
pi                                   # 先交互式配置好 /remote-pi

remote-pi create ~/某个目录 --name "名字"   # 注册为 daemon
remote-pi daemon start               # 启动
```

常用：

```bash
remote-pi daemons                    # 列表
remote-pi daemon status              # 详细状态
remote-pi daemon send <id> "提示词"  # 给指定 daemon 发指令
remote-pi daemon stop / restart      # 停止 / 重启
remote-pi cron add <id> "0 9 * * *" "每天总结" --tz Asia/Shanghai   # 定时任务
```

> ⚠️ 注意：daemon 模式下工具执行不弹确认框（Bash/Edit/Write 直接执行），先配好权限再启用。

---

## 八、配置文件位置

| 路径 | 作用域 | 内容 |
|------|--------|------|
| `<cwd>/.pi/remote-pi/config.json` | 每个目录 | agent_name / session_name / auto_start_relay |
| `~/.pi/remote/config.json` | 每个用户 | relay 地址 |
| `~/.pi/remote/peers.json` | 每台机器 | 已配对的手机设备 |
| `~/.pi/remote/sessions/<name>/` | 每个会话 | broker socket + audit.jsonl |
| `~/.pi/remote/skills/agent-network/SKILL.md` | 每个用户 | LLM 读的 agent 技能 |

---

## 九、常见问题

**Q: 手机连不上**
**A**: 检查两端 relay URL 是否一致；自建 relay 的话手机也要在同一 VPN 内。

**Q: `agent_request` 总是超时**
**A**: 默认 30s 超时；耗时任务接收方改用 `agent_send` 并带 `re: <原id>` 回复。

**Q: 同目录开多个终端报 `RoomAlreadyOpenError`**
**A**: 先停掉另一个终端的 `/remote-pi stop` 再启动。

**Q: 底部显示 🟡 relay waiting for pairing 但我配过了**
**A**: 图标只反映"本机是否配过设备"，重启 Pi 刷新缓存即可。

---

## 十、官方资源

- 主页：https://remote-pi.jacobmoura.work
- 源码：https://github.com/jacobaraujo7/remote_pi
- 自建 relay 指南：https://github.com/jacobaraujo7/remote_pi/blob/main/relay/README.md

---

*本说明由 hong-daemon 整理，2026-08-01*
