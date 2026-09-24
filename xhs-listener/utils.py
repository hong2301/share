import os
import sys
import argparse
from datetime import datetime


class Tee:
    """stdout 双写：同时输出到终端和日志文件"""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


def setup_log():
    """启动日志：在 log/ 目录下每次运行生成一个带时间戳的日志文件"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, datetime.now().strftime("main_%Y%m%d_%H%M%S.log"))
    sys.stdout = Tee(sys.__stdout__, open(log_path, "a", encoding="utf-8"))
    return log_path


def get_range_args():
    """外接参数 --start / --end，控制采集索引范围（从1开始，含端点；end=0表示到最后一条）"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0, help="0表示到最后一条")
    return parser.parse_args()