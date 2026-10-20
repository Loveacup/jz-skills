#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_youtube_comments.py — YouTube 评论双路径抓取

用途：B站搬运视频常转载自 YouTube，抓取原片评论可做跨平台口碑对比。
本脚本可**独立运行**，也被 fetch_all.py 的搬运检测自动调用。

双路径（best-effort 降级，任一成功即返回）：
  路径1（优先）yt-dlp --write-comments --skip-download
      - 复用 Netscape cookie 文件 / --cookies-from-browser chrome 获取登录态评论
      - 解析 yt-dlp 落盘的 {id}.info.json 中的 comments 字段
  路径2（fallback）youtube-comment-downloader / yt-comment-dl CLI
      - 输出 jsonl，逐行解析

输出统一格式（与 B站评论概念对齐，字段加 platform=youtube）：
  {
    "status": "ok" | "degraded" | "failed",
    "source": "yt_dlp" | "yt_comment_dl" | null,
    "count": 50,
    "comments": [
       {"text","likes","author","timestamp","platform":"youtube","is_reply"}, ...
    ],
    "video_id": "...",
    "trace": [ {step,status,reason}, ... ]
  }

约定：输出走 RESULT_JSON_START/END 协议（供 fetch_all.py 解析）。

用法:
  python3 fetch_youtube_comments.py <youtube_url 或 video_id> [--limit N] [--output FILE.json]
"""

import sys
import os

# 依赖兜底：append 真实属主用户级 site-packages（与其它 fetch_* 一致）。详见 bili_env.py。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site, ensure_cookie_file
ensure_user_site()

import re
import json
import shutil
import tempfile
import argparse
import subprocess
from datetime import datetime, timezone


# ============ trace 日志（与 fetch_subtitle_auto 同构）============
TRACE = []


def trace(step, status, reason=''):
    """记录一步结果。status: 'ok' | 'fail' | 'skip'。"""
    TRACE.append({'step': step, 'status': status, 'reason': reason})
    icon = {'ok': '✅', 'fail': '✗', 'skip': '·'}.get(status, '•')
    line = f"   {icon} [trace] {step}: {status}"
    if reason:
        line += f" — {reason}"
    print(line)


# ============ 工具函数 ============
def extract_video_id(url_or_id):
    """从 URL 或裸 id 中提取 11 位 YouTube video_id，提取不到返回 None。

    覆盖：youtube.com/watch?v=ID、youtu.be/ID、shorts/ID、embed/ID，以及裸 id。
    """
    s = (url_or_id or '').strip()
    # 裸 11 位 id（YouTube id 由 [A-Za-z0-9_-] 组成）
    if re.fullmatch(r'[0-9A-Za-z_-]{11}', s):
        return s
    patterns = [
        r'(?:youtube\.com/watch\?[^ ]*\bv=)([0-9A-Za-z_-]{11})',
        r'youtu\.be/([0-9A-Za-z_-]{11})',
        r'youtube\.com/shorts/([0-9A-Za-z_-]{11})',
        r'youtube\.com/embed/([0-9A-Za-z_-]{11})',
        r'[?&]v=([0-9A-Za-z_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, s)
        if m:
            return m.group(1)
    return None


def _parse_likes(val):
    """点赞数归一化为 int。

    yt-dlp 给 int/None；yt-comment-dl 给字符串如 "5" / "1.2K" / "3.4万"。
    解析失败返回 0。
    """
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().replace(',', '')
    if not s:
        return 0
    try:
        mult = 1.0
        if s[-1] in 'kK':
            mult, s = 1e3, s[:-1]
        elif s[-1] in 'mM':
            mult, s = 1e6, s[:-1]
        elif s.endswith('万'):
            mult, s = 1e4, s[:-1]
        elif s.endswith('亿'):
            mult, s = 1e8, s[:-1]
        return int(float(s) * mult)
    except (ValueError, IndexError):
        return 0


def _epoch_to_date(ts):
    """epoch 秒 → 'YYYY-MM-DD'，无效返回空串。"""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime('%Y-%m-%d')
    except (ValueError, TypeError, OSError):
        return ''


def yt_url(video_id):
    return f'https://www.youtube.com/watch?v={video_id}'


# ============ 路径1：yt-dlp ============
def fetch_via_ytdlp(video_id, limit):
    """yt-dlp --write-comments 抓评论，解析 info.json。失败返回 None。"""
    if not shutil.which('yt-dlp'):
        trace('yt-dlp', 'skip', '未安装 yt-dlp')
        return None

    tmpdir = tempfile.mkdtemp(prefix=f'yt_comments_{video_id}_')
    try:
        out_tpl = os.path.join(tmpdir, '%(id)s')
        cmd = [
            'yt-dlp',
            '--write-comments',
            '--skip-download',
            '--no-playlist',
            # 限制评论抓取量，避免热门视频拉取数万条拖垮耗时
            '--extractor-args', f'youtube:comment_sort=top;max_comments={max(limit * 2, limit)},all,all',
            '-o', out_tpl,
            yt_url(video_id),
        ]
        # cookie：优先复用 Netscape 文件（best-effort），退回浏览器直读 chrome
        cookie_path = ensure_cookie_file()
        if cookie_path:
            cmd[1:1] = ['--cookies', cookie_path]
        else:
            cmd[1:1] = ['--cookies-from-browser', 'chrome']

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # 找 info.json
        info_files = [
            os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
            if f.endswith('.info.json')
        ]
        if not info_files:
            trace('yt-dlp', 'fail', (result.stderr or 'no info.json')[-160:])
            return None

        with open(info_files[0], 'r', encoding='utf-8') as f:
            info = json.load(f)

        raw_comments = info.get('comments') or []
        if not raw_comments:
            trace('yt-dlp', 'fail', '评论字段为空（可能评论关闭或需登录）')
            return None

        comments = []
        for c in raw_comments:
            parent = c.get('parent', 'root')
            comments.append({
                'text': c.get('text', ''),
                'likes': _parse_likes(c.get('like_count')),
                'author': c.get('author', ''),
                'timestamp': _epoch_to_date(c.get('timestamp')) or c.get('_time_text', ''),
                'platform': 'youtube',
                'is_reply': bool(parent and parent != 'root'),
            })

        # 按点赞降序，截到 limit
        comments.sort(key=lambda x: x['likes'], reverse=True)
        comments = comments[:limit]

        trace('yt-dlp', 'ok', f'{len(comments)} 条（原始 {len(raw_comments)}）')
        return {'source': 'yt_dlp', 'comments': comments}
    except subprocess.TimeoutExpired:
        trace('yt-dlp', 'fail', '超时（300s）')
        return None
    except Exception as e:
        trace('yt-dlp', 'fail', f'{type(e).__name__}: {e}')
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ============ 路径2：youtube-comment-downloader ============
def _find_yt_comment_dl():
    """返回可用的 youtube-comment-downloader 可执行名，找不到返回 None。"""
    for name in ('youtube-comment-downloader', 'yt-comment-dl'):
        if shutil.which(name):
            return name
    return None


def fetch_via_yt_comment_dl(video_id, limit):
    """youtube-comment-downloader CLI 抓评论（jsonl）。失败返回 None。"""
    exe = _find_yt_comment_dl()
    if not exe:
        trace('yt-comment-dl', 'skip', '未安装 youtube-comment-downloader')
        return None

    tmpdir = tempfile.mkdtemp(prefix=f'ytcdl_{video_id}_')
    out_path = os.path.join(tmpdir, f'{video_id}.json')
    try:
        # youtube-comment-downloader：--youtubeid + --output（jsonl，每行一条）
        # --limit 限制条数，--sort 1 为热门
        cmd = [
            exe,
            '--youtubeid', video_id,
            '--output', out_path,
            '--limit', str(limit),
            '--sort', '1',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            trace('yt-comment-dl', 'fail', (result.stderr or 'no output')[-160:])
            return None

        comments = []
        with open(out_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    c = json.loads(line)
                except json.JSONDecodeError:
                    continue
                comments.append({
                    'text': c.get('text', ''),
                    'likes': _parse_likes(c.get('votes')),
                    'author': c.get('author', ''),
                    # time_parsed 是 epoch 浮点；time 是 "2 years ago" 文本
                    'timestamp': _epoch_to_date(c.get('time_parsed')) or c.get('time', ''),
                    'platform': 'youtube',
                    'is_reply': bool(c.get('reply')),
                })

        if not comments:
            trace('yt-comment-dl', 'fail', '解析后评论为空')
            return None

        comments.sort(key=lambda x: x['likes'], reverse=True)
        comments = comments[:limit]
        trace('yt-comment-dl', 'ok', f'{len(comments)} 条')
        return {'source': 'yt_comment_dl', 'comments': comments}
    except subprocess.TimeoutExpired:
        trace('yt-comment-dl', 'fail', '超时（300s）')
        return None
    except Exception as e:
        trace('yt-comment-dl', 'fail', f'{type(e).__name__}: {e}')
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ============ 主流程 ============
def fetch_youtube_comments(video_id, limit=50):
    """双路径抓取，返回统一格式 dict（始终返回，不抛）。"""
    result = fetch_via_ytdlp(video_id, limit)
    if result is None:
        result = fetch_via_yt_comment_dl(video_id, limit)

    if result is None:
        return {
            'status': 'failed',
            'source': None,
            'count': 0,
            'comments': [],
            'video_id': video_id,
            'trace': TRACE,
        }

    comments = result['comments']
    # degraded：成功但条数明显不足目标（如评论关闭部分、登录态缺失）
    status = 'ok' if len(comments) >= min(limit, 10) else 'degraded'
    return {
        'status': status,
        'source': result['source'],
        'count': len(comments),
        'comments': comments,
        'video_id': video_id,
        'trace': TRACE,
    }


def main():
    parser = argparse.ArgumentParser(
        description='YouTube 评论双路径抓取（yt-dlp 优先，youtube-comment-downloader 兜底）',
    )
    parser.add_argument('target', help='YouTube URL 或 11 位 video_id')
    parser.add_argument('--limit', type=int, default=50, help='抓取评论数上限（默认 50）')
    parser.add_argument('--output', help='输出 JSON 路径（默认 /tmp/{video_id}_youtube_comments.json）')
    args = parser.parse_args()

    video_id = extract_video_id(args.target)
    if not video_id:
        print(f'❌ 无法从输入识别 YouTube video_id: {args.target}')
        print('\nRESULT_JSON_START')
        print(json.dumps({
            'status': 'failed', 'source': None, 'count': 0,
            'comments': [], 'video_id': None,
            'trace': [{'step': 'parse', 'status': 'fail', 'reason': 'invalid url/id'}],
        }, ensure_ascii=False, indent=2))
        print('RESULT_JSON_END')
        sys.exit(1)

    print(f'🎬 YouTube 评论抓取: {video_id} (limit={args.limit})')
    print('=' * 60)

    result = fetch_youtube_comments(video_id, args.limit)

    # 落盘
    out_path = args.output or f'/tmp/{video_id}_youtube_comments.json'
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        result['path'] = out_path
        print(f'\n💾 已保存: {out_path}')
    except OSError as e:
        print(f'\n⚠️  保存失败: {e}')

    print(f"\n📦 结果: status={result['status']} source={result['source']} count={result['count']}")
    # 展示前 3 条
    for i, c in enumerate(result['comments'][:3], 1):
        reply_tag = ' [回复]' if c['is_reply'] else ''
        print(f"  {i}. [{c['author']}]{reply_tag} 👍{c['likes']}  {c['text'][:80]}")

    print('\n' + '=' * 60)
    print('RESULT_JSON_START')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('RESULT_JSON_END')

    if result['status'] == 'failed':
        sys.exit(1)


if __name__ == '__main__':
    main()
