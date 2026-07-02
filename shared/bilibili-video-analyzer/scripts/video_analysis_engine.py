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
import warnings
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Callable, Tuple


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


@dataclass
class SectionSpec:
    """老版报告章节的显式规格。

    这是 P2 内容规划层：不是生成文本，而是规定每节的目的、证据、门槛和
    是否允许降级。旧版 §0–§8 是 baseline；BiliNote/其它项目只能作为增强机制。
    """
    id: str
    title: str
    purpose: str
    evidence: List[str] = field(default_factory=list)
    required: bool = True
    allowed: bool = True
    quality_gate: str = ''
    min_items: int = 0
    min_words_per_item: int = 0
    needs_external_research: bool = False
    notes: str = ''


@dataclass
class ReportPlan:
    """一篇视频稿件的内容规划。

    ReportPlan 把 EvidenceSourceGate 的来源判断，映射到老版内容引擎框架。
    后续 LLM/模板/WRR 都应读 plan，而不是各自猜章节。
    """
    mode: str
    baseline: str
    can_generate_formal_report: bool
    blocking_reason: str
    sections: List[SectionSpec]
    absorbed_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


OLD_FRAMEWORK_BASELINE = 'old_bilibili_v3_framework'
BILINOTE_ABSORBED_PATTERNS = [
    'BiliNote: subtitle-first before media download',
    'BiliNote: RequestChunker/checkpoint as long-context inspiration',
    'BiliNote: prompt style knobs as plan metadata, not template replacement',
    'OpenNote: timestamped retrieval/citation for evidence-backed sections',
    'NoteTaker-py: chunk salience + clustering as future section planner',
]


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


def _section_allowed(gate: Dict[str, Any], section_name: str, default=True) -> bool:
    return bool((gate.get('sections') or {}).get(section_name, {}).get('allowed', default))


def _old_full_sections(gate: Dict[str, Any], mode: str) -> List[SectionSpec]:
    """旧版 §0–§8 的显式规格。

    字段来自 `output-template.md` / `v3-detailed-prompt.md` / `verify_report.py`。
    condensed 只放宽 §3/§4/§5；§7 维持全量门槛。
    """
    has_social = _section_allowed(gate, '§3 评论分析', default=False)
    external_route = (gate.get('sources') or {}).get('external_research') or {}
    needs_external = bool(external_route.get('available'))
    condensed = mode == 'condensed'
    return [
        SectionSpec('0', '元信息 (Meta)', '建立视频身份、价值判断和数据来源边界', ['metadata']),
        SectionSpec('1', '逻辑链 (Logic Chain)', '用表格和 Mermaid 压缩叙事弧线，禁止流水账', ['transcript'], quality_gate='G1'),
        SectionSpec('2', '弹幕深度分析 (Danmaku Intelligence)', '提炼即时受众情绪、梗、争议焦点', ['danmaku'], required=has_social, allowed=has_social, notes='数据稀疏时 ≤50 字，不注水'),
        SectionSpec('2.5', '评论深度分析 (Comments Analysis)', '提炼热评信息增量、观点聚合、弹幕/评论差异', ['comments'], required=has_social, allowed=has_social, notes='数据稀疏时降级为一句说明'),
        SectionSpec('3', '核心洞察 (Key Insights)', '提炼 3–5 个高价值认知点并绑定证据', ['transcript', 'comments', 'danmaku'], quality_gate='G3', min_items=2 if condensed else 3, min_words_per_item=150 if condensed else 200),
        SectionSpec('4', '内容深度拆解 (Deep Dive)', '按主题模块做非线性深拆，吸收 BiliNote chunk/checkpoint 用于长上下文', ['transcript', 'external_research'], quality_gate='G4', min_items=2 if condensed else 3, min_words_per_item=0 if condensed else 500, needs_external_research=needs_external),
        SectionSpec('5', '高光时刻 (Highlights & Quotes)', '保留原文金句、上下文、时间戳', ['transcript', 'danmaku'], quality_gate='G5', min_items=2 if condensed else 5),
        SectionSpec('6', '知识图谱 (Knowledge Graph)', '抽取概念、工具、人物、文化梗并链接 OB 知识体系', ['transcript', 'external_research'], needs_external_research=needs_external),
        SectionSpec('7', '批判与行动 (Critical Review & Action)', '输出价值、局限和可执行行动；精简版也不削弱', ['transcript', 'comments', 'external_research'], quality_gate='G7', min_items=8, needs_external_research=needs_external),
        SectionSpec('8', '附录 (Appendix)', '记录数据来源、工具、事实核查和限制', ['metadata', 'transcript', 'external_research']),
    ]


def build_report_plan(inp: AnalysisInput, evidence_gate: Optional[Dict[str, Any]] = None) -> ReportPlan:
    """从输入和 EvidenceSourceGate 生成内容规划。

    模式选择遵循旧 skill：无 transcript → preanalysis；有 transcript 且 >=30min → full；
    短视频默认 condensed。这里不调用 LLM，不生成正文，只锁定结构与证据预算。
    """
    gate = evidence_gate or build_evidence_source_gate(inp)
    can_generate = bool(gate.get('can_generate_formal_report'))
    blocking = gate.get('blocking_reason', '')
    if not can_generate:
        return ReportPlan(
            mode='preanalysis',
            baseline=OLD_FRAMEWORK_BASELINE,
            can_generate_formal_report=False,
            blocking_reason=blocking or 'missing_transcript',
            sections=[
                SectionSpec('0', '元信息 (Meta)', '仅记录可验证元数据和素材边界', ['metadata']),
                SectionSpec('8', '附录 (Appendix)', '说明无 transcript/ASR，禁止正式稿', ['metadata']),
            ],
            absorbed_patterns=BILINOTE_ABSORBED_PATTERNS,
        )

    mode = 'full' if int(inp.duration or 0) >= 30 * 60 else 'condensed'
    return ReportPlan(
        mode=mode,
        baseline=OLD_FRAMEWORK_BASELINE,
        can_generate_formal_report=True,
        blocking_reason='',
        sections=_old_full_sections(gate, mode),
        absorbed_patterns=BILINOTE_ABSORBED_PATTERNS,
    )


# ============ EvidenceMap：transcript → 带时间戳引用候选 ============
@dataclass
class EvidenceCandidate:
    """一条可引用的证据候选。

    硬约束：直接来自原始素材片段（transcript/danmaku/comments），不做 LLM 合成、
    embedding 或外部检索。B站时间戳 URL 用秒数公式，不是 MM:SS。
    """
    source_type: str            # transcript | danmaku | comments
    section_id: str
    start: Optional[float] = None
    end: Optional[float] = None
    timestamp: str = ''         # 'M:SS' / 'H:MM:SS' 可读标签
    url: str = ''
    text: str = ''
    context: str = ''           # 暂等于 text，后续可扩展前后文窗口
    score: float = 0.0          # 简单启发式显著度，>0
    reason: str = ''            # 对应 section purpose 的候选用途标记


@dataclass
class EvidenceMap:
    """按 SectionSpec.id 分组的证据候选表。"""
    video_id: str = ''
    baseline: str = ''
    by_section: Dict[str, List[EvidenceCandidate]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'video_id': self.video_id,
            'baseline': self.baseline,
            'by_section': {
                sid: [asdict(c) for c in cands] for sid, cands in self.by_section.items()
            },
            'warnings': list(self.warnings),
        }


# 老版 §1/§3/§4/§5/§7 由 transcript 直接支撑；reason 标明该节的候选用途
_TRANSCRIPT_SECTION_REASON = {
    '1': 'logic_candidate',
    '3': 'insight_candidate',
    '4': 'deep_dive_candidate',
    '5': 'quote_candidate',
    '7': 'critical_candidate',
}
_TRANSCRIPT_EVIDENCE_SECTIONS = tuple(_TRANSCRIPT_SECTION_REASON.keys())


def _seg_score(text: str) -> float:
    """简单启发式显著度（恒 >0）：按片段文本长度归一，避免引入依赖/LLM。"""
    return round(max(0.01, len((text or '').strip()) / 100.0), 4)


def _bili_timestamp_url(video_id: str, start: Optional[float]) -> str:
    """B站秒数定位 URL：?t={int(start)}。start=150 → ?t=150（不是 ?t=230）。"""
    if start is None:
        return ''
    return f'https://www.bilibili.com/video/{video_id}?t={int(start)}'


def _timestamp_url(platform: str, video_id: str, start: Optional[float]) -> str:
    if platform == 'bilibili':
        return _bili_timestamp_url(video_id, start)
    return ''


def build_evidence_map(inp: AnalysisInput, report_plan: ReportPlan) -> EvidenceMap:
    """从原始素材直接生成各章节的带时间戳引用候选。

    - transcript 片段 → §1/§3/§4/§5/§7（每节挂全量候选，由上层挑选）。
    - danmaku（带 time）→ §2；comments → §2.5。
    - 无 comments/danmaku 时不为 §2/§2.5 伪造候选。
    - 不调用 LLM / embedding / 外部检索，纯片段抽取。
    """
    by_section: Dict[str, List[EvidenceCandidate]] = {}
    warnings: List[str] = []
    section_ids = {s.id for s in report_plan.sections}
    section_allowed = {s.id: s.allowed for s in report_plan.sections}

    tr = inp.transcript
    segments = tr.segments if (tr and tr.segments) else []

    def _seg_candidate(sid: str, seg: TranscriptSegment) -> EvidenceCandidate:
        return EvidenceCandidate(
            source_type='transcript',
            section_id=sid,
            start=seg.start,
            end=seg.end,
            timestamp=_fmt_duration(int(seg.start)) if seg.start is not None else '',
            url=_timestamp_url(inp.platform, inp.video_id, seg.start),
            text=seg.text,
            context=seg.text,
            score=_seg_score(seg.text),
            reason=_TRANSCRIPT_SECTION_REASON[sid],
        )

    if not segments:
        warnings.append('no_transcript: transcript-backed sections (§1/§3/§4/§5/§7) left empty')

    for sid in _TRANSCRIPT_EVIDENCE_SECTIONS:
        if sid not in section_ids or not section_allowed.get(sid, True):
            continue
        if not segments:
            continue
        by_section[sid] = [_seg_candidate(sid, seg) for seg in segments if seg.text]

    # §2 弹幕：仅在有弹幕时生成
    if inp.danmaku and '2' in section_ids and section_allowed.get('2', True):
        by_section['2'] = [
            EvidenceCandidate(
                source_type='danmaku',
                section_id='2',
                start=d.time,
                end=None,
                timestamp=_fmt_duration(int(d.time)) if d.time is not None else '',
                url=_timestamp_url(inp.platform, inp.video_id, d.time),
                text=d.text,
                context=d.text,
                score=_seg_score(d.text),
                reason='danmaku_signal',
            )
            for d in inp.danmaku if d.text
        ]

    # §2.5 评论：评论无可靠视频时间戳，start/end/url/timestamp 留空，不伪造 ?t
    if inp.comments and '2.5' in section_ids and section_allowed.get('2.5', True):
        by_section['2.5'] = [
            EvidenceCandidate(
                source_type='comments',
                section_id='2.5',
                start=None,
                end=None,
                timestamp='',
                url='',
                text=c.text,
                context=c.text,
                score=_seg_score(c.text),
                reason='comment_signal',
            )
            for c in inp.comments if c.text
        ]

    return EvidenceMap(
        video_id=inp.video_id,
        baseline=report_plan.baseline,
        by_section=by_section,
        warnings=warnings,
    )


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
    report_plan = build_report_plan(inp, evidence_gate)
    evidence_map = build_evidence_map(inp, report_plan)
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
    return {
        'frontmatter': frontmatter,
        'evidence_gate': evidence_gate,
        'report_plan': report_plan.to_dict(),
        'evidence_map': evidence_map.to_dict(),
        'sections': sections,
    }


def _render_frontmatter(fm: Dict[str, Any]) -> List[str]:
    lines = ['---']
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f'{k}: [{", ".join(map(str, v))}]')
        else:
            lines.append(f'{k}: {v}')
    lines.append('---')
    lines.append('')
    return lines


def _format_evidence_line(cand: Dict[str, Any]) -> str:
    """把一条证据候选渲染成 blockquote 行，并保留 source_type/reason 标记。

    有 url → `> [timestamp](url) text`；无 url → `> {source_type}证据：text`。
    标记以 HTML 注释承载，不污染正文词数。
    """
    text = (cand.get('text') or '').strip()
    url = cand.get('url') or ''
    src = cand.get('source_type') or ''
    reason = cand.get('reason') or ''
    marker = f'  <!-- source={src} reason={reason} -->'
    if url:
        label = cand.get('timestamp') or url
        return f'> [{label}]({url}) {text}{marker}'
    return f'> {src}证据：{text}{marker}'


def _emit_evidence(lines: List[str], cands: List[Dict[str, Any]], top_n: int = 3) -> bool:
    """注入前 1-3 条证据候选；有内容返回 True。"""
    emitted = False
    for cand in (cands or [])[:top_n]:
        if not (cand.get('text') or '').strip():
            continue
        lines.append(_format_evidence_line(cand))
        emitted = True
    if emitted:
        lines.append('')
    return emitted


# ============ §5 高光时刻 writer（P2-C2）============
def _is_noisy_highlight_fragment(text: str) -> bool:
    """判断 §5 候选片段是否属于标题/短问句等噪声。"""
    stripped = (text or '').strip()
    if not stripped:
        return True
    if stripped.startswith('## '):
        return True
    if stripped.endswith(('？', '?')) and len(stripped) < 35:
        return True
    return False


def _split_long_quote_candidate(cand: Dict[str, Any], max_parts: int) -> List[Dict[str, Any]]:
    """把 H200/ASR 产生的超长 quote_candidate 切成多个可独立计数的 blockquote。"""
    text = (cand.get('text') or '').strip()
    if _is_noisy_highlight_fragment(text):
        return []
    if max_parts <= 1:
        return [cand]
    # 短文本不切；如果是直接候选，仍保留。
    if len(text) < 80:
        return [cand]

    sentences = [
        s.strip() for s in re.split(r'(?<=[。！？!?])\s*', text)
        if len(s.strip()) >= 18
        and not _is_noisy_highlight_fragment(s.strip())
    ]
    parts = sentences[:max_parts]

    if not parts:
        return []

    split = []
    for part in parts:
        new_cand = dict(cand)
        new_cand['text'] = part
        split.append(new_cand)
    return split


def write_highlights_section(section_context: Dict[str, Any]) -> str:
    """§5「高光时刻」纯确定性 writer：从 transcript 金句候选生成 blockquote 正文。

    入参：build_writer_section_context() 产出的单个 section dict（id=="5"）。
    出参：## 5. 节的正文 Markdown（不含 ## 标题，只含正文）。

    仅取 section_context['evidence'] 中 source_type=='transcript' 且
    reason=='quote_candidate' 且 text 非空的候选，逐条渲染为独立 blockquote 组
    （组间空行分隔，使 verify_report.measure_g5 把每条计为一个引用块组）。
      - 有 url：`> "text" — [timestamp](url)`
      - 无 url：`> "text" — timestamp`
      - 零候选：仅 `### 高光时刻` + 占位行，不输出任何 blockquote。
    不调用 LLM / 不合成内容。
    """
    lines: List[str] = ['### 高光时刻', '']
    quotes: List[Dict[str, Any]] = []
    target_quotes = 5 if section_context.get('quality_gate') == 'G5' else 2
    for cand in (section_context.get('evidence') or []):
        if not isinstance(cand, dict):
            continue
        if cand.get('source_type') != 'transcript':
            continue
        if cand.get('reason') != 'quote_candidate':
            continue
        if not (cand.get('text') or '').strip():
            continue
        remaining = max(target_quotes - len(quotes), 1)
        quotes.extend(_split_long_quote_candidate(cand, remaining))

    if not quotes:
        lines.append('_骨架占位：暂无原文金句。_')
        return '\n'.join(lines) + '\n'

    for cand in quotes:
        text = (cand.get('text') or '').strip()
        timestamp = (cand.get('timestamp') or '').strip()
        url = (cand.get('url') or '').strip()
        ref = f'[{timestamp or url}]({url})' if url else timestamp
        lines.append(f'> "{text}" — {ref}')
        lines.append('')
    return '\n'.join(lines)


def _emit_section_skeleton(
    lines: List[str],
    sid: str,
    cands: List[Dict[str, Any]],
    report: Optional[Dict[str, Any]] = None,
    provider: Optional[WriterProvider] = None
) -> None:
    """给 verify_report 关注的 §3/§4/§5/§7 最小子结构；其余节注入证据或占位。

    如果 provider 非 None 且 sid 为 '3'/'4'/'7'，尝试调用 LLM 生成内容；验证通过
    则用 LLM 内容替换标题和正文，否则 fallback 到骨架占位。
    """
    if sid == '3':
        # 默认骨架标题
        heading = '### 💡 Skeleton Insight'
        fallback_body = ['_骨架占位：核心洞察待 LLM 基于上方证据填充。_', '']

        if provider and report:
            try:
                contexts = build_typed_writer_section_contexts(report)
                ctx = next((c for c in contexts if c.section_id == '3'), None)
                if ctx:
                    result = write_llm_section(ctx, provider, retries=2)
                    if result.validation_passed:
                        # 用 LLM 内容替换；result.content 自带 verify_report 可识别的 ### 子标题
                        lines.append(result.content)
                        lines.append('')
                        return
                    warnings.warn(
                        f"§3 LLM writer validation failed, falling back to skeleton: {result.validation_errors}"
                    )
            except Exception as e:
                # 任何异常都 fallback 到骨架，但记录 warning 供调试
                warnings.warn(f"§3 LLM writer failed, falling back to skeleton: {e}")
                pass

        # fallback 到原骨架
        lines.append(heading)
        lines.append('')
        _emit_evidence(lines, cands)
        lines.extend(fallback_body)
        return
    if sid == '4':
        # 默认骨架标题
        heading = '### 模块 1: Skeleton Module'
        fallback_body = ['_骨架占位：深度拆解待 LLM 基于上方证据填充。_', '']

        if provider and report:
            try:
                contexts = build_typed_writer_section_contexts(report)
                ctx = next((c for c in contexts if c.section_id == '4'), None)
                if ctx:
                    result = write_llm_section(ctx, provider, retries=2)
                    if result.validation_passed:
                        # 用 LLM 内容替换；result.content 自带 verify_report 可识别的 ### 子标题
                        lines.append(result.content)
                        lines.append('')
                        return
                    warnings.warn(
                        f"§4 LLM writer validation failed, falling back to skeleton: {result.validation_errors}"
                    )
            except Exception as e:
                # 任何异常都 fallback 到骨架，但记录 warning 供调试
                warnings.warn(f"§4 LLM writer failed, falling back to skeleton: {e}")
                pass

        # fallback 到原骨架
        lines.append(heading)
        lines.append('')
        _emit_evidence(lines, cands)
        lines.extend(fallback_body)
        return
    if sid == '5':
        body = write_highlights_section({'evidence': cands, 'quality_gate': 'G5'})
        lines.extend(body.split('\n'))
        return
    if sid == '7':
        # 默认骨架标题
        heading = '### 观众反馈 Skeleton'
        fallback_body = ['_骨架占位：观众反馈待 LLM 基于上方证据填充。_', '']

        if provider and report:
            try:
                contexts = build_typed_writer_section_contexts(report)
                ctx = next((c for c in contexts if c.section_id == '7'), None)
                if ctx:
                    result = write_llm_section(ctx, provider, retries=2)
                    if result.validation_passed:
                        # 用 LLM 内容替换；result.content 自带 verify_report 可识别的 ### 子标题
                        lines.append(result.content)
                        lines.append('')
                        return
                    warnings.warn(
                        f"§7 LLM writer validation failed, falling back to skeleton: {result.validation_errors}"
                    )
            except Exception as e:
                # 任何异常都 fallback 到骨架，但记录 warning 供调试
                warnings.warn(f"§7 LLM writer failed, falling back to skeleton: {e}")
                pass

        # fallback 到原骨架
        lines.append(heading)
        lines.append('')
        _emit_evidence(lines, cands)
        lines.extend(fallback_body)
        return
    if not _emit_evidence(lines, cands):
        lines.append('_骨架占位：暂无证据候选。_')
        lines.append('')


# §8 Source Appendix 表的固定列与固定行顺序（确定性渲染）。
_SOURCE_TABLE_COLUMNS = [
    'source_type', 'available', 'method', 'language', 'segments', 'chars',
    'count', 'json_path', 'txt_path', 'parts', 'failed_parts', 'notes',
]
_SOURCE_TABLE_ROW_ORDER = [
    'transcript', 'comments', 'danmaku', 'fact_checks', 'external_research',
]


def _parse_transcript_source(source: str) -> Dict[str, str]:
    """拆解 P2-B3 编码的 transcript.source 串为字段字典，不改上游 schema。

    形如 `mlx-whisper|json_path=/x.json|txt_path=/x.txt|parts=2/3|failed_parts=...`。
    第一段为 method，其余 `key=value` 段落进入对应键（json_path/txt_path/
    parts/failed_parts）。无法解析时返回空 method。
    """
    parts = (source or '').split('|')
    out: Dict[str, str] = {'method': parts[0].strip() if parts and parts[0] else ''}
    for token in parts[1:]:
        if '=' in token:
            key, value = token.split('=', 1)
            out[key.strip()] = value.strip()
    return out


def _table_cell(value: Any) -> str:
    """把单元格值转为安全的 Markdown 表格文本：空值留空，转义 `|` 与换行。"""
    if value in (None, ''):
        return ''
    return str(value).replace('|', '\\|').replace('\n', ' ').strip()


def _source_table_rows(report: Dict[str, Any]) -> List[Dict[str, str]]:
    """从 evidence_gate.sources 构建固定行顺序的表格行（缺省单元格留空）。"""
    sources = ((report.get('evidence_gate') or {}).get('sources') or {})
    rows: List[Dict[str, str]] = []
    for name in _SOURCE_TABLE_ROW_ORDER:
        src = sources.get(name) or {}
        row: Dict[str, str] = {col: '' for col in _SOURCE_TABLE_COLUMNS}
        row['source_type'] = name
        row['available'] = 'true' if src.get('available') else 'false'
        if name == 'transcript':
            if src.get('available'):
                parsed = _parse_transcript_source(src.get('source', ''))
                row['method'] = parsed.get('method', '')
                row['json_path'] = parsed.get('json_path', '')
                row['txt_path'] = parsed.get('txt_path', '')
                row['parts'] = parsed.get('parts', '')
                row['failed_parts'] = parsed.get('failed_parts', '')
                row['language'] = str(src.get('language', '') or '')
                row['segments'] = str(src.get('segments', 0))
                row['chars'] = str(src.get('chars', 0))
        elif name in ('comments', 'danmaku'):
            row['count'] = str(src.get('count', 0))
        elif name == 'fact_checks':
            row['count'] = str(src.get('claims', 0))
        elif name == 'external_research':
            row['method'] = str(src.get('route', '') or '')
            row['notes'] = str(src.get('reason', '') or '')
        rows.append(row)
    return rows


def _emit_source_appendix(lines: List[str], report: Dict[str, Any],
                          section: str) -> None:
    """渲染用户可见的 Source Appendix。

    数据只读 evidence_gate.sources，不依赖 evidence_map.by_section。
      - §0：精简版，只给 transcript_available 与 method/language/segments/chars，
        绝不展开 json_path / txt_path / parts / failed_parts。
      - §8：确定性 Markdown 表格，固定列与固定行顺序，transcript.source 解析进
        各单元格；无 transcript 时各路径单元格留空，不伪造任何字段。
    """
    tr = (((report.get('evidence_gate') or {}).get('sources') or {})
          .get('transcript') or {})
    available = bool(tr.get('available'))
    lines.append('### Source Appendix')
    lines.append('')

    if section == '0':
        lines.append(f'- transcript_available={"true" if available else "false"}')
        if available:
            method = _parse_transcript_source(tr.get('source', '')).get('method', '')
            lines.append(f'- method: {method}')
            lines.append(f'- language: {tr.get("language", "")}')
            lines.append(f'- segments: {tr.get("segments", 0)}')
            lines.append(f'- chars: {tr.get("chars", 0)}')
        lines.append('')
        return

    lines.append(f'- transcript_available={"true" if available else "false"}')
    lines.append('')
    lines.append('| ' + ' | '.join(_SOURCE_TABLE_COLUMNS) + ' |')
    lines.append('| ' + ' | '.join(['---'] * len(_SOURCE_TABLE_COLUMNS)) + ' |')
    for row in _source_table_rows(report):
        cells = [_table_cell(row.get(col, '')) for col in _SOURCE_TABLE_COLUMNS]
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines.append('')


def _render_plan_skeleton(
    report: Dict[str, Any],
    lines: List[str],
    plan_sections: List[Dict[str, Any]],
    provider: Optional[WriterProvider] = None
) -> str:
    """按 SectionSpec 顺序渲染老版 §0–§8 骨架，注入 evidence_map 候选。

    如果 provider 非 None，则传给 _emit_section_skeleton 用于 LLM 生成。
    """
    by_section = (report.get('evidence_map') or {}).get('by_section') or {}
    for spec in plan_sections:
        sid = str(spec.get('id', ''))
        title = spec.get('title', '')
        lines.append(f'## {sid}. {title}')
        lines.append('')
        purpose = spec.get('purpose')
        if purpose:
            lines.append(f'_目的：{purpose}_')
            lines.append('')
        _emit_section_skeleton(lines, sid, by_section.get(sid, []), report, provider)
        if sid in ('0', '8'):
            _emit_source_appendix(lines, report, sid)
    return '\n'.join(lines)


def render_markdown(report: Dict[str, Any], provider: Optional[WriterProvider] = None) -> str:
    """把 analyze_video 的报告字典渲染成完整 Markdown 文本（含 YAML frontmatter）。

    若 report 含 report_plan.sections，则按 SectionSpec 顺序输出老版 §0–§8
    plan-aware skeleton（注入 evidence_map 候选）；否则退回旧版 sections 渲染。

    如果 provider 非 None，则传给骨架渲染用于 LLM 生成（默认使用 deepseek_writer_provider）。
    """
    fm = report.get('frontmatter', {})
    lines = _render_frontmatter(fm)

    plan_sections = (report.get('report_plan') or {}).get('sections') or []
    if plan_sections:
        return _render_plan_skeleton(report, lines, plan_sections, provider)

    for title, body in report.get('sections', {}).items():
        lines.append(f'## {title}')
        lines.append('')
        lines.append(body)
        lines.append('')
    return '\n'.join(lines)


# ============ Writer 适配层（P2-C1）============
def build_writer_section_context(report: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]:
    """把 analyze_video 报告投影成确定性的 writer adapter context（不调用 LLM）。

    输出固定 JSON 可序列化 schema，供下游写手按节填稿：
      - source_appendix.transcript_summary 是 §0 风格精简字段（method/language/
        segments/chars），绝不暴露 json_path= / txt_path= / parts= / failed_parts=
        原始编码串。
      - source_appendix.table_rows 复用 §8 Source Appendix 表契约（_source_table_rows）。
      - sections 按 report_plan.sections 顺序逐节给出 heading/purpose/quality_gate/
        门槛、evidence（evidence_map.by_section[id][:top_n]）、占位与 writer_contract。
      - warnings = evidence_map.warnings + 无 transcript 时的 missing_transcript blocker。

    无 transcript：can_generate_formal_report=False，blocking_reason=missing_transcript，
    sections 仅 §0/§8，不伪造任何 path/evidence。
    """
    plan = report.get('report_plan') or {}
    evidence_map = report.get('evidence_map') or {}
    by_section = evidence_map.get('by_section') or {}
    tr = (((report.get('evidence_gate') or {}).get('sources') or {})
          .get('transcript') or {})
    available = bool(tr.get('available'))
    can_generate = bool(plan.get('can_generate_formal_report'))
    blocking = plan.get('blocking_reason', '') or ''

    # top_n clamp：负数视为 0，None 用默认 5
    n = 5 if top_n is None else max(0, int(top_n))

    transcript_summary: Dict[str, Any] = {
        'transcript_available': available,
        'method': (_parse_transcript_source(tr.get('source', '')).get('method', '')
                   if available else ''),
        'language': (tr.get('language', '') if available else ''),
        'segments': int(tr.get('segments', 0) or 0) if available else 0,
        'chars': int(tr.get('chars', 0) or 0) if available else 0,
    }

    sections: List[Dict[str, Any]] = []
    for spec in (plan.get('sections') or []):
        sid = str(spec.get('id', ''))
        title = spec.get('title', '')
        purpose = spec.get('purpose', '') or ''
        cands = list(by_section.get(sid, []) or [])[:n]
        contract = {
            'evidence_kinds': list(spec.get('evidence', []) or []),
            'quality_gate': spec.get('quality_gate', ''),
            'min_items': int(spec.get('min_items', 0) or 0),
            'min_words_per_item': int(spec.get('min_words_per_item', 0) or 0),
            'needs_external_research': bool(spec.get('needs_external_research', False)),
            'required': bool(spec.get('required', True)),
            'allowed': bool(spec.get('allowed', True)),
            'notes': spec.get('notes', ''),
            'no_fabrication': True,
        }
        sections.append({
            'id': sid,
            'heading': f'## {sid}. {title}',
            'purpose': purpose,
            'quality_gate': spec.get('quality_gate', ''),
            'min_items': int(spec.get('min_items', 0) or 0),
            'min_words_per_item': int(spec.get('min_words_per_item', 0) or 0),
            'needs_external_research': bool(spec.get('needs_external_research', False)),
            'evidence': cands,
            'draft_placeholder': f'_待写：{title}。{purpose}_',
            'writer_contract': contract,
        })

    warnings = list(evidence_map.get('warnings') or [])
    if not can_generate:
        warnings.append(
            'missing_transcript: formal report blocked; only §0/§8 planned, '
            'no fabricated paths/evidence'
        )

    return {
        'baseline': plan.get('baseline', ''),
        'mode': plan.get('mode', ''),
        'can_generate_formal_report': can_generate,
        'blocking_reason': blocking,
        'source_appendix': {
            'transcript_summary': transcript_summary,
            'table_rows': _source_table_rows(report),
        },
        'sections': sections,
        'warnings': warnings,
    }


# ============ LLM Writer Harness（可插拔）============
WriterProvider = Callable[[str, str], str]


def make_cli_writer_provider(command: Optional[str] = None, timeout: Optional[int] = None) -> WriterProvider:
    """创建一个通用 CLI writer provider。

    默认命令读取环境变量 ``BILI_WRITER_CLI``；未设置时使用已配置好的 OMP：
    ``omp -p --no-session --max-time 240 --no-skills --no-extensions --no-rules``。

    CLI 的模型/provider/key 配置由该 CLI 自己负责，video_analysis_engine 只负责把
    system/user prompt 合并成单个 prompt 参数传入，因此可沿用调用环境中的 OMP / Hermes /
    其他 agent CLI 配置。
    """
    import shlex
    import subprocess

    command_text = command or os.environ.get(
        'BILI_WRITER_CLI',
        'omp -p --no-session --max-time 240 --no-skills --no-extensions --no-rules'
    )
    run_timeout = timeout or int(os.environ.get('BILI_WRITER_CLI_TIMEOUT', '300'))
    base_cmd = shlex.split(command_text)
    if not base_cmd:
        raise ValueError('BILI_WRITER_CLI 为空，无法创建 CLI writer provider')

    def provider(system: str, user: str) -> str:
        prompt = (
            f"{system}\n\n"
            "---\n\n"
            f"{user}\n\n"
            "请只输出 Markdown 正文，不要输出解释、JSON、代码块或额外前后缀。"
        )
        completed = subprocess.run(
            base_cmd + [prompt],
            capture_output=True,
            text=True,
            timeout=run_timeout,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or '').strip()
            stdout = (completed.stdout or '').strip()
            detail = stderr or stdout or f'exit {completed.returncode}'
            raise RuntimeError(f'CLI writer provider failed: {detail}')
        output = (completed.stdout or '').strip()
        if not output:
            raise RuntimeError('CLI writer provider returned empty output')
        return output

    return provider


def cli_writer_provider(system: str, user: str) -> str:
    """默认 CLI writer provider；等价于 make_cli_writer_provider()(system, user)。"""
    return make_cli_writer_provider()(system, user)


def deepseek_writer_provider(system: str, user: str) -> str:
    """
    DeepSeek API writer provider（纯标准库实现）。

    读取环境变量 DEEPSEEK_API_KEY，调用 DeepSeek chat/completions endpoint。
    model: deepseek-chat，temperature: 0.3，max_tokens: 4096。

    Raises:
        ValueError: DEEPSEEK_API_KEY 未设置
        RuntimeError: API 请求失败
    """
    import urllib.request
    import urllib.error

    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY 环境变量未设置。请设置后再使用 deepseek_writer_provider。"
        )

    url = "https://api.deepseek.com/v1/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.3,
        "max_tokens": 4096
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        raise RuntimeError(
            f"DeepSeek API 请求失败 (HTTP {e.code}): {error_body}"
        ) from e
    except Exception as e:
        raise RuntimeError(f"DeepSeek API 调用异常: {str(e)}") from e


@dataclass
class WriterEvidenceCandidate:
    """writer prompt 中的单条证据候选。"""
    index: int
    text: str
    timestamp: Optional[str] = None
    source: Optional[str] = None


@dataclass
class WriterSectionContext:
    """传给 LLM 写手的结构化上下文。"""
    section_id: str
    heading: str
    purpose: str
    quality_gate: Optional[str] = None
    min_items: Optional[int] = None
    min_words_per_item: Optional[int] = None
    evidence: List[WriterEvidenceCandidate] = field(default_factory=list)
    draft_placeholder: str = ""
    transcript_summary: Optional[str] = None


@dataclass
class WriterResult:
    """LLM 写手的输出 + 验证结果。"""
    section_id: str
    content: str
    sources_used: List[int] = field(default_factory=list)
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    raw_response: str = ""


def build_typed_writer_section_contexts(report: dict) -> List[WriterSectionContext]:
    """
    将 build_writer_section_context 的输出转为 typed dataclasses。
    """
    writer_ctx = build_writer_section_context(report)
    typed = []
    for sec in writer_ctx.get('sections', []):
        evidence_candidates = []
        for idx, ev in enumerate(sec.get('evidence', []), start=1):
            evidence_candidates.append(WriterEvidenceCandidate(
                index=idx,
                text=ev.get('text', ''),
                timestamp=ev.get('timestamp'),
                source=ev.get('source_type') or ev.get('source')
            ))

        typed.append(WriterSectionContext(
            section_id=sec.get('id', ''),
            heading=sec.get('heading', ''),
            purpose=sec.get('purpose', ''),
            quality_gate=sec.get('quality_gate'),
            min_items=sec.get('min_items'),
            min_words_per_item=sec.get('min_words_per_item'),
            evidence=evidence_candidates,
            draft_placeholder=sec.get('draft_placeholder', ''),
            transcript_summary=sec.get('transcript_summary')
        ))
    return typed


WRITER_PROMPTS = {
    "3": {
        "system": """你是一位专业的视频分析师，负责从采集到的证据中提炼核心观点。

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 3.` 大标题；直接从 `###` 小标题开始
- 必须输出至少 3 个洞察小节，每个小节标题必须是 `### 💡 洞察 N：标题`
- 每个洞察小节正文至少 1 段，并必须包含 [E#] 引用证据（如 [E1]、[E2]）
- 禁止编造或猜测视频中未提及的内容
- 对不确定的信息，使用"从现有证据只能看出..."表述
- 禁止使用"显然""必然""毫无疑问"等绝对化表达""",
        "user": """# 任务：{heading}

目的：{purpose}

质量标准：{quality_gate}

最少条目数：{min_items}
每条最少字数：{min_words}

## 可用证据
{evidence}

请根据以上证据撰写该节内容，确保每条观点都引用 [E#] 标记。"""
    },
    "4": {
        "system": """你是一位专业的视频分析师，负责做内容深度拆解。

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 4.` 大标题；直接从 `###` 小标题开始
- 必须输出至少 3 个模块，每个模块标题必须是 `### 模块 N：标题`
- 每个模块正文至少 500 个中文字符/词，不要输出短模块，并必须包含 [E#] 引用证据（如 [E1]、[E2]）
- 禁止编造或猜测视频中未提及的内容
- 对不确定的信息，使用"从现有证据只能看出..."表述
- 禁止使用"显然""必然""毫无疑问"等绝对化表达""",
        "user": """# 任务：{heading}

目的：{purpose}

质量标准：{quality_gate}

最少条目数：{min_items}
每条最少字数：{min_words}

## 可用证据
{evidence}

请根据以上证据撰写该节内容，确保每条技术点都引用 [E#] 标记。"""
    },
    "7": {
        "system": """你是一位专业的视频分析师，负责输出批判性评估与可执行行动。

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 7.` 大标题；直接从 `###` 小标题开始
- 必须包含 3 个小节，标题分别包含：`### 独特价值`、`### 局限与偏见`、`### 可行动项`
- `独特价值` 和 `局限与偏见` 小节下必须使用 `- ` bullet
- `可行动项` 小节下可使用 `- ` 或 `1. ` 列表
- 每个列表项必须包含 [E#] 引用证据（如 [E1]、[E2]）
- 禁止编造或猜测评论区中未提及的内容
- 对不确定的信息，使用"从现有证据只能看出..."表述
- 禁止使用"显然""必然""毫无疑问"等绝对化表达""",
        "user": """# 任务：{heading}

目的：{purpose}

质量标准：{quality_gate}

最少条目数：{min_items}
每条最少字数：{min_words}

## 可用证据
{evidence}

请根据以上证据撰写该节内容，确保每条讨论点都引用 [E#] 标记。"""
    }
}


FABRICATION_MARKERS = [
    "根据公开资料",
    "业内普遍认为",
    "数据显示",
    "研究表明",
    "众所周知",
    "显而易见",
    "不言而喻"
]


def _format_evidence_for_prompt(candidates: List[WriterEvidenceCandidate]) -> str:
    """
    将证据候选列表格式化为 prompt 可读文本。
    """
    lines = []
    for c in candidates:
        parts = [f"[E{c.index}] \"{c.text}\""]
        if c.timestamp:
            parts.append(f"— {c.timestamp}")
        if c.source:
            parts.append(f"({c.source})")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _extract_markdown_items(content: str) -> List[str]:
    """
    从 markdown 内容中提取列表项或段落。
    """
    items = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('- ') or line.startswith('* '):
            items.append(line[2:].strip())
        elif line.startswith(tuple(f"{i}. " for i in range(1, 100))):
            items.append(re.sub(r'^\d+\.\s*', '', line))
        elif line and not line.startswith('#'):
            if len(line) > 10:
                items.append(line)
    return items


def _count_writer_words(text: str) -> int:
    """
    中英文混合词数统计。
    """
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    return chinese_chars + english_words


def _split_writer_subsections(content: str, heading_pattern: str) -> List[Tuple[str, str]]:
    """按 ### 小节切分，返回 (heading, body_text)。"""
    sections: List[Tuple[str, List[str]]] = []
    current_head: Optional[str] = None
    current_body: List[str] = []
    regex = re.compile(heading_pattern, re.I)

    for line in content.splitlines():
        if regex.search(line):
            if current_head is not None:
                sections.append((current_head, current_body))
            current_head = line.strip()
            current_body = []
        elif current_head is not None:
            current_body.append(line)
    if current_head is not None:
        sections.append((current_head, current_body))
    return [(h, "\n".join(body).strip()) for h, body in sections]


def _validate_writer_format(content: str, section_id: str, min_words_per_item: int = 0) -> List[str]:
    """验证 LLM writer 输出是否符合 verify_report.py 可识别的章节格式。"""
    errors = []
    non_heading_text = [
        line.strip() for line in content.splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]
    if not non_heading_text:
        errors.append("有效正文不足：只有标题或空内容")

    if section_id == '3':
        insight_sections = _split_writer_subsections(content, r'^\s*###.*💡')
        if len(insight_sections) < 3:
            errors.append("§3 格式不符合 verify_report：至少需要 3 个含 💡 的 `###` 洞察标题")
        if min_words_per_item:
            for i, (_head, body) in enumerate(insight_sections, 1):
                wc = _count_writer_words(body)
                if wc < min_words_per_item:
                    errors.append(f"§3 第 {i} 个洞察正文词数不足：需要 {min_words_per_item}，实际 {wc}")
    elif section_id == '4':
        module_sections = _split_writer_subsections(content, r'^\s*###\s*(模块\s*\d|Module\s*\d)')
        if len(module_sections) < 3:
            errors.append("§4 格式不符合 verify_report：至少需要 3 个 `### 模块 N：...` 标题")
        if min_words_per_item:
            for i, (_head, body) in enumerate(module_sections, 1):
                wc = _count_writer_words(body)
                if wc < min_words_per_item:
                    errors.append(f"§4 模块 {i} 词数不足：需要 {min_words_per_item}，实际 {wc}")
    elif section_id == '7':
        required = [
            ('独特价值', r'^\s*-\s+'),
            ('局限', r'^\s*-\s+'),
            ('可行动', r'(^\s*-\s+)|(^\s*\d+\.\s)|(^\s*-\s*\[[ xX]?\])'),
        ]
        headings = [line for line in content.splitlines() if line.lstrip().startswith('###')]
        for keyword, item_pattern in required:
            matching_heads = [h for h in headings if keyword in h]
            if not matching_heads:
                errors.append(f"§7 格式不符合 verify_report：缺少包含 `{keyword}` 的 `###` 小节")
                continue
            # 粗粒度即可：对应关键词标题后续至少出现一个列表项；精确计数留给 verify_report。
            idx = content.find(matching_heads[0])
            tail = content[idx:]
            if not re.search(item_pattern, tail, re.M):
                errors.append(f"§7 格式不符合 verify_report：`{keyword}` 小节下缺少列表项")
    return errors


def validate_section(result: WriterResult, contract: WriterSectionContext) -> WriterResult:
    """
    确定性验证 LLM 输出是否符合约束。
    """
    errors = []

    for marker in FABRICATION_MARKERS:
        if marker in result.content:
            errors.append(f"包含编造标记词：{marker}")

    errors.extend(_validate_writer_format(
        result.content,
        contract.section_id,
        contract.min_words_per_item or 0,
    ))

    if not re.search(r'\[E\d+\]', result.content):
        errors.append("未找到任何 [E#] 证据引用")

    if contract.min_items:
        items = _extract_markdown_items(result.content)
        if len(items) < contract.min_items:
            errors.append(f"条目数不足：需要 {contract.min_items}，实际 {len(items)}")

    if contract.min_words_per_item:
        items = _extract_markdown_items(result.content)
        for i, item in enumerate(items, 1):
            word_count = _count_writer_words(item)
            if word_count < contract.min_words_per_item:
                errors.append(
                    f"第 {i} 条词数不足：需要 {contract.min_words_per_item}，实际 {word_count}"
                )

    result.validation_passed = len(errors) == 0
    result.validation_errors = errors
    return result


def write_llm_section(
    context: WriterSectionContext,
    provider: WriterProvider,
    retries: int = 2
) -> WriterResult:
    """
    调用 LLM provider 生成章节内容，并进行确定性验证。
    """
    if context.section_id not in WRITER_PROMPTS:
        return WriterResult(
            section_id=context.section_id,
            content=context.draft_placeholder,
            validation_passed=False,
            validation_errors=[f"未找到 section_id={context.section_id} 的 prompt"]
        )

    prompts = WRITER_PROMPTS[context.section_id]
    system = prompts["system"]
    user_template = prompts["user"]

    evidence_text = _format_evidence_for_prompt(context.evidence)
    user = user_template.format(
        heading=context.heading,
        purpose=context.purpose,
        quality_gate=context.quality_gate or "无",
        min_items=context.min_items or "无",
        min_words=context.min_words_per_item or "无",
        evidence=evidence_text
    )

    for attempt in range(retries + 1):
        raw = provider(system, user)
        result = WriterResult(
            section_id=context.section_id,
            content=raw.strip(),
            raw_response=raw
        )

        sources = re.findall(r'\[E(\d+)\]', raw)
        result.sources_used = sorted(set(int(s) for s in sources))

        result = validate_section(result, context)
        if result.validation_passed:
            return result

    return result


# ============ Report Coherence Checker ============
@dataclass
class ReportCoherenceIssue:
    """跨节一致性检查发现的单个问题。"""
    severity: str      # 'nit' | 'concern' | 'blocker'
    code: str          # stable machine code
    message: str
    section_id: Optional[str] = None


@dataclass
class ReportCoherenceResult:
    """跨节一致性检查结果。"""
    passed: bool
    issues: List[ReportCoherenceIssue] = field(default_factory=list)


def check_report_coherence(markdown: str) -> ReportCoherenceResult:
    """
    确定性检查报告的跨节一致性。

    检查规则：
    1. section 顺序：应按 ## 0. → ## 1. → ... → ## 8. 单调递增
       缺 §0 或 §8 = concern；倒序 = blocker
    2. skeleton residue：LLM 内容不应残留 _骨架占位 或 Skeleton
       发现 = concern
    3. duplicate paragraphs：相同非空正文段落（≥30字）出现 2 次以上 = concern
    4. evidence citation syntax：[E 后必须跟数字，否则 = concern
    5. empty LLM section：§3/§4/§7 标题存在但正文少于 20 字 = blocker
    """
    issues = []

    # Rule 1: section 顺序检查
    section_pattern = re.compile(r'^## (\d+)\.')
    section_ids = []
    for line in markdown.splitlines():
        m = section_pattern.match(line)
        if m:
            section_ids.append(int(m.group(1)))

    if section_ids:
        if 0 not in section_ids:
            issues.append(ReportCoherenceIssue(
                severity='concern',
                code='missing_section_0',
                message='报告缺少 §0 元信息节'
            ))
        if 8 not in section_ids:
            issues.append(ReportCoherenceIssue(
                severity='concern',
                code='missing_section_8',
                message='报告缺少 §8 数据源节'
            ))

        for i in range(len(section_ids) - 1):
            if section_ids[i] > section_ids[i + 1]:
                issues.append(ReportCoherenceIssue(
                    severity='blocker',
                    code='section_order',
                    message=f'章节顺序错误：§{section_ids[i]} 出现在 §{section_ids[i+1]} 之前'
                ))
                break

    # 先切分章节内容，供 LLM 节检查复用
    section_contents = {}
    current_section = None
    current_content = []

    for line in markdown.splitlines():
        m = section_pattern.match(line)
        if m:
            if current_section:
                section_contents[current_section] = '\n'.join(current_content)
            current_section = m.group(1)
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        section_contents[current_section] = '\n'.join(current_content)

    # Rule 2: skeleton residue 检查（只检查 LLM writer 节 §3/§4/§7）
    for sec_id in ('3', '4', '7'):
        content = section_contents.get(sec_id, '')
        if re.search(r'(Skeleton|_骨架占位)', content):
            issues.append(ReportCoherenceIssue(
                severity='concern',
                code='skeleton_residue',
                message=f'§{sec_id} 中残留 skeleton 占位符',
                section_id=sec_id,
            ))

    # Rule 3: duplicate paragraphs 检查
    paragraphs = []
    for line in markdown.splitlines():
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('*'):
            if len(line) >= 30:
                paragraphs.append(line)

    para_counts = Counter(paragraphs)
    for para, count in para_counts.items():
        if count >= 2:
            issues.append(ReportCoherenceIssue(
                severity='concern',
                code='duplicate_paragraph',
                message=f'发现重复段落（{count} 次）: {para[:50]}...'
            ))

    # Rule 4: evidence citation syntax 检查
    bad_citations = re.findall(r'\[E(?!\d)[^\]]*\]', markdown)
    if bad_citations:
        issues.append(ReportCoherenceIssue(
            severity='concern',
            code='bad_evidence_citation',
            message=f'发现错误的证据引用格式: {", ".join(set(bad_citations))}'
        ))

    # Rule 5: empty LLM section 检查（§3/§4/§7）
    llm_sections = ['3', '4', '7']

    for sec_id in llm_sections:
        if sec_id in section_contents:
            content = section_contents[sec_id].strip()
            if len(content) < 20:
                issues.append(ReportCoherenceIssue(
                    severity='blocker',
                    code='empty_llm_section',
                    message=f'§{sec_id} 标题存在但正文少于 20 字',
                    section_id=sec_id
                ))

    passed = not any(issue.severity == 'blocker' for issue in issues)
    return ReportCoherenceResult(passed=passed, issues=issues)


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
