from DrissionPage import Chromium
import time
from urllib.parse import quote

port = 3348
dp = Chromium(port)
tab = dp.get_tab()

with open('input.csv', encoding='utf-8') as f:
    for kw in f:
        kw = kw.strip()
        if not kw:
            continue
        url = f'https://s.taobao.com/search?q={quote(kw)}&search_type=item&sourceId=tb.index'
        tab.get(url)

        input(2)
        

