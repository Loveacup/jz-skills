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
    获取评论（单页）

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


def fetch_comment_replies(oid, root_rpid, sessdata=None, ps=10):
    """
    获取某条评论的回复（楼中楼）

    Args:
        oid: AV号
        root_rpid: 根评论ID
        sessdata: 登录凭证
        ps: 每页数量

    Returns:
        回复列表或空列表
    """
    url = "https://api.bilibili.com/x/v2/reply/reply"
    params = {
        "oid": oid,
        "type": 1,
        "root": root_rpid,
        "ps": ps,
        "pn": 1
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://www.bilibili.com/video/av{oid}/",
    }

    cookies = {}
    if sessdata:
        cookies["SESSDATA"] = sessdata

    try:
        resp = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            replies = data.get("data", {}).get("replies", [])
            return [
                {
                    "rpid": r.get("rpid"),
                    "user": {
                        "mid": r.get("member", {}).get("mid"),
                        "name": r.get("member", {}).get("uname"),
                    },
                    "content": r.get("content", {}).get("message", ""),
                    "like": r.get("like", 0),
                    "ctime": r.get("ctime"),
                }
                for r in replies
            ]
    except Exception:
        pass
    return []


def fetch_comments_multi_page(oid, sort=2, target_count=50, sessdata=None):
    """
    分页获取评论直到满足目标数量

    Args:
        oid: AV号
        sort: 排序方式 2=热门 0=时间
        target_count: 目标数量
        sessdata: 登录凭证

    Returns:
        (comments_list, total_count, total_acount)
    """
    all_comments = []
    page = 1
    ps = 20  # B站API每页最多20条
    total_count = 0
    total_acount = 0

    while len(all_comments) < target_count:
        data = fetch_comments(oid, sort=sort, page=page, ps=ps, sessdata=sessdata)

        if data.get("code") != 0:
            break

        replies = data.get("data", {}).get("replies", []) or []
        if not replies:
            break

        # 首次拉取记录总数
        if page == 1:
            page_info = data.get("data", {}).get("page", {})
            total_count = page_info.get("count", 0)
            total_acount = page_info.get("acount", 0)

        all_comments.extend(replies)

        # 如果返回的评论数少于ps，说明已到底
        if len(replies) < ps:
            break

        page += 1

        # 安全阀：最多拉取10页
        if page > 10:
            break

    return all_comments[:target_count], total_count, total_acount


def process_comments_from_raw_list(raw_replies, top_n=None):
    """
    处理评论数据，提取关键信息（从原始回复列表）

    Args:
        raw_replies: API返回的replies列表
        top_n: 限制数量，None表示不限制

    Returns:
        处理后的评论列表
    """
    comments = []
    for reply in raw_replies[:top_n] if top_n else raw_replies:
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
            "is_up": reply.get("is_up", False)
        }

        comments.append(comment_info)

    return comments


def process_comments(raw_data, top_n=50):
    """处理评论数据，提取关键信息（兼容旧接口）"""
    replies = raw_data.get('data', {}).get('replies', []) or []
    return process_comments_from_raw_list(replies, top_n)


def main():
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(
        description="获取 Bilibili 视频评论（支持分页、分层策略、高赞回复）"
    )
    parser.add_argument("bvid", help="BV号或URL")
    parser.add_argument("sessdata", nargs="?", default=None, help="SESSDATA 登录凭证")
    parser.add_argument(
        "count",
        nargs="?",
        type=int,
        default=None,
        help="获取评论数量（位置参数，已弃用；请用 --count，默认50）",
    )
    parser.add_argument(
        "--count",
        dest="count_opt",
        type=int,
        default=None,
        help="获取评论数量（默认50，覆盖位置参数 count）",
    )
    parser.add_argument(
        "--strategy",
        choices=["hot", "recent", "mixed"],
        default="hot",
        help="采样策略: hot=仅热门, recent=仅时间序, mixed=热门+时间序合并去重（默认hot）"
    )
    args = parser.parse_args()
    input_str = args.bvid
    sessdata = args.sessdata
    # 优先 --count，其次位置参数 count，最后默认 50
    top_n = args.count_opt if args.count_opt is not None else (args.count if args.count is not None else 50)
    strategy = args.strategy

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
    print(f"   策略: {strategy}, 目标数量: {top_n}")

    # 根据策略获取评论
    hot_comments = []
    recent_comments = []
    total_count = 0
    total_acount = 0

    if strategy in ["hot", "mixed"]:
        print(f"\n📥 正在获取热门评论（分页模式）...")
        hot_raw, total_count, total_acount = fetch_comments_multi_page(
            oid, sort=2, target_count=top_n, sessdata=sessdata
        )
        hot_comments = process_comments_from_raw_list(hot_raw)
        print(f"   获取热门评论: {len(hot_comments)} 条")

    if strategy in ["recent", "mixed"]:
        print(f"\n📥 正在获取最新评论（分页模式）...")
        recent_raw, tc, ta = fetch_comments_multi_page(
            oid, sort=0, target_count=top_n // 2 if strategy == "mixed" else top_n, sessdata=sessdata
        )
        recent_comments = process_comments_from_raw_list(recent_raw)
        print(f"   获取最新评论: {len(recent_comments)} 条")
        if not total_count:
            total_count, total_acount = tc, ta

    # 合并去重（基于rpid）
    seen_rpids = set()
    merged_comments = []
    for c in hot_comments + recent_comments:
        if c["rpid"] not in seen_rpids:
            seen_rpids.add(c["rpid"])
            merged_comments.append(c)

    print(f"\n   总评论数: {total_count}")
    print(f"   总回复数: {total_acount}")
    print(f"   去重后评论: {len(merged_comments)} 条")

    # 获取高赞回复（仅对热门评论中like高且rcount>0的）
    replies_collected = []
    high_engagement = [
        c for c in hot_comments
        if c["rcount"] > 0 and c["like"] >= 50  # 阈值：50赞且有回复
    ]

    if high_engagement:
        print(f"\n📥 正在获取 {len(high_engagement)} 条高赞评论的回复...")
        for i, comment in enumerate(high_engagement[:10], 1):  # 最多抓10条的回复
            rpid = comment["rpid"]
            replies = fetch_comment_replies(oid, rpid, sessdata=sessdata, ps=10)
            if replies:
                replies_collected.append({
                    "root_rpid": rpid,
                    "root_content": comment["content"][:50],
                    "replies": replies
                })
                print(f"   [{i}/{len(high_engagement[:10])}] rpid={rpid}: {len(replies)} 条回复")

        print(f"   ✅ 收集到 {len(replies_collected)} 组高赞回复")

    # 显示前5条
    print("\n📝 前5条评论预览:")
    for i, c in enumerate(merged_comments[:5], 1):
        up_tag = " [UP主]" if c["is_up"] else ""
        top_tag = " [置顶]" if c["is_top"] else ""
        print(f"\n{i}. [{c['user']['name']}]{up_tag}{top_tag} 👍{c['like']} 💬{c['rcount']}")
        print(f"   {c['content'][:150]}...")

    # 保存结果（向后兼容：保留hot_comments字段）
    result = {
        "bvid": bvid,
        "oid": oid,
        "title": title,
        "total_count": total_count,
        "total_acount": total_acount,
        "strategy": strategy,
        "hot_comments": hot_comments,  # 向后兼容
        "recent_comments": recent_comments if strategy in ["recent", "mixed"] else [],
        "replies": replies_collected,
        "merged_comments": merged_comments,
    }

    output_path = f"/tmp/{bvid}_comments.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存: {output_path}")
    print(f"   统计: 热门{len(hot_comments)} + 最新{len(recent_comments)} = 去重后{len(merged_comments)} + 回复组{len(replies_collected)}")

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
