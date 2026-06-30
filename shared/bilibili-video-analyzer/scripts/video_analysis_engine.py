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


def _emit_section_skeleton(lines: List[str], sid: str, cands: List[Dict[str, Any]]) -> None:
    """给 verify_report 关注的 §3/§4/§5/§7 最小子结构；其余节注入证据或占位。"""
    if sid == '3':
        lines.append('### 💡 Skeleton Insight')
        lines.append('')
        _emit_evidence(lines, cands)
        lines.append('_骨架占位：核心洞察待 LLM 基于上方证据填充。_')
        lines.append('')
        return
    if sid == '4':
        lines.append('### 模块 1: Skeleton Module')
        lines.append('')
        _emit_evidence(lines, cands)
        lines.append('_骨架占位：深度拆解待 LLM 基于上方证据填充。_')
        lines.append('')
        return
    if sid == '5':
        if not _emit_evidence(lines, cands):
            lines.append('> _骨架占位：高光引用待填充。_')
            lines.append('')
        return
    if sid == '7':
        lines.append('### 独特价值')
        lines.append('- 骨架占位：独特价值待填充。')
        lines.append('')
        lines.append('### 局限与偏见')
        lines.append('- 骨架占位：局限与偏见待填充。')
        lines.append('')
        lines.append('### 可行动项')
        lines.append('- [ ] 骨架占位：可行动项待填充。')
        lines.append('')
        return
    if not _emit_evidence(lines, cands):
        lines.append('_骨架占位：暂无证据候选。_')
        lines.append('')


def _render_plan_skeleton(report: Dict[str, Any], lines: List[str],
                          plan_sections: List[Dict[str, Any]]) -> str:
    """按 SectionSpec 顺序渲染老版 §0–§8 骨架，注入 evidence_map 候选。"""
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
        _emit_section_skeleton(lines, sid, by_section.get(sid, []))
    return '\n'.join(lines)


def render_markdown(report: Dict[str, Any]) -> str:
    """把 analyze_video 的报告字典渲染成完整 Markdown 文本（含 YAML frontmatter）。

    若 report 含 report_plan.sections，则按 SectionSpec 顺序输出老版 §0–§8
    plan-aware skeleton（注入 evidence_map 候选）；否则退回旧版 sections 渲染。
    """
    fm = report.get('frontmatter', {})
    lines = _render_frontmatter(fm)

    plan_sections = (report.get('report_plan') or {}).get('sections') or []
    if plan_sections:
        return _render_plan_skeleton(report, lines, plan_sections)

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
