import csv
import os
import json
import time
from datetime import datetime
from DrissionPage import Chromium
from utils import setup_log, get_range_args

"""变量区"""""""""""""""""""""""""""""""""""""""""""""
input_data=[]
# 浏览器端口
tabPort=7746
# 浏览器对象
dp=Chromium(tabPort)
# 标签页对象
tab=dp.get_tab()
# tab.ele("@class=sdf",timeout=0.1).click()
"""变量区"""""""""""""""""""""""""""""""""""""""""""""

"""函数区"""""""""""""""""""""""""""""""""""""""""""""


def get_note_id(url):
    """从链接提取帖子id"""
    return url.split('/')[-1].split('?')[0]


def _vid_url(video):
    """从 video.media.stream.<codec>[0] 提取视频地址（SSR与feed结构一致）"""
    try:
        for lst in (((video or {}).get('media') or {}).get('stream') or {}).values():
            if lst:
                u = lst[0].get('master_url') or lst[0].get('masterUrl') or ''
                if u:
                    return u
    except Exception:
        pass
    return ''


def parse_note(note, is_ssr):
    """把 SSR note（驼峰）或 feed note_card（下划线）统一解析成基础数据 dict"""
    def g(*ks):
        for k in ks:
            if isinstance(note, dict) and note.get(k) is not None:
                return note[k]
        return None

    if is_ssr:
        imgs = note.get('imageList') or []
        ii = note.get('interactInfo') or {}
        user = note.get('user') or {}
        tags = [t.get('name') or '' for t in (note.get('tagList') or [])]
        video = note.get('video') or {}
        cover = imgs[0].get('urlDefault') or imgs[0].get('url') if imgs else ''
        img_urls = [x.get('urlDefault') or x.get('url') or '' for x in imgs]
        return {
            'noteId': note.get('noteId', ''),
            'title': note.get('title', ''),
            'type': note.get('type', ''),
            'desc': note.get('desc', ''),
            'tags': tags,
            'cover': cover,
            'images': img_urls,
            'videoUrl': _vid_url(video),
            'videoDuration': ((video.get('capa') or {}).get('duration', '') or ''),
            'likedCount': ii.get('likedCount', ''),
            'collectedCount': ii.get('collectedCount', ''),
            'commentCount': ii.get('commentCount', ''),
            'shareCount': ii.get('shareCount', ''),
            'authorNickname': user.get('nickname', ''),
            'authorUserId': user.get('userId', '') or user.get('user_id', ''),
            'ipLocation': note.get('ipLocation', ''),
            'publishTime': note.get('time', ''),
            'xsecToken': note.get('xsecToken', ''),
        }
    else:
        imgs = note.get('image_list') or []
        ii = note.get('interact_info') or {}
        user = note.get('user') or {}
        tags = [t.get('name') or t.get('tag_name') or '' for t in (note.get('tag_list') or [])]
        video = note.get('video') or {}
        cover = imgs[0].get('url_default') or imgs[0].get('url') if imgs else ''
        img_urls = [x.get('url_default') or x.get('url') or '' for x in imgs]
        return {
            'noteId': note.get('note_id', ''),
            'title': note.get('title', ''),
            'type': note.get('type', ''),
            'desc': note.get('desc', ''),
            'tags': tags,
            'cover': cover,
            'images': img_urls,
            'videoUrl': _vid_url(video),
            'videoDuration': ((video.get('capa') or {}).get('duration', '') or ''),
            'likedCount': ii.get('liked_count', ''),
            'collectedCount': ii.get('collected_count', ''),
            'commentCount': ii.get('comment_count', ''),
            'shareCount': ii.get('share_count', ''),
            'authorNickname': user.get('nickname', ''),
            'authorUserId': user.get('user_id', '') or user.get('userId', ''),
            'ipLocation': note.get('ip_location', ''),
            'publishTime': note.get('time', ''),
            'xsecToken': note.get('xsec_token', ''),
        }


def get_ssr_note(tab, nid, timeout=10):
    """从页面 SSR __INITIAL_STATE__.note.noteDetailMap 提取笔记数据"""
    start = time.time()
    while time.time() - start < timeout:
        s = tab.run_js(
            'return JSON.stringify((window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note '
            '&& window.__INITIAL_STATE__.note.noteDetailMap) ? window.__INITIAL_STATE__.note.noteDetailMap : null)',
            timeout=5,
        )
        if s and s != 'null':
            m = json.loads(s)
            v = m.get(nid)
            n = (v or {}).get('note') or {}
            if n.get('noteId') or n.get('title') or n.get('desc'):
                return n
        time.sleep(0.5)
    return None


def getPostData(tab, url):
    """
    监听浏览器接口 + 页面 SSR 双通道获取帖子基础数据（不依赖 cookie 鉴权/签名解密）。
    每次结果保存为 result/postData/<noteId>.json，原始数据存 api_raw/<noteId>/
    """
    nid = get_note_id(url)
    record = {
        'noteId': nid,
        'url': url,
        'collectedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'fail',
        'msg': '',
        'data': {},
    }
    try:
        # 监听浏览器自己的接口请求（feed 若有则捕获，SSR 无数据时兜底）
        tab.listen.start('api/sns/web')
        tab.get(url)

        # 主通道：页面 SSR 数据
        note = get_ssr_note(tab, nid)
        raw_saved = 'ssr'
        if note:
            data = parse_note(note, is_ssr=True)
            raw_obj = {'noteDetail': note}
        else:
            # 兜底通道：监听 feed 接口响应
            p = tab.listen.wait(timeout=8)
            note = None
            while p:
                if 'api/sns/web/v1/feed' in p.url:
                    b = p.response.body
                    if isinstance(b, dict):
                        items = (b.get('data') or {}).get('items') or []
                        if items:
                            note = items[0].get('note_card') or {}
                            break
                p = tab.listen.wait(timeout=0.5)
            if not note:
                raise RuntimeError('未获取到帖子数据（SSR 与 feed 均无响应）')
            data = parse_note(note, is_ssr=False)
            raw_saved = 'feed'
            raw_obj = {'feedItems': [note]}

        record['status'] = 'success'
        record['msg'] = 'ok'
        record['data'] = data

        # 原始数据落盘（api_raw/ 已被 .gitignore 忽略）
        d = os.path.join('api_raw', nid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'note_info_{raw_saved}.json'), 'w', encoding='utf-8') as f:
            json.dump(raw_obj, f, ensure_ascii=False, indent=1)

        print(f'  数据源: {raw_saved}')
        print(f'  标题: {data["title"]}')
        print(f'  类型: {data["type"]}  图片数: {len(data["images"])}')
        print(f'  封面: {data["cover"][:80]}')
        print(f'  正文: {data["desc"][:60]}')
        print(f'  标签: {", ".join(data["tags"])}')
        print(f'  赞/藏/评/分享: {data["likedCount"]} / {data["collectedCount"]} / {data["commentCount"]} / {data["shareCount"]}')

    except Exception as e:
        record['msg'] = str(e)[:300]
        print(f'  ❌ 失败原因: {record["msg"]}')

    # 每次结果保存到 result/postData/<noteId>.json
    out_dir = os.path.join('result', 'postData')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{nid}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    print(f'  {record["status"].upper()} → 结果已保存: {out_path}')
    return record


"""函数区"""""""""""""""""""""""""""""""""""""""""""""

"""主流程"""""""""""""""""""""""""""""""""""""""""""""
if __name__ == "__main__":
    args = get_range_args()
    print(f"日志文件: {setup_log()}")   # 启动日志

    # 读取input
    with open("input.csv", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        input_data = [row for row in reader if row.get("url", "").strip()]

    total = len(input_data)
    start = max(1, args.start)
    end = min(total, args.end if args.end else total)
    print(f"采集范围: 第{start}~{end}条（共{total}条）")

    # 遍历处理
    for i in range(start, end + 1):
        taskUrl = input_data[i - 1]["url"].strip()
        print(f"[{i}/{total}] {taskUrl}")

        getPostData(tab, taskUrl)