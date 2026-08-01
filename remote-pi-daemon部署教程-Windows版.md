# remote-pi Daemon 部署教程（Windows 版）

> 本教程针对 **Windows** 机器（本机实测环境：Node v25、pi 已装、remote-pi 0.5.3）。
> Windows 上 daemon 模式官方支持，底层用 **任务计划程序（Task Scheduler）** 实现。

---

## 一、Windows 上 daemon 是怎么跑的

```
登录 Windows ──触发──> 任务计划程序任务 "RemotePiSupervisor"
                          │ (wscript.exe 隐藏启动，不弹黑窗)
                          ▼
                    pi-supervisord（supervisor）
                          │ 管 理
                    ┌─────┴─────┐
                    ▼           ▼
                 daemon 1     daemon 2     （每个文件夹一个）
```

关键细节（来自源码，确认过）：

| 项目 | 值 |
|------|-----|
| 任务名 | `RemotePiSupervisor` |
| 触发时机 | **用户登录时**（LogonTrigger，非开机启动） |
| 启动方式 | `wscript.exe` 跑 VBScript 隐藏包装器，无控制台窗口 |
| 日志文件 | `C:\Users\Administrator\.pi\remote\supervisord.log` |
| 崩溃重启 | 自动，间隔 1 分钟，最多 999 次 |
| 安装权限 | 需要 **UAC 授权**（用 `schtasks /Create /XML` 注册任务） |
| 运行级别 | 最小权限（LeastPrivilege），当前登录用户 |

---

## 二、前置检查

```bash
node -v        # 需要 20+（本机 v25.0.0 ✅）
pi --version   # pi 已安装
```

---

## 三、安装步骤（三步）

### 第 1 步：全局安装 CLI

```bash
npm install -g remote-pi
```

> 说明：`pi install npm:remote-pi` 只装 pi 扩展，**PATH 上没有 `remote-pi` 命令**。
> 全局装才有 `remote-pi` 和 `pi-supervisord` 两个命令。

验证：

```bash
remote-pi --help
```

### 第 2 步：先交互式配置 + 配对（每个要部署的文件夹）

```bash
cd C:/Users/Administrator/hong
pi
```

在 pi 终端里依次执行：

```text
/remote-pi          # 向导：agent 名、session、auto-start relay 选 Yes
/remote-pi pair     # 手机 App 扫码配对（daemon 自己不能出二维码，必须先配！）
/remote-pi devices  # 确认手机已在列表
/remote-pi stop     # 退出交互会话，把位置让给 daemon
```

### 第 3 步：安装 supervisor 服务

```bash
remote-pi install
```

会发生什么：
1. 弹出 **UAC 授权窗口** → 点"是"
2. 生成任务 XML（UTF-16LE 编码）→ `schtasks /Create /XML ... /TN RemotePiSupervisor /F`
3. 立即运行任务：`schtasks /Run /TN RemotePiSupervisor`
4. 输出示例：
   ```
   [remote-pi] Supervisor service installed (windows).
     Unit: ...\task-scheduler.xml
   ```

> 安装时会把当时的 Node 路径和 PATH 写进任务；如果之后 Node 路径变了，重跑一次 `remote-pi install` 刷新。

---

## 四、注册并启动 daemon

```bash
# 注册（id 由文件夹路径生成，跨机器稳定）
remote-pi create C:/Users/Administrator/hong --name "hong-daemon"
# → Daemon registered: id=xxxx name="hong-daemon" cwd=C:/Users/Administrator/hong

# 启动所有 daemon
remote-pi daemon start

# 验证
remote-pi daemons
remote-pi daemon status      # pid、uptime、重启次数
```

之后每次登录 Windows，supervisor 会自动起来，daemon 跟着拉起。

---

## 五、日常命令

| 命令 | 作用 |
|------|------|
| `remote-pi daemons` | 列出所有 daemon 及状态 |
| `remote-pi daemon status` | 详细状态（pid/uptime/重启次数） |
| `remote-pi daemon start` | 启动所有 |
| `remote-pi daemon stop` | 停止所有 |
| `remote-pi daemon restart` | 重启所有（改配置后用它） |
| `remote-pi daemon send <id> "提示词"` | 给指定 daemon 发指令 |
| `remote-pi cron add <id> "0 9 * * *" "提示词" --tz Asia/Shanghai` | 定时任务 |
| `remote-pi cron list / run / enable / disable / remove / log` | cron 管理 |
| `remote-pi remove <id>` | 注销某个 daemon（保留配置） |
| `remote-pi uninstall` | 移除服务（保留 daemon 注册表） |

---

## 六、查看日志

```bash
tail -f C:/Users/Administrator/.pi/remote/supervisord.log
```

每个 daemon 的 stderr 带 `[<cwd>]` 前缀：

```bash
tail -f C:/Users/Administrator/.pi/remote/supervisord.log | grep '\[C:/Users/Administrator/hong\]'
```

也可以用任务计划程序图形界面看任务：

```text
Win+R → taskschd.msc → 任务计划程序库 → RemotePiSupervisor
```

---

## 七、排错（Windows 专项）

### 1. `remote-pi install` 没反应 / 报错
- **没弹 UAC**：用管理员 PowerShell 重跑一次
- **报 supervisor script not found**：先 `npm install -g remote-pi`，确认 `pi-supervisord` 在 PATH

### 2. 任务没随登录启动
```bash
schtasks /Query /TN RemotePiSupervisor /V   # 查看任务状态/上次结果
```
- 日志里 `pi: command not found` → 装 pi 之后没重跑 `remote-pi install`（PATH 没刷新）
- Node 路径变了 → 重跑 `remote-pi install`

### 3. daemon 一直 crashed
```bash
# 看该 daemon 的 stderr
tail -f C:/Users/Administrator/.pi/remote/supervisord.log | grep '\[<cwd>\]'

# 手动前台跑，看完整报错
cd <cwd>
REMOTE_PI_DAEMON=1 pi --mode rpc -e C:/Users/Administrator/AppData/Roaming/npm/node_modules/remote-pi/dist/index.js

# 修复后重启
remote-pi daemon restart
```

### 4. `daemon send` 提示 "daemon not running"
```bash
remote-pi daemon status
remote-pi daemon start
```

### 5. 手机连不上 daemon
- 配对必须在转 daemon **之前**做（daemon 不出二维码）
- 确认 relay URL 两端一致：`/remote-pi status` vs 手机 App 设置
- 改完 relay 后 `remote-pi daemon restart`

### 6. 彻底重装
```bash
remote-pi uninstall
rm -rf C:/Users/Administrator/.pi/remote
npm uninstall -g remote-pi
npm install -g remote-pi
remote-pi install
# 重新配对、重新 create daemon
```

---

## 八、注意事项（Windows 特有）

1. **登录才启动**：任务是 LogonTrigger，**用户未登录不会跑**。如需开机即跑，可手动用 `schtasks /Create /RU` 存密码改成"不管用户是否登录都运行"（需要管理员，超出本工具默认行为）
2. **工具不弹确认**：daemon 模式下 Bash/Edit/Write 直接执行，先配好权限再启用
3. **UAC 依赖**：第一次 `install` 和 `uninstall` 需要你点 UAC
4. **一个文件夹一个 daemon**：同目录重复 `create` 会被拒绝
5. **日志只有一份**：所有 daemon 输出都进 `supervisord.log`

---

## 九、诊断速查

```bash
# 任务是否注册
schtasks /Query /TN RemotePiSupervisor

# daemon 注册表（可手动修）
type C:/Users/Administrator/.pi/remote/daemons.json

# 已配对设备
type C:/Users/Administrator/.pi/remote/peers.json

# 快速存活检查
remote-pi daemon status
```

---

*本教程由 hong-daemon 整理（Windows 实测版），2026-08-01*
