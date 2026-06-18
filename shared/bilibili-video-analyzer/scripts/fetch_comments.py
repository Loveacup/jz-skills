#!/usr/bin/env python3
"""
获取 Bilibili 视频评论
用法: python3 fetch_comments.py <BV号或AV号> [SESSDATA]

特点:
- 直接调用 B站评论 API
- 获取热门评论和最新评论
- 包含评论的点赞数、回复数等信息
"""

import sys
import os

# 依赖兜底：append 真实属主的用户级 site-packages。
# 原写法 sys.path.insert(0, '~/...') 双重 bug：字面量 '~' 从不展开 + insert(0)。
# Hermes profile 会改写 $HOME，故用 pwd.getpwuid。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site
ensure_user_site()

import requests
import json
import re


def extract_bvid(url_or_bvid):
    """从URL或BV号中提取BV号"""
    if url_or_bvid.startswith('BV'):
        return url_or_bvid
    
    # 从URL中提取
    match = re.search(r'BV[0-9A-Za-z]+', url_or_bvid)
    if match:
        return match.group(0)
    
    return None


def get_avid_from_bvid(bvid):
    """通过BV号获取AV号(OID)"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://www.bilibili.com/video/{bvid}/",
    }
    
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    data = resp.json()
    
    if data.get("code") == 0:
        return data["data"]["aid"], data["data"]["title"]
    else:
        print(f"❌ 获取视频信息失败: {data.get('message')}")
        return None, None


def fetch_comments(oid, sort=2, page=1, ps=20, sessdata=None):
    """
    获取评论
    
    Args:
        oid: AV号
        sort: 排序方式 2=热门 0=时间
        page: 页码
        ps: 每页数量
        sessdata: 登录凭证
    """
    url = "https://api.bilibili.com/x/v2/reply"
    params = {
        "oid": oid,
        "type": 1,  # 视频
        "pn": page,
        "ps": ps,
        "sort": sort
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://www.bilibili.com/video/av{oid}/",
    }
    
    cookies = {}
    if sessdata:
        cookies["SESSDATA"] = sessdata
    
    resp = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=15)
    return resp.json()


def process_comments(raw_data, top_n=50):
    """处理评论数据，提取关键信息"""
    
    comments = []
    replies = raw_data.get('data', {}).get('replies', []) or []
    
    for reply in replies[:top_n]:
        member = reply.get('member', {})
        content = reply.get('content', {})
        
        comment_info = {
            "rpid": reply.get("rpid"),  # 评论ID
            "user": {
                "mid": member.get("mid"),
                "name": member.get("uname"),
                "avatar": member.get("avatar"),
                "level": member.get("level_info", {}).get("current_level"),
                "is_vip": member.get("vip", {}).get("status") == 1
            },
            "content": content.get("message", ""),
            "ctime": reply.get("ctime"),  # 发布时间
            "like": reply.get("like", 0),
            "rcount": reply.get("rcount", 0),  # 回复数
            "is_top": reply.get("is_top", False),
            "is_up": reply.get("mid") == raw_data.get("data", {}).get("upper", {}).get("mid")
        }
        
        comments.append(comment_info)
    
    return comments


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_comments.py <BV号或URL> [SESSDATA] [获取数量]")
        print("示例: python3 fetch_comments.py BV12Q6TBwE2J")
        sys.exit(1)
    
    input_str = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 20  # B站API限制，默认20条
    
    # 提取BV号
    bvid = extract_bvid(input_str)
    if not bvid:
        print("❌ 无法识别BV号")
        sys.exit(1)
    
    print(f"🎬 BV号: {bvid}")
    
    # 获取AV号
    oid, title = get_avid_from_bvid(bvid)
    if not oid:
        sys.exit(1)
    
    print(f"   标题: {title}")
    print(f"   AV号: {oid}")
    
    # 获取热门评论 (ps最大20，通过分页获取更多)
    print(f"\n📥 正在获取热门评论...")
    ps = min(top_n, 20)  # B站API限制每页最多20条
    hot_data = fetch_comments(oid, sort=2, page=1, ps=ps, sessdata=sessdata)
    
    if hot_data.get("code") != 0:
        print(f"❌ 获取失败: {hot_data.get('message')}")
        sys.exit(1)
    
    page_info = hot_data.get("data", {}).get("page", {})
    total_count = page_info.get("count", 0)
    total_acount = page_info.get("acount", 0)
    
    print(f"   总评论数: {total_count}")
    print(f"   总回复数: {total_acount}")
    
    # 处理评论
    hot_comments = process_comments(hot_data, top_n)
    print(f"   获取热门评论: {len(hot_comments)} 条")
    
    # 显示前5条
    print("\n📝 前5条热门评论:")
    for i, c in enumerate(hot_comments[:5], 1):
        up_tag = " [UP主]" if c["is_up"] else ""
        top_tag = " [置顶]" if c["is_top"] else ""
        print(f"\n{i}. [{c['user']['name']}]{up_tag}{top_tag} 👍{c['like']} 💬{c['rcount']}")
        print(f"   {c['content'][:150]}...")
    
    # 保存结果
    result = {
        "bvid": bvid,
        "oid": oid,
        "title": title,
        "total_count": total_count,
        "total_acount": total_acount,
        "hot_comments": hot_comments
    }
    
    output_path = f"/tmp/{bvid}_comments.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 已保存: {output_path}")
    
    # 输出JSON结果
    print("\n" + "="*60)
    print("RESULT_JSON_START")
    print(json.dumps(result, ensure_ascii=False))
    print("RESULT_JSON_END")
    print("="*60)
    
    print(f"\n✅ 评论获取完成!")
    return result


if __name__ == "__main__":
    main()
