from DrissionPage import Chromium, ChromiumOptions
import time
import random
import csv
import os
import re
import json
import openai

# ===================== 配置 =====================

tabPort = 2728

MAX_POSTS = 20  # 每个关键词最多采集的有效帖子数（AI 判断 valid=True 的帖子）

USE_AI = True  # 总开关：True=调用DeepSeek判断；False=跳过AI调用

token = 'sk-82ddcf2706654c7cbd1f87734bf7f646'

SYSTEM_PROMPT = """你是数据清洗助手，判断一条X(推特)帖子是否为需要保留的有效数据。
有效数据：与Lululemon品牌相关（含PFAS安全争议、危机讨论、品牌回应及相关话题）的真实英文内容（原创帖、带新观点的回复/引用帖均可）。
命中以下任一情况即判定无效(valid=false)：
1. 空文本：无实质内容
2. 非英文：主要内容不是英文
3. 纯转发：只有转发没有新增文字
4. 明显广告：营销推广性质
5. 优惠券/折扣码：含促销码、折扣信息、返利链接
6. 与Lululemon无关：内容与Lululemon毫无关联
7. 机器人/垃圾内容：模板化机器人发帖、垃圾信息
只输出JSON（不要输出任何其他文字），格式：
{"valid": true或false, "category": "有效/空文本/非英文/纯转发/广告/优惠券折扣码/与Lululemon无关/机器人垃圾", "reason": "不超过10个词的简短原因"}"""

# ===================== 主逻辑 =====================

def main():
    dp = Chromium(tabPort)
    tab = dp.get_tab()

    # 遍历 input.csv（url,关键词,状态） 状态: done=已完成 pending=待处理 error=出错
    tasks = []
    with open("input.csv", 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[1:]:  # 跳过表头
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            url = parts[0].strip()
            keyword = parts[1].strip() if len(parts) > 1 else ''
            status = parts[2].strip() if len(parts) > 2 else 'pending'
            tasks.append((url, keyword, status))

    # 帖子级去重 + 回复链历史（从已有 output.csv 恢复）
    done_urls, history = load_existing()

    for i, (url, keyword, status) in enumerate(tasks):
        if status in ('done', 'error'):
            print(f"{i + 1}/{len(tasks)}: {keyword} 已处理过（{status}），跳过")
            continue
        print(f"{i + 1}/{len(tasks)}: {url} | 关键词: {keyword}")
        try:
            tab.get(url)

            # 随机等待 5-10 秒
            time.sleep(random.uniform(5, 10))

            # 获取帖子
            checkNum=0
            postCount=0
            urls=set(done_urls)   # 已采集过的帖子全局去重
            while checkNum<5 and postCount<MAX_POSTS:
                checkNum+=1
                # 两种 article 布局：普通帖 / 带 r-1ut4w64 的布局，XPath 一次查两种
                postEles=tab.eles("xpath://article[contains(@class,'css-g5y9jx r-18u37iz r-1udh08x r-1c4vpko r-1c7gwzm r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21') or contains(@class,'css-g5y9jx r-1ut4w64 r-18u37iz r-1udh08x r-1c4vpko r-1c7gwzm r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21')]",timeout=1)
                for postEle in postEles:
                    try:
                        url=''
                        fbz=''
                        fbsj=''
                        zw=''
                        dz=''
                        hf=''
                        zf=''
                        ll=''
                        ht=''
                        handle=''
                        parentPostUrl=[]      # 被回复的原帖 URL（数组）
                        parentPostUserId=[]   # 被回复的用户ID（数组）
                        zfPostUrl=''
                        zfPostUserId=''
                        zfPostZw=''
                        zfPostZwLang=''
                        lang=''
                        ai_valid=''
                        ai_reason=''

                        urlEle=postEle.ele("@@tag()=a@@class=css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-xoduu5 r-1q142lx r-1w6e6rj r-9aw3ui r-3s2u2q r-1loqt21",timeout=0.5)
                        if urlEle:
                            url=urlEle.link
                            timeEle=urlEle.ele("@tag()=time",timeout=0.5)
                            if timeEle:
                                fbsj=timeEle.attr("datetime")
                            # 从帖子链接解析作者 handle（/handle/status/xxx）
                            mh = re.search(r'/([^/]+)/status/', url)
                            handle = mh.group(1) if mh else ''
                        if url in urls:
                            continue
                        postEle.scroll.to_see()
                        checkNum=0
                        urls.add(url)

                        fbzEles=postEle.eles("@@tag()=a@@class=css-g5y9jx r-1wbh5a2 r-dnmrzs r-1ny4l3l r-1loqt21",timeout=0.5)
                        for fbzEle in fbzEles:
                            if '@' in fbzEle.text:
                                fbz=fbzEle.text
                                break

                        # 被回复的原帖（本帖是回复时，可能@多个人，逐个匹配历史已采集帖子）
                        pBox=postEle.ele("@class=css-g5y9jx r-4qtqp9 r-zl2h9q",timeout=0.2)
                        if pBox:
                            if 'Replying to ' in pBox.text:
                                aEles=pBox.eles("@tag()=a",timeout=0.5)
                                for aEle in aEles:
                                    uid = aEle.text.strip()
                                    if not uid:
                                        continue
                                    parentPostUserId.append(uid)
                                    # 归一化：@elonmusk / Elon Musk → elonmusk，忽略大小写
                                    pid = re.sub(r'[@\s]', '', uid).lower()
                                    # 从最近的已采集帖子往回找，匹配该作者即命中
                                    for fb, hd, lu in reversed(history):
                                        if pid == re.sub(r'[@\s]', '', fb).lower() or (hd and pid == re.sub(r'[@\s]', '', hd).lower()):
                                            parentPostUrl.append(lu)
                                            break
                                if parentPostUrl:
                                    print(f"   ↳ 本帖回复了 {len(parentPostUrl)} 条: {parentPostUrl}")

                        zwEle=postEle.ele("xpath:.//div[@data-testid='tweetText']",timeout=1)
                        if zwEle:
                            # 只有真的点开了 Show more 才等它展开，并重新读正文
                            if seeMoreClick(postEle):
                                time.sleep(0.8)
                                zwEle=postEle.ele("xpath:.//div[@data-testid='tweetText']",timeout=0.5)
                            zw=zwEle.text
                            lang=zwEle.attr("lang")   # 帖子语言，如 en/ja
                            # 提取正文末尾的标签 #xxx
                            tags = re.findall(r'#\w+', zw)
                            ht = ' '.join(tags)

                        # AI 判断帖子是否有效（空文本/非英文/纯转发/广告/优惠券/无关/机器人）
                        if USE_AI:
                            ai_raw = getDataByAi(f"发布者:{fbz}\n正文:{zw}\n关键词:{keyword}")
                            ai_result = parseAiResult(ai_raw)
                            ai_valid = str(ai_result.get('valid', 'unknown'))
                            ai_reason = f"{ai_result.get('category','')} {ai_result.get('reason','')}".strip()
                            print(f"   AI判断: valid={ai_valid} | {ai_reason}")

                        # 转发
                        zfBox=postEle.ele("@class=css-g5y9jx r-adacv r-1udh08x r-1ets6dv r-1867qdf r-rs99b7 r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21",timeout=0.1)
                        if zfBox:
                            zfPostUserIdEles=zfBox.eles("@class=css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3",timeout=1)
                            for zfPostUserIdEle in zfPostUserIdEles:
                                if '@' in zfPostUserIdEle.text:
                                    zfPostUserId=zfPostUserIdEle.text
                                    old_url = tab.url
                                    zfPostUserIdEle.click(by_js=True)
                                    # click(by_js=True) 同步执行完就返回，页面跳转是异步的，
                                    # 必须等 URL 真正变化后再取数据，不能依赖 input()/固定 sleep
                                    try:
                                        tab.wait.url_change(old_url, timeout=5)
                                    except Exception:
                                        pass
                                    time.sleep(0.5)   # 新页面渲染缓冲
                                    zfPostUrl=tab.url
                                    zfPostZwEle=tab.ele("xpath:.//div[@data-testid='tweetText']",timeout=1)
                                    if zfPostZwEle:
                                        zfPostZw=zfPostZwEle.text
                                        zfPostZwLang=zfPostZwEle.attr("lang")
                                    tab.back()
                                    tab.wait.doc_loaded()
                                    print(zfPostZw)
                                    break

                        sjEle=postEle.ele("@class=css-g5y9jx r-1kbdv8c r-18u37iz r-1wtj0ep r-1ye8kvj r-1s2bzr4",timeout=0.5)
                        if sjEle:
                            sj=sjEle.attr("aria-label")
                            # 解析4个指标: repost, likes, bookmark/replies, views
                            m_repost  = re.search(r'(\d[\d,]*)\s*repost', sj)
                            m_likes   = re.search(r'(\d[\d,]*)\s*likes?', sj)
                            m_replies = re.search(r'(\d[\d,]*)\s*repl(?:y|ies)', sj)
                            m_book    = re.search(r'(\d[\d,]*)\s*bookmark', sj)
                            m_views   = re.search(r'(\d[\d,]*)\s*views?', sj)
                            zf = m_repost.group(1)  if m_repost  else '0'
                            hf = m_replies.group(1) if m_replies else (m_book.group(1) if m_book else '0')
                            dz = m_likes.group(1)   if m_likes   else '0'
                            ll = m_views.group(1)   if m_views   else '0'

                        # 即刻写入 CSV
                        CSV_PATH = "output.csv"
                        file_exists = os.path.exists(CSV_PATH)
                        with open(CSV_PATH, 'a', encoding='utf-8-sig', newline='') as f:
                            writer = csv.writer(f)
                            if not file_exists:
                                writer.writerow(['发布者', '发布时间', '正文', '点赞数', '回复数', '转发数', '浏览量', '话题标签', '关键词', '链接', '被回复的用户ID', '被回复的帖子链接', '转发原帖用户ID', '转发原帖正文', '转发原帖链接', 'AI有效', 'AI无效原因', '语言', '转发原帖语言'])
                            writer.writerow([fbz, fbsj, zw, dz, hf, zf, ll, ht, keyword, url, json.dumps(parentPostUserId, ensure_ascii=False), json.dumps(parentPostUrl, ensure_ascii=False), zfPostUserId, zfPostZw, zfPostUrl, ai_valid, ai_reason, lang, zfPostZwLang])
                        print(f"已写入: {fbz} | {fbsj}")
                        # 记录本条进历史，供后续帖子做回复链匹配
                        history.append((fbz, handle, url))
                        # 只统计有效帖子（AI 判断 valid=True；AI 关闭时全部算有效）
                        is_valid = (ai_valid == 'True') if USE_AI else True
                        if is_valid:
                            postCount += 1
                            print(f"   [有效 {postCount}/{MAX_POSTS}]")
                        if postCount >= MAX_POSTS:
                            break
                    except Exception as e:
                        pass
        except Exception as e:
            # 任务级出错（如页面打不开）→ 标 error，下次跳过（想重试手动改回 pending）
            print(f"  ✗ 任务出错: {e}")
            update_task_status(i, 'error')
            continue
        # 处理完标记 done（无论采满还是0条，下次跳过）
        update_task_status(i, 'done')
        print(f"  ✓ {keyword} 完成，共采 {postCount} 条有效")


# ===================== 辅助函数 =====================

def seeMoreClick(ele):
    try:
        # timeout 调小：没有按钮时不再白等 1 秒
        btns=ele.eles("@@tag()=button@@class=css-146c3p1 r-bcqeeo r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-fdjqy7",timeout=0.1)
        for btnItem in btns:
            if 'Show more' in btnItem.text:
                btnItem.click(by_js=True)
                return True
        return False
    except Exception as e:
        return False

def getDataByAi(text):
    try:
        client = openai.OpenAI(
            api_key=token,
            base_url="https://api.deepseek.com"
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            stream=False,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API调用出错: {e}")
        return None

def parseAiResult(res):
    if not res:
        return {'valid': 'unknown', 'category': '', 'reason': 'API调用失败'}
    m = re.search(r'\{.*\}', res, re.S)
    if m:
        res = m.group(0)
    try:
        return json.loads(res)
    except Exception:
        return {'valid': 'unknown', 'category': '', 'reason': res[:50]}

def load_existing():
    """读取已有 output.csv，返回：
    done_urls   所有已采集帖子的 url 集合（帖子级去重）
    history     已采集帖子 [(fbz, handle, url)]，供回复链匹配
    """
    done_urls = set()
    history = []
    if not os.path.exists("output.csv"):
        return done_urls, history
    with open("output.csv", 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return done_urls, history
        try:
            i_url = header.index('链接')
            i_fbz = header.index('发布者')
        except ValueError:
            # 表头不完整（旧格式），保守返回空
            return done_urls, history
        for row in reader:
            if len(row) <= max(i_url, i_fbz):
                continue
            u = row[i_url].strip()
            if not u:
                continue
            done_urls.add(u)
            mh = re.search(r'/([^/]+)/status/', u)
            hd = mh.group(1) if mh else ''
            history.append((row[i_fbz], hd, u))
    return done_urls, history

def update_task_status(task_idx, new_status):
    """把 input.csv 第 task_idx 个任务（0基，不含表头）的状态改为 new_status，立即写回"""
    with open("input.csv", 'r', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    if len(rows) <= task_idx + 1:
        return
    row = rows[task_idx + 1]
    if len(row) < 3:
        row.append(new_status)
    else:
        row[2] = new_status
    with open("input.csv", 'w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerows(rows)


if __name__ == '__main__':
    main()
