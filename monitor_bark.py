# -*- coding: utf-8 -*-
"""
Bark 监控: 检测 project_meta_api 目录 JSON 数量,
如果连续 5 分钟没有变化(采集疑似停止/卡住), 发 Bark 通知到 iPhone。

- 每分钟检查一次
- 连续 5 分钟文件数不变 -> 发通知(带当前数量与停滞时长)
- 防刷屏: 通知后冷却 30 分钟; 文件数一旦恢复变化立刻重置, 下次停滞满 5 分钟再触发

用法:
    python3 -u monitor_bark.py            # 前台
    nohup python3 -u monitor_bark.py > /dev/null 2>&1 &   # 后台
"""
import os
import subprocess
import time

WATCH_DIR = '/Users/hong/Desktop/indiegogo/运行包/project_meta_api'
INTERVAL = 60           # 检查间隔(秒)= 1 分钟
STALL_MIN = 5           # 连续 N 分钟无变化触发通知
NOTIFY_COOLDOWN = 1800  # 通知冷却(秒)= 30 分钟, 防刷屏
BARK = '/Users/hong/.pi/agent/bin/bark'
LOG = '/Users/hong/Desktop/indiegogo/运行包/monitor_bark.log'


def count_json():
    try:
        if not os.path.isdir(WATCH_DIR):
            return 0
        return len([f for f in os.listdir(WATCH_DIR) if f.endswith('.json')])
    except Exception:
        return -1


def send_bark(title, body):
    try:
        r = subprocess.run([BARK, '-t', title, '-b', body],
                           timeout=20, capture_output=True, text=True)
        out = (r.stdout or r.stderr or '').strip()
        log(f'bark 发送: {out or "OK"}')
        return True
    except Exception as e:
        log(f'bark 发送失败: {e}')
        return False


def log(msg):
    line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def main():
    last = None
    stall = 0           # 连续无变化的分钟数
    stall_start = None  # 本次停滞起始时间
    last_notify = 0     # 上次通知时间
    log(f'Bark 监控启动 | 监控目录: {WATCH_DIR} | 阈值: 连续 {STALL_MIN} 分钟无变化')

    while True:
        n = count_json()
        now = time.time()
        if last is None:
            last = n
            log(f'基线: 当前 {n} 个 JSON')
        elif n != last:
            if stall > 0:
                log(f'恢复采集: 文件数 {last} -> {n}(停滞 {stall} 分钟后), 监控已重置')
            else:
                log(f'文件数变化: {last} -> {n}')
            stall = 0
            stall_start = None
            last = n
        else:
            if stall == 0:
                stall_start = now
            stall += 1
            if stall >= STALL_MIN and now - last_notify >= NOTIFY_COOLDOWN:
                duration = max(5, int(now - stall_start) // 60)
                log(f'⚠️ 停滞预警: 连续 {duration} 分钟无变化, 当前 {n} 个 JSON, 发 Bark 通知')
                send_bark('⚠️ Indiegogo 采集停止', f'project_meta_api 已 {duration} 分钟无新增, 当前 {n} 个')
                last_notify = now
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()