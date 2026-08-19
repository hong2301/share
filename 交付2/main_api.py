# -*- coding: utf-8 -*-
"""
遍历 links.csv 中 status 为 pending/error 的链接，使用 Indiegogo 评论 API 采集评论。

认证方式：
- 用 DrissionPage 打开项目原链接，等待重定向到真实 URL
- 然后直接访问真实 URL 的 /comments 页面获取 cookie 和 commentThreadID
- 之后全部使用 requests 请求 API，一页一页追加写入

输出：
- comments_out_api/comments_<行号>.csv
- project_meta_api/project_<行号>.json

说明：
- 本脚本只读取 links.csv（link / status 两列），绝不修改 links.csv
- status 为 pending 或 error 的任务才会处理，done 跳过
- 不依赖 links 里任何其他字段（备注、计数等）做判断

使用方式：
    cd /Users/hong/Desktop/交付2
    python3 main_api.py [-h] [--meta-only]

首次运行前请确保端口 4835 的浏览器已启动并通过 Cloudflare 验证。
--meta-only 参数（或启动时交互确认）：仅采集项目元数据生成 project_*.json，跳过评论采集与认证流程。
"""

import csv
import json
import re
import sys
import time
from pathlib import Path

from curl_cffi import requests
from DrissionPage import Chromium

# ==================== 配置 ====================
LINKS_CSV = Path("links.csv")
OUTPUT_DIR = Path("comments_out_api")
PROJECT_META_DIR = Path("project_meta_api")
PROGRESS_DIR = Path("indiegogo_main_api_progress")
BROWSER_PORT = 4835

# True=仅采集元数据（不生成评论 csv，单链接约 5-8s）；False=正常采集评论；None=启动时询问
META_ONLY = True

# True=评论断点接续（用进度文件继续，跳过已采集的）；False=每个链接全量重采
RESUME = True


class EmptyLinkError(Exception):
    """项目链接被重定向到 Indiegogo 首页，视为空链接。"""
    pass


class NoCommentsError(Exception):
    """项目页没有 Comments 按钮或评论数为 0。"""
    pass


def goto_blank(tab):
    """
    每次打开链接之前，先把当前标签页清空为空白页（about:blank），
    避免上一个项目的页面状态 / 滚动位置 / 弹窗等残留影响本次访问。
    """
    try:
        tab.get("about:blank", timeout=5, retry=0)
        print("[auth] 已清空页面为空白")
    except Exception as e:
        print(f"[auth] 清空页面失败（忽略）: {e}")


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

# 所有 project_*.json 统一的字段结构：无论 done/error/empty，都写满这些字段（失败时用默认值）
META_SCHEMA = {
    "projectID": "",
    "phase": "",
    "status": "",
    "campaignOutcome": "",
    "campaignStart": "",
    "campaignEnd": "",
    "mj": "",
    "backers": "",
    "wcMj": "",
    "rewards": 0,
    "tags": 0,
    "medias": 0,
    "mediaUrls": "",
    "updates": "",
    "FAQ": "",
    "currency": "",
    "statusText": "",
    "rewardData": "",
    "tagTexts": "",
    "shortDescription": "",
    "projectStory": "",
    "expected_count": None,
    "url": "",
    "cjStatus": "",
    "error": "",
    "raw": None,
}

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
def url_to_filename(url):
    """将链接转换为安全的文件名（参考处理器/rename_by_url.py）。"""
    if not url:
        return None
    name = re.sub(r"^https?://", "", url)
    name = re.sub(r"^[^/]+/", "", name)
    name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]", "", name)
    name = name.strip("-")
    return name if name else None


def load_tasks():
    """
    读取 links.csv，只取 link 列（其余列一律忽略），不修改 links.csv。
    返回 [{link, file_id}, ...]，file_id=链接转换的安全文件名(用于输出与命名)
    """
    with LINKS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        if "link" not in header:
            raise SystemExit("links.csv 缺少必要列（需要有 link 列）")
        link_idx = header.index("link")
        tasks = []
        for i, r in enumerate(reader):
            link = r[link_idx] if len(r) > link_idx else ""
            fname = url_to_filename(link)
            tasks.append(
                {
                    "link": link,
                    "file_id": fname if fname else str(i),
                }
            )
    return tasks


def update_cj_status(file_id, cj_status, error=None, url=""):
    """
    确保 project_<file_id>.json 一定存在，且字段与正常 meta 完全一致（统一 META_SCHEMA）；
    成功路径已写完整 meta，这里只需保证字段集合并更新 cjStatus/error；
    失败/空链接路径则用空字段补齐后再写。
    """
    PROJECT_META_DIR.mkdir(parents=True, exist_ok=True)
    path = PROJECT_META_DIR / f"project_{file_id}.json"
    data = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
    # 按统一 schema 补齐：已有值保留，缺失用默认值
    out = {k: data.get(k, default) for k, default in META_SCHEMA.items()}
    out["cjStatus"] = cj_status
    if url:
        out["url"] = url
    out["error"] = str(error) if error else ""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def delete_meta(file_id):
    """删除某个链接的 json（采集出错/中断时调用），使其下次被重新处理。"""
    path = PROJECT_META_DIR / f"project_{file_id}.json"
    try:
        if path.exists():
            path.unlink()
            print(f"[清理] 已删除 {path.name}，下次将重新处理")
    except Exception as e:
        print(f"[清理] 删除失败: {e}")


# ==================== 认证：加载原链接 -> 重定向 -> 访问 /comments ====================
def get_auth_from_browser(dp, link, save_project_id=None, meta_only=False):
    """
    使用 DrissionPage 获取 cookie 和 commentThreadID。
    如果 link 已经是评论链接（含 /comments），直接访问；
    否则先打开项目原链接，重定向后再构造 /comments 链接访问。
    save_project_id 用于 JSON 文件名，默认使用从页面读取的 projectID。
    """
    tab = dp.get_tab()
    comments_url = link.strip()

    # 每次访问链接前，确保当前是空页面
    goto_blank(tab)

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
            nowELe.scroll.to_see()
            temp=nowELe.next()
            if temp:
                # 循环最多 30 次（每次间隔 0.1s）读取状态文本，非空才记录并停止
                for _ in range(30):
                    val = temp.text
                    if val and val.strip():
                        statusText = val
                        break
                    time.sleep(0.1)

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
        json_name = save_project_id if save_project_id else projectID
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
            "cjStatus": "",
            "error": "",
            "raw": initial_state,
        }
        PROJECT_META_DIR.mkdir(parents=True, exist_ok=True)
        meta_path = PROJECT_META_DIR / f"project_{json_name}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"[auth] 项目元数据已保存: {meta_path}")

        if meta_only:
            print("[auth] 仅元数据模式：元数据处理完毕，跳过评论认证流程")
            return None

        tab.scroll.to_top()
        time.sleep(0.5)
        tab.scroll(500)

        # 点击 Comments 按钮进入评论页（复用上面找到的按钮）
        if commentBtn is None:
            raise NoCommentsError("未找到 Comments 按钮")
        if expected_count == 0:
            raise NoCommentsError("Comments 按钮无数字，视为无评论")
        commentBtn.click(by_js=True)
        time.sleep(2)

        comments_url = tab.url
        print(f"[auth] 评论页 URL: {comments_url}")

    print(f"[auth] 等待评论页加载: {comments_url}")
    goto_blank(tab)  # 加载评论页前同样先清空页面
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
    project_id = task["file_id"] or ""   # 进度与输出都统一用链接转换名
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
    # 解析命令行参数：支持 start=0 stop=5 port=1234 --meta-only
    cli = {}
    for a in sys.argv[1:]:
        for k in ("start", "stop", "port"):
            if a.startswith(k + "="):
                cli[k] = a.split("=", 1)[1]
    cli_mode = bool(cli) or "--meta-only" in sys.argv

    # 优先级：命令行 --meta-only > 配置 META_ONLY > 启动时询问
    meta_only = "--meta-only" in sys.argv
    if not meta_only and META_ONLY is not None:
        meta_only = META_ONLY
    if not meta_only and META_ONLY is None:
        ans = input("仅采集元数据、不采集评论？[y/N] ").strip().lower()
        meta_only = ans in ("y", "yes")
    if meta_only:
        print("[main] 仅元数据模式：只生成项目元数据 JSON，跳过评论采集")

    # 读取 links（只认 link 列），处理全部链接；不修改 links.csv，结果状态写入各个 json 的 cjStatus
    tasks = load_tasks()
    print(f"[main] links 共 {len(tasks)} 条，全部处理")
    if not tasks:
        print("[main] links 为空")
        return

    # 开始/结束索引：优先命令行参数；CLI 模式缺省 start=0/stop=不限；否则交互询问
    if cli_mode:
        start_idx = int(cli["start"]) if "start" in cli else 0
        end_idx = int(cli["stop"]) if "stop" in cli and cli["stop"] else None
    else:
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

    # 端口：优先命令行 port= 参数，否则用配置 BROWSER_PORT
    browser_port = int(cli["port"]) if "port" in cli else BROWSER_PORT
    dp = Chromium(browser_port)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROJECT_META_DIR.mkdir(parents=True, exist_ok=True)

    for n, task in enumerate(tasks):
        if n < start_idx:
            continue
        if end_idx is not None and n > end_idx:
            print(f"[main] 已达到结束索引 {end_idx}，停止")
            break

        file_id = task["file_id"]
        project_url = task["link"]
        out_path = OUTPUT_DIR / f"comments_{file_id}.csv"

        # 内置断点续跑：已有 json 且状态为 done/empty 的直接跳过（error 需重试）
        meta_path = PROJECT_META_DIR / f"project_{file_id}.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as _f:
                    if json.load(_f).get("cjStatus") in ("done", "empty"):
                        print(f"[{n}] 已有记录（cjStatus=done/empty），跳过")
                        continue
            except Exception:
                pass

        if not project_url.strip():
            # 链接为空 → empty
            update_cj_status(file_id, "empty", "link 为空", project_url)
            continue

        print(f"\n[{n}] 开始: {project_url}")
        success = False
        try:
            if meta_only:
                get_auth_from_browser(dp, project_url, save_project_id=file_id, meta_only=True)
                success = True
                print(f"[{n}] 仅元数据处理完成，meta JSON 已生成")
            else:
                auth = get_auth_from_browser(dp, project_url, save_project_id=file_id)

                # 评论数量为 0（无评论）时无需采集，保存 json 后即可 done
                if auth.get("expected_count") == 0:
                    print(f"[{n}] 无评论（expected_count=0），无需采集")
                    success = True
                else:
                    progress = load_progress(file_id)
                    # 评论接续开关：RESUME=True 用进度接续；False 则全量重采
                    if not RESUME:
                        print(f"[{n}] 全量重采（RESUME=False），重置进度")
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
                        print(f"[{n}] 第 {page_count} 页...")
                        try:
                            has_more, page_count_written, page_total = fetch_one_page(dp, task, out_path, progress, auth)
                        except PermissionError:
                            print(f"[{n}] cookie 失效，刷新中...")
                            auth = get_auth_from_browser(dp, project_url, save_project_id=file_id)
                            progress["cookies"] = auth["cookies"]
                            progress["referer"] = auth["referer"]
                            progress["ts"] = auth.get("ts", time.time())
                            has_more, page_count_written, page_total = fetch_one_page(dp, task, out_path, progress, auth)

                        written_count = page_count_written
                        if expected_count is None and page_total is not None:
                            expected_count = page_total
                        if not has_more:
                            break

                    # 评论采集彻底结束 → done
                    button_count = auth.get("expected_count")
                    api_count = expected_count
                    comment_count = button_count if button_count is not None else (api_count if api_count is not None else written_count)
                    success = True
                    if written_count == 0:
                        print(f"[{n}] 没有评论（应有 {comment_count} 条）")
                    else:
                        print(f"[{n}] 完成: 应有 {comment_count} 条，实际 {written_count} 条")

        except EmptyLinkError as e:
            update_cj_status(file_id, "empty", str(e), project_url)
            print(f"[{n}] 空链接: {e}")
        except NoCommentsError as e:
            success = True
            print(f"[{n}] 无评论: {e}")
        except Exception as e:
            # 采集出错/失败：删除 json，下次重新处理
            delete_meta(file_id)
            print(f"[{n}] 错误: {e}")

        # 成功（评论采完 / 无评论 / 仅元数据）→ 写回 done
        if success:
            update_cj_status(file_id, "done", None, project_url)
            print(f"[{n}] cjStatus 已写为 done")


if __name__ == "__main__":
    main()