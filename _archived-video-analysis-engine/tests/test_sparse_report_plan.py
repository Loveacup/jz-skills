# -*- coding: utf-8 -*-
"""Slice C1: evidence budget + deterministic sparse writers contract tests."""

from video_analysis_engine import (
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    EvidenceBudget,
    build_evidence_budget,
    build_evidence_source_gate,
    build_report_plan,
    analyze_video,
    write_sparse_analysis_sections,
    write_sparse_logic_chain_section,
    render_debug_markdown,
    _emit_section_skeleton,
    assemble_draft_report_slice,
)

FORBIDDEN_HALLUCINATIONS = ['NASA', 'ESA', 'SpaceX', '拜占庭', 'Obsidian', 'Hermes']
SKELETON_MARKERS = ['_骨架占位', '骨架占位', 'TODO', '待补充', 'Skeleton']


def _sparse_input():
    """92s, 1 segment, 146 chars → triggers sparse mode."""
    text = '这是一段真实的抖音视频转录内容用于测试证据预算机制和稀疏报告计划模式的正确性。' * 2
    # Ensure exactly 146 chars
    text = text[:146].ljust(146, '。')
    assert len(text) == 146, f"Expected 146, got {len(text)}"
    return AnalysisInput(
        video_id='DY_SPARSE_001',
        title='测试短视频标题',
        author='测试作者',
        duration=92,
        platform='douyin',
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, text)],
            language='zh',
            source='h200-asr',
        ),
    )


def _full_input():
    """duration >= 1800 → full."""
    text = '这是长视频转录内容示例。' * 30
    return AnalysisInput(
        video_id='BV_FULL_001',
        title='长视频测试',
        duration=1800,
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, text)],
            language='zh',
            source='mlx-whisper',
        ),
    )


def _condensed_input():
    """181s with >600 chars and 3 anchors → condensed (not sparse)."""
    text = '中等长度视频转录内容。' * 60  # > 600 chars
    return AnalysisInput(
        video_id='DY_CONDENSED_001',
        title='中等视频',
        duration=181,
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, text[:200]),
                TranscriptSegment(60.0, text[200:400]),
                TranscriptSegment(120.0, text[400:]),
            ],
            language='zh',
            source='h200-asr',
        ),
    )


# ── Test 1 ──────────────────────────────────────────────────────────────────
def test_sparse_plan_for_92s_single_segment_146_chars():
    """92s + 1 segment + 146 chars → sparse; evidence budget is serialized."""
    inp = _sparse_input()
    gate = build_evidence_source_gate(inp)
    plan = build_report_plan(inp, gate)

    assert plan.mode == 'sparse', f"Expected sparse, got {plan.mode}"
    assert plan.can_generate_formal_report is True

    # evidence_budget is present in to_dict()
    d = plan.to_dict()
    budget = d.get('evidence_budget')
    assert budget is not None, "evidence_budget must be present in plan.to_dict()"
    assert budget['duration_seconds'] == 92
    assert budget['transcript_chars'] == 146
    assert budget['transcript_segments'] == 1
    assert budget['mode'] == 'sparse'
    assert 'reason' in budget


# ── Test 2 ──────────────────────────────────────────────────────────────────
def test_181s_is_not_sparse():
    """181s does not become sparse (duration > 180 threshold)."""
    inp = AnalysisInput(
        video_id='DY_181',
        title='刚超出阈值的视频',
        duration=181,
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, 'X' * 146)],
            language='zh',
            source='h200-asr',
        ),
    )
    gate = build_evidence_source_gate(inp)
    plan = build_report_plan(inp, gate)

    assert plan.mode != 'sparse', f"181s should not be sparse, got {plan.mode}"
    assert plan.mode == 'condensed'


# ── Test 3 ──────────────────────────────────────────────────────────────────
def test_1800s_is_full_even_with_one_tiny_segment():
    """duration >= 1800 stays full regardless of sparse transcript."""
    inp = AnalysisInput(
        video_id='BV_1800',
        title='长视频最短转录',
        duration=1800,
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, 'A' * 10)],
            language='zh',
            source='h200-asr',
        ),
    )
    gate = build_evidence_source_gate(inp)
    plan = build_report_plan(inp, gate)

    assert plan.mode == 'full', f"1800s should be full, got {plan.mode}"


# ── Test 4 ──────────────────────────────────────────────────────────────────
def test_no_transcript_stays_preanalysis():
    """No transcript → preanalysis; blocking_reason = missing_transcript."""
    inp = AnalysisInput(video_id='DY_NOASR', title='无转录视频', duration=90)
    gate = build_evidence_source_gate(inp)
    plan = build_report_plan(inp, gate)

    assert plan.mode == 'preanalysis'
    assert plan.can_generate_formal_report is False
    assert plan.blocking_reason == 'missing_transcript'


# ── Test 5 ──────────────────────────────────────────────────────────────────
def test_sparse_section_bodies_quality():
    """Sparse §3/§4/§7 are non-placeholder, cite [E1], include boundary, no hallucinations."""
    inp = _sparse_input()
    report = analyze_video(inp)

    sparse_bodies = write_sparse_analysis_sections(report)

    assert set(sparse_bodies.keys()) == {'3', '4', '7'}

    for sid, body in sparse_bodies.items():
        # Non-placeholder
        for marker in SKELETON_MARKERS:
            assert marker not in body, f"§{sid} contains skeleton marker '{marker}'"

        # Must cite [E1]
        assert '[E1]' in body, f"§{sid} must cite resolvable [E1]"

        # No hallucinations
        for bad in FORBIDDEN_HALLUCINATIONS:
            assert bad not in body, f"§{sid} must not contain '{bad}'"

    # §3: must have ### 💡 heading and explicit boundary language
    body3 = sparse_bodies['3']
    assert '### 💡' in body3, "§3 must have ### 💡 heading"
    assert '边界' in body3 or '超出' in body3, "§3 must include explicit evidence boundary"

    # §4: must have ### 模块 1 heading
    body4 = sparse_bodies['4']
    assert '### 模块 1' in body4, "§4 must start with ### 模块 1：... heading"

    # §7: must have 独特价值, 局限, 可行动 headings each with one bullet/item
    body7 = sparse_bodies['7']
    assert '独特价值' in body7, "§7 must have 独特价值 section"
    assert '局限' in body7, "§7 must have 局限 section"
    assert '可行动' in body7, "§7 must have 可行动 section"
    # At least one bullet under each key heading
    import re
    assert re.search(r'独特价值.*?^- ', body7, re.M | re.S), "§7 独特价值 must have at least one bullet"
    assert re.search(r'局限.*?^- ', body7, re.M | re.S), "§7 局限 must have at least one bullet"
    assert re.search(r'可行动.*?^- ', body7, re.M | re.S), "§7 可行动 must have at least one bullet"


# ── Test 6 ──────────────────────────────────────────────────────────────────
def test_sparse_sections_provider_spy_called_zero_times():
    """Provider passed to render/assembly is NOT called for sparse §3/§4/§7."""
    inp = _sparse_input()
    report = analyze_video(inp)

    call_count = 0

    def spy_provider(system, user):
        nonlocal call_count
        call_count += 1
        return '### 💡 洞察 1：标题\n\n内容 [E1]\n\n证据：@[E1]'

    # Via assemble_draft_report_slice
    assemble_draft_report_slice(
        report,
        section_ids=('3', '4', '7'),
        provider=spy_provider,
    )
    assert call_count == 0, (
        f"assemble_draft_report_slice called provider {call_count} time(s) for sparse §3/§4/§7"
    )

    # Via _emit_section_skeleton
    by_section = (report.get('evidence_map') or {}).get('by_section') or {}
    for sid in ('3', '4', '7'):
        lines = []
        _emit_section_skeleton(lines, sid, by_section.get(sid, []), report, spy_provider)
    assert call_count == 0, (
        f"_emit_section_skeleton called provider {call_count} time(s) for sparse §3/§4/§7"
    )


# ── Test 7 ──────────────────────────────────────────────────────────────────
def test_full_and_condensed_thresholds_unchanged():
    """Existing full/condensed construction thresholds are not affected by Slice C1."""
    # Full: duration >= 1800
    plan_full = build_report_plan(_full_input())
    assert plan_full.mode == 'full'
    by_id_f = {s.id: s for s in plan_full.sections}
    assert by_id_f['4'].min_items >= 3, "full §4 must require >= 3 modules"
    assert by_id_f['4'].min_words_per_item >= 500, "full §4 min_words_per_item must be >= 500"
    assert by_id_f['7'].min_items == 8, "full §7 must keep min_items == 8"

    # Condensed: 181s
    plan_cond = build_report_plan(_condensed_input())
    assert plan_cond.mode == 'condensed'
    by_id_c = {s.id: s for s in plan_cond.sections}
    assert by_id_c['7'].required is True, "condensed §7 must remain required"
    assert by_id_c['7'].quality_gate == 'G7', "condensed §7 must keep G7 gate"
    assert by_id_c['7'].min_items == 8, "condensed §7 min_items must be 8"
    assert by_id_c['4'].min_items == 2, "condensed §4 min_items must be 2"


# ── Test 8: sparse §1 literal timeline ──────────────────────────────────────
def test_sparse_section1_literal_timeline_no_narrative_labels():
    """Sparse §1 outputs literal-observation table; no narrative-phase labels."""
    FORBIDDEN_LABELS = ['提出问题', '深化分析', '得出结论', '叙事阶段', '起点', '推进', '转折', '收束']
    inp = _sparse_input()
    report = analyze_video(inp)

    body = write_sparse_logic_chain_section(report)

    # Must contain a Markdown table
    assert '| 时间 |' in body, "§1 sparse body must have a Markdown table with 时间 column"
    assert '| 来源 |' in body, "§1 sparse body must have 来源 column"
    assert '| 字面摘要 |' in body, "§1 sparse body must have 字面摘要 column"
    assert '证据边界' in body, "§1 sparse body must state evidence boundary"

    # Must not contain narrative-phase labels
    for label in FORBIDDEN_LABELS:
        assert label not in body, f"§1 sparse body must not contain narrative label '{label}'"

    # Must not contain skeleton markers
    for marker in SKELETON_MARKERS:
        assert marker not in body, f"§1 sparse body must not contain skeleton marker '{marker}'"

    # No forbidden hallucinations
    for bad in FORBIDDEN_HALLUCINATIONS:
        assert bad not in body, f"§1 sparse body must not contain '{bad}'"


def test_sparse_section1_contains_literal_transcript_text():
    """Sparse §1 table rows include actual transcript excerpt, not empty or placeholder."""
    inp = _sparse_input()
    report = analyze_video(inp)

    body = write_sparse_logic_chain_section(report)

    # The transcript text should appear (truncated) in the table
    transcript_text = inp.transcript.segments[0].text
    excerpt = transcript_text[:30]
    assert excerpt in body, (
        f"§1 sparse body must contain literal transcript excerpt; "
        f"expected substring '{excerpt}' in:\n{body}"
    )


def test_sparse_section1_escapes_table_delimiters_and_rejects_metadata_fallback():
    """Transcript pipes cannot corrupt the table; missing evidence cannot fall back to metadata prose."""
    inp = _sparse_input()
    inp.transcript.segments[0].text = '遥测|信号正常'
    report = analyze_video(inp)

    body = write_sparse_logic_chain_section(report)
    assert '遥测\\|信号正常' in body

    report['evidence_map']['by_section']['1'] = []
    empty_body = write_sparse_logic_chain_section(report)
    assert '拒绝生成叙事内容' in empty_body
    assert '以元数据为准' not in empty_body


def test_full_mode_section1_retains_generic_logic_chain():
    """Full mode §1 continues to use the generic logic chain writer (阶段/逻辑动作 columns)."""
    inp = _full_input()
    report = analyze_video(inp)
    assert report['report_plan']['mode'] == 'full'

    md = render_debug_markdown(report)

    # Full mode §1 has 阶段/逻辑动作 columns (generic writer)
    assert '| 阶段 |' in md or '| 逻辑动作 |' in md, (
        "Full mode §1 must use generic logic chain with 阶段/逻辑动作 columns"
    )
    # Full mode §1 must NOT use the sparse header
    assert '### 转录时间线' not in md, (
        "Full mode §1 must not render the sparse 转录时间线 header"
    )
