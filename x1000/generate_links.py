#!/usr/bin/env python3
"""按天生成 Lululemon 采集链接（input.csv）"""
import csv
from datetime import datetime, timedelta
from urllib.parse import quote

# 6个关键词组
QUERY_GROUPS = {
    "A-整体讨论": '(lululemon OR @lululemon) lang:en -is:retweet',
    "B-化学品争议": '(lululemon OR @lululemon) (PFAS OR "forever chemicals" OR toxic OR chemical) lang:en -is:retweet',
    "C-健康安全": '(lululemon OR @lululemon) (health OR safety OR cancer OR immune OR harmful) lang:en -is:retweet',
    "D-透明度": '(lululemon OR @lululemon) (transparency OR disclose OR testing OR evidence OR report) lang:en -is:retweet',
    "E-绿洗质疑": '(lululemon OR @lululemon) (greenwashing OR sustainability OR hypocrisy) lang:en -is:retweet',
    "F-抵制声浪": '(lululemon OR @lululemon) (boycott OR refund OR trust OR betrayed OR "stop buying") lang:en -is:retweet',
}

def make_search_url(query: str, since: str, until: str) -> str:
    """生成 X 搜索链接"""
    q = f"{query} since:{since} until:{until}"
    return f"https://x.com/search?q={quote(q)}&src=typed_query"

def main():
    start = datetime(2026, 1, 1)
    end = datetime(2026, 7, 31)
    rows = []
    current = start

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        # since = 当天, until = 次日（X搜索左闭右开）
        next_day = current + timedelta(days=1)
        until_str = next_day.strftime("%Y-%m-%d")

        for group_name, query in QUERY_GROUPS.items():
            url = make_search_url(query, date_str, until_str)
            rows.append([url, group_name])
        
        current += timedelta(days=1)

    with open("/Users/hong/Desktop/x1000/input.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "关键词"])
        writer.writerows(rows)

    print(f"✅ 已生成 {len(rows)} 条链接 → input.csv")
    print(f"   时间范围：2026-01-01 ~ 2026-07-31")
    print(f"   关键词组：{len(QUERY_GROUPS)} 组")
    print(f"   天数：{(end - start).days + 1} 天")

if __name__ == "__main__":
    main()
