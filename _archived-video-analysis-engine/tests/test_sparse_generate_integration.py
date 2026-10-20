# -*- coding: utf-8 -*-
"""Slice C3a integration tests: engine mode override + sparse generate path."""

import generate_report
from research_wrr_adapter import HermesWRRAdapter


# ============ Fixtures ============

def _92s_sparse_results(tmp_path):
    """92s, 1 segment at t=10 → auto selects sparse (duration≤180 AND distinct_starts<3)."""
    jp = tmp_path / "BVsparse_subtitle.json"
    jp.write_text(
        '{"body":[{"from":10,"to":20,"content":'
        '"Obsidian 和 Claude 是知识管理工具，帮助构建双链笔记。"}]}',
        encoding="utf-8",
    )
    return {
        "bvid": "BVsparse",
        "title": "Obsidian 双链笔记工具介绍",
        "duration": 92,
        "subtitle": {"method": "official", "json_path": str(jp), "language": "zh"},
        "comments": None,
        "danmaku": None,
    }


def _condensed_results(tmp_path):
    """600s, 3 distinct segments → auto selects condensed."""
    jp = tmp_path / "BVcondensed_subtitle.json"
    jp.write_text(
        '{"body":['
        '{"from":0,"to":60,"content":"第一段：提出问题，分析 AI 应用融资和 ARR。"},'
        '{"from":200,"to":260,"content":"第二段：深入探讨 Cursor 和 Claude Code 的商业模式。"},'
        '{"from":400,"to":460,"content":"第三段：总结对观众的启发，提出可行动建议。"}'
        ']}',
        encoding="utf-8",
    )
    return {
        "bvid": "BVcondensed",
        "title": "AI 应用能融下一轮吗",
        "duration": 600,
        "subtitle": {"method": "official", "json_path": str(jp), "language": "zh"},
        "comments": None,
        "danmaku": None,
    }


def _no_transcript_results():
    return {
        "bvid": "BVnotr",
        "title": "无字幕视频",
        "duration": 60,
        "subtitle": None,
        "comments": None,
        "danmaku": None,
    }


# ============ Mode selection ============

def test_auto_92s_1segment_selects_sparse(tmp_path):
    """mode='auto' with 92s/1 segment → effective sparse."""
    _, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
    )
    assert report["report_plan"]["mode"] == "sparse"


def test_explicit_full_override_on_sparse_input_selects_full(tmp_path):
    """mode='full' forces full regardless of evidence budget."""
    _, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="full",
    )
    assert report["report_plan"]["mode"] == "full"


def test_explicit_full_mode_calls_provider_3_times(tmp_path):
    """mode='full' with provider → §3/§4/§7 each call provider once; render_debug_markdown hits cache."""
    import run_quality_gate

    calls = []

    def counting_provider(system, user):
        calls.append((system, user))
        return run_quality_gate.fixture_writer_provider(system, user)

    generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        provider=counting_provider,
        mode="full",
    )

    assert len(calls) == len(set(calls)), "duplicate prompts indicate cache miss"
    assert len(calls) == 3, f"expected 3 (§3/§4/§7), got {len(calls)}"


# ============ Sparse provider isolation ============

def test_sparse_mode_provider_never_called(tmp_path):
    """Sparse mode must never invoke the LLM writer provider."""
    calls = []

    def spy_provider(system, user):
        calls.append((system, user))
        return "spy was called"

    generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        provider=spy_provider,
        mode="auto",
    )

    assert calls == [], f"provider was called {len(calls)} times in sparse mode"


def _validated_research_adapter():
    def executor(query):
        query_uid = str(query["query_uid"])
        claim_uids = list(query.get("claim_uids") or ())
        if not claim_uids:
            return {"candidates": []}
        claim_uid = claim_uids[0]
        quote = f"独立研究资料确认该主张，并提供可复核说明：{claim_uid}。"
        return {"candidates": [{
            "url": f"https://research.example/{query_uid}",
            "title": f"独立研究来源 {query_uid}",
            "content": quote,
            "source_kind": "research",
            "quote_candidates": [{
                "claim_uid": claim_uid,
                "quote_text": quote,
            }],
        }]}

    return HermesWRRAdapter(executor)


def test_sparse_research_projection_is_provider_free_and_byte_stable(tmp_path):
    writer_calls = []

    def spy_writer(system, user):
        writer_calls.append((system, user))
        return "writer must not run"

    kwargs = {
        "run_fact_check": False,
        "provider": spy_writer,
        "mode": "auto",
        "research_provider": _validated_research_adapter(),
        "research_context": {
            "evidence_bundle_hash": "sha256:evidence",
            "canonical_id": "BVsparse",
            "platform": "bilibili",
            "created_at": "2026-07-14T00:00:00Z",
            "plan_id": "plan-sparse-research",
        },
    }
    markdown_a, report_a = generate_report.report_markdown(
        _92s_sparse_results(tmp_path), **kwargs
    )
    markdown_b, report_b = generate_report.report_markdown(
        _92s_sparse_results(tmp_path), **kwargs
    )

    assert writer_calls == []
    assert markdown_a == markdown_b
    assert "### 外部研究补充" in markdown_a
    assert "[R1]" in markdown_a
    assert report_a["research_artifacts"]["research_projection"] is not None
    assert report_a["research_artifacts"]["research_projection_records"]
    assert (
        report_a["research_artifacts"]["research_projection"].projection_semantic_hash
        == report_b["research_artifacts"]["research_projection"].projection_semantic_hash
    )


def test_sparse_no_research_baseline_is_byte_compatible(tmp_path):
    baseline, _ = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
        research_policy="off",
    )
    unavailable, _ = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
        research_provider=None,
        research_policy="auto",
    )

    assert unavailable == baseline
    assert "### 外部研究补充" not in baseline


def test_sparse_assembled_sections_appear_in_markdown(tmp_path):
    """§3/§4/§7 deterministic bodies must appear in the final Markdown."""
    markdown, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
    )
    assert report["report_plan"]["mode"] == "sparse"
    assert "## 3." in markdown
    assert "## 4." in markdown
    assert "## 7." in markdown
    # Deterministic bodies reference the evidence token
    assert "[E1]" in markdown


def test_sparse_render_has_no_debug_artifact_comment(tmp_path):
    """Sparse render must not contain the draft_markdown_preview HTML comment."""
    markdown, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
    )
    assert report["report_plan"]["mode"] == "sparse"
    assert "artifact_kind" not in markdown
    assert "draft_markdown_preview" not in markdown
    assert "publishable: false" not in markdown


# ============ Formal output preflight ============

def test_formal_sparse_writer_none_passes_preflight(tmp_path):
    """Formal path + writer=none allowed when effective mode is sparse."""
    formal = tmp_path / "B站笔记_sparse_test_20260713.md"
    _, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
    )
    assert report["report_plan"]["mode"] == "sparse"

    result = generate_report.validate_output_preflight(
        formal, "none", report_plan=report["report_plan"]
    )
    assert result is None


def test_formal_full_writer_none_fails_preflight(tmp_path):
    """Formal path + writer=none rejected when effective mode is full."""
    formal = tmp_path / "B站笔记_full_test_20260713.md"
    _, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="full",
    )
    assert report["report_plan"]["mode"] == "full"

    result = generate_report.validate_output_preflight(
        formal, "none", report_plan=report["report_plan"]
    )
    assert result is not None
    assert result["error_code"] == "FORMAL_OUTPUT_REQUIRES_WRITER"


def test_formal_auto_condensed_effective_writer_none_fails(tmp_path):
    """Auto mode that resolves to condensed must reject writer=none for formal output."""
    formal = tmp_path / "B站笔记_condensed_test_20260713.md"
    _, report = generate_report.report_markdown(
        _condensed_results(tmp_path),
        run_fact_check=False,
        mode="auto",
    )
    assert report["report_plan"]["mode"] == "condensed"

    result = generate_report.validate_output_preflight(
        formal, "none", report_plan=report["report_plan"]
    )
    assert result is not None
    assert result["error_code"] == "FORMAL_OUTPUT_REQUIRES_WRITER"


# ============ Formal publish gate ============

def test_formal_sparse_publish_gate_passes_and_returns_publishedmarkdown_gates(tmp_path):
    """Formal sparse + writer=none passes preflight and publish_markdown gate."""
    formal = tmp_path / "B站笔记_sparse_gate_20260713.md"
    markdown, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="auto",
    )
    assert report["report_plan"]["mode"] == "sparse"

    passed, summary = generate_report.check_formal_output_publishable(formal, markdown, report)

    assert passed is True, f"expected pass, failed_codes={summary.get('failed_codes')}"
    assert summary["skipped"] is False
    assert summary["passed"] is True
    assert summary["failed_codes"] == []
    # Gates come from publish_markdown (PublishedMarkdown-backed)
    assert isinstance(summary["gates"], dict)
    assert "P0_NO_SKELETON" in summary["gates"]


def test_formal_full_writer_none_publish_gate_fails(tmp_path):
    """Full mode with writer=none produces skeleton §3/§4/§7 → publish gate fails."""
    formal = tmp_path / "B站笔记_full_skeleton_20260713.md"
    markdown, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        mode="full",
        provider=None,
    )
    assert report["report_plan"]["mode"] == "full"

    passed, summary = generate_report.check_formal_output_publishable(formal, markdown, report)

    assert passed is False
    assert summary["skipped"] is False
    assert len(summary["failed_codes"]) > 0


# ============ No transcript ============

def test_no_transcript_stays_preanalysis_despite_sparse_override(tmp_path):
    """Missing transcript blocks formal report regardless of mode_override."""
    _, report = generate_report.report_markdown(
        _no_transcript_results(),
        run_fact_check=False,
        mode="sparse",
    )
    plan = report["report_plan"]
    assert plan["mode"] == "preanalysis"
    assert plan["can_generate_formal_report"] is False

    formal = tmp_path / "B站笔记_notr_20260713.md"
    result = generate_report.validate_output_preflight(
        formal, "none", report_plan=plan
    )
    assert result is not None, "preanalysis must not pass formal preflight with writer=none"
    assert result["error_code"] == "FORMAL_OUTPUT_REQUIRES_WRITER"


# ============ API backward compatibility ============

def test_report_markdown_default_mode_is_full(tmp_path):
    """Calling report_markdown without mode keeps old full-mode behavior."""
    _, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
    )
    # 92s input auto-selects sparse, but default mode='full' overrides it
    assert report["report_plan"]["mode"] == "full"


def test_report_markdown_default_full_reuses_provider_cache_3_calls(tmp_path):
    """Default mode='full' with provider: §3/§4/§7 each called once, render hits cache."""
    import run_quality_gate

    calls = []

    def counting_provider(system, user):
        calls.append((system, user))
        return run_quality_gate.fixture_writer_provider(system, user)

    generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        provider=counting_provider,
        # mode not passed → defaults to 'full'
    )

    assert len(calls) == len(set(calls)), "duplicate prompts indicate cache miss"
    assert len(calls) == 3, f"expected 3 (§3/§4/§7), got {len(calls)}"


# ============ Review Fix 1: render_draft_markdown for all modes ============

def test_full_mode_provider_renders_assembled_content_no_debug_marker(tmp_path):
    """Full mode + provider: content assembled in draft_with_qa; output has no debug artifact comment."""
    import run_quality_gate

    markdown, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        provider=run_quality_gate.fixture_writer_provider,
        mode='full',
    )

    assert report["report_plan"]["mode"] == "full"
    assert "artifact_kind" not in markdown
    assert "draft_markdown_preview" not in markdown
    assert "publishable: false" not in markdown
    assert "## 3." in markdown
    assert "## 7." in markdown


def test_full_mode_assembly_qa_exclusion_fails_closed_no_bypass(monkeypatch, tmp_path):
    """When assembly excludes §3 from draft_sections, renderer falls back to skeleton — not a second writer path."""
    import run_quality_gate

    real_assemble = generate_report.assemble_draft_report_slice

    def mocked_assemble(report, section_ids=None, **kwargs):
        draft = real_assemble(report, section_ids=section_ids, **kwargs)
        draft.draft_sections.pop('3', None)
        return draft

    monkeypatch.setattr(generate_report, 'assemble_draft_report_slice', mocked_assemble)

    markdown, report = generate_report.report_markdown(
        _92s_sparse_results(tmp_path),
        run_fact_check=False,
        provider=run_quality_gate.fixture_writer_provider,
        mode='full',
    )

    assert report["report_plan"]["mode"] == "full"
    assert "## 3." in markdown
    assert "骨架占位" in markdown, "§3 QA exclusion must fail closed to skeleton, not regenerate via second writer"
    assert "artifact_kind" not in markdown
