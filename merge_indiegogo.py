# -*- coding: utf-8 -*-
"""
合并多个 indiegogo 处理目录（indiegogo, indiegogo2, ... 数量不限）：

用法：
    python3 merge_indiegogo.py                    # 自动发现 BASE 下所有 indiegogo* 目录
    python3 merge_indiegogo.py dir1 dir2 dir3 ... # 或手动指定目录名

合并规则：
1. links.csv：按 projectID 合并，状态优先级 done > no_comments > error > pending
   （pending 是待处理，其余都是处理过的）
2. 同一状态出现在多个目录时（冲突）：随机选一个目录的数据
3. comments_out_api / project_meta_api / indiegogo_main_api_progress 同名文件同理：
   取状态优先级最高目录中的文件，同优先级随机；最高状态目录没有该文件则顺延下一个状态

输出：BASE/indiegogo_total/
"""

import csv
import os
import random
import re
import shutil
import sys
from pathlib import Path

BASE = Path("/Users/hong/Desktop")
OUT_NAME = "indiegogo_total"
SUBS = ["comments_out_api", "project_meta_api", "indiegogo_main_api_progress"]

# 状态优先级，从高到低
STATUS_ORDER = ["done", "no_comments", "error", "pending"]
STATUS_RANK = {s: i for i, s in enumerate(STATUS_ORDER)}

DIR_RE = re.compile(r"^indiegogo\d*$")


def discover_dirs(args):
    """返回参与合并的目录名列表（按名称排序）。"""
    if args:
        return sorted(args)
    return sorted(p.name for p in BASE.iterdir() if p.is_dir() and DIR_RE.match(p.name))


def load_links(d):
    with open(BASE / d / "links.csv", encoding="utf-8-sig", newline="") as f:
        return {row["projectID"]: row for row in csv.DictReader(f)}


def status_rank(row):
    """行状态优先级数字（越小越优先），无行按 pending。"""
    return STATUS_RANK.get(row["status"] if row else "pending", len(STATUS_ORDER))


def pick_random_winner(candidates):
    """从候选 (目录, 行) 中随机选一个。"""
    return random.choice(candidates)


def main():
    dirs = discover_dirs(sys.argv[1:])
    if not dirs:
        print(f"[err] {BASE} 下没有找到 indiegogo* 目录")
        sys.exit(1)
    print(f"[info] 参与合并的目录 ({len(dirs)} 个): {dirs}")

    # ---------- 1. 读入所有 links.csv ----------
    rows = {d: load_links(d) for d in dirs}
    all_ids = list(rows[dirs[0]].keys())
    for d in dirs[1:]:
        for k in rows[d]:
            if k not in rows[dirs[0]]:
                print(f"[warn] {d} 有额外 projectID: {k}")
                all_ids.append(k)
    print(f"[info] 链接总数: {len(all_ids)}")

    # ---------- 2. 合并 links：每个 projectID 选状态优先级最高的目录行，同优先级随机 ----------
    merged = {}
    status_count = {}
    for pid in all_ids:
        # 按状态分组，取最高状态组
        best_rank = min(status_rank(rows[d].get(pid)) for d in dirs if rows[d].get(pid) is not None)
        candidates = [(d, rows[d][pid]) for d in dirs if rows[d].get(pid) is not None and status_rank(rows[d][pid]) == best_rank]
        d, row = pick_random_winner(candidates)
        merged[pid] = row
        status_count[row["status"]] = status_count.get(row["status"], 0) + 1

    out_rows = [merged[pid] for pid in all_ids]

    # ---------- 3. 输出合并后的 links.csv ----------
    out_dir = BASE / OUT_NAME
    out_dir.mkdir(exist_ok=True)
    fieldnames = list(out_rows[0].keys())
    with open(out_dir / "links.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"[links] 已写入 {out_dir / 'links.csv'} 共 {len(out_rows)} 行")
    print(f"[links] 状态分布: {status_count}")

    # ---------- 4. 合并 api 目录：同名文件取状态优先级最高目录的，同优先级随机 ----------
    for sub in SUBS:
        out_sub = out_dir / sub
        out_sub.mkdir(exist_ok=True)
        # 收集三目录所有文件: pid -> [(目录, path)]
        files = {}
        for d in dirs:
            sub_path = BASE / d / sub
            if not sub_path.exists():
                continue
            for name in os.listdir(sub_path):
                pid = name.rsplit("_", 1)[1].rsplit(".", 1)[0]
                files.setdefault(pid, []).append((d, sub_path / name))
        copied = 0
        for pid in all_ids:
            cands = files.get(pid)
            if not cands:
                continue
            # 按状态优先级升序排，同状态随机（shuffle 后稳定排序保证同组内顺序随机）
            random.shuffle(cands)
            cands.sort(key=lambda t: status_rank(rows[t[0]].get(pid)))
            src = cands[0][1]
            dst = out_sub / src.name
            shutil.copy2(src, dst)
            copied += 1
        print(f"[{sub}] 已合并 {copied} 个文件 → {out_sub}")

    # ---------- 5. 汇总报告 ----------
    print("\n===== 汇总 =====")
    for sub in SUBS:
        print(f"{sub}: {len(list((out_dir / sub).iterdir()))} 个文件")
    no_c = sum(1 for pid, r in merged.items() if r["status"] == "done" and not (out_dir / "comments_out_api" / f"comments_{pid}.csv").exists())
    print(f"done 但无 comments 文件: {no_c} 个")


if __name__ == "__main__":
    main()
