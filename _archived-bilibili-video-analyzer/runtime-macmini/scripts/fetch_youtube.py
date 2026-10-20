#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_youtube.py — YouTube 视频独立分析入口（对标 fetch_all.py，针对 YouTube）

职责：采集 YouTube 视频的 metadata / 字幕 / 评论，收敛为分析引擎的
AnalysisInput(platform='youtube')，产出 Obsidian-ready Markdown 报告。

数据采集（全程 best-effort 降级，任一失败不阻塞其余）：
  1. metadata：yt-dlp --dump-json（title / duration / uploader / description）
  2. 字幕：优先 youtube-transcript-api（免 yt-dlp），fallback yt-dlp --write-auto-subs
  3. 评论：复用 fetch_youtube_comments.py（yt-dlp / youtube-comment-downloader 双路径）

输出：
  - /tmp/{video_id}_youtube_report.md（Obsidian Markdown）
  - stdout 走 RESULT_JSON_START/END 协议（兼容 fetch_all 生态）

用法:
  python3 fetch_youtube.py <youtube_url 或 video_id> [--limit N] [--report] [--output FILE.md]
  （--report 仅为语义对齐 fetch_all；本入口默认即产出报告）
"""

import sys
import os

# 依赖兜底：append 真实属主用户级 site-packages（youtube-transcript-api 等需要）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_env import ensure_user_site, ensure_cookie_file
ensure_user_site()

import re
import json
import shutil
import tempfile
import argparse
import subprocess

from video_analysis_engine import (
    AnalysisInput, Transcript, TranscriptSegment, Comment,
    analyze_video, render_markdown,
)
from fetch_youtube_comments import extract_video_id, fetch_youtube_comments


# ============ trace 日志（与 fetch_youtube_comments 同构）============
TRACE = []


def trace(step, status, reason=''):
    """记录一步结果。status: 'ok' | 'fail' | 'skip'。"""
    TRACE.append({'step': step, 'status': status, 'reason': reason})
    icon = {'ok': '✅', 'fail': '✗', 'skip': '·'}.get(status, '•')
    line = f"   {icon} [trace] {step}: {status}"
    if reason:
        line += f" — {reason}"
    print(line)


def yt_url(video_id):
    return f'https://www.youtube.com/watch?v={video_id}'


# ============ 1. metadata（yt-dlp --dump-json）============
def fetch_metadata(video_id):
    """yt-dlp --dump-json 拿 metadata。失败返回 {}（不抛）。"""
    if not shutil.which('yt-dlp'):
        trace('metadata', 'skip', '未安装 yt-dlp')
        return {}
    try:
        cmd = ['yt-dlp', '--dump-json', '--no-playlist', '--skip-download', yt_url(video_id)]
        cookie_path = ensure_cookie_file()
        if cookie_path:
            cmd[1:1] = ['--cookies', cookie_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0 or not result.stdout.strip():
            trace('metadata', 'fail', (result.stderr or 'no output')[-160:])
            return {}
        info = json.loads(result.stdout.strip().splitlines()[0])
        meta = {
            'title': info.get('title', '') or '',
            'duration': int(info.get('duration', 0) or 0),
            'uploader': info.get('uploader') or info.get('channel') or '',
            'description': info.get('description', '') or '',
        }
        trace('metadata', 'ok', f"{meta['title'][:40]} ({meta['duration']}s)")
        return meta
    except subprocess.TimeoutExpired:
        trace('metadata', 'fail', '超时（120s）')
        return {}
    except Exception as e:
        trace('metadata', 'fail', f'{type(e).__name__}: {e}')
        return {}


# ============ 2. 字幕 ============
_SUB_LANGS = ['zh-Hans', 'zh-Hant', 'zh', 'zh-CN', 'en', 'en-US']


def fetch_subtitle_via_api(video_id):
    """youtube-transcript-api 抓字幕（免 yt-dlp）。返回 Transcript 或 None。

    兼容新旧 API：新版为实例方法 .fetch()，旧版为类方法 .get_transcript()。
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        trace('subtitle-api', 'skip', '未安装 youtube-transcript-api')
        return None

    raw = None
    try:
        # 新版实例 API
        if hasattr(YouTubeTranscriptApi, 'fetch') and not hasattr(YouTubeTranscriptApi, 'get_transcript'):
            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id, languages=_SUB_LANGS)
            raw = fetched.to_raw_data() if hasattr(fetched, 'to_raw_data') else [
                {'text': s.text, 'start': s.start, 'duration': getattr(s, 'duration', 0)}
                for s in fetched
            ]
        else:
            # 旧版类方法 API
            raw = YouTubeTranscriptApi.get_transcript(video_id, languages=_SUB_LANGS)
    except Exception as e:
        trace('subtitle-api', 'fail', f'{type(e).__name__}: {e}')
        return None

    if not raw:
        trace('subtitle-api', 'fail', '返回空字幕')
        return None

    segments = []
    for item in raw:
        text = (item.get('text') or '').strip()
        if not text:
            continue
        try:
            start = float(item.get('start', 0) or 0)
        except (TypeError, ValueError):
            start = 0.0
        segments.append(TranscriptSegment(start=start, text=text))
    if not segments:
        trace('subtitle-api', 'fail', '解析后片段为空')
        return None
    trace('subtitle-api', 'ok', f'{len(segments)} 片段')
    return Transcript(segments=segments, language='auto', source='youtube-transcript-api')


def _parse_json3(path):
    """解析 yt-dlp 导出的 json3 字幕：{events:[{tStartMs,segs:[{utf8}]}]}。"""
    segments = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return segments
    for ev in data.get('events', []) or []:
        text = ''.join(s.get('utf8', '') for s in (ev.get('segs') or []))
        text = text.strip()
        if text:
            start = float(ev.get('tStartMs', 0) or 0) / 1000.0
            segments.append(TranscriptSegment(start=start, text=text))
    return segments


def fetch_subtitle_via_ytdlp(video_id):
    """fallback：yt-dlp --write-auto-subs 下 json3 字幕并解析。返回 Transcript 或 None。"""
    if not shutil.which('yt-dlp'):
        trace('subtitle-ytdlp', 'skip', '未安装 yt-dlp')
        return None
    tmpdir = tempfile.mkdtemp(prefix=f'yt_subs_{video_id}_')
    try:
        out_tpl = os.path.join(tmpdir, '%(id)s')
        cmd = [
            'yt-dlp', '--write-auto-subs', '--write-subs',
            '--sub-langs', 'zh.*,zh-Hans,zh-Hant,en.*',
            '--sub-format', 'json3', '--skip-download', '--no-playlist',
            '-o', out_tpl, yt_url(video_id),
        ]
        cookie_path = ensure_cookie_file()
        if cookie_path:
            cmd[1:1] = ['--cookies', cookie_path]
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        sub_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith('.json3')]
        if not sub_files:
            trace('subtitle-ytdlp', 'fail', '无 json3 字幕文件（可能无字幕）')
            return None
        # 优先中文字幕文件
        sub_files.sort(key=lambda p: (0 if ('.zh' in os.path.basename(p)) else 1, p))
        segments = _parse_json3(sub_files[0])
        if not segments:
            trace('subtitle-ytdlp', 'fail', 'json3 解析后为空')
            return None
        lang = 'zh' if '.zh' in os.path.basename(sub_files[0]) else 'en'
        trace('subtitle-ytdlp', 'ok', f'{len(segments)} 片段 ({os.path.basename(sub_files[0])})')
        return Transcript(segments=segments, language=lang, source='yt-dlp-auto-subs')
    except subprocess.TimeoutExpired:
        trace('subtitle-ytdlp', 'fail', '超时（180s）')
        return None
    except Exception as e:
        trace('subtitle-ytdlp', 'fail', f'{type(e).__name__}: {e}')
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def fetch_subtitle(video_id):
    """字幕双路径：youtube-transcript-api 优先，yt-dlp --write-auto-subs 兜底。"""
    tr = fetch_subtitle_via_api(video_id)
    if tr is None:
        tr = fetch_subtitle_via_ytdlp(video_id)
    return tr


# ============ 3. 评论 ============
def fetch_comments(video_id, limit):
    """复用 fetch_youtube_comments，返回 (Comment 列表, 原始结果 dict)。"""
    try:
        res = fetch_youtube_comments(video_id, limit)
    except Exception as e:
        trace('comments', 'fail', f'{type(e).__name__}: {e}')
        return [], {'status': 'failed', 'count': 0, 'comments': []}
    comments = [
        Comment(
            text=c.get('text', '') or '',
            likes=int(c.get('likes', 0) or 0),
            author=c.get('author', '') or '',
            platform='youtube',
            is_reply=bool(c.get('is_reply')),
            timestamp=c.get('timestamp', '') or '',
        )
        for c in (res.get('comments') or [])
    ]
    trace('comments', 'ok' if res.get('status') != 'failed' else 'fail',
          f"{res.get('count', 0)} 条 (source={res.get('source')})")
    return comments, res


# ============ 主流程 ============
def build_report(video_id, limit):
    """采集 → AnalysisInput(platform='youtube') → 报告。返回 (markdown, report, meta, comments_res)。"""
    print("\n📋 [1/3] 获取 metadata...")
    meta = fetch_metadata(video_id)

    print("\n📖 [2/3] 获取字幕...")
    transcript = fetch_subtitle(video_id)

    print("\n💬 [3/3] 获取评论...")
    comments, comments_res = fetch_comments(video_id, limit)

    # claim 提取（best-effort，有字幕才做）
    fact_checks = None
    if transcript and transcript.segments:
        try:
            import fact_check_wrr as fcw
            claims = fcw.extract_claims(transcript.full_text())
            fact_checks = fcw.build_result(claims, video_id, dry_run=True)
        except Exception:
            fact_checks = None

    inp = AnalysisInput(
        video_id=video_id,
        title=meta.get('title', '') or '',
        author=meta.get('uploader', '') or '',
        duration=int(meta.get('duration', 0) or 0),
        platform='youtube',
        description=meta.get('description', '') or '',
        transcript=transcript,
        comments=comments,
        fact_checks=fact_checks,
    )
    report = analyze_video(inp)
    return render_markdown(report), report, meta, comments_res


def main():
    parser = argparse.ArgumentParser(
        description='YouTube 视频独立分析入口（metadata + 字幕 + 评论 → Obsidian 报告）',
    )
    parser.add_argument('target', help='YouTube URL 或 11 位 video_id')
    parser.add_argument('--limit', type=int, default=50, help='抓取评论数上限（默认 50）')
    parser.add_argument('--report', action='store_true', help='生成报告（默认即生成，仅语义对齐 fetch_all）')
    parser.add_argument('--output', help='Markdown 输出路径（默认 /tmp/{video_id}_youtube_report.md）')
    args = parser.parse_args()

    video_id = extract_video_id(args.target)
    if not video_id:
        print(f'❌ 无法识别 YouTube video_id: {args.target}')
        print('\nRESULT_JSON_START')
        print(json.dumps({'status': 'failed', 'video_id': None,
                          'error': 'invalid url/id'}, ensure_ascii=False, indent=2))
        print('RESULT_JSON_END')
        sys.exit(1)

    print(f'🎬 YouTube 视频分析: {video_id} (limit={args.limit})')
    print('=' * 70)

    markdown, report, meta, comments_res = build_report(video_id, args.limit)

    out_path = args.output or f'/tmp/{video_id}_youtube_report.md'
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f'\n💾 报告已保存: {out_path}  ({len(markdown)} 字符)')
    except OSError as e:
        out_path = None
        print(f'\n⚠️  报告保存失败: {e}')

    fm = report.get('frontmatter', {})
    print(f"   标题: {fm.get('title') or '（未知）'}")
    print(f"   字幕: {'有' if fm.get('has_transcript') else '无'} | "
          f"评论: {fm.get('comment_count', 0)} 条")

    out = {
        'status': 'ok',
        'video_id': video_id,
        'platform': 'youtube',
        'report_path': out_path,
        'markdown_chars': len(markdown),
        'frontmatter': fm,
        'sections': list(report.get('sections', {}).keys()),
        'comments_source': comments_res.get('source'),
        'comments_count': comments_res.get('count', 0),
        'trace': TRACE,
    }
    print('\n' + '=' * 70)
    print('RESULT_JSON_START')
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print('RESULT_JSON_END')


if __name__ == '__main__':
    main()
