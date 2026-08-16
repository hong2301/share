# -*- coding: utf-8 -*-
"""
遍历 links.csv 中 status=pending 的链接，使用 Indiegogo 评论 API 采集评论。

认证方式：
- 用 DrissionPage 打开项目原链接，等待重定向到真实 URL
- 然后直接访问真实 URL 的 /comments 页面获取 cookie 和 commentThreadID
- 之后全部使用 requests 请求 API，一页一页追加写入

输出：
- comments_out_api/comments_<projectID>.csv
- 更新 links.csv 的 status 和 comment_count

使用方式：
    cd /Users/hong/Desktop/评论
    python3 main_api.py

首次运行前请确保端口 4830 的浏览器已启动并通过 Cloudflare 验证。
"""

import csv
import json
import re
import time
from pathlib import Path

from curl_cffi import requests
from DrissionPage import Chromium

# ==================== 配置 ====================
LINKS_CSV = Path("links.csv")
OUTPUT_DIR = Path("comments_out_api")
PROJECT_META_DIR = Path("project_meta_api")
PROGRESS_DIR = Path("indiegogo_main_api_progress")
BROWSER_PORT = 4841

S_PENDING = "pending"
S_DONE = "done"
S_NO_COMMENT = "no_comments"
S_ERROR = "error"


class EmptyLinkError(Exception):
    """项目链接被重定向到 Indiegogo 首页，视为空链接。"""
    pass


class NoCommentsError(Exception):
    """项目页没有 Comments 按钮或评论数为 0。"""
    pass

def is404(tab):
    """判断当前页面是否为 404 页面（空链接）。"""
    try:
        title = tab.title
        if title and '404' in title:
            return True
        html = tab.html
        for marker in ('404: Page Not Found', 'Page Not Found', 'page-not-found'):
            if marker in html:
                return True
    except Exception:
        pass
    return False

def is_homepage(url):
    """判断 URL 是否为 Indiegogo 首页（被重定向后无效的项目页）。"""
    if not url:
        return True
    # 首页 URL 通常形如 https://www.indiegogo.com/zh/#/ 或 /en/#/
    # 有效项目页一定包含 /projects/
    return "/projects/" not in url

OUT_FIELDNAMES = ["comment_id", "parent_id", "depth", "name", "is_creator", "content", "created_at", "url", "raw"]

DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "content-type": "application/json",
    "origin": "https://www.indiegogo.com",
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
}


# ==================== 文件读写 ====================
def load_tasks():
    """读取 links.csv，返回所有行和字段名。兼容 status / comment_status 两种列名。"""
    with LINKS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    fieldnames = reader.fieldnames or ["link", "sortId", "status", "comment_count"]
    # 兼容 comment_status -> status
    if "status" not in fieldnames and "comment_status" in fieldnames:
        for r in rows:
            r["status"] = r.get("comment_status", "")
        fieldnames.append("status")
    # 统一 sortId：优先 sortId 列，其次旧 id 列（main.py 格式），再其次旧 projectID 列，最后用行索引
    if "sortId" not in fieldnames:
        fieldnames.append("sortId")
        for i, r in enumerate(rows):
            if r.get("id"):
                r["sortId"] = r["id"]
            elif r.get("projectID"):
                r["sortId"] = r["projectID"]
            else:
                r["sortId"] = str(i)
    # 移除已废弃的列（projectID / id），写回时不再输出
    for col in ("projectID", "id"):
        if col in fieldnames:
            fieldnames.remove(col)
    return rows, fieldnames


def save_tasks(rows, fieldnames):
    """写回 links.csv。"""
    with LINKS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ==================== 认证：加载原链接 -> 重定向 -> 访问 /comments ====================
def get_auth_from_browser(dp, link, save_project_id=None):
    """
    使用 DrissionPage 获取 cookie 和 commentThreadID。
    如果 link 已经是评论链接（含 /comments），直接访问；
    否则先打开项目原链接，重定向后再构造 /comments 链接访问。
    save_project_id 用于 JSON 文件名，默认使用从页面读取的 projectID。
    """
    tab = dp.get_tab()
    comments_url = link.strip()

    # 如果不是评论链接，先访问原链接获取真实 URL
    if "/comments" not in comments_url:
        print(f"[auth] 打开项目页: {link}")
        tab.get(link, timeout=10, retry=0)
        tab.scroll(500)

        # 判断是不是空链接（404 页面）
        is_404 = is404(tab)
        if is_404:
            print(f"[auth] 404 空链接: {tab.url}")
            raise EmptyLinkError(f"404 空链接: {tab.url}")

        real_url = tab.url
        for i in range(10):
            time.sleep(1)
            current_url = tab.url
            if current_url != link and 'indiegogo.com' in current_url:
                real_url = current_url
                break
        print(f"[auth] 真实 URL: {real_url}")

        # 检查是否被重定向到首页（空链接）
        if is_homepage(real_url):
            raise EmptyLinkError(f"空链接: {real_url}")

        # TODO: 项目页加载成功后、加载评论页之前，用 tab 保存需要的数据
        mj=''
        backers=''
        wcMj=''
        projectID=''
        phase=''
        status=''
        campaignOutcome=''
        campaignStart=''
        campaignEnd=''
        shortDescription=''
        rewards=0
        tags=0
        tagTexts=''
        projectStory=''
        medias=0
        mediaUrls=''
        updates=0
        FAQ=0
        currency=''
        statusText=''
        rewardData=''

        # 从 window.__INITIAL_STATE__ 读取项目核心数据
        initial_state = None  # 保存原始 window 数据到 meta.raw
        try:
            initial_state = tab.run_js("return window.__INITIAL_STATE__")
            stats = initial_state.get("projectState", {}).get("statistics", {})
            mj = stats.get("totalFundsGathered", "")
            backers = stats.get("totalBackersCount", "")
            wcMj = stats.get("fundsGathered", "")

            project = initial_state.get("projectContext", {}).get("project", {})
            projectID = project.get("projectID", "")
            phase = project.get("phase", "")
            status = project.get("status", "")
            campaignOutcome = project.get("campaignOutcome", "")
            campaignStart = project.get("campaignStart", "")
            campaignEnd = project.get("campaignEnd", "")
            shortDescription = project.get("shortDescription", "")

            checkout_currencies = initial_state.get("checkoutCurrencies", [])
            current_currency_id = initial_state.get("currentCheckoutCurrencyId")
            for c in checkout_currencies:
                if c.get("currencyID") == current_currency_id:
                    currency = c.get("shortName", "")
                    break
            if not currency and checkout_currencies:
                currency = checkout_currencies[0].get("shortName", "")
        except Exception as e:
            print(f"[auth] window.__INITIAL_STATE__ 读取失败: {e}")
        # print(mj, backers, wcMj, projectID, phase, status, campaignOutcome, campaignStart, campaignEnd)

        rAeles=tab.eles("@class=gfu-table-of-contents__item gfu-list-subitem",timeout=1)
        for rAeleItem in rAeles:
            if 'rewards' in rAeleItem.link:
                rewards+=1

        tagBox=tab.ele("@text()=Tags",timeout=1)
        if tagBox:
            n=tagBox.next()
            tagChildren=n.children()
            tags=len(tagChildren)
            for tagItem in tagChildren:
                tagTexts+=tagItem.text+" | "

        # print(rewards,tags)

        projectStoryEle=tab.ele("@class=gfu-layout-wrapper gfu-layout-wrapper--extranarrow gfu-4of5--l gfu-3of5--xl",timeout=1)
        if projectStoryEle:
            projectStory=projectStoryEle.text
            imgEles=projectStoryEle.eles("@@tag()=img@@class=gfu-embed__item",timeout=1)
            for imgItem in imgEles:
                mediaUrls+=imgItem.link+' | '
            videoEles=projectStoryEle.eles("@@tag()=video@@class=gfu-embed__item",timeout=1)
            for videoItem in videoEles:
                url=videoItem.link or videoItem.attr('src')
                if url:
                    mediaUrls+=url+' | '
            medias=len(imgEles)+len(videoEles)

        # print(projectStory,imgs)

        updateBtn=None
        commentBtns=tab.eles("@@tag()=div@@class=gfu-navbar-link",timeout=1)
        for commentBtnItem in commentBtns:
            if 'Updates' in commentBtnItem.text:
                updateBtn=commentBtnItem
                break
        unEle=updateBtn.ele("@class=gfu-navbar-badge _ml-1",timeout=1)
        if unEle:
            updates=unEle.text

        FAQBtn=None
        commentBtns=tab.eles("@@tag()=div@@class=gfu-navbar-link",timeout=1)
        for commentBtnItem in commentBtns:
            if 'FAQ' in commentBtnItem.text:
                FAQBtn=commentBtnItem
                break
        unEle=FAQBtn.ele("@class=gfu-navbar-badge _ml-1",timeout=1)
        if unEle:
            FAQ=unEle.text

        try:
            btn=tab.ele("@class=gfu-table-of-contents__item gfu-list-item",timeout=1)
            if btn:
                btn.click(by_js=True)
                time.sleep(0.5)
        except Exception:
            pass

        rewardEles=tab.eles("@class=gfu-card__wrap",timeout=1)
        for rewardEleItem in rewardEles:
            rewardItemData=''
            name=rewardEleItem.ele("@class=gfu-reward-card__title gfu-hd gfu-hd--h1 gfu-hd--decorative",timeout=1)
            if name:
                rewardItemData=name.text
            priceSpans=rewardEleItem.eles("@tag()=span",timeout=1)
            for priceSpanItem in priceSpans:
                if priceSpanItem.attr('data-qa')=='price-type:Effective':
                    rewardItemData+=('__'+priceSpanItem.text)
                    break
            img=rewardEleItem.ele("@@tag()=img@@class=gfu-embed__item",timeout=1)
            if img:
                rewardItemData+=('('+img.link+')')
            rewardData+=(rewardItemData+' | ')

        try:
            projectTimelineBtn=tab.ele("@class=gfu-table-of-contents__item gfu-list-item _pb-0",timeout=1)
            if projectTimelineBtn:
                projectTimelineBtn.click(by_js=True)
                time.sleep(0.5)
        except Exception:
            pass

        nowELe=tab.ele("@class=gfu-project-timeline-card__badge _px-2 _tc--white _fw-b _ttu _bgc--accent",timeout=1)
        if nowELe:
            temp=nowELe.next()
            if temp:
                statusText=temp.text

        # 查找 Comments 按钮并读取应有评论数（先于元数据保存，meta 一次写入）
        print("[auth] 查找 Comments 按钮...")
        commentBtn = None
        expected_count = None
        try:
            commentBtns = tab.eles("@@tag()=div@@class=gfu-navbar-link", timeout=2)
            for commentBtnItem in commentBtns:
                if 'Comments' in commentBtnItem.text:
                    commentBtn = commentBtnItem
                    break
        except Exception:
            commentBtn = None

        if commentBtn:
            btn_text = commentBtn.text or ''
            digits = re.findall(r'\d+', btn_text)
            if digits:
                expected_count = int(digits[0])
                print(f"[auth] Comments 按钮数字: {expected_count}")
            else:
                expected_count = 0
                print("[auth] Comments 按钮无数字，标记 expected_count=0（无评论）")
        else:
            print("[auth] 未找到 Comments 按钮")

        # 保存项目元数据到 JSON（expected_count 首次即写入，无需二次更新）
        meta = {
            "projectID": projectID,
            "phase": phase,
            "status": status,
            "campaignOutcome": campaignOutcome,
            "campaignStart": campaignStart,
            "campaignEnd": campaignEnd,
            "mj": mj,
            "backers": backers,
            "wcMj": wcMj,
            "rewards": rewards,
            "tags": tags,
            "medias": medias,
            "mediaUrls": mediaUrls,
            "updates": updates,
            "FAQ": FAQ,
            "currency": currency,
            "statusText": statusText,
            "rewardData": rewardData,
            "tagTexts": tagTexts,
            "shortDescription": shortDescription,
            "projectStory": projectStory,
            "expected_count": expected_count,
            "url": link,
            "raw": initial_state,
        }
        PROJECT_META_DIR.mkdir(parents=True, exist_ok=True)
        json_name = save_project_id if save_project_id else projectID
        meta_path = PROJECT_META_DIR / f"project_{json_name}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"[auth] 项目元数据已保存: {meta_path}")
        tab.scroll.to_top()
        time.sleep(0.5)
        tab.scroll(500)

        # 仿照 main.py 点击 Comments 按钮进入评论页（复用上面找到的按钮）
        if commentBtn is None:
            raise NoCommentsError("未找到 Comments 按钮")
        if expected_count == 0:
            raise NoCommentsError("Comments 按钮无数字，视为无评论")
        commentBtn.click(by_js=True)
        time.sleep(2)

        comments_url = tab.url
        print(f"[auth] 评论页 URL: {comments_url}")

    print(f"[auth] 等待评论页加载: {comments_url}")
    tab.get(comments_url, timeout=10, retry=0)

    # 等待 Cloudflare 和评论组件加载
    print("[auth] 等待评论页加载...")
    for i in range(30):
        time.sleep(2)
        title = tab.title
        if "Just a moment" not in title and "请稍候" not in title and "Indiegogo" in title:
            print(f"[auth] 页面已加载: {title}")
            break
        print(f"[auth] 等待 Cloudflare... ({i + 1})")
    else:
        raise RuntimeError("Cloudflare 验证超时")

    html = tab.html
    match = re.search(r'"commentThreadID":(\d+)', html)
    for i in range(10):
        if match:
            break
        time.sleep(1)
        html = tab.html
        match = re.search(r'"commentThreadID":(\d+)', html)
    if not match:
        raise RuntimeError("未找到 commentThreadID")

    thread_id = int(match.group(1))
    print(f"[auth] commentThreadID = {thread_id}")

    # 等待 cookie 稳定
    time.sleep(3)
    cookies = tab.cookies("all")
    cookie_dict = {c["name"]: c["value"] for c in cookies if "indiegogo.com" in c.get("domain", "")}
    print(f"[auth] 获取 cookie {len(cookie_dict)} 个")

    # 验证 cookie 是否可用于 API 请求
    print("[auth] 验证 cookie...")
    headers = DEFAULT_HEADERS.copy()
    headers["referer"] = comments_url
    test_payload = {
        "commentThreadID": thread_id,
        "sortType": 0,
        "lastFetchedCommentID": None,
        "highlightedCommentID": None,
        "freshCommentID": None,
        "lastScore": None,
        "lastPinnedAt": None,
        "tag": None,
        "GetCommentsForCurrentUser": False,
        "getCommentsWithCreatorInput": False,
        "selectedCommentFilter": None,
        "commentID": None,
        "parentID": None,
    }
    test_resp = post_with_retry(
        "https://www.indiegogo.com/api/comments/getComments",
        headers=headers,
        cookies=cookie_dict,
        payload=test_payload,
    )
    if test_resp.status_code != 200:
        print(f"[error] cookie 验证失败，状态码: {test_resp.status_code}")
        print(f"[error] 响应: {test_resp.text[:300]}")
        raise RuntimeError(f"cookie 验证失败，API 状态码: {test_resp.status_code}")
    print("[auth] cookie 验证通过")

    return {
        "comment_thread_id": thread_id,
        "cookies": cookie_dict,
        "referer": comments_url,
        "ts": time.time(),
        "expected_count": expected_count,
    }


# ==================== API 请求 ====================
def post_with_retry(url, headers, cookies, payload, max_retries=4, timeout=30):
    """POST 请求；429 限流时等待递增时长后重试，最多 max_retries 次。"""
    resp = None
    for attempt in range(1, max_retries + 1):
        resp = requests.post(url, headers=headers, cookies=cookies, json=payload, timeout=timeout, impersonate="chrome")
        if resp.status_code != 429:
            return resp
        wait = 10 * attempt + (hash(str(payload)) % 21)  # 递增: 10-30s, 20-40s, 30-50s, 40-60s
        print(f"[retry] 429 限流(第{attempt}/{max_retries}次)，等待 {wait} 秒后重试...")
        time.sleep(wait)
    return resp


def extract_total_count(data):
    """从 API 响应中尝试提取评论总数（应有评论数）。"""
    d = data.get("data") or {}
    for key in ["totalCount", "total", "count", "totalItems", "total_count", "commentsCount"]:
        val = d.get(key)
        if isinstance(val, int):
            return val
    return None


def fetch_page(auth, last_id=None, parent_id=None, fresh_comment_id=None):
    """请求 getComments 一页，返回 (items, total_count)。"""
    url = "https://www.indiegogo.com/api/comments/getComments"
    headers = DEFAULT_HEADERS.copy()
    headers["referer"] = auth["referer"]
    payload = {
        "commentThreadID": auth["comment_thread_id"],
        "sortType": 0,
        "lastFetchedCommentID": last_id,
        "highlightedCommentID": None,
        "freshCommentID": fresh_comment_id,
        "lastScore": 0 if fresh_comment_id else None,
        "lastPinnedAt": None,
        "tag": None,
        "GetCommentsForCurrentUser": False,
        "getCommentsWithCreatorInput": False,
        "selectedCommentFilter": None,
        "commentID": None,
        "parentID": parent_id,
    }
    resp = post_with_retry(url, headers=headers, cookies=auth["cookies"], payload=payload)
    time.sleep(1)  # 模拟自动化点击间隔
    if resp.status_code == 403:
        raise PermissionError("cookie 失效，请刷新浏览器后重试")
    if resp.status_code != 200:
        raise RuntimeError(f"getComments 失败: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"getComments 返回失败: {data.get('message')}")
    total_count = extract_total_count(data)
    return data["data"]["pagedItems"], total_count


def fetch_authors(auth, author_ids):
    """批量获取作者信息。"""
    if not author_ids:
        return {}
    url = "https://www.indiegogo.com/api/comments/getCommentsAuthors"
    headers = DEFAULT_HEADERS.copy()
    headers["referer"] = auth["referer"]
    payload = {"authorIDs": author_ids, "commentThreadID": auth["comment_thread_id"]}
    resp = post_with_retry(url, headers=headers, cookies=auth["cookies"], payload=payload)
    time.sleep(1)
    if resp.status_code != 200:
        raise RuntimeError(f"getCommentsAuthors 失败: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"getCommentsAuthors 返回失败: {data.get('message')}")
    return data["data"]


# ==================== 子评论加载 ====================
def load_children_for_parent(auth, parent_item, fresh_comment_id):
    """加载某个父评论下所有缺失的子评论。"""
    parent_id = parent_item["commentID"]
    children = parent_item.get("children") or []
    total = parent_item.get("childrenTotalCount", 0)
    if total <= len(children):
        return children

    collected = {c["commentID"]: c for c in children}
    last_id = max(collected.keys()) if collected else None

    while len(collected) < total:
        items, _ = fetch_page(auth, last_id=last_id, parent_id=parent_id, fresh_comment_id=fresh_comment_id)
        if not items:
            break
        new_last = items[-1]["commentID"]
        if new_last == last_id:
            break
        for item in items:
            collected[item["commentID"]] = item
        last_id = new_last
        print(f"  [fetch] parent {parent_id}: +{len(items)} 子评论 = {len(collected)}/{total}")
        time.sleep(1)

    return list(collected.values())


def flatten_page_with_children(root_items, auth, fresh_comment_id):
    """加载一页根评论及其完整子评论，平铺成 (item, parent_id, depth)。"""
    rows = []
    for root in root_items:
        rows.append((root, None, 0))
        # 页面自带的 children
        for child in root.get("children") or []:
            rows.append((child, root["commentID"], 1))
        # 补充加载更多子评论
        all_children = load_children_for_parent(auth, root, fresh_comment_id)
        loaded_ids = {c["commentID"] for c in root.get("children") or []}
        for child in all_children:
            if child["commentID"] not in loaded_ids:
                rows.append((child, root["commentID"], 1))
    return rows


# ==================== CSV 写入 ====================
def append_rows_to_csv(rows, authors, output_path, project_url):
    """追加写入 CSV，文件不存在时写表头。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists()
    with open(output_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for item, parent_id, depth in rows:
            author_id = item["authorID"]
            author = authors.get(str(author_id)) or authors.get(author_id)
            name = ""
            if author:
                name = author.get("nickname") or author.get("urlName") or ""
            writer.writerow(
                {
                    "comment_id": item["commentID"],
                    "parent_id": parent_id if parent_id is not None else "",
                    "depth": str(depth),
                    "name": name,
                    "is_creator": "yes" if item.get("authorType") == 1 else "no",
                    "content": (item.get("text") or "").replace("\r", " ").replace("\n", " "),
                    "created_at": item.get("createdAt", ""),
                    "url": project_url,
                    "raw": json.dumps(item, ensure_ascii=False),
                }
            )


# ==================== 进度文件 ====================
def load_progress(project_id):
    path = PROGRESS_DIR / f"progress_{project_id}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "fresh_comment_id": None,
        "last_root_id": None,
        "root_finished": False,
        "written_count": 0,
        "authors": {},
    }


def save_progress(project_id, progress):
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    path = PROGRESS_DIR / f"progress_{project_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ==================== 一页采集 ====================
def fetch_one_page(dp, task, out_path, progress=None, auth=None):
    """
    为单个项目加载一页根评论 + 该页子评论，追加写入 CSV。
    返回 (是否还有更多, 当前已写入总数)
    """
    project_id = task["sortId"] or ""
    project_url = task["link"]
    if progress is None:
        progress = load_progress(project_id)
    if auth is None:
        auth = get_auth_from_browser(dp, project_url, save_project_id=project_id)
        progress["comment_thread_id"] = auth["comment_thread_id"]
        progress["cookies"] = auth["cookies"]
        progress["referer"] = auth["referer"]
        progress["ts"] = auth.get("ts", time.time())

    if progress["root_finished"]:
        print(f"[fetch] 项目 {project_id} 根评论已加载完毕，跳过")
        return False, progress["written_count"], progress.get("total_count")

    print(f"[fetch] 加载根页，last_root_id={progress['last_root_id']}")
    items, total_count = fetch_page(
        auth,
        last_id=progress["last_root_id"],
        parent_id=None,
        fresh_comment_id=progress["fresh_comment_id"],
    )
    if not items:
        progress["root_finished"] = True
        save_progress(project_id, progress)
        print(f"[fetch] 项目 {project_id} 根评论加载完毕")
        return False, progress["written_count"], total_count

    if progress["fresh_comment_id"] is None:
        progress["fresh_comment_id"] = items[0]["commentID"]
        if total_count is not None:
            progress["total_count"] = total_count
    progress["last_root_id"] = items[-1]["commentID"]

    rows = flatten_page_with_children(items, auth, progress["fresh_comment_id"])

    # 获取新作者
    author_ids = sorted({item["authorID"] for item, _, _ in rows if str(item["authorID"]) not in progress["authors"]})
    if author_ids:
        authors = fetch_authors(auth, author_ids)
        progress["authors"].update({str(k): v for k, v in authors.items()})
        print(f"[fetch] 获取 {len(author_ids)} 个新作者")

    append_rows_to_csv(rows, progress["authors"], out_path, project_url)
    progress["written_count"] += len(rows)
    save_progress(project_id, progress)
    print(f"[fetch] 本页写入 {len(rows)} 条，项目 {project_id} 累计 {progress['written_count']} 条")

    return True, progress["written_count"], progress.get("total_count")


# ==================== 主流程 ====================

def main():
    rows, fieldnames = load_tasks()
    for col in ["status", "comment_count", "actual_count", "备注"]:
        if col not in fieldnames:
            fieldnames.append(col)
            for r in rows:
                r[col] = ""

    pending_indices = [i for i, r in enumerate(rows) if r.get("status") == S_PENDING]
    print(f"[main] 共有 {len(pending_indices)} 个 pending 任务")
    if not pending_indices:
        print("[main] 没有 pending 任务")
        return

    raw_start = input("请输入开始索引（从0开始，直接回车=0）: ").strip()
    raw_end = input("请输入结束索引（直接回车=不限制）: ").strip()
    try:
        start_idx = int(raw_start) if raw_start else 0
    except ValueError:
        start_idx = 0
    try:
        end_idx = int(raw_end) if raw_end else None
    except ValueError:
        end_idx = None
    start_idx = max(0, start_idx)
    if end_idx is not None:
        end_idx = max(start_idx, end_idx)
        print(f"[main] 从索引 {start_idx} 到 {end_idx}")
    else:
        print(f"[main] 从索引 {start_idx} 开始，无限制")

    dp = Chromium(BROWSER_PORT)
    # tab=dp.get_tab()
    # tab.ele("@class=asdf",timeout=0.1).click()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for idx in pending_indices:
        if idx < start_idx:
            continue
        if end_idx is not None and idx > end_idx:
            print(f"[main] 已达到结束索引 {end_idx}，停止")
            break

        task = rows[idx]
        project_id = task["sortId"] or str(idx)
        project_url = task["link"]
        out_path = OUTPUT_DIR / f"comments_{project_id}.csv"

        print(f"\n[{idx}] 开始: {project_url}")
        try:
            auth = get_auth_from_browser(dp, project_url, save_project_id=project_id)

            progress = load_progress(project_id)
            # 全量重采：重置进度，确保从头重新采集评论
            # （旧项目 progress 的 root_finished=true 会导致 fetch_one_page 跳过评论采集）
            progress["fresh_comment_id"] = None
            progress["last_root_id"] = None
            progress["root_finished"] = False
            progress["written_count"] = 0
            progress["comment_thread_id"] = auth["comment_thread_id"]
            progress["cookies"] = auth["cookies"]
            progress["referer"] = auth["referer"]
            progress["ts"] = auth.get("ts", time.time())

            written_count = 0
            expected_count = None
            page_count = 0
            while True:
                page_count += 1
                print(f"[{idx}] 第 {page_count} 页...")
                try:
                    has_more, page_count_written, page_total = fetch_one_page(dp, task, out_path, progress, auth)
                except PermissionError as e:
                    print(f"[{idx}] cookie 失效，刷新中...")
                    auth = get_auth_from_browser(dp, project_url, save_project_id=project_id)
                    progress["cookies"] = auth["cookies"]
                    progress["referer"] = auth["referer"]
                    progress["ts"] = auth.get("ts", time.time())
                    has_more, page_count_written, page_total = fetch_one_page(dp, task, out_path, progress, auth)

                written_count = page_count_written
                if expected_count is None and page_total is not None:
                    expected_count = page_total
                if not has_more:
                    break

            # 应有评论数：优先用 Comments 按钮数字，其次 API 返回总数，最后拿实际采集数兜底
            button_count = auth.get("expected_count")
            api_count = expected_count
            comment_count = button_count if button_count is not None else (api_count if api_count is not None else written_count)
            if written_count == 0:
                task["status"] = S_NO_COMMENT
                task["comment_count"] = str(comment_count)
                task["actual_count"] = "0"
                print(f"[{idx}] 没有评论")
            else:
                task["status"] = S_DONE
                task["comment_count"] = str(comment_count)
                task["actual_count"] = str(written_count)
                print(f"[{idx}] 完成: 应有 {comment_count} 条，实际 {written_count} 条")
            save_tasks(rows, fieldnames)

        except EmptyLinkError as e:
            print(f"[{idx}] 空链接: {e}")
            task["status"] = S_NO_COMMENT
            task["comment_count"] = "0"
            task["actual_count"] = "0"
            task["备注"] = "空链接"
            save_tasks(rows, fieldnames)
        except NoCommentsError as e:
            print(f"[{idx}] 无评论: {e}")
            task["status"] = S_NO_COMMENT
            task["comment_count"] = "0"
            task["actual_count"] = "0"
            save_tasks(rows, fieldnames)
        except Exception as e:
            print(f"[{idx}] 错误: {e}")
            task["status"] = S_ERROR
            save_tasks(rows, fieldnames)


if __name__ == "__main__":
    main()
