#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_analysis_engine.py — 平台无关的视频分析引擎（骨架）

定位：bilibili / youtube 等平台脚本采集到的原始数据，统一收敛为本模块的
数据类，再交给 analyze_video() 产出 Obsidian-ready 的 Markdown 报告字典。

Phase 2 范围：只做**基础结构分析**（时长、章节占位、高频词、评论概览、
claim 核查概览）。Phase 3 再补深度分析（情感、观点聚类、翻译质量等）。

设计约束：
  - 纯标准库，可被任何解释器 import（不引入 jieba 等可选依赖）。
  - 数据类全部 dataclass，便于上层构造与序列化。
  - analyze_video(input) -> {'frontmatter': dict, 'sections': {编号节: md}}。

用法（作为库）:
  from video_analysis_engine import AnalysisInput, Transcript, analyze_video
  report = analyze_video(AnalysisInput(...))

用法（自检 demo）:
  python3 video_analysis_engine.py --demo
"""

from __future__ import annotations

import os
import re
import json
import argparse
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# ============ 统一数据类 ============
@dataclass
class TranscriptSegment:
    """一条字幕/转录片段。"""
    start: float            # 起始时间（秒）
    text: str               # 文本内容
    end: Optional[float] = None


@dataclass
class Transcript:
    """整段字幕/转录。"""
    segments: List[TranscriptSegment] = field(default_factory=list)
    language: str = 'unknown'
    source: str = 'unknown'   # official | ytdlp | whisper.cpp | mlx-whisper ...

    def full_text(self) -> str:
        """拼接全部片段为纯文本。"""
        return '\n'.join(s.text for s in self.segments if s.text)


@dataclass
class Comment:
    """一条评论（B站 / YouTube 通用）。"""
    text: str
    likes: int = 0
    author: str = ''
    platform: str = 'bilibili'   # bilibili | youtube
    is_reply: bool = False
    timestamp: str = ''


@dataclass
class Danmaku:
    """一条弹幕。"""
    text: str
    time: float = 0.0    # 弹幕在视频中出现的时间（秒）


@dataclass
class AnalysisInput:
    """分析引擎的统一输入。"""
    video_id: str                                   # BV 号或 YouTube id
    title: str = ''
    author: str = ''
    duration: int = 0                               # 秒
    platform: str = 'bilibili'
    description: str = ''
    transcript: Optional[Transcript] = None
    comments: List[Comment] = field(default_factory=list)
    danmaku: List[Danmaku] = field(default_factory=list)
    fact_checks: Optional[Dict[str, Any]] = None    # fact_check_wrr 输出
    cross_platform: Optional[Dict[str, Any]] = None # 搬运检测：youtube_url + 评论


# ============ 证据来源 Gate ============
def detect_external_research_route() -> Dict[str, Any]:
    """检测辅助事实核查/扩展信息路由。

    优先本地 WRR（独立仓库或 Hermes plugin symlink）。若不可用，不阻塞报告，
    标记为 fallback_search，由上层使用当前 Hermes 可用的 Exa/Brave/web_search 等搜索工具。
    """
    candidates = [
        os.path.expanduser('~/code/web-research-router'),
        os.path.expanduser('~/.hermes/plugins/wrr'),
    ]
    if any(os.path.exists(p) for p in candidates):
        return {
            'available': True,
            'route': 'wrr_local',
            'mode': 'grounding',
            'reason': 'local WRR detected',
        }
    return {
        'available': True,
        'route': 'fallback_search',
        'mode': 'grounding',
        'reason': 'local WRR not detected; use configured web/search tools',
    }


def build_evidence_source_gate(inp: AnalysisInput) -> Dict[str, Any]:
    """构建报告生成前的来源充分性 gate。

    verify_report.py 只检查结构深度；这里负责声明每类证据是否存在、哪些章节可用，
    以及是否允许生成正式 full report。当前硬规则：正式报告必须有 transcript。
    """
    transcript = inp.transcript
    has_transcript = bool(transcript and transcript.segments)
    full_text = transcript.full_text() if has_transcript else ''
    has_comments = bool(inp.comments)
    has_danmaku = bool(inp.danmaku)
    has_fact_checks = bool(inp.fact_checks and inp.fact_checks.get('claims'))
    external_research = detect_external_research_route()

    sources = {
        'transcript': {
            'available': has_transcript,
            'source': transcript.source if has_transcript else '',
            'language': transcript.language if has_transcript else '',
            'segments': len(transcript.segments) if has_transcript else 0,
            'chars': len(full_text),
        },
        'comments': {
            'available': has_comments,
            'count': len(inp.comments),
        },
        'danmaku': {
            'available': has_danmaku,
            'count': len(inp.danmaku),
        },
        'fact_checks': {
            'available': has_fact_checks,
            'claims': len(inp.fact_checks.get('claims', [])) if has_fact_checks else 0,
        },
        'external_research': external_research,
    }

    factcheck_evidence = ['fact_checks'] if has_fact_checks else []
    if not factcheck_evidence and has_transcript and external_research.get('available'):
        factcheck_evidence = ['transcript', 'external_research']

    sections = {
        '§1 基本信息': {
            'allowed': True,
            'requires': [],
            'evidence': ['metadata'],
        },
        '§2 内容分析': {
            'allowed': has_transcript,
            'requires': ['transcript'],
            'evidence': ['transcript'] if has_transcript else [],
        },
        '§3 评论分析': {
            'allowed': has_comments or has_danmaku,
            'requires': [],
            'evidence': [k for k, ok in (('comments', has_comments), ('danmaku', has_danmaku)) if ok],
        },
        '§4 关键声明核查': {
            'allowed': bool(factcheck_evidence),
            'requires': [],
            'evidence': factcheck_evidence,
        },
    }

    return {
        'can_generate_formal_report': has_transcript,
        'blocking_reason': '' if has_transcript else 'missing_transcript',
        'sources': sources,
        'sections': sections,
    }


# ============ 基础分析工具 ============
# 高频词停用词（中文常见虚词 + 英文 stopwords 的精简集），不追求完整
_STOPWORDS = set("""
的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好
自己 这 那 这个 那个 我们 你们 他们 它 还 把 被 让 给 但 而 与 或 等 啊 吧 呢 吗
这样 那样 因为 所以 如果 然后 现在 已经 可以 这些 那些 一些 什么 怎么 这种
the a an and or but of to in on for with at by is are was were be been it this that
i you we they he she it my your our their as from so if then than will can just
""".split())


def _tokenize(text: str) -> List[str]:
    """轻量分词：英文按词、中文按 2-gram 近似（不引入 jieba）。

    中文无空格分词困难，用相邻汉字 2-gram 作为词的近似单位——足够支撑
    「高频词」概览，避免引入可选依赖。
    """
    tokens = []
    # 英文/数字词
    for w in re.findall(r'[A-Za-z][A-Za-z\-]+|\d+(?:\.\d+)?', text):
        wl = w.lower()
        if len(wl) >= 2 and wl not in _STOPWORDS:
            tokens.append(wl)
    # 中文 2-gram
    for run in re.findall(r'[一-鿿]{2,}', text):
        for i in range(len(run) - 1):
            bg = run[i:i + 2]
            if bg not in _STOPWORDS:
                tokens.append(bg)
    return tokens


def top_keywords(text: str, n: int = 15) -> List[tuple]:
    """返回 [(word, count), ...] 前 n 个高频词。"""
    if not text:
        return []
    return Counter(_tokenize(text)).most_common(n)


def _fmt_duration(seconds: int) -> str:
    """秒 → 'H:MM:SS' 或 'M:SS'。"""
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


# ============ 分节构建 ============
def _section_basic(inp: AnalysisInput) -> str:
    lines = [
        f'- **标题**: {inp.title or "（未知）"}',
        f'- **作者/UP主**: {inp.author or "（未知）"}',
        f'- **平台**: {inp.platform}',
        f'- **视频 ID**: {inp.video_id}',
        f'- **时长**: {_fmt_duration(inp.duration)}',
    ]
    if inp.cross_platform and inp.cross_platform.get('youtube_url'):
        lines.append(f'- **搬运源**: {inp.cross_platform["youtube_url"]}')
    return '\n'.join(lines)


def _section_content(inp: AnalysisInput) -> str:
    tr = inp.transcript
    if not tr or not tr.segments:
        return '_无字幕/转录，跳过内容分析。_'
    text = tr.full_text()
    kws = top_keywords(text, 15)
    parts = [
        f'- **字幕来源**: {tr.source}（语言 {tr.language}）',
        f'- **字幕片段数**: {len(tr.segments)}',
        f'- **正文字数**: 约 {len(text)} 字',
        '',
        '**高频词 TOP15**:',
        '',
        ' / '.join(f'`{w}`×{c}' for w, c in kws) if kws else '_无_',
    ]
    return '\n'.join(parts)


def _section_comments(inp: AnalysisInput) -> str:
    parts = []
    bili = [c for c in inp.comments if c.platform == 'bilibili']
    yt = [c for c in inp.comments if c.platform == 'youtube']
    # 跨平台搬运评论也可能挂在 cross_platform
    if inp.cross_platform:
        ytc = (inp.cross_platform.get('youtube_comments') or {}).get('comments') or []
        yt = yt + [
            Comment(text=c.get('text', ''), likes=c.get('likes', 0),
                    author=c.get('author', ''), platform='youtube',
                    is_reply=c.get('is_reply', False))
            for c in ytc
        ]

    parts.append(f'- **B站评论**: {len(bili)} 条 / **YouTube 评论**: {len(yt)} 条')
    parts.append(f'- **弹幕**: {len(inp.danmaku)} 条')

    def _top(comments, label):
        top = sorted(comments, key=lambda c: c.likes, reverse=True)[:3]
        if not top:
            return []
        out = ['', f'**{label} 热评 TOP3**:', '']
        for i, c in enumerate(top, 1):
            out.append(f'{i}. 👍{c.likes} [{c.author}] {c.text[:80]}')
        return out

    parts += _top(bili, 'B站')
    parts += _top(yt, 'YouTube')
    return '\n'.join(parts) if parts else '_无评论数据。_'


def _section_factcheck(inp: AnalysisInput) -> str:
    fc = inp.fact_checks
    if not fc or not fc.get('claims'):
        return '_未提供 claim 核查数据（运行 fact_check_wrr.py 生成）。_'
    s = fc.get('summary', {})
    lines = [
        f'- **claim 总数**: {s.get("total", len(fc["claims"]))}',
        f'- **已核实/待定/未找到**: {s.get("verified", 0)} / {s.get("uncertain", 0)} / {s.get("unfound", 0)}',
    ]
    if s.get('by_type'):
        lines.append(f'- **类型分布**: {s["by_type"]}')
    lines += ['', '**关键 claim（按可验证性）**:', '']
    for i, c in enumerate(fc['claims'][:8], 1):
        verdict = c.get('verdict', 'uncertain')
        lines.append(f'{i}. [{c.get("type")}/{verdict}] {c.get("claim", "")[:90]}')
    return '\n'.join(lines)


def analyze_video(inp: AnalysisInput) -> Dict[str, Any]:
    """主入口：返回 Obsidian-ready 报告字典。

    返回结构:
      {
        'frontmatter': { ...YAML 友好的 dict... },
        'evidence_gate': { ...来源充分性 gate... },
        'sections': { '§1 基本信息': md, '§2 内容分析': md,
                      '§3 评论分析': md, '§4 关键声明核查': md },
      }
    """
    evidence_gate = build_evidence_source_gate(inp)
    transcript_source = evidence_gate['sources']['transcript']['source']
    frontmatter = {
        'title': inp.title,
        'platform': inp.platform,
        'video_id': inp.video_id,
        'author': inp.author,
        'duration_seconds': inp.duration,
        'has_transcript': bool(inp.transcript and inp.transcript.segments),
        'evidence_gate': 'pass' if evidence_gate['can_generate_formal_report'] else 'blocked',
        'evidence_transcript_source': transcript_source,
        'comment_count': len(inp.comments),
        'danmaku_count': len(inp.danmaku),
        'is_cross_platform': bool(inp.cross_platform and inp.cross_platform.get('youtube_url')),
        'tags': ['video-analysis', inp.platform],
    }

    sections = {
        '§1 基本信息': _section_basic(inp),
        '§2 内容分析': _section_content(inp),
        '§3 评论分析': _section_comments(inp),
        '§4 关键声明核查': _section_factcheck(inp),
    }
    return {'frontmatter': frontmatter, 'evidence_gate': evidence_gate, 'sections': sections}


def render_markdown(report: Dict[str, Any]) -> str:
    """把 analyze_video 的报告字典渲染成完整 Markdown 文本（含 YAML frontmatter）。"""
    fm = report.get('frontmatter', {})
    lines = ['---']
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f'{k}: [{", ".join(map(str, v))}]')
        else:
            lines.append(f'{k}: {v}')
    lines.append('---')
    lines.append('')
    for title, body in report.get('sections', {}).items():
        lines.append(f'## {title}')
        lines.append('')
        lines.append(body)
        lines.append('')
    return '\n'.join(lines)


# ============ 自检 demo ============
def _demo() -> AnalysisInput:
    return AnalysisInput(
        video_id='BVdemo123',
        title='示例视频：AI 模型横评',
        author='示例UP主',
        duration=754,
        platform='bilibili',
        description='搬运自 https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, 'GPT-4 在 2023 年 3 月发布，是当时最强的模型。'),
                TranscriptSegment(5.0, '它的参数量突破 1000 亿，准确率提升了 30%。'),
            ],
            language='zh', source='official',
        ),
        comments=[
            Comment('讲得太好了', likes=120, author='观众A', platform='bilibili'),
            Comment('great video', likes=88, author='userB', platform='youtube'),
        ],
        danmaku=[Danmaku('前排', 1.2), Danmaku('学到了', 30.0)],
        fact_checks={
            'claims': [
                {'claim': 'GPT-4 在 2023 年 3 月发布', 'type': 'date',
                 'verdict': 'uncertain', 'sources': []},
                {'claim': '参数量突破 1000 亿', 'type': 'number',
                 'verdict': 'uncertain', 'sources': []},
            ],
            'summary': {'total': 2, 'verified': 0, 'uncertain': 2, 'unfound': 0,
                        'by_type': {'number': 1, 'date': 1, 'ranking': 0, 'superlative': 0}},
        },
        cross_platform={'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},
    )


def main():
    parser = argparse.ArgumentParser(description='视频分析引擎（骨架）自检')
    parser.add_argument('--demo', action='store_true', help='用内置示例数据跑一遍并打印报告')
    parser.add_argument('--markdown', action='store_true', help='同时打印渲染后的 Markdown')
    args = parser.parse_args()

    if not args.demo:
        parser.print_help()
        return

    report = analyze_video(_demo())
    print('RESULT_JSON_START')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('RESULT_JSON_END')
    if args.markdown:
        print('\n' + '=' * 60)
        print(render_markdown(report))


if __name__ == '__main__':
    main()
