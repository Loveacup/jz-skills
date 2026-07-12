#!/usr/bin/env python3
"""
获取 YouTube 视频评论（跨平台口碑分析）

用法: python3 fetch_youtube_comments.py <YouTube URL> [--limit N]

特点:
- 使用 youtube-comment-downloader (无需 API key)
- 支持自定义抓取数量上限
- 输出 RESULT_JSON 格式供 fetch_all.py 消费
"""

import sys
import os
import json
import re
from urllib.parse import urlparse, parse_qs

# 依赖兜底
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site
ensure_user_site()


def extract_video_id(url_or_id):
    """从 YouTube URL 或 video_id 提取视频 ID"""
    if not url_or_id:
        return None

    # 已经是 11 字符 video_id
    if re.match(r'^[0-9A-Za-z_-]{11}$', url_or_id):
        return url_or_id

    # 标准 watch?v= 格式
    if 'youtube.com/watch' in url_or_id:
        parsed = urlparse(url_or_id)
        params = parse_qs(parsed.query)
        if 'v' in params and params['v']:
            return params['v'][0]

    # youtu.be 短链接
    if 'youtu.be/' in url_or_id:
        match = re.search(r'youtu\.be/([0-9A-Za-z_-]{11})', url_or_id)
        if match:
            return match.group(1)

    return None


def fetch_youtube_comments_native(video_id, limit=100):
    """使用 youtube-comment-downloader 抓取评论（无需 API key）

    Returns:
        {'comments': [...], 'count': N, 'source': 'youtube-comment-downloader'}
        或失败时返回 None
    """
    try:
        from youtube_comment_downloader import YoutubeCommentDownloader
    except ImportError:
        return None

    try:
        downloader = YoutubeCommentDownloader()
        generator = downloader.get_comments_from_url(
            f'https://www.youtube.com/watch?v={video_id}',
            sort_by=0  # 0=top, 1=new
        )

        comments = []
        for i, comment in enumerate(generator):
            if i >= limit:
                break

            comments.append({
                'text': comment.get('text', ''),
                'author': comment.get('author', ''),
                'likes': comment.get('votes', 0),
                'time': comment.get('time', ''),
                'is_reply': bool(comment.get('parent')),
                'platform': 'youtube',
            })

        return {
            'comments': comments,
            'count': len(comments),
            'source': 'youtube-comment-downloader'
        }
    except Exception as e:
        print(f"❌ youtube-comment-downloader 失败: {e}", file=sys.stderr)
        return None


def fetch_youtube_comments_ytdlp(video_id, limit=100):
    """使用 yt-dlp 抓取评论（备用方案）

    Returns:
        {'comments': [...], 'count': N, 'source': 'yt-dlp'}
        或失败时返回 None
    """
    import subprocess

    try:
        # yt-dlp --skip-download --write-comments --print-json
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--print', '%(comments)j',
            f'https://www.youtube.com/watch?v={video_id}'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return None

        # yt-dlp 输出 JSON array
        comments_raw = json.loads(result.stdout or '[]')
        comments = []

        for c in comments_raw[:limit]:
            comments.append({
                'text': c.get('text', ''),
                'author': c.get('author', ''),
                'likes': c.get('like_count', 0),
                'time': c.get('timestamp', ''),
                'is_reply': bool(c.get('parent')),
                'platform': 'youtube',
            })

        return {
            'comments': comments,
            'count': len(comments),
            'source': 'yt-dlp'
        }
    except Exception as e:
        print(f"❌ yt-dlp 失败: {e}", file=sys.stderr)
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description='获取 YouTube 视频评论')
    parser.add_argument('url', help='YouTube URL 或 video_id')
    parser.add_argument('--limit', type=int, default=100, help='抓取数量上限（默认 100）')

    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"❌ 无法解析 YouTube 视频 ID: {args.url}", file=sys.stderr)
        sys.exit(1)

    print(f"🎬 获取 YouTube 评论: {video_id} (limit={args.limit})")

    # 优先尝试 youtube-comment-downloader（无需 API key）
    result = fetch_youtube_comments_native(video_id, args.limit)

    # 备用方案：yt-dlp
    if not result:
        print("   · youtube-comment-downloader 不可用，尝试 yt-dlp...")
        result = fetch_youtube_comments_ytdlp(video_id, args.limit)

    if not result:
        print("❌ 所有方案均失败", file=sys.stderr)
        sys.exit(1)

    print(f"✅ 成功抓取 {result['count']} 条评论 (source={result['source']})")

    # 输出 RESULT_JSON 供 fetch_all.py 消费
    print("\nRESULT_JSON_START")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("RESULT_JSON_END")


if __name__ == '__main__':
    main()
