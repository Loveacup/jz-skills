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
from typing import List, Optional, Dict, Any, Callable, Tuple, Literal


# ============ Type Literals for validation ============
ClaimSourceType = Literal["transcript", "comment", "danmaku", "audience", "metadata", "external"]
ClaimType = Literal["observed", "inferred", "recommendation"]
AuditAction = Literal["keep", "downgrade", "drop"]
TargetSection = Literal["3", "4", "7"]


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


@dataclass
class Claim:
    """A single claim extracted from evidence.

    Represents a factual assertion, inference, or recommendation grounded in evidence.
    Part of the claim-first architecture for depth analysis.
    """
    id: str
    text: str
    confidence: float  # 0.0-1.0
    evidence_ids: List[str]
    source_type: ClaimSourceType
    grounds: List[str] = field(default_factory=list)
    warrant: str = ""
    backing: str = ""
    qualifier: str = ""
    rebuttal: str = ""
    claim_type: ClaimType = "observed"

    def __post_init__(self):
        if not self.evidence_ids:
            raise ValueError(f"Claim {self.id} must have non-empty evidence_ids")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Claim {self.id} confidence must be in [0.0, 1.0], got {self.confidence}")
        valid_source_types = {"transcript", "comment", "danmaku", "audience", "metadata", "external"}
        if self.source_type not in valid_source_types:
            raise ValueError(f"Claim {self.id} source_type must be one of {valid_source_types}, got {self.source_type}")
        valid_claim_types = {"observed", "inferred", "recommendation"}
        if self.claim_type not in valid_claim_types:
            raise ValueError(f"Claim {self.id} claim_type must be one of {valid_claim_types}, got {self.claim_type}")


@dataclass
class Insight(Claim):
    """An insight is a Claim with additional depth/novelty/targeting metadata."""
    depth: float = 0.0
    novelty: float = 0.0
    target_section: TargetSection = "3"

    def __post_init__(self):
        super().__post_init__()
        if not (0.0 <= self.depth <= 1.0):
            raise ValueError(f"Insight {self.id} depth must be in [0.0, 1.0], got {self.depth}")
        if not (0.0 <= self.novelty <= 1.0):
            raise ValueError(f"Insight {self.id} novelty must be in [0.0, 1.0], got {self.novelty}")
        valid_sections = {"3", "4", "7"}
        if self.target_section not in valid_sections:
            raise ValueError(f"Insight {self.id} target_section must be one of {valid_sections}, got {self.target_section}")


@dataclass
class ClaimAuditResult:
    """Result of auditing a claim for evidence quality."""
    action: AuditAction
    original_claim: Claim
    reason: str

    def __post_init__(self):
        valid_actions = {"keep", "downgrade", "drop"}
        if self.action not in valid_actions:
            raise ValueError(f"ClaimAuditResult action must be one of {valid_actions}, got {self.action}")


@dataclass
class ClaimBundle:
    """Collection of claims, insights, and audit results."""
    claims: List[Claim] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    audit_log: List[ClaimAuditResult] = field(default_factory=list)


@dataclass
class DraftReport:
    """A non-publishable structured draft artifact.

    DraftReport is the explicit home for ReportPlan/EvidenceMap skeleton output.
    It may be useful for debugging, writer context, and future DraftReport writers,
    but it is not an Obsidian-ready note.
    """
    report: Dict[str, Any]
    artifact_kind: str = 'draft_report'
    publishable: bool = False
    debug_render_allowed: bool = True
    warnings: List[str] = field(default_factory=list)
    draft_sections: Dict[str, str] = field(default_factory=dict)
    qa_results: Dict[str, SectionQualityResult] = field(default_factory=dict)
    claim_bundle: Optional[Dict[str, Any]] = None


@dataclass
class PublishedMarkdown:
    """Markdown that has passed the publishable Obsidian gate."""
    markdown: str
    gates: Dict[str, Any]
    artifact_kind: str = 'published_markdown'
    publishable: bool = True


class PublishableReportError(ValueError):
    """Raised when Markdown is not safe to treat as PublishedMarkdown."""

    def __init__(self, failed_codes: List[str], gates: Dict[str, Any]):
        self.failed_codes = failed_codes
        self.gates = gates


# ============ Section QA gate (Phase 1) ============
@dataclass
class DimensionResult:
    dimension: str
    passed: bool
    score: float
    issues: List[str]


@dataclass
class SectionQualityResult:
    section_id: str
    overall_passed: bool
    dimension_results: List[DimensionResult]
    blockers: List[str]
    critical_issues: List[str]
    improvements: List[str]
    word_count: int
    evidence_refs_count: int
    time_anchor_count: int


# Phase 4: 分段豁免配置
# §1 基本信息：结构化表格为主，免除 not-mechanical 和 insight-density
# §5 高光引文：大量 blockquote 为主，免除 not-mechanical 和 insight-density
SECTION_DIMENSION_EXEMPTIONS: Dict[str, List[str]] = {
    "1": ["not-mechanical", "insight-density", "warrant-present", "rebuttal-or-boundary", "actionability"],
    "5": ["not-mechanical", "insight-density", "warrant-present", "rebuttal-or-boundary", "actionability"],
    "6": ["warrant-present", "rebuttal-or-boundary", "actionability"],
}


def evaluate_draft_section_quality(
    section_id: str,
    section_body: str,
    context: Any = None,
    claim_qa_gate: bool = False,
) -> SectionQualityResult:
    body = (section_body or '').strip()
    lines = [ln for ln in body.splitlines() if ln.strip()]

    # ----- word + evidence counts -----
    word_count = _count_writer_words(body)
    evidence_refs_count = len(re.findall(r'\[E\d+\]', body))
    time_anchor_count = len(re.findall(r'\b\d{1,2}:\d{2}\b', body))

    # ----- D5: no-skeleton (P0) -----
    skeleton_hits = [t for t in ('_骨架占位', '骨架占位', 'TODO', '待补充') if t in body]
    d5_passed = not skeleton_hits and len(body) > 5

    # ----- D1: evidence-grounded (P1) -----
    d1_passed = evidence_refs_count >= 1 or time_anchor_count >= 1

    # ----- D2: not-mechanical (P1) -----
    table_rows = sum(1 for ln in lines if ln.strip().startswith('|'))
    quote_rows = sum(1 for ln in lines if ln.strip().startswith('>'))
    mechanical_ratio = (table_rows + quote_rows) / max(len(lines), 1)
    d2_passed = mechanical_ratio < 0.70

    # ----- D3: human-readable (P2) -----
    # count complete sentences (ends with 。！？!? and has reasonable length)
    sentences = re.findall(r'[^。！？!?\n]{5,}[。！？!?]', body)
    d3_passed = len(sentences) >= 2

    # ----- D4: insight-density (P2) -----
    insight_markers = re.findall(r'因为|导致|说明|可见|原因|所以|因此|从而|意味着|反映出', body)
    paragraphs = [ln for ln in lines if ln and not ln.startswith(('#', '|', '>', '-', '*'))]
    d4_passed = len(insight_markers) >= 1 or len(paragraphs) >= 2

    # ----- D6: warrant-present (claim-first only) -----
    d6_passed = True
    if claim_qa_gate and section_id in ('3', '4', '7'):
        warrant_keywords = re.findall(r'因为|由于|基于|根据|warrant|推理|许可|逻辑|前提|假设', body)
        d6_passed = len(warrant_keywords) >= 1

    # ----- D7: rebuttal-or-boundary (claim-first only) -----
    d7_passed = True
    if claim_qa_gate and section_id in ('3', '4', '7'):
        boundary_keywords = re.findall(r'反证|边界|例外|qualifier|局限|但是|然而|不过|除非|前提|条件|适用范围', body)
        d7_passed = len(boundary_keywords) >= 1

    # ----- D8: actionability (claim-first only, §7 only) -----
    d8_passed = True
    if claim_qa_gate and section_id == '7':
        action_keywords = re.findall(r'立即|短期|长期|行动|建议|步骤|可以|应该|需要|执行|实施', body)
        d8_passed = len(action_keywords) >= 1

    # ----- dimension results -----
    dims = [
        DimensionResult('evidence-grounded', d1_passed, 1.0 if d1_passed else 0.0, [] if d1_passed else ['缺少证据引用 [E#] 或时间锚点 MM:SS']),
        DimensionResult('not-mechanical', d2_passed, 1.0 if d2_passed else 0.0, [] if d2_passed else [f'表格+blockquote占比 {mechanical_ratio:.0%} ≥70%']),
        DimensionResult('human-readable', d3_passed, 1.0 if d3_passed else 0.0, [] if d3_passed else ['含完整句子数不足2个']),
        DimensionResult('insight-density', d4_passed, 1.0 if d4_passed else 0.0, [] if d4_passed else ['缺少因果/分析关键词且纯文本段落不足2段']),
        DimensionResult('no-skeleton', d5_passed, 1.0 if d5_passed else 0.0, [] if d5_passed else [f'骨架占位: {skeleton_hits}'] if skeleton_hits else ['章节正文为空']),
        DimensionResult('warrant-present', d6_passed, 1.0 if d6_passed else 0.0, [] if d6_passed else ['缺少推理许可关键词（因为/由于/基于/warrant/推理/逻辑）']),
        DimensionResult('rebuttal-or-boundary', d7_passed, 1.0 if d7_passed else 0.0, [] if d7_passed else ['缺少反证/边界/局限关键词（反证/边界/例外/局限/但是/然而）']),
        DimensionResult('actionability', d8_passed, 1.0 if d8_passed else 0.0, [] if d8_passed else ['§7 缺少可行动项关键词（立即/短期/长期/行动/建议/步骤）']),
    ]

    # ----- Phase 4: 应用分段豁免 -----
    exemptions = SECTION_DIMENSION_EXEMPTIONS.get(section_id, [])
    if exemptions:
        new_dims = []
        for d in dims:
            if d.dimension in exemptions and not d.passed:
                # 豁免：强制通过，score=1.0，在 issues 中注明
                new_dims.append(DimensionResult(
                    dimension=d.dimension,
                    passed=True,
                    score=1.0,
                    issues=[f"exempted: structural section §{section_id}"]
                ))
            else:
                new_dims.append(d)
        dims = new_dims

    blockers: List[str] = []
    critical_issues: List[str] = []
    improvements: List[str] = []

    for d in dims:
        if d.dimension == 'no-skeleton' and not d.passed:
            blockers.append(f'D5 no-skeleton: {d.issues[0]}')
        elif d.dimension in ('evidence-grounded', 'not-mechanical') and not d.passed:
            critical_issues.append(f'{d.dimension}: {d.issues[0]}')
        elif not d.passed:
            improvements.append(f'{d.dimension}: {d.issues[0]}')

    overall_passed = all(d.passed for d in dims)

    return SectionQualityResult(
        section_id=section_id,
        overall_passed=overall_passed,
        dimension_results=dims,
        blockers=blockers,
        critical_issues=critical_issues,
        improvements=improvements,
        word_count=word_count,
        evidence_refs_count=evidence_refs_count,
        time_anchor_count=time_anchor_count,
    )


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
        SectionSpec('2', '弹幕深度分析 (Danmaku Intelligence)', '提炼即时受众情绪、梗、争议焦点', ['danmaku'], required=False, allowed=True, notes='数据稀疏时输出框架并标注"数据不足"，不注水'),
        SectionSpec('2.5', '评论深度分析 (Comments Analysis)', '提炼热评信息增量、观点聚合、弹幕/评论差异', ['comments'], required=False, allowed=True, notes='数据稀疏时输出框架并标注"数据不足"，不注水'),
        SectionSpec('3', '核心洞察 (Key Insights)', '提炼 3–5 个高价值认知点并绑定证据', ['transcript', 'comments', 'danmaku'], quality_gate='G3', min_items=2 if condensed else 3, min_words_per_item=100),
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

    # 跨平台证据：YouTube 评论（搬运视频的跨平台口碑）
    # 作为 §3/§4/§7 的补充证据来源，特别是无 B站评论或字幕不足时
    if inp.cross_platform:
        yt_comments_data = inp.cross_platform.get('youtube_comments')
        # 检查 youtube_comments 是否成功抓取（status='ok' 且有 comments 数组）
        if (yt_comments_data
            and isinstance(yt_comments_data, dict)
            and yt_comments_data.get('status') == 'ok'
            and yt_comments_data.get('comments')):

            yt_comments = yt_comments_data.get('comments', [])
            yt_url = inp.cross_platform.get('youtube_url', '')

            # YouTube 评论可作为 §3（初步印象）、§4（深度探索）、§7（价值评估）的跨平台证据
            for sid in ['3', '4', '7']:
                if sid not in section_ids or not section_allowed.get(sid, True):
                    continue

                # 为每个相关章节生成 YouTube 评论候选
                youtube_candidates = [
                    EvidenceCandidate(
                        source_type='youtube',
                        section_id=sid,
                        start=None,
                        end=None,
                        timestamp='',
                        url=yt_url,  # 指向 YouTube 视频
                        text=comment.get('text', ''),
                        context=f"[YouTube评论 by {comment.get('author', 'Anonymous')}] {comment.get('text', '')}",
                        score=_seg_score(comment.get('text', '')) + (comment.get('likes', 0) * 0.01),  # 点赞数轻微加权
                        reason='cross_platform_sentiment',
                    )
                    for comment in yt_comments if comment.get('text')
                ]

                # 合并到对应章节（如果已有其他候选，追加；否则新建）
                if sid in by_section:
                    by_section[sid].extend(youtube_candidates)
                else:
                    by_section[sid] = youtube_candidates

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


# ============ DraftReport deterministic slice writers（§1/§5）============
def _clean_inline_text(text: str, limit: int = 90) -> str:
    cleaned = re.sub(r'\s+', ' ', (text or '').strip())
    cleaned = cleaned.replace('|', '\\|')
    if len(cleaned) > limit:
        return cleaned[: max(0, limit - 1)].rstrip() + '…'
    return cleaned


def write_logic_chain_section(section_context: Dict[str, Any]) -> str:
    """§1「逻辑链」纯确定性 writer：从 logic_candidate 生成结构化表格。

    This writer is intentionally conservative: it summarizes transcript snippets
    into a deterministic table so publish gate can distinguish a logic chain from
    raw blockquote dumps. It does not call LLMs and does not infer unseen facts.
    """
    raw_candidates = section_context.get('evidence') or []
    seen = set()
    candidates: List[Dict[str, Any]] = []
    for cand in raw_candidates:
        if not isinstance(cand, dict):
            continue
        text = (cand.get('text') or '').strip()
        if not text:
            continue
        if cand.get('source_type') != 'transcript':
            continue
        if cand.get('reason') != 'logic_candidate':
            continue
        key = re.sub(r'\s+', '', text)[:80]
        if key in seen:
            continue
        seen.add(key)
        candidates.append(cand)

    if not candidates:
        return '### 逻辑链总览\n\n_骨架占位：暂无可用逻辑链证据。_\n'

    candidates.sort(key=lambda c: (c.get('start') is None, float(c.get('start') or 0)))
    stage_names = ['起点', '推进', '转折', '收束']
    action_names = ['提出问题', '展开机制', '补充条件', '形成结论']

    lines = [
        '### 逻辑链总览',
        '',
        '| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |',
        '| --- | --- | --- | --- | --- |',
    ]
    for idx, cand in enumerate(candidates, start=1):
        timestamp = (cand.get('timestamp') or '').strip()
        url = (cand.get('url') or '').strip()
        stage = stage_names[idx - 1] if idx <= len(stage_names) else f'补充 {idx - len(stage_names)}'
        action = action_names[idx - 1] if idx <= len(action_names) else '补充证据'
        link = f'[{timestamp or url}]({url})' if url else timestamp
        summary = _clean_inline_text(cand.get('text') or '', 90)
        lines.append(
            f'| {_table_cell(timestamp)} | {_table_cell(stage)} | {_table_cell(action)} | {summary} | {_table_cell(link)} |'
        )
    lines.append('')
    return '\n'.join(lines)


# ============ DraftReport §8 deterministic appendix writer (P5-5) ============
_APPENDIX_METHOD_LIMITATIONS = {
    'transcript': '字幕/转录可能缺失语气、停顿和视觉信息；机器转录可能包含识别错误。',
    'comments': '评论样本受平台排序与采集时点影响，高赞评论未必代表整体观众。',
    'danmaku': '弹幕具有瞬时性，重复和情绪化表达较多，难以代表深度观点。',
    'fact_checks': '事实核查仅覆盖明确可验证的 claim，未核查内容不代表错误。',
    'external_research': '外部检索结果受时间、来源和路由策略影响，需人工复核。',
}


def write_appendix_section(report: Dict[str, Any]) -> str:
    """§8 附录确定性 writer：数据来源、可用性摘要、方法限制、Source Appendix 表。

    P5-5: 不调用 LLM，纯结构化输出。
    """
    sources = ((report.get('evidence_gate') or {}).get('sources') or {})
    lines = []

    # 数据可用性摘要
    lines.append('### 数据来源与可用性')
    lines.append('')
    available_sources = []
    unavailable_sources = []
    for name in _SOURCE_TABLE_ROW_ORDER:
        src = sources.get(name) or {}
        if src.get('available'):
            available_sources.append(name)
        else:
            unavailable_sources.append(name)

    if available_sources:
        lines.append('- **可用来源**：' + '、'.join(available_sources))
    if unavailable_sources:
        lines.append('- **不可用来源**：' + '、'.join(unavailable_sources))
    lines.append('')

    # 方法限制
    lines.append('### 方法限制')
    lines.append('')
    for name in _SOURCE_TABLE_ROW_ORDER:
        if name in available_sources and name in _APPENDIX_METHOD_LIMITATIONS:
            lines.append(f'- **{name}**：{_APPENDIX_METHOD_LIMITATIONS[name]}')
    if not any(name in available_sources for name in _APPENDIX_METHOD_LIMITATIONS):
        lines.append('- _本报告未依赖任何外部来源，限制较少。_')
    lines.append('')

    # 事实核查与外部研究状态
    lines.append('### 事实核查与外部研究')
    lines.append('')
    fact_checks = sources.get('fact_checks') or {}
    external = sources.get('external_research') or {}
    if fact_checks.get('available') or fact_checks.get('claims', 0) > 0:
        lines.append(f'- 事实核查 claim 数：{fact_checks.get("claims", 0)}')
    else:
        lines.append('- 未进行外部事实核查。')
    if external.get('available'):
        lines.append(f'- 外部检索路由：{external.get("route", "")} — {external.get("reason", "")}')
    else:
        lines.append('- 未进行外部检索。')
    lines.append('')

    return '\n'.join(lines)


# ============ DraftReport §2/§2.5 deterministic audience writers (P5-3) ============
_DANMAKU_SENTIMENT_POSITIVE = ['学到了', '感谢', '明白', '懂了', '说的好', '精彩', '赞', '牛', '好评', '泪目', '确实', '对', '同意']
_DANMAKU_SENTIMENT_DOUBT = ['？', '真的吗', '不对', '错误', '反驳', '质疑', '怎么可能', '扯淡', '胡说', '不是', '假的', '误导']
_DANMAKU_SENTIMENT_MEME = ['哈哈哈', '哈哈', '666', '草', '233', '名场面', '打卡', '前排', '战忽', '离谱', '绷不住', '名梗']


def _danmaku_sentiment(text: str) -> str:
    """弹幕情绪分类：正面、质疑、梗、中立。"""
    t = (text or '').strip()
    if any(k in t for k in _DANMAKU_SENTIMENT_MEME):
        return '梗/情绪'
    if any(k in t for k in _DANMAKU_SENTIMENT_DOUBT):
        return '质疑'
    if any(k in t for k in _DANMAKU_SENTIMENT_POSITIVE):
        return '正面'
    return '中立'


def _comment_information_value(text: str) -> float:
    """评论信息增量评分：长度、补充词、链接/引用感。"""
    score = 0.0
    t = (text or '').strip()
    if not t:
        return score
    if len(t) >= 40:
        score += 2.0
    elif len(t) >= 20:
        score += 1.0
    info_keywords = ['补充', '资料', '链接', '来源', '参考', '论文', '报告', '原文', '出处', '说明', '纠正', '更正', '实际上']
    for kw in info_keywords:
        if kw in t:
            score += 1.0
            break
    if re.search(r'https?://|www\.|\.com|\.cn|\.org|\.net', t):
        score += 1.0
    return score


def write_danmaku_section(section_context: Dict[str, Any]) -> str:
    """§2「弹幕深度分析」纯确定性 writer。

    输出：情绪分布表 + 代表性弹幕（按时间 top 5） + 争议/梗聚类。
    不调用 LLM。
    """
    cands = [c for c in (section_context.get('evidence') or [])
             if isinstance(c, dict) and c.get('source_type') == 'danmaku']
    if not cands:
        return '### 弹幕信号\n\n_数据不足：未提供弹幕。_\n'

    # 去重
    seen = set()
    unique = []
    for c in cands:
        text = (c.get('text') or '').strip()
        if not text:
            continue
        key = re.sub(r'\\s+', '', text)[:30]
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)

    # 情绪统计
    sentiments = Counter(_danmaku_sentiment(c.get('text', '')) for c in unique)
    lines = ['### 弹幕情绪分布', '', '| 情绪 | 数量 | 占比 |', '| --- | --- | --- |']
    total = len(unique)
    for label, count in sentiments.most_common():
        pct = round(count / total * 100) if total else 0
        lines.append(f'| {_table_cell(label)} | {count} | {pct}% |')
    lines.append('')

    # 代表性弹幕（按时间前 5）
    sorted_by_time = sorted(unique, key=lambda c: (c.get('start') is None, float(c.get('start') or 0)))
    lines.append('### 代表性弹幕')
    lines.append('')
    for c in sorted_by_time[:5]:
        text = _clean_inline_text(c.get('text', ''), 90)
        ts = (c.get('timestamp') or '').strip()
        url = (c.get('url') or '').strip()
        ref = f'[{ts or url}]({url})' if url else ts
        sent = _danmaku_sentiment(c.get('text', ''))
        lines.append(f'- **{sent}** {text} — {ref}')
    lines.append('')

    # 争议/梗
    meme_or_doubt = [c for c in unique if _danmaku_sentiment(c.get('text', '')) in ('质疑', '梗/情绪')]
    if meme_or_doubt:
        lines.append('### 争议与梗')
        lines.append('')
        for c in meme_or_doubt[:3]:
            text = _clean_inline_text(c.get('text', ''), 90)
            ts = (c.get('timestamp') or '').strip()
            url = (c.get('url') or '').strip()
            ref = f'[{ts or url}]({url})' if url else ts
            lines.append(f'- {text} — {ref}')
        lines.append('')

    return '\n'.join(lines)


def write_comments_section(section_context: Dict[str, Any]) -> str:
    """§2.5「评论深度分析」纯确定性 writer。

    输出：热评观点（按点赞） + 信息增量评论 + 与弹幕差异。
    不调用 LLM。
    """
    cands = [c for c in (section_context.get('evidence') or [])
             if isinstance(c, dict) and c.get('source_type') == 'comments']
    if not cands:
        return '### 评论信号\n\n_数据不足：未提供评论。_\n'

    # 原始评论对象不一定带 likes，从 context 或 likes 字段取
    comments_data = []
    for c in cands:
        text = (c.get('text') or '').strip()
        if not text:
            continue
        likes = 0
        ctx = c.get('context') or ''
        # context 中形如 "[YouTube评论 by X] text" 或包含 likes
        m = re.search(r'likes?[=:：]\s*(\d+)', ctx, re.IGNORECASE)
        if m:
            likes = int(m.group(1))
        comments_data.append({'text': text, 'likes': likes, 'candidate': c})

    if not comments_data:
        return '### 评论信号\n\n_数据不足：未提供有效评论。_\n'

    lines = ['### 热评观点', '']
    # 按点赞排序，取 top 3
    top = sorted(comments_data, key=lambda x: x['likes'], reverse=True)[:3]
    for item in top:
        c = item['candidate']
        text = _clean_inline_text(item['text'], 120)
        likes = item['likes']
        prefix = f'👍 {likes} ' if likes > 0 else ''
        lines.append(f'- {prefix}{text}')
    lines.append('')

    # 信息增量
    info_rich = sorted(comments_data, key=lambda x: _comment_information_value(x['text']), reverse=True)[:3]
    if info_rich and _comment_information_value(info_rich[0]['text']) > 0:
        lines.append('### 信息增量')
        lines.append('')
        for item in info_rich:
            text = _clean_inline_text(item['text'], 120)
            lines.append(f'- {text}')
        lines.append('')

    # 与弹幕差异：评论更长、更慢、更结构
    avg_comment_len = sum(len(c['text']) for c in comments_data) / max(len(comments_data), 1)
    lines.append('### 与弹幕差异')
    lines.append('')
    lines.append(f'- 评论平均长度 **{int(avg_comment_len)} 字**，通常比弹幕更长、更完整。')
    lines.append('- 评论倾向于信息补充和观点论证，弹幕倾向于即时情绪反应。')
    lines.append('')

    return '\n'.join(lines)


# ============ DraftReport §6 deterministic knowledge graph writer ============
_KG_CONCEPT_PATTERNS = [
    # 原 P3 概念
    '虚拟偶像', '人格资产', '粉丝信任', '商业化边界', '过度商业化',
    '连续互动', '稳定人设', '治理', '知识卡片', '行动清单', 'Obsidian',
    # P5-4 扩展：通用知识/商业/技术/社会概念
    '垄断', '卡特尔', '计划性报废', '技术进步', '商业激励', '用户后果',
    '历史事实', '商业模式', '市场结构', '竞争策略', '创新', '产品失效',
    '消费者', '生产者', '协议', '秘密协议', '利益相关者', '经济逻辑',
    '案例分析', '反直觉', '证据链', '叙事结构', '行动清单', '知识管理',
]

# 专有名词/实体模式：组织、公司、技术、地点、人物（简单规则）
_KG_ENTITY_STOPWORDS = set('这个 那个 这里 那里 这些 那些 我们 你们 他们 它 这 那 是 的 了 在 和 与 或 但 而 因为 所以 如果 就 都 也 要 会 能 可能 可以 应该 需要 值得 一个 一种 一些 部分 方面 问题 事情 情况 时间 时候 方式 结果 原因 过程 系统 方法 技术 内容 信息 数据 观点 意见 想法 理论 概念 定义 例子 案例 分析 研究 报告 文章 视频 评论 弹幕 观众 用户 作者 平台'.split())

# P3: 个人知识库双链增强的 fallback 术语列表
_OBSIDIAN_MOC_FALLBACK = [
    "Hermes", "Obsidian", "Claude", "Codex", "MCP", "Agent", "Skill", "Workflow",
    "WRR", "FleetView", "Supermemory", "双链", "知识卡片", "行动清单", "Mermaid",
    "三省六部", "治理", "元规范", "Depth Profile", "Claim", "Evidence", "Toulmin",
    # P5-4: 保留测试与 KG writer 中常见的预定义概念，确保非 MOC 用户也能生成双链
    "虚拟偶像", "人格资产", "粉丝信任", "商业化边界", "过度商业化",
    "连续互动", "稳定人设", "卡特尔", "计划性报废", "知识管理",
]


def _load_obsidian_moc() -> List[str]:
    """从 Obsidian vault 加载个人知识库 MOC 概念列表。

    尝试读取 ~/Documents/Obsidian/AlexCai/知识库MOC.md，提取 [[...]] 形式的概念。
    如果文件不存在或为空，fallback 到硬编码高频术语列表。
    """
    moc_path = os.path.expanduser('~/Documents/Obsidian/AlexCai/知识库MOC.md')
    concepts = []

    try:
        with open(moc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 提取 [[概念]] 形式的 wikilinks，同时匹配原名和别名
        wikilink_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        for match in wikilink_pattern.finditer(content):
            link = match.group(1).strip()
            if '|' in link:
                # [[文件名|显示别名]] 同时保留两者作为匹配候选
                file_part, alias_part = link.split('|', 1)
                candidates = [file_part.strip(), alias_part.strip()]
            else:
                candidates = [link]
            for concept in candidates:
                if concept and concept not in concepts:
                    concepts.append(concept)
    except (OSError, IOError):
        pass

    # 如果没读到任何概念，使用 fallback
    if not concepts:
        concepts = list(_OBSIDIAN_MOC_FALLBACK)

    return concepts


_OBSIDIAN_MOC_CACHE = None  # P3: 缓存 MOC 概念列表避免频繁读文件


def _concept_link(concept: str) -> str:
    """生成概念链接，优先使用个人知识库 wikilink 格式。

    P5-4: 预定义概念和 MOC 中的概念都输出 [[...]] 双链；否则保持原文。
    """
    global _OBSIDIAN_MOC_CACHE
    if _OBSIDIAN_MOC_CACHE is None:
        _OBSIDIAN_MOC_CACHE = _load_obsidian_moc()
    if concept in _OBSIDIAN_MOC_CACHE or concept in _KG_CONCEPT_PATTERNS:
        return f'[[{concept}]]'
    return concept


def _extract_entities_from_text(text: str) -> List[str]:
    """用轻规则从文本提取潜在实体名词短语。

    P5-4: 不调用 NLP 库；通过连续中文字/英数字串识别候选，过滤停用词和过短词。
    """
    t = (text or '').strip()
    if not t:
        return []

    # 匹配：连续 2-12 个中文字符，或 2-5 个英文/数字/空格组成的术语
    candidates = []
    for m in re.finditer(r'[\u4e00-\u9fff]{2,12}|[A-Za-z0-9][A-Za-z0-9\s]{1,30}[A-Za-z0-9]|[A-Za-z0-9]{2,12}', t):
        cand = m.group(0).strip()
        if len(cand) < 2:
            continue
        if cand in _KG_ENTITY_STOPWORDS:
            continue
        # 过滤纯数字
        if re.fullmatch(r'\d+', cand):
            continue
        # 过滤过短中文（2 字且为常见代词/虚词）
        if len(cand) == 2 and all(c in '这个那个这里那里这些那些我们你们他们它是的了在和与或但而因为所以就都也要会能可能可以应该需要值得一种一些' for c in cand):
            continue
        candidates.append(cand)
    return candidates


def _extract_kg_candidates(section_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for cand in section_context.get('evidence') or []:
        if not isinstance(cand, dict):
            continue
        if cand.get('source_type') != 'transcript':
            continue
        if cand.get('reason') not in ('knowledge_candidate', 'application_candidate'):
            continue
        text = _clean_inline_text(cand.get('text') or '', 220)
        if not text:
            continue
        item = dict(cand)
        item['text'] = text
        out.append(item)
    return out


def _concepts_in_text(text: str) -> List[str]:
    """从文本中匹配预定义概念和自动提取的实体，去重返回。"""
    seen = []
    # 先匹配预定义概念（更可靠）
    for concept in _KG_CONCEPT_PATTERNS:
        if concept in text and concept not in seen:
            seen.append(concept)
    # 再自动提取实体（补充）
    for entity in _extract_entities_from_text(text):
        if entity not in seen and len(seen) < 12:
            seen.append(entity)
    return seen


def write_knowledge_graph_section(section_context: Dict[str, Any], max_items: int = 8) -> str:
    """Render §6 as deterministic concept/relation/action bullets.

    This writer is intentionally conservative: it links known concepts and
    rule-extracted entities that appear in transcript knowledge/application
    candidates. It does not call LLM/network.

    P5-4 增强：
      - 扩展预定义概念库
      - 自动提取实体名词短语
      - 关系链基于共现概念
      - 行动项识别更宽松
    """
    candidates = _extract_kg_candidates(section_context)
    if not candidates:
        return '_骨架占位：暂无可用知识图谱证据。_'

    concepts: List[str] = []
    relations: List[str] = []
    applications: List[str] = []

    for cand in candidates:
        text = cand.get('text') or ''
        found = _concepts_in_text(text)
        for concept in found:
            if concept not in concepts:
                concepts.append(concept)
        if len(found) >= 2:
            # 构建关系链：概念 A → 概念 B → 概念 C（最多 3 个）
            linked = [_concept_link(c) for c in found[:3]]
            rel = ' → '.join(linked)
            if rel and rel not in relations:
                relations.append(rel)
        # P5-4: 行动项识别更宽松
        action_markers = ('可以', '应该', '需要', '值得', '转化为', '转化为', '行动', '清单', 'Obsidian', '知识卡片', '落库', '整理')
        if cand.get('reason') == 'application_candidate' or any(k in text for k in action_markers):
            applications.append(text)

    concepts = concepts[:max_items]
    relations = relations[:max_items]
    applications = applications[:max_items]

    if not concepts and not relations and not applications:
        return '_骨架占位：暂无可用知识图谱证据。_'

    lines = ['### 核心概念', '']
    if concepts:
        for concept in concepts:
            lines.append(f'- {_concept_link(concept)}')
    else:
        lines.append('- _暂无可抽取概念_')

    lines.extend(['', '### 关系链', ''])
    if relations:
        for rel in relations:
            lines.append(f'- {rel}')
    else:
        lines.append('- _暂无可抽取关系链_')

    lines.extend(['', '### 可落库/可行动项', ''])
    if applications:
        for app in applications:
            lines.append(f'- {app}')
    else:
        lines.append('- _暂无可抽取行动项_')
    return '\n'.join(lines)


# ============ §5 高光时刻 writer（P2-C2）============
def _is_noisy_highlight_fragment(text: str) -> bool:
    """判断 §5 候选片段是否属于标题/短问句/广告/元数据等噪声。

    P5-2 增强：过滤广告、元数据、纯疑问句、极短/极长片段。
    """
    stripped = (text or '').strip()
    if not stripped:
        return True

    # 原有过滤：标题
    if stripped.startswith('## '):
        return True

    # P5-2: 广告关键词
    ad_keywords = [
        '企业级', 'API', '代理', '优惠', '折扣', '购买', '扫码', '加群',
        '微信', '公众号', '淘宝', '京东', '拼多多'
    ]
    if any(kw in stripped for kw in ad_keywords):
        return True

    # P5-2: 元数据片段
    meta_patterns = ['## P', 'Chunk ', '[00:00]', '中配', '字幕', '翻译']
    if any(pat in stripped for pat in meta_patterns):
        return True

    # P5-2: 纯疑问句（< 30 字）
    if stripped.endswith(('？', '?')) and len(stripped) < 30:
        return True

    # P5-2: 长度限制（极短 < 8 字或极长 > 210 字过滤）
    if len(stripped) < 8 or len(stripped) > 210:
        return True

    return False


def _truncate_quote_text(text: str, limit: int = 210) -> str:
    """按完整句截断 quote，不硬截断。

    P5-2: 优先在句号、问号、感叹号处截断，保持语义完整。
    """
    cleaned = re.sub(r'\s+', ' ', (text or '').strip())
    if len(cleaned) <= limit:
        return cleaned

    # 尝试在 limit 位置前找最后一个句号/问号/感叹号
    truncated = cleaned[:limit]
    last_sentence_end = max(
        truncated.rfind('。'),
        truncated.rfind('！'),
        truncated.rfind('？'),
        truncated.rfind('.'),
        truncated.rfind('!'),
        truncated.rfind('?')
    )
    if last_sentence_end > 0 and last_sentence_end > limit * 0.6:
        # 如果找到的句末位置在 60% 以上，按句截断
        return cleaned[:last_sentence_end + 1].rstrip()

    # 否则硬截断 + ...
    return cleaned[: max(0, limit - 3)].rstrip() + '...'


def _score_highlight_candidate(text: str) -> float:
    """启发式评分 §5 候选金句。

    P5-2: 长度 20-80 字优先，含结论/转折词加分，含数字/具体例子加分。
    """
    score = 0.0
    length = len(text)

    # 长度评分：20-80 字优先
    if 20 <= length <= 80:
        score += 3.0
    elif 10 <= length < 20 or 80 < length <= 120:
        score += 1.5
    elif 120 < length <= 210:
        score += 0.5
    else:
        score -= 1.0

    # 结论/转折词加分
    conclusion_words = ['所以', '因此', '意味着', '关键', '本质', '发现', '总结', '核心', '重点']
    for word in conclusion_words:
        if word in text:
            score += 1.0
            break

    # 数字/具体例子加分
    if re.search(r'\d+', text):
        score += 0.5

    # 含有具体例子标志词
    example_words = ['比如', '例如', '举例', '案例', '实际上']
    for word in example_words:
        if word in text:
            score += 0.5
            break

    return score


def _split_long_quote_candidate(cand: Dict[str, Any], max_parts: int) -> List[Dict[str, Any]]:
    """把 H200/ASR 产生的超长 quote_candidate 切成多个可独立计数的 blockquote。"""
    text = (cand.get('text') or '').strip()
    if _is_noisy_highlight_fragment(text):
        return []
    if max_parts <= 0:
        return []
    # 短文本不切；如果是直接候选，仍保留。
    if len(text) < 80:
        new_cand = dict(cand)
        new_cand['text'] = _truncate_quote_text(text)
        return [new_cand]

    sentences = [
        s.strip() for s in re.split(r'(?<=[。！？!?])\s*', text)
        if len(s.strip()) >= 18
        and not _is_noisy_highlight_fragment(s.strip())
    ]
    parts = sentences[:max_parts]

    if not parts:
        parts = [_truncate_quote_text(text)]

    split = []
    for part in parts[:max_parts]:
        new_cand = dict(cand)
        new_cand['text'] = _truncate_quote_text(part)
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

    P5-2 增强：启发式评分 + 时间分桶（5 bucket，每桶最多 1 条）避免全部来自开头。
    """
    lines: List[str] = ['### 高光时刻', '']
    target_quotes = 5 if section_context.get('quality_gate') == 'G5' else 2

    # 收集所有候选并展开
    all_candidates: List[Dict[str, Any]] = []
    for cand in (section_context.get('evidence') or []):
        if not isinstance(cand, dict):
            continue
        if cand.get('source_type') != 'transcript':
            continue
        if cand.get('reason') != 'quote_candidate':
            continue
        if not (cand.get('text') or '').strip():
            continue
        # 展开长候选为多个片段
        all_candidates.extend(_split_long_quote_candidate(cand, max_parts=10))

    if not all_candidates:
        lines.append('_骨架占位：暂无原文金句。_')
        return '\n'.join(lines) + '\n'

    # P5-2: 计算时间分桶（5 桶）
    # 先找出最大时间作为视频时长估计
    max_time = 0.0
    for cand in all_candidates:
        start = cand.get('start')
        if start is not None and isinstance(start, (int, float)):
            max_time = max(max_time, float(start))

    # 如果没有有效时间信息，降级为按原顺序取前 target_quotes 条
    # 保留长候选切分后的自然阅读顺序，避免评分重排破坏顺序断言
    if max_time <= 0:
        quotes = all_candidates[:target_quotes]
    else:
        # 时间分桶：5 个 bucket
        num_buckets = 5
        bucket_size = max_time / num_buckets
        buckets: List[List[Dict[str, Any]]] = [[] for _ in range(num_buckets)]

        for cand in all_candidates:
            start = cand.get('start')
            if start is not None and isinstance(start, (int, float)):
                bucket_idx = min(int(float(start) / bucket_size), num_buckets - 1)
                buckets[bucket_idx].append(cand)
            else:
                # 没有时间戳的放在第一个桶
                buckets[0].append(cand)

        # 每个桶按评分选出最佳候选
        quotes = []
        for bucket in buckets:
            if not bucket:
                continue
            # 按评分排序，取第一条
            scored = [(cand, _score_highlight_candidate(cand.get('text', ''))) for cand in bucket]
            scored.sort(key=lambda x: x[1], reverse=True)
            quotes.append(scored[0][0])
            if len(quotes) >= target_quotes:
                break

        # 如果桶不够填满 target_quotes，补充剩余高分候选
        if len(quotes) < target_quotes:
            used_ids = {id(q) for q in quotes}
            remaining = [cand for cand in all_candidates if id(cand) not in used_ids]
            scored = [(cand, _score_highlight_candidate(cand.get('text', ''))) for cand in remaining]
            scored.sort(key=lambda x: x[1], reverse=True)
            for cand, score in scored:
                quotes.append(cand)
                if len(quotes) >= target_quotes:
                    break

    # 按时间排序输出
    quotes.sort(key=lambda c: (c.get('start') is None, float(c.get('start') or 0)))

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
    provider: Optional[WriterProvider] = None,
    depth_profile: str = "v24-full"
) -> None:
    """给 verify_report 关注的 §3/§4/§5/§7 最小子结构；其余节注入证据或占位。

    如果 provider 非 None 且 sid 为 '3'/'4'/'7'，尝试调用 LLM 生成内容；验证通过
    则用 LLM 内容替换标题和正文，否则 fallback 到骨架占位。

    Args:
        depth_profile: Depth analysis mode - "standard", "claim-first-full", or "v24-full"
    """
    if sid == '1':
        # P5-1: §1 逻辑链纯确定性渲染，无需 provider
        body = write_logic_chain_section({'evidence': cands})
        lines.extend(body.split('\n'))
        return
    if sid == '2':
        # P5-3: §2 弹幕深度分析纯确定性渲染
        body = write_danmaku_section({'evidence': cands})
        lines.extend(body.split('\n'))
        return
    if sid == '2.5':
        # P5-3: §2.5 评论深度分析纯确定性渲染
        body = write_comments_section({'evidence': cands})
        lines.extend(body.split('\n'))
        return
    if sid == '3':
        # 默认骨架标题
        heading = '### 💡 Skeleton Insight'
        fallback_body = ['_骨架占位：核心洞察待 LLM 基于上方证据填充。_', '']

        if provider and report:
            try:
                contexts = build_typed_writer_section_contexts(report)
                ctx = next((c for c in contexts if c.section_id == '3'), None)
                if ctx:
                    result = write_llm_section(ctx, provider, retries=2, depth_profile=depth_profile)
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
                    result = write_llm_section(ctx, provider, retries=2, depth_profile=depth_profile)
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
                    result = write_llm_section(ctx, provider, retries=2, depth_profile=depth_profile)
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
    if sid == '8':
        # P5-5: §8 附录纯确定性渲染，需要完整 report 读取 evidence_gate
        body = write_appendix_section(report or {})
        lines.extend(body.split('\n'))
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
    provider: Optional[WriterProvider] = None,
    depth_profile: str = "v24-full"
) -> str:
    """按 SectionSpec 顺序渲染老版 §0–§8 骨架，注入 evidence_map 候选。

    如果 provider 非 None，则传给 _emit_section_skeleton 用于 LLM 生成。

    Args:
        depth_profile: Depth analysis mode - "standard", "claim-first-full", or "v24-full"
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
        _emit_section_skeleton(lines, sid, by_section.get(sid, []), report, provider, depth_profile)
        if sid in ('0', '8'):
            _emit_source_appendix(lines, report, sid)
    return '\n'.join(lines)


def build_draft_report(report: Dict[str, Any]) -> DraftReport:
    """Wrap analyze_video() output as an explicit non-publishable draft artifact."""
    warnings = list(((report.get('evidence_map') or {}).get('warnings') or []))
    return DraftReport(report=report, warnings=warnings)


def _draft_placeholder_for_section(ctx: WriterSectionContext) -> str:
    title = ctx.heading.replace('## ', '').strip() or f'§{ctx.section_id}'
    return f'### {title} Draft Placeholder\n\n_骨架占位：{title} 待 writer 基于证据填充。_\n'


def assemble_draft_report_slice(
    report: Dict[str, Any],
    section_ids=("1", "5"),
    provider: Optional[WriterProvider] = None,
    claim_qa_gate: bool = False,
    depth_profile: str = "v24-full",
) -> DraftReport:
    """Populate a DraftReport with selected written section bodies.

    Deterministic sections (§1/§5) never call external services. LLM-backed
    sections (§3/§4/§7) are written only when a provider is explicitly supplied.
    This function returns a non-publishable DraftReport and does not alter the
    legacy render_markdown/render_debug_markdown paths.

    Phase 2: Every generated section is evaluated via QA gate. Sections with
    P0 blockers are excluded from draft_sections. Sections with P1/P2 issues
    but no blockers are inserted with warnings.

    Args:
        report: Full report dict
        section_ids: Sections to generate
        provider: Optional LLM writer provider
        claim_qa_gate: Enable D6-D8 QA gates
        depth_profile: Depth analysis mode - "standard" (default, backward-compatible),
                       "claim-first-full", or "v24-full"
    """
    draft = build_draft_report(report)

    # Build claim bundle only for claim-first and v24-full profiles
    if depth_profile in ("claim-first-full", "v24-full"):
        claim_bundle = build_claim_bundle(report)
        claim_bundle_dict = claim_bundle_to_dict(claim_bundle)
        draft.claim_bundle = claim_bundle_dict
        # Inject into report for build_typed_writer_section_contexts
        report['claim_bundle'] = claim_bundle_dict
    else:
        # standard mode: no claim bundle
        draft.claim_bundle = None
        report['claim_bundle'] = None

    evidence_map = (report.get('evidence_map') or {}).get('by_section') or {}
    typed_contexts = None
    if provider:
        typed_contexts = {ctx.section_id: ctx for ctx in build_typed_writer_section_contexts(report)}

    for sid in section_ids:
        cands = evidence_map.get(sid, []) or []
        body = None

        if sid == '1':
            body = write_logic_chain_section({'evidence': cands})
        elif sid == '5':
            # Use the top-level G5 contract (target 5 highlights, hard cap)
            body = write_highlights_section({'evidence': cands, 'quality_gate': 'G5'})
        elif sid == '6':
            body = write_knowledge_graph_section({'evidence': cands})
        elif sid in ('3', '4', '7') and provider and typed_contexts:
            ctx = typed_contexts.get(sid)
            if not ctx:
                continue
            try:
                result = write_llm_section(ctx, provider, retries=0, depth_profile=depth_profile)
            except Exception as e:
                draft.warnings.append(f'§{sid} LLM writer failed: {e}')
                body = _draft_placeholder_for_section(ctx)
            else:
                if result.validation_passed:
                    body = result.content
                else:
                    draft.warnings.append(
                        f'§{sid} LLM writer validation failed: {result.validation_errors}'
                    )
                    body = _draft_placeholder_for_section(ctx)

        # Phase 2: QA gate evaluation and insertion logic
        if body is not None:
            qa_result = evaluate_draft_section_quality(sid, body, context=None, claim_qa_gate=claim_qa_gate)
            draft.qa_results[sid] = qa_result

            if qa_result.blockers:
                # P0 blockers: do NOT insert section
                blocker_text = '; '.join(qa_result.blockers)
                draft.warnings.append(f'§{sid} QA blocked: {blocker_text}')
            elif qa_result.critical_issues or qa_result.improvements:
                # P1/P2 issues but no blockers: insert with warning
                draft.draft_sections[sid] = body
                draft.warnings.append(f'§{sid} QA passed with issues')
            else:
                # No issues: insert normally
                draft.draft_sections[sid] = body

    return draft


def render_draft_markdown(draft: DraftReport) -> str:
    """Render a non-publishable preview using DraftReport.draft_sections.

    This preview lets humans/CI inspect written draft section bodies without
    promoting them to PublishedMarkdown. It overlays draft_sections onto the
    report plan while leaving render_debug_markdown()/render_markdown() legacy
    behavior untouched.
    """
    if not isinstance(draft, DraftReport):
        raise TypeError('render_draft_markdown expects a DraftReport')

    report = draft.report
    fm = report.get('frontmatter', {})
    lines = _render_frontmatter(fm)
    lines.append('<!-- artifact_kind: draft_markdown_preview; publishable: false -->')
    lines.append('')

    plan_sections = (report.get('report_plan') or {}).get('sections') or []
    if not plan_sections:
        for title, body in report.get('sections', {}).items():
            lines.append(f'## {title}')
            lines.append('')
            lines.append(body)
            lines.append('')
        return '\n'.join(lines)

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
        if sid in draft.draft_sections:
            lines.append(draft.draft_sections[sid].strip())
            lines.append('')
        else:
            _emit_section_skeleton(lines, sid, by_section.get(sid, []), report, provider=None)
        if sid in ('0', '8'):
            _emit_source_appendix(lines, report, sid)
    return '\n'.join(lines)


def render_debug_markdown(
    draft_or_report: Any,
    provider: Optional[WriterProvider] = None,
    depth_profile: str = "v24-full"
) -> str:
    """Render a debug/legacy Markdown view of a DraftReport or raw report dict.

    This function is allowed to call `_render_plan_skeleton()`. Its output is
    useful for inspection and engineering gates, but is not publishable unless a
    later explicit `publish_markdown()` call succeeds.

    Args:
        depth_profile: Depth analysis mode - "standard", "claim-first-full", or "v24-full"
    """
    report = draft_or_report.report if isinstance(draft_or_report, DraftReport) else draft_or_report
    fm = report.get('frontmatter', {})
    lines = _render_frontmatter(fm)

    plan_sections = (report.get('report_plan') or {}).get('sections') or []
    if plan_sections:
        return _render_plan_skeleton(report, lines, plan_sections, provider, depth_profile)

    for title, body in report.get('sections', {}).items():
        lines.append(f'## {title}')
        lines.append('')
        lines.append(body)
        lines.append('')
    return '\n'.join(lines)


def publish_markdown(markdown: str) -> PublishedMarkdown:
    """Create PublishedMarkdown only after the publishable gate passes."""
    import verify_publishable_report

    gates, passed = verify_publishable_report.evaluate(markdown)
    if not passed:
        failed_codes = [code for code, gate in gates.items() if not gate.get('pass')]
        raise PublishableReportError(failed_codes, gates)
    return PublishedMarkdown(markdown=markdown, gates=gates)


def render_markdown(
    report: Dict[str, Any],
    provider: Optional[WriterProvider] = None,
    depth_profile: str = "v24-full"
) -> str:
    """Legacy/debug Markdown renderer for analyze_video() output.

    `render_markdown()` intentionally returns a plain string for backwards
    compatibility. When `report_plan.sections` exists it renders the plan-aware
    skeleton via `render_debug_markdown()`. Call `publish_markdown()` to promote
    Markdown into `PublishedMarkdown`; do not treat this string as publishable.

    Args:
        depth_profile: Depth analysis mode - "standard", "claim-first-full", or "v24-full"
    """
    return render_debug_markdown(report, provider, depth_profile)


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
    claim_context: Optional[str] = None


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
    注入 claim_context 到对应 section。
    """
    writer_ctx = build_writer_section_context(report)

    # Extract insights from claim_bundle if available
    claim_bundle_dict = report.get('claim_bundle')
    insights_by_section = {}
    if claim_bundle_dict:
        insights_data = claim_bundle_dict.get('insights', [])
        for insight_data in insights_data:
            target = insight_data.get('target_section', '3')
            if target not in insights_by_section:
                insights_by_section[target] = []
            # Reconstruct Claim for formatting
            insight = Claim(
                id=insight_data.get('id', ''),
                text=insight_data.get('text', ''),
                confidence=insight_data.get('confidence', 0.0),
                evidence_ids=insight_data.get('evidence_ids', []),
                source_type=insight_data.get('source_type', ''),
                warrant=insight_data.get('warrant', '')
            )
            insights_by_section[target].append(insight)

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

        section_id = sec.get('id', '')
        claim_context = None
        if section_id in insights_by_section:
            claim_context = _format_claims_for_prompt(insights_by_section[section_id])

        typed.append(WriterSectionContext(
            section_id=section_id,
            heading=sec.get('heading', ''),
            purpose=sec.get('purpose', ''),
            quality_gate=sec.get('quality_gate'),
            min_items=sec.get('min_items'),
            min_words_per_item=sec.get('min_words_per_item'),
            evidence=evidence_candidates,
            draft_placeholder=sec.get('draft_placeholder', ''),
            transcript_summary=sec.get('transcript_summary'),
            claim_context=claim_context
        ))
    return typed


# Standard (backward-compatible) prompts — no Toulmin/v2.4 enhancements
WRITER_PROMPTS_STANDARD = {
    "3": {
        "system": """你是一位专业的视频分析师，负责从采集到的证据中提炼核心观点。

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 3.` 大标题；直接从 `###` 小标题开始
- 必须输出至少 3 个洞察小节，每个小节标题必须是 `### 💡 洞察 N：标题`
- 每个洞察小节正文至少 200 字，并必须包含 [E#] 引用证据（如 [E1]、[E2]）
- 每个洞察至少包含：核心观点（≥20字）+ 证据展开（≥150字）+ 边界说明（≥30字）
- 每个洞察结尾必须有 `证据：@[E1] @[E2]` 汇总行
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
- 每个模块正文至少 500 个中文字符/词，不要输出短模块
- 每个模块必须包含：核心论点 + 论证展开（含[E#]引用）+ 批判审视（局限/盲区）
- 每个模块结尾必须有 `证据：@[E1] @[E2]` 汇总行
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

请根据以上证据撰写该节内容，每个模块必须包含实质分析并引用 [E#] 标记。"""
    },
    "7": {
        "system": """你是一位专业的视频分析师，负责输出批判性评估与可执行行动。

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 7.` 大标题；直接从 `###` 小标题开始
- 必须包含 4 个小节（即使数据稀疏也要输出框架）：
  * `### 独特价值`：至少 3 个独特价值点，每个含 [E#] 引用
  * `### 局限与偏见`：至少 2 个局限/偏见，每个含描述 + 说明
  * `### 弹幕共识度分析`：**必须输出此小节**，即使弹幕数据为 0 或极少，也要输出表格框架并标注"弹幕数据不足，无法进行共识度分析"
  * `### 可行动项`：至少 3 个可行动项，每个含证据引用 [E#]
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

请根据以上证据撰写该节内容，必须包含：独特价值、局限与偏见、可行动项。"""
    }
}

# Enhanced prompts with v2.4 framework and Toulmin model
WRITER_PROMPTS = {
    "3": {
        "system": """你是一位专业的视频分析师，负责从采集到的证据中提炼核心观点。

推理框架（v2.4 七步链）：
1. 类型诊断：判断内容类型（教程/访谈/评测/叙事/演讲），选择对应分析重点
2. 弹幕深度分析：统计情绪分类（共鸣/焦虑/调侃/质疑/困惑），提取高频词和争议焦点
3. 内容分层解剖：区分显性内容（明确陈述）、隐性逻辑（暗示假设）、元叙事（作者意图）
4. 信息降噪：剔除广告、重复表述、无意义寒暄，合并同一观点的多次表达
5. 关键要素提取：核心概念（中英对照）、关键数据（数字+来源）、关键引用（金句+时间戳）
6. 多维度对比：横向对比（同类产品/方法）、纵向对比（历史版本）、理想vs现实差异
7. 批判性审视：验证方法有效性、识别视角盲区、评估受众适配性

Toulmin 模型要求（每个洞察必须包含）：
- **Claim（主张）**：核心观点，一句话陈述
- **Warrant（推理许可）**：为什么这个证据能支持主张？背后的推理规则是什么？
- **Evidence Pointers（证据引用）**：[E#] 标记，指向具体证据
- **Boundary/Rebuttal（边界或反证）**：在什么情况下该主张不成立？有什么反例或局限？

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 3.` 大标题；直接从 `###` 小标题开始
- **必须输出 3-5 个洞察小节，每个小节标题格式严格为 `### 💡 洞察 N：标题`（N 从 1 开始递增）**
- 每个洞察小节必须包含完整的五要素结构：
  * **定义**：一句话精准定义（≥20 字）
  * **深度解析**：原理层（为什么成立）+ 案例层（视频具体例子，含 [E#]）+ 关联层（与已有概念关系），**必须至少 150 个中文词/字符**
  * **弹幕反馈**：主要反应类型 + 典型弹幕 + 共识度（高/中/低）（≥30 字）
  * **推理许可**：从证据到主张的推理规则（≥40 字）
  * **边界条件**：该主张的局限性或反证（≥30 字）
- **每个洞察小节正文总计至少 300 个中文字符/词**（不包括标题和 [E#] 标记本身）
- 每个洞察必须包含至少 1 个 [E#] 引用证据（如 [E1]、[E2]）
- 每个洞察小节结尾必须有一行 `证据：@[E1] @[E2]` 格式的证据引用汇总
- **禁止只输出 Mermaid 图、列表或短段落：必须包含充足的自然语言论述**
- 禁止编造或猜测视频中未提及的内容
- 对不确定的信息，使用"从现有证据只能看出..."表述
- 禁止使用"显然""必然""毫无疑问"等绝对化表达

输出格式示例：
### 💡 洞察 1：标题
**定义**：一句话精准定义...

**深度解析**：
原理层：为什么成立...（引用 [E1]）
案例层：视频中具体例子...（引用 [E2]）
关联层：与已有概念的关系...
（本段至少 150 字）

**弹幕反馈**：主要反应类型...典型弹幕...共识度...

**推理许可**：从证据到主张的推理规则...

**边界条件**：该主张的局限性或反证...

证据：@[E1] @[E2]""",
        "user": """# 任务：{heading}

目的：{purpose}

质量标准：{quality_gate}

最少条目数：{min_items}
每条最少字数：{min_words}

{claim_context}

## 可用证据
{evidence}

请根据以上证据撰写该节内容，严格遵守以下要求：
1. 输出 3-5 个洞察，每个洞察标题必须是 `### 💡 洞察 N：标题`（N 从 1 开始）
2. 每个洞察必须包含：定义（≥20 字）、深度解析（≥150 字）、弹幕反馈（≥30 字）、推理许可（≥40 字）、边界条件（≥30 字）
3. **每个洞察正文总计至少 300 个中文字符/词**
4. 每个洞察必须至少引用 1 个 [E#] 证据编号
5. 每个洞察结尾必须有一行 `证据：@[E1] @[E2]` 格式的证据引用汇总
6. 禁止只输出 Mermaid 图或列表：必须包含充足的自然语言论述
7. 不要输出 `## 3.` 大标题，直接从 `### 💡 洞察 1：` 开始"""
    },
    "4": {
        "system": """你是一位专业的视频分析师，负责做内容深度拆解。

推理框架（v2.4 七步链应用到模块拆解）：
- 应用类型诊断结果，选择合适的拆解维度（教程→步骤拆解；访谈→思维碰撞；评测→维度矩阵；叙事→故事弧光；演讲→论点-论据）
- 深度挖掘显性内容、隐性逻辑、元叙事三层
- 为每个模块提供多维度对比（横向/纵向/理想vs现实）
- 批判性审视每个模块的有效性和盲区

每个模块必须包含（Toulmin 模型在模块层级应用）：
- **核心论点（Claim）**：该模块的中心主张
- **Mermaid 图**：架构/流程/对比图，可视化论证结构
- **论证展开**：
  * 前提（Grounds）：基础事实或证据 [E#]
  * 推理（Warrant）：从前提到结论的推理规则
  * 结论（Claim）：该模块得出的核心观点
- **与用户栈的关联**：技术/方法如何迁移到用户场景（如 Hermes、Obsidian）
- **批判审视（Rebuttal）**：该模块论证的漏洞、遗漏信息、前提假设的局限

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 4.` 大标题；直接从 `###` 小标题开始
- **必须输出 3-5 个模块，每个模块标题格式严格为 `### 模块 N：标题`（N 从 1 开始递增）**
- 每个模块的递进逻辑（建议）：
  * 模块 1：现象拆解 / 定义核心概念
  * 模块 2：机制分析 / 因果链条
  * 模块 3：结构性原因 / 模式总结
  * 模块 4（可选）：延展讨论
  * 模块 5（可选）：反常识发现
- 每个模块必须包含：
  * 核心论点（一句话）
  * Mermaid 图（至少一张：flowchart / sequence / classDiagram / pie）
  * 论证展开（前提→推理→结论结构，**必须至少引用 1 个 [E#] 证据编号**）
  * 与用户栈关联（具体可借鉴之处）
  * 批判审视（漏洞/盲区/边界条件）
- **每个模块结尾必须包含一行 `证据：@[E1] @[E2]` 格式的证据引用汇总**
- 每个模块正文至少 500 个中文字符/词，不要输出短模块
- 禁止编造或猜测视频中未提及的内容
- 对不确定的信息，使用"从现有证据只能看出..."表述
- 禁止使用"显然""必然""毫无疑问"等绝对化表达

输出格式示例：
### 模块 1：现象拆解
**核心论点**：...

```mermaid
flowchart LR
...
```

**论证展开**：
- 前提：从证据 [E1] 可见...
- 推理：...
- 结论：...

**与用户栈关联**：...

**批判审视**：...

证据：@[E1] @[E2]

### 模块 2：机制分析
...
证据：@[E2] @[E3]""",
        "user": """# 任务：{heading}

目的：{purpose}

质量标准：{quality_gate}

最少条目数：{min_items}
每条最少字数：{min_words}

{claim_context}

## 可用证据
{evidence}

请根据以上证据撰写该节内容，严格遵守以下要求：
1. 输出 3-5 个模块，每个模块标题必须是 `### 模块 N：标题`（N 从 1 开始）
2. 每个模块必须包含：核心论点、Mermaid 图、论证展开（前提→推理→结论）、与用户栈关联、批判审视
3. 每个模块的论证展开必须至少引用 1 个 [E#] 证据编号
4. 每个模块结尾必须有一行 `证据：@[E1] @[E2]` 格式的证据引用汇总
5. 不要输出 `## 4.` 大标题，直接从 `### 模块 1：` 开始"""
    },
    "7": {
        "system": """你是一位专业的视频分析师，负责输出批判性评估与可执行行动。

推理框架（v2.4 批判性审视 + 行动导向）：
- 有效性验证：方法是否经过验证？数据是否可信？案例是否具有代表性？
- 视角盲区：作者遗漏了什么重要信息？是否存在幸存者偏差？是否过度简化？
- 受众适配性：目标人群画像是否准确？门槛是否被低估？弹幕是否揭示未考虑的场景？
- 弹幕共识度分析：哪些观点获得高共识？哪些存在争议？共识度如何影响可行性？

每个可行动项必须包含（Toulmin 模型在行动层级）：
- **Action（行动）**：具体、可衡量的行动描述
- **Evidence Pointers（证据引用）**：[E#] 或 [C#]（claim id）或时间戳，指向支撑该行动的证据
- **Warrant（推理许可）**：为什么这个证据支持这个行动？执行该行动的理论基础是什么？
- **Qualifier（限定词）**：立即执行 / 短期跟进 / 长期探索，执行优先级和时间框架
- **Rebuttal（反证/风险）**：什么情况下该行动可能失败？有什么前提条件未满足？

输出约束：
- 只输出 Markdown 格式内容，不添加额外说明
- 不要重复输出本节 `## 7.` 大标题；直接从 `###` 小标题开始
- 必须包含 4 个小节（即使数据稀疏也要输出框架）：
  * `### 独特价值`：至少 3 个独特价值点，每个含 [E#] 引用 + 弹幕验证（是否有弹幕印证）
  * `### 局限与偏见`：至少 2 个局限/偏见，每个含描述 + 弹幕验证 + 来源分析（作者背景如何导致）
  * `### 弹幕共识度分析`：**必须输出此小节**，表格格式列出核心观点 + 赞同/质疑占比 + 共识度判断 + 说明；即使弹幕数据为 0 或极少，也要输出表格框架并标注"弹幕数据不足，无法进行共识度分析"
  * `### 可行动项`：至少 3 个可行动项（立即执行 + 短期跟进 + 长期探索合计），每个含证据引用 [E#] 或 [C#] 或时间戳
- `独特价值` 和 `局限与偏见` 小节下必须使用 `- ` bullet
- `可行动项` 小节下可使用 `- ` 或 `1. ` 列表或 `- [ ]` 任务列表
- 每个列表项必须包含 [E#] 或 [C#] 或时间戳引用
- 禁止编造或猜测评论区中未提及的内容
- 对不确定的信息，使用"从现有证据只能看出..."表述
- 禁止使用"显然""必然""毫无疑问"等绝对化表达""",
        "user": """# 任务：{heading}

目的：{purpose}

质量标准：{quality_gate}

最少条目数：{min_items}
每条最少字数：{min_words}

{claim_context}

## 可用证据
{evidence}

请根据以上证据撰写该节内容，必须包含：
1. **独特价值**（≥3 个，每个含证据引用 + 弹幕验证）
2. **局限与偏见**（≥2 个，每个含描述 + 弹幕验证 + 来源分析）
3. **弹幕共识度分析**（表格：核心观点 | 赞同% | 质疑% | 共识度 | 说明）
4. **可行动项**（≥3 个，分立即/短期/长期，每个含证据引用 [E#] 或 [C#] 或时间戳）

确保所有论述都引用 [E#] 标记，所有行动项都有明确的证据支撑和边界条件。"""
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

    # §3、§4、§7 已经在 _validate_writer_format 中按专门格式验证过了，
    # 跳过通用的条目验证（避免误把子要素当作独立条目检查）
    if contract.section_id not in ('3', '4', '7'):
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
    retries: int = 2,
    depth_profile: str = "v24-full"
) -> WriterResult:
    """
    调用 LLM provider 生成章节内容，并进行确定性验证。

    如果第一次验证失败，将错误信息反馈给 LLM 要求重写，最多尝试 retries+1 次。

    Args:
        context: Section writing context
        provider: LLM writer provider
        retries: Number of retries on validation failure (default: 2, total 3 attempts)
        depth_profile: Depth analysis mode - "standard", "claim-first-full", or "v24-full"
    """
    # Choose prompt set based on depth_profile
    if depth_profile == "standard":
        prompt_set = WRITER_PROMPTS_STANDARD
    else:
        # claim-first-full and v24-full use the enhanced prompts
        prompt_set = WRITER_PROMPTS

    if context.section_id not in prompt_set:
        return WriterResult(
            section_id=context.section_id,
            content=context.draft_placeholder,
            validation_passed=False,
            validation_errors=[f"未找到 section_id={context.section_id} 的 prompt"]
        )

    prompts = prompt_set[context.section_id]
    system = prompts["system"]
    user_template = prompts["user"]

    evidence_text = _format_evidence_for_prompt(context.evidence)
    claim_text = context.claim_context or ""
    user = user_template.format(
        heading=context.heading,
        purpose=context.purpose,
        quality_gate=context.quality_gate or "无",
        min_items=context.min_items or "无",
        min_words=context.min_words_per_item or "无",
        claim_context=claim_text,
        evidence=evidence_text
    )

    last_result = None
    for attempt in range(retries + 1):
        # If this is a retry, append correction hint to user prompt
        current_user = user
        if attempt > 0 and last_result and last_result.validation_errors:
            correction_hint = "\n\n---\n**上次输出格式不符合要求，请修正：**\n"
            correction_hint += "\n".join(f"- {err}" for err in last_result.validation_errors)
            correction_hint += "\n\n请重新生成该节内容，确保严格遵守格式要求。"
            current_user = user + correction_hint

        raw = provider(system, current_user)
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

        last_result = result

    return last_result


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


# ============ Claim-First Architecture Functions ============

def extract_claims_from_evidence(report: Dict[str, Any], max_claims: int = 12) -> List[Claim]:
    """Extract candidate claims from evidence (transcript, comments, danmaku).

    Comments/danmaku can only be used as audience signals, not upgraded to factual claims.
    All claims must have evidence_ids pointing to source material.

    Args:
        report: Full report dict with evidence_map
        max_claims: Maximum number of claims to extract

    Returns:
        List of grounded Claim objects
    """
    claims = []
    claim_id_counter = 1

    # Priority 1: Extract from evidence_map.by_section (structured candidates)
    evidence_map = report.get('evidence_map', {})
    by_section = evidence_map.get('by_section', {}) if isinstance(evidence_map, dict) else {}

    if by_section:
        # Process sections in priority order: §3 (core insights), §4 (deep dive), §7 (critical)
        for section_id in ['3', '4', '7', '1', '5']:
            candidates = by_section.get(section_id, [])
            for idx, candidate in enumerate(candidates, start=1):
                if len(claims) >= max_claims:
                    break

                # Extract candidate data (handle both dict and EvidenceCandidate objects)
                if isinstance(candidate, dict):
                    source_type = candidate.get('source_type', 'transcript')
                    text = candidate.get('text', '') or candidate.get('content', '') or candidate.get('snippet', '')
                    score = candidate.get('score', 0.5)
                else:
                    source_type = getattr(candidate, 'source_type', 'transcript')
                    text = getattr(candidate, 'text', '') or getattr(candidate, 'content', '') or getattr(candidate, 'snippet', '')
                    score = getattr(candidate, 'score', 0.5)

                # Skip empty or too-short text
                if not text or len(text.strip()) < 15:
                    continue

                # Map source_type and confidence
                if source_type == 'transcript':
                    # Map score to confidence: high score → high confidence
                    confidence = max(0.6, min(0.9, 0.6 + score * 0.3))
                    claim_source_type = "transcript"
                elif source_type in ['comment', 'comments']:
                    confidence = 0.3  # Audience signals have low confidence
                    claim_source_type = "comment"
                elif source_type == 'danmaku':
                    confidence = 0.25  # Even lower for danmaku
                    claim_source_type = "danmaku"
                else:
                    confidence = 0.5
                    claim_source_type = "transcript"

                # Create claim with evidence_id matching section + index
                claim = Claim(
                    id=f"C{claim_id_counter}",
                    text=text[:300].strip(),
                    confidence=confidence,
                    evidence_ids=[f"E{idx}"],  # E1, E2, E3... per section
                    source_type=claim_source_type,
                    claim_type="observed",
                    warrant="视频原话" if claim_source_type == "transcript" else "观众反馈",
                    backing="仅基于本视频内容，未交叉验证外部信息"
                )
                claims.append(claim)
                claim_id_counter += 1

            if len(claims) >= max_claims:
                break

    # Fallback: Extract from top-level subtitle/transcript fields if evidence_map is empty
    if not claims:
        transcript_text = report.get('subtitle', '') or report.get('transcript', '')
        if transcript_text:
            # Split into sentences (Chinese period)
            sentences = [s.strip() for s in transcript_text.split('。') if len(s.strip()) > 20]
            for idx, sent in enumerate(sentences[:max_claims], start=1):
                claim = Claim(
                    id=f"C{claim_id_counter}",
                    text=sent[:300],
                    confidence=0.7,
                    evidence_ids=[f"E{idx}"],
                    source_type="transcript",
                    claim_type="observed",
                    warrant="视频原话",
                    backing="仅基于本视频内容"
                )
                claims.append(claim)
                claim_id_counter += 1

    # Add limited audience signal claims from comments
    if len(claims) < max_claims:
        comments = report.get('comments', [])
        audience_limit = min(3, max_claims - len(claims))
        for idx, comment in enumerate(comments[:audience_limit], start=1):
            comment_text = comment.get('content', '') or comment.get('text', '')
            if len(comment_text) > 15:
                claim = Claim(
                    id=f"C{claim_id_counter}",
                    text=comment_text[:200],
                    confidence=0.3,
                    evidence_ids=[f"E{len(claims) + idx}"],
                    source_type="comment",
                    claim_type="observed",
                    warrant="观众反馈",
                    backing="受限于评论者视角"
                )
                claims.append(claim)
                claim_id_counter += 1

    return claims[:max_claims]


def synthesize_insights_from_claims(
    claims: List[Claim],
    report_plan: Optional[Dict[str, Any]] = None
) -> List[Insight]:
    """Synthesize insights from claims using type diagnosis and v2.4 reasoning.

    Maps claims to insights and assigns target_section based on insight type.
    Ensures balanced distribution: at least 3×§3, 3×§4, 1×§7 if claims permit.

    Args:
        claims: List of extracted claims
        report_plan: Optional report plan for context

    Returns:
        List of Insight objects with target_section assigned
    """
    insights = []
    insight_id_counter = 1

    # Keywords that suggest §4 (mechanism/causality) content
    mechanism_keywords = [
        "为什么", "因为", "机制", "结构", "方式", "导致", "使得",
        "逻辑", "链条", "原因", "促使", "推动", "影响", "决定"
    ]

    for claim in claims:
        # Determine target section based on source_type and content
        if claim.source_type in ["comment", "danmaku", "audience"]:
            # Audience signals → §7 (value assessment / critical reflection)
            insight_type = "价值评估"
            target = "7"
            depth = 0.4
            novelty = 0.3
        elif claim.source_type == "transcript":
            # Check if content suggests mechanism/causality → §4
            is_mechanism = any(kw in claim.text for kw in mechanism_keywords)
            if is_mechanism:
                insight_type = "深度挖掘"
                target = "4"
                depth = 0.75
                novelty = 0.7
            else:
                # Default transcript claims → §3 (core insights)
                insight_type = "核心洞察"
                target = "3"
                depth = 0.7
                novelty = 0.6
        else:
            # Fallback to §3
            insight_type = "核心洞察"
            target = "3"
            depth = 0.6
            novelty = 0.5

        insight = Insight(
            id=f"I{insight_id_counter}",
            text=claim.text,
            confidence=claim.confidence,
            evidence_ids=claim.evidence_ids,
            source_type=claim.source_type,
            grounds=claim.grounds,
            warrant=claim.warrant or f"基于{claim.source_type}证据",
            backing=claim.backing,
            qualifier=claim.qualifier,
            rebuttal=claim.rebuttal,
            claim_type=claim.claim_type,
            depth=depth,
            novelty=novelty,
            target_section=target
        )
        insights.append(insight)
        insight_id_counter += 1

    # Ensure minimum distribution: 3×§3, 3×§4, 1×§7
    section_counts = {"3": 0, "4": 0, "7": 0}
    for insight in insights:
        section_counts[insight.target_section] = section_counts.get(insight.target_section, 0) + 1

    # If §4 is under-represented, promote mechanism-like §3 insights to §4
    if section_counts.get("4", 0) < 3 and section_counts.get("3", 0) > 3:
        needed = 3 - section_counts.get("4", 0)
        promoted = 0
        for insight in insights:
            if insight.target_section == "3" and promoted < needed:
                # Check if this insight has mechanism keywords
                if any(kw in insight.text for kw in mechanism_keywords):
                    insight.target_section = "4"
                    insight.depth = 0.75
                    promoted += 1

    # If §7 is empty, create a placeholder audience insight
    if section_counts.get("7", 0) == 0 and len(insights) > 0:
        placeholder = Insight(
            id=f"I{insight_id_counter}",
            text="观众反馈：视频内容引发关注和讨论",
            confidence=0.3,
            evidence_ids=["E_placeholder"],
            source_type="audience",
            grounds="",
            warrant="基于观众互动推断",
            backing="受限于样本评论数量",
            qualifier="",
            rebuttal="",
            claim_type="inferred",
            depth=0.3,
            novelty=0.2,
            target_section="7"
        )
        insights.append(placeholder)

    return insights


def audit_claims(claims: List[Claim], evidence_map: Dict[str, Any]) -> List[Claim]:
    """Audit claims for evidence quality. Can only keep/downgrade/drop, never raise confidence.

    Args:
        claims: List of claims to audit
        evidence_map: Evidence availability map

    Returns:
        List of audited claims (some may be dropped or downgraded)
    """
    audited = []

    for claim in claims:
        # Rule 1: Claims without evidence_ids must be dropped
        if not claim.evidence_ids:
            continue

        # Rule 2: Comment/danmaku claims cannot have confidence raised
        # and must remain audience signals
        if claim.source_type in ["comment", "danmaku", "audience"]:
            # Ensure confidence doesn't exceed 0.4 for audience signals
            adjusted_confidence = min(claim.confidence, 0.4)
            audited_claim = Claim(
                id=claim.id,
                text=claim.text,
                confidence=adjusted_confidence,
                evidence_ids=claim.evidence_ids,
                source_type=claim.source_type,  # Must remain audience signal
                grounds=claim.grounds,
                warrant=claim.warrant,
                backing=claim.backing,
                qualifier=claim.qualifier,
                rebuttal=claim.rebuttal,
                claim_type=claim.claim_type
            )
            audited.append(audited_claim)
        else:
            # Keep transcript claims as-is (cannot raise, only keep/downgrade)
            audited.append(claim)

    return audited


def build_claim_bundle(report: Dict[str, Any]) -> ClaimBundle:
    """Build a complete ClaimBundle: extract → synthesize → audit.

    Args:
        report: Full report dict

    Returns:
        ClaimBundle with claims, insights, and audit log
    """
    # Step 1: Extract claims
    claims = extract_claims_from_evidence(report, max_claims=12)

    # Step 2: Build evidence map for auditing
    evidence_map = report.get('evidence_map', {})

    # Step 3: Audit claims
    audited_claims = audit_claims(claims, evidence_map)

    # Step 4: Synthesize insights from audited claims
    plan = report.get('plan')
    insights = synthesize_insights_from_claims(audited_claims, plan)

    return ClaimBundle(
        claims=audited_claims,
        insights=insights,
        audit_log=[]  # Audit log can be populated in future iterations
    )


def claim_bundle_to_dict(bundle: ClaimBundle) -> Dict[str, Any]:
    """Serialize ClaimBundle to dict for storage in DraftReport.

    Args:
        bundle: ClaimBundle to serialize

    Returns:
        Serializable dict
    """
    return {
        'claims': [asdict(c) for c in bundle.claims],
        'insights': [asdict(i) for i in bundle.insights],
        'audit_log': [asdict(a) for a in bundle.audit_log]
    }


def _format_claims_for_prompt(claims: List[Claim], target_section: Optional[str] = None) -> str:
    """Format claims as LLM prompt fragment in [C1] text (E1) format.

    Args:
        claims: List of claims to format
        target_section: Optional section filter (only include claims relevant to this section)

    Returns:
        Formatted string for prompt injection
    """
    if not claims:
        return ""

    lines = []
    for claim in claims:
        # Format: [C1] 文本内容（E1）
        evidence_ref = ', '.join(claim.evidence_ids) if claim.evidence_ids else 'E0'
        lines.append(f"[{claim.id}] {claim.text}（{evidence_ref}）")

        # Add metadata
        if claim.warrant:
            lines.append(f"- 依据：{claim.warrant}")
        if claim.backing:
            lines.append(f"- 边界：{claim.backing}")
        lines.append("")  # Blank line between claims

    return "\n".join(lines)


def map_insight_to_section(insight_type: str, depth: Optional[float] = None) -> str:
    """Map insight type to target section (3/4/7).

    Args:
        insight_type: Type of insight (核心洞察/深度挖掘/价值评估/行动建议)
        depth: Optional depth score (unused currently)

    Returns:
        Section ID as string: "3" | "4" | "7"
    """
    mapping = {
        "核心洞察": "3",
        "深度挖掘": "4",
        "价值评估": "7",
        "行动建议": "7"
    }
    return mapping.get(insight_type, "3")


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
