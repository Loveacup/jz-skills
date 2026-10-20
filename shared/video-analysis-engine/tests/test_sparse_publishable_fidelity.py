# -*- coding: utf-8 -*-
"""test_sparse_publishable_fidelity.py — Slice C2b: report-aware sparse fidelity gate.

Run:
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3.12 -m pytest -q \
      -p no:cacheprovider tests/test_sparse_publishable_fidelity.py
"""

import copy
import json

import pytest

from video_analysis_engine import (
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    PublishedMarkdown,
    PublishableReportError,
    analyze_video,
    render_debug_markdown,
    publish_markdown,
    write_sparse_analysis_sections,
)
from verify_publishable_report import (
    evaluate_sparse_report_fidelity,
    evaluate_publishable_report,
    _normalize_sparse_section,
)


# ─── Shared fixture ──────────────────────────────────────────────────────────

def _sparse_rocket_input() -> AnalysisInput:
    """92s single-segment ≤600 chars → sparse mode; title/desc contain 长征十号乙运载火箭."""
    text = (
        '长征十号乙运载火箭完成一子级发射回收，标志着中国商业航天实现重要突破，'
        '一子级在着陆场精确着陆，整体发射流程顺利完成。'
    )
    assert len(text) <= 600, f"transcript too long: {len(text)}"
    return AnalysisInput(
        video_id='DY_ROCKET_SPARSE_001',
        title='长征十号乙运载火箭发射回收全程直播',
        description='发射回收现场实录，一子级精确着陆，商业航天重要里程碑。',
        author='航天直播号',
        duration=92,
        platform='douyin',
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, text)],
            language='zh',
            source='h200-asr',
        ),
    )


def _build_sparse_report():
    """Return (report, markdown) for the rocket sparse input."""
    inp = _sparse_rocket_input()
    report = analyze_video(inp)
    assert report['report_plan']['mode'] == 'sparse', (
        f"Expected sparse mode, got: {report['report_plan']['mode']}"
    )
    md = render_debug_markdown(report)
    return report, md


# ─── Test 1: exact render passes fidelity and publish_markdown ────────────────

def test_exact_sparse_render_passes_fidelity():
    report, md = _build_sparse_report()

    result = evaluate_sparse_report_fidelity(md, report)

    assert result['skipped'] is False
    assert result['passed'] is True
    assert result['mismatched_sections'] == []
    assert result['missing_local_evidence_sections'] == []


def test_exact_sparse_render_publish_markdown_returns_published_markdown():
    report, md = _build_sparse_report()

    pm = publish_markdown(md, report)

    assert isinstance(pm, PublishedMarkdown)
    assert pm.publishable is True
    assert pm.markdown == md
    assert 'P0_SPARSE_REPORT_FIDELITY' in pm.gates
    assert pm.gates['P0_SPARSE_REPORT_FIDELITY']['pass'] is True


# ─── Test 2: add unsupported sentence to §3 → fidelity fails ─────────────────

def test_added_unsupported_sentence_in_section3_fails_fidelity():
    report, md = _build_sparse_report()

    # Insert an unsupported hallucination sentence just before the evidence footer
    tampered = md.replace(
        '\n证据：@[E1]',
        '\nNASA 已验证此发射技术的多次实验可行性，具有国际先进水平。\n\n证据：@[E1]',
        1,
    )
    assert tampered != md, "Tampering had no effect"

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    assert result['skipped'] is False
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '3' in mismatch_sids


def test_added_unsupported_sentence_raises_in_publish_markdown():
    report, md = _build_sparse_report()
    tampered = md.replace(
        '\n证据：@[E1]',
        '\nNASA 已验证此发射技术的多次实验可行性，具有国际先进水平。\n\n证据：@[E1]',
        1,
    )

    with pytest.raises(PublishableReportError) as exc_info:
        publish_markdown(tampered, report)

    assert 'P0_SPARSE_REPORT_FIDELITY' in exc_info.value.failed_codes


# ─── Test 3: change one word in §4 or §7 → fidelity fails ───────────────────

def test_changed_word_in_section4_fails_fidelity():
    report, md = _build_sparse_report()

    # §4 body contains '可推导'; changing it breaks the deterministic output
    assert '可推导' in md, "Expected §4 to contain '可推导'"
    tampered = md.replace('可推导', '能推导', 1)

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '4' in mismatch_sids


def test_changed_word_in_section7_fails_fidelity():
    report, md = _build_sparse_report()

    # §7 body contains '独特价值'; removing one line breaks exact match
    assert '独特价值' in md, "Expected §7 to contain '独特价值'"
    tampered = md.replace(
        '### 独特价值\n\n- 转录片段 [E1]',
        '### 独特价值\n\n- 改写后的独特价值',
        1,
    )

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '7' in mismatch_sids


# ─── Test 4: missing local transcript candidate → fails ──────────────────────

def test_missing_local_transcript_candidate_fails_fidelity():
    report, md = _build_sparse_report()

    # Deep-copy and strip transcript candidates from §3's evidence_map entry
    report_missing = copy.deepcopy(report)
    by_section = report_missing['evidence_map']['by_section']
    original_3 = by_section.get('3', [])
    # Keep metadata/other candidates but drop transcript ones
    by_section['3'] = [
        c for c in original_3
        if not (isinstance(c, dict) and c.get('source_type') == 'transcript')
    ]

    result = evaluate_sparse_report_fidelity(md, report_missing)

    assert result['passed'] is False
    assert '3' in result['missing_local_evidence_sections']


def test_missing_local_evidence_fails_even_if_body_contains_e1():
    """Gate must fail on missing local evidence even if [E1] appears in the rendered body."""
    report, md = _build_sparse_report()

    report_missing = copy.deepcopy(report)
    by_section = report_missing['evidence_map']['by_section']
    # Remove transcript from all three sparse sections
    for sid in ('3', '4', '7'):
        by_section[sid] = []

    result = evaluate_sparse_report_fidelity(md, report_missing)

    assert result['passed'] is False
    # All three sections should be listed as missing local evidence
    for sid in ('3', '4', '7'):
        assert sid in result['missing_local_evidence_sections'], (
            f"Expected sid={sid!r} in missing_local_evidence_sections"
        )


# ─── Test 5: full/condensed skips fidelity; existing semantics unchanged ─────

def test_full_mode_report_skips_fidelity():
    result = evaluate_sparse_report_fidelity("any markdown", {'report_plan': {'mode': 'full'}})

    assert result['passed'] is True
    assert result['skipped'] is True
    assert result['reason'] == 'not_sparse_mode'


def test_condensed_mode_report_skips_fidelity():
    result = evaluate_sparse_report_fidelity("any markdown", {'report_plan': {'mode': 'condensed'}})

    assert result['passed'] is True
    assert result['skipped'] is True


def test_fidelity_gate_absent_from_evaluate_publishable_report_for_full_mode():
    """For full/condensed reports, P0_SPARSE_REPORT_FIDELITY must not appear in results."""
    report = {'report_plan': {'mode': 'full'}}
    # Use a minimal markdown that satisfies only structure checks (gate may fail on other P0s)
    results, _passed = evaluate_publishable_report("## 0. x\n\n## 1. y\n\n", report)

    assert 'P0_SPARSE_REPORT_FIDELITY' not in results


# ─── Test 6: publish_markdown(md) without report stays backward compatible ───

def test_publish_markdown_without_report_passes_for_valid_sparse_md():
    """No-report path must use evaluate() (Markdown-only) and succeed for clean md."""
    report, md = _build_sparse_report()

    # publish_markdown without report uses the Markdown-only gate
    pm = publish_markdown(md)

    assert isinstance(pm, PublishedMarkdown)
    assert 'P0_SPARSE_REPORT_FIDELITY' not in pm.gates


def test_publish_markdown_without_report_raises_for_skeleton():
    with pytest.raises(PublishableReportError) as exc_info:
        publish_markdown("## 3. 核心洞察\n\n_骨架占位：待填充。_\n")

    assert 'P0_NO_SKELETON' in exc_info.value.failed_codes


# ─── Test 7: gate measured data is compact and JSON serializable ──────────────

def test_fidelity_result_is_json_serializable_on_pass():
    report, md = _build_sparse_report()

    result = evaluate_sparse_report_fidelity(md, report)

    serialized = json.dumps(result)
    parsed = json.loads(serialized)
    assert parsed['passed'] is True
    assert parsed['mismatched_sections'] == []


def test_fidelity_result_is_json_serializable_on_fail():
    report, md = _build_sparse_report()
    tampered = md.replace('\n证据：@[E1]', '\n拜占庭将军问题证明了此系统的容错性。\n\n证据：@[E1]', 1)

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    serialized = json.dumps(result)
    parsed = json.loads(serialized)
    assert parsed['passed'] is False
    for entry in parsed['mismatched_sections']:
        assert 'sid' in entry
        assert 'expected_chars' in entry
        assert 'actual_chars' in entry
        assert 'expected_hash' in entry
        assert 'actual_hash' in entry
    # Hashes are short (12 hex chars), not full report text
    for entry in parsed['mismatched_sections']:
        assert len(entry['expected_hash']) == 12
        assert len(entry['actual_hash']) == 12


def test_fidelity_result_from_evaluate_publishable_report_is_json_serializable():
    report, md = _build_sparse_report()

    results, passed = evaluate_publishable_report(md, report)

    assert 'P0_SPARSE_REPORT_FIDELITY' in results
    # The gate's measured field must be JSON serializable
    json.dumps(results['P0_SPARSE_REPORT_FIDELITY'])


# ─── Regression: purpose-line normalization prefix-only contract ──────────────

def test_normalize_strips_renderer_prefix_purpose_line():
    """Renderer-injected ## heading + purpose line must be stripped; body unchanged."""
    section_with_prefix = (
        "## 3. 核心洞察 (Key Insights)\n"
        "\n"
        "_目的：提炼 1 个高价值认知点并绑定证据_\n"
        "\n"
        "### 💡 可见内容摘要\n"
        "\n"
        "正文内容。\n"
    )
    body_only = "### 💡 可见内容摘要\n\n正文内容。"

    assert _normalize_sparse_section(section_with_prefix) == body_only
    # Normalizing the body alone must produce the same result
    assert _normalize_sparse_section(body_only) == body_only


def test_purpose_line_inside_body_is_retained_and_causes_mismatch():
    """A _目的：..._ line inside the deterministic body must cause a fidelity failure."""
    report, md = _build_sparse_report()

    # Inject a purpose-looking line INSIDE §3 body (after the first paragraph,
    # well past the renderer prefix position)
    inject = '_目的：NASA 已验证此发射技术的多次实验可行性，具有国际先进水平。_'
    tampered = md.replace(
        '\n\n因为当前证据为',
        '\n\n' + inject + '\n\n因为当前证据为',
        1,
    )
    assert tampered != md, "Injection had no effect on the markdown"

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '3' in mismatch_sids, (
        f"Expected §3 mismatch; got mismatched_sections={result['mismatched_sections']}"
    )


# ─── §1 fidelity tests ───────────────────────────────────────────────────────

def test_exact_sparse_section1_passes_fidelity():
    """Exact sparse §1 from deterministic writer passes fidelity gate."""
    report, md = _build_sparse_report()

    result = evaluate_sparse_report_fidelity(md, report)

    assert result['skipped'] is False
    assert result['passed'] is True, (
        f"Expected fidelity to pass; mismatched={result.get('mismatched_sections')}"
    )
    # §1 must not appear in mismatches
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '1' not in mismatch_sids


def test_added_unsupported_sentence_in_section1_fails_fidelity():
    """Adding an unsupported sentence to sparse §1 fails fidelity with sid '1'."""
    report, md = _build_sparse_report()

    # Inject an unsupported sentence into §1 (before the evidence boundary line)
    assert '**证据边界**' in md, "Expected §1 to contain evidence boundary"
    tampered = md.replace(
        '\n**证据边界**',
        '\nNASA 官方数据证明此发射为里程碑式成就，技术达到国际最高水平。\n\n**证据边界**',
        1,
    )
    assert tampered != md, "Tampering §1 had no effect"

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '1' in mismatch_sids, (
        f"Expected §1 mismatch; got mismatched_sections={result['mismatched_sections']}"
    )


def test_changed_word_in_section1_fails_fidelity():
    """Changing a word in sparse §1 fails fidelity with sid '1'."""
    report, md = _build_sparse_report()

    # §1 body contains '字面摘要' (table column header); changing it breaks exact match
    assert '字面摘要' in md, "Expected §1 to contain '字面摘要' column header"
    tampered = md.replace('字面摘要', '内容摘要', 1)

    result = evaluate_sparse_report_fidelity(tampered, report)

    assert result['passed'] is False
    mismatch_sids = {m['sid'] for m in result['mismatched_sections']}
    assert '1' in mismatch_sids


def test_missing_local_transcript_evidence_for_section1_fails_fidelity():
    """Missing transcript candidate in by_section['1'] fails fidelity."""
    import copy
    report, md = _build_sparse_report()

    report_missing = copy.deepcopy(report)
    by_section = report_missing['evidence_map']['by_section']
    # Strip all transcript candidates from §1
    by_section['1'] = [
        c for c in (by_section.get('1') or [])
        if not (isinstance(c, dict) and c.get('source_type') == 'transcript')
    ]

    result = evaluate_sparse_report_fidelity(md, report_missing)

    assert result['passed'] is False
    assert '1' in result['missing_local_evidence_sections'], (
        f"Expected '1' in missing_local_evidence_sections; got {result['missing_local_evidence_sections']}"
    )
