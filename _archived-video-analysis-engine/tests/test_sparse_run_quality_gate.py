# -*- coding: utf-8 -*-
"""Slice C3b: run_quality_gate requested/effective mode wiring tests.

Covers:
  1. auto sparse passes publishable gate; summary has mode/requested_mode/effective_mode;
     P0_SPARSE_REPORT_FIDELITY passes; output concise/non-skeleton.
  2. Monkeypatch spy: auto sparse calls fixture provider zero times.
  3. Explicit mode='full' on p2e fixture: requested/effective both full,
     fixture provider called exactly 3 times, existing gates pass.
  4. Explicit mode='sparse' forces sparse for transcript-bearing input;
     no-transcript input stays preanalysis/effective preanalysis and fails
     formal quality.
  5. CLI --mode auto --json accepts and emits requested/effective fields.
  6. run_corpus_manifest(mode='auto', execute=True) propagates effective sparse
     in sample_summary.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import run_quality_gate

REPO_ROOT = Path(__file__).resolve().parents[1]
P2E_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "p2e_fetch_all.json"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _make_sparse_fetch_all(tmp_path: Path) -> str:
    """92-second sparse fixture: 2 subtitle segments, no danmaku/comments."""
    subtitle_body = [
        {
            "from": 8.0,
            "content": "长征十号乙运载火箭今日成功完成首飞，发动机推力达到1200吨，采用一子级可回收技术。",
            "to": 20.0,
        },
        {
            "from": 55.0,
            "content": "火箭一子级成功回收，精确降落在预定回收平台，标志着新一代运载火箭研发取得重大突破。",
            "to": 68.0,
        },
    ]
    subtitle_file = tmp_path / "changzheng_subtitle.json"
    subtitle_file.write_text(
        json.dumps({"body": subtitle_body}, ensure_ascii=False), encoding="utf-8"
    )
    results = {
        "bvid": "BVsparseChangzheng01",
        "title": "长征十号乙运载火箭发射回收全程记录",
        "author": "航天爱好者",
        "description": "记录长征十号乙运载火箭发射全过程，包括一子级成功回收的历史时刻。",
        "duration": 92,
        "subtitle": {
            "method": "fixture-asr",
            "json_path": str(subtitle_file),
            "language": "zh-Hans",
            "parts": 1,
            "total_parts": 1,
            "failed_parts": [],
        },
        "comments": None,
        "danmaku": None,
        "cross_platform": None,
    }
    fetch_all_file = tmp_path / "changzheng_fetch_all.json"
    fetch_all_file.write_text(
        json.dumps(results, ensure_ascii=False), encoding="utf-8"
    )
    return str(fetch_all_file)


def _make_no_transcript_fetch_all(tmp_path: Path) -> str:
    """92-second fixture with no subtitle — triggers preanalysis."""
    results = {
        "bvid": "BVnoTranscriptTest",
        "title": "无字幕短视频",
        "author": "test",
        "description": "test",
        "duration": 92,
        "subtitle": None,
        "comments": None,
        "danmaku": None,
        "cross_platform": None,
    }
    fetch_all_file = tmp_path / "no_transcript_fetch_all.json"
    fetch_all_file.write_text(
        json.dumps(results, ensure_ascii=False), encoding="utf-8"
    )
    return str(fetch_all_file)


def _write_corpus_manifest(tmp_path: Path, samples: list) -> Path:
    manifest = {
        "schema_version": 1,
        "name": "sparse-c3b-test",
        "created_at": "2026-07-13",
        "execution_policy": {
            "default_execute": False,
            "requires_execute_flag": True,
            "auto_download_allowed": False,
            "auto_llm_allowed": False,
        },
        "samples": samples,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def _corpus_sample(sid, bvid, input_path, status="candidate"):
    return {
        "id": sid,
        "bvid": bvid,
        "category": "航天",
        "source_note": {
            "type": "test",
            "path": "",
            "title": "",
            "evidence_status": "candidate_extracted_from_existing_notes",
        },
        "input": {
            "fetch_all_json_path": input_path,
            "cache_status": "present",
            "collected_at": None,
            "collector_command": None,
        },
        "run": {
            "last_run_at": None,
            "writer_provider": None,
            "output_path": None,
            "summary_json_path": None,
            "publishable_passed": None,
            "failed_codes": [],
        },
        "rubric": {
            "status": status,
            "reviewed_by": None,
            "reviewed_at": None,
            "verdict_source": None,
        },
    }


# ---------------------------------------------------------------------------
# Test 1: auto sparse passes publishable gate; summary fields correct
# ---------------------------------------------------------------------------

def test_auto_sparse_passes_publishable_gate(tmp_path):
    input_path = _make_sparse_fetch_all(tmp_path)
    out = tmp_path / "sparse_report.md"

    passed, summary = run_quality_gate.run_quality_gate(
        input_path,
        str(out),
        writer_provider="fixture",
        mode="auto",
        publishable_gate=True,
    )

    # Mode summary fields
    assert summary["mode"] == "auto", "mode field must equal requested mode for backward compat"
    assert summary["requested_mode"] == "auto"
    assert summary["effective_mode"] == "sparse"

    # Core quality gate
    assert summary["verify_passed"] is True, f"verify gates: {summary['verify_gates']}"
    assert summary["coherence_passed"] is True

    # Publishable gate
    assert summary["publishable_passed"] is True, (
        f"publishable gate failed: {summary['publishable_failed_codes']}\n"
        f"gates: {json.dumps(summary['publishable_gates'], ensure_ascii=False, indent=2)}"
    )
    gates = summary["publishable_gates"] or {}
    p0_fidelity = gates.get("P0_SPARSE_REPORT_FIDELITY")
    assert p0_fidelity is not None, "P0_SPARSE_REPORT_FIDELITY gate must be present for sparse"
    assert p0_fidelity["pass"] is True, f"P0_SPARSE_REPORT_FIDELITY failed: {p0_fidelity}"

    # Output is evidence-based, not skeleton
    md = out.read_text(encoding="utf-8")
    assert "_骨架占位" not in md, "sparse output must not contain skeleton placeholder"
    assert "长征" in md or "火箭" in md, "sparse output must include evidence-based content"
    assert passed is True


# ---------------------------------------------------------------------------
# Test 2: auto sparse calls fixture provider zero times
# ---------------------------------------------------------------------------

def test_auto_sparse_calls_provider_zero_times(tmp_path, monkeypatch):
    input_path = _make_sparse_fetch_all(tmp_path)
    out = tmp_path / "sparse_report_spy.md"

    call_count = [0]
    original = run_quality_gate.fixture_writer_provider

    def spy_provider(system, user):
        call_count[0] += 1
        return original(system, user)

    monkeypatch.setattr(run_quality_gate, "fixture_writer_provider", spy_provider)

    passed, summary = run_quality_gate.run_quality_gate(
        input_path,
        str(out),
        writer_provider="fixture",
        mode="auto",
    )

    assert summary["effective_mode"] == "sparse"
    assert call_count[0] == 0, (
        f"auto sparse must not call fixture provider; called {call_count[0]} time(s)"
    )


# ---------------------------------------------------------------------------
# Test 3: explicit full on p2e fixture: requested/effective full, 3 provider calls
# ---------------------------------------------------------------------------

def test_explicit_full_on_p2e_fixture_calls_provider_three_times(tmp_path, monkeypatch):
    out = tmp_path / "p2e_full_report.md"

    call_count = [0]
    original = run_quality_gate.fixture_writer_provider

    def spy_provider(system, user):
        call_count[0] += 1
        return original(system, user)

    monkeypatch.setattr(run_quality_gate, "fixture_writer_provider", spy_provider)

    passed, summary = run_quality_gate.run_quality_gate(
        str(P2E_FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
    )

    assert summary["requested_mode"] == "full"
    assert summary["effective_mode"] == "full"
    assert summary["verify_passed"] is True, f"full verify gates: {summary['verify_gates']}"
    assert summary["coherence_passed"] is True
    assert passed is True

    # Fixture provider called exactly once per LLM section: §3, §4, §7
    assert call_count[0] == 3, (
        f"expected fixture provider called 3 times for §3/§4/§7; got {call_count[0]}"
    )

    md = out.read_text(encoding="utf-8")
    assert "### 💡 洞察 1" in md
    assert "### 模块 1" in md
    assert "### 独特价值" in md


# ---------------------------------------------------------------------------
# Test 4: explicit sparse override; no-transcript stays preanalysis
# ---------------------------------------------------------------------------

def test_explicit_sparse_forces_sparse_for_transcript_input(tmp_path):
    """mode='sparse' on a transcript-bearing 92s input → effective_mode='sparse'."""
    input_path = _make_sparse_fetch_all(tmp_path)
    out = tmp_path / "explicit_sparse_report.md"

    passed, summary = run_quality_gate.run_quality_gate(
        input_path,
        str(out),
        writer_provider="fixture",
        mode="sparse",
    )

    assert summary["requested_mode"] == "sparse"
    assert summary["effective_mode"] == "sparse"
    assert summary["verify_passed"] is True


def test_no_transcript_stays_preanalysis_regardless_of_mode_override(tmp_path):
    """mode='sparse' with no transcript → effective_mode='preanalysis', verify fails."""
    input_path = _make_no_transcript_fetch_all(tmp_path)
    out = tmp_path / "preanalysis_report.md"

    passed, summary = run_quality_gate.run_quality_gate(
        input_path,
        str(out),
        writer_provider="fixture",
        mode="sparse",
    )

    assert summary["requested_mode"] == "sparse"
    assert summary["effective_mode"] == "preanalysis"
    # Preanalysis report lacks §3/§4/§7 → fails formal full thresholds
    assert summary["verify_passed"] is False, (
        "preanalysis report must fail formal quality gate (no §3/§4/§7)"
    )
    assert passed is False


# ---------------------------------------------------------------------------
# Test 5: CLI --mode auto --json emits requested/effective fields
# ---------------------------------------------------------------------------

def test_cli_mode_auto_emits_requested_effective_fields(tmp_path):
    input_path = _make_sparse_fetch_all(tmp_path)
    out = tmp_path / "cli_auto_report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_quality_gate.py",
            "--input", input_path,
            "--output", str(out),
            "--writer-provider", "fixture",
            "--mode", "auto",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"CLI --mode auto should exit 0 for sparse fixture\n"
        f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-1000:]}"
    )

    # Extract JSON payload
    stdout = result.stdout
    start = stdout.find("RESULT_JSON_START")
    end = stdout.find("RESULT_JSON_END")
    assert start != -1 and end != -1, "RESULT_JSON_START/END markers expected in stdout"
    payload = json.loads(stdout[start + len("RESULT_JSON_START"):end].strip())

    assert payload["requested_mode"] == "auto"
    assert payload["effective_mode"] == "sparse"
    assert payload["mode"] == "auto"


# ---------------------------------------------------------------------------
# Test 6: corpus manifest mode='auto' propagates effective sparse in sample_summary
# ---------------------------------------------------------------------------

def test_corpus_manifest_mode_auto_propagates_effective_sparse(tmp_path):
    input_path = _make_sparse_fetch_all(tmp_path)
    sample = _corpus_sample("sparse-c3b-01", "BVsparseChangzheng01", input_path)
    manifest_path = _write_corpus_manifest(tmp_path, [sample])

    summary = run_quality_gate.run_corpus_manifest(
        str(manifest_path),
        lane="candidates",
        execute=True,
        writer_provider="fixture",
        mode="auto",
        output_dir=str(tmp_path / "out"),
    )

    assert summary["executed"] is True
    assert len(summary["results"]) == 1
    res = summary["results"][0]
    assert res["executed"] is True, f"sample execution failed: {res.get('error')}"
    assert res["passed"] is True, f"sparse gate failed: {res['summary']}"

    sample_summary = res["summary"]
    assert sample_summary["requested_mode"] == "auto"
    assert sample_summary["effective_mode"] == "sparse"
    assert sample_summary["mode"] == "auto"


# ---------------------------------------------------------------------------
# Review Fix 1 regression tests: assembly seam + fallback signals
# ---------------------------------------------------------------------------

def test_vae_monkeypatch_seam_injects_blocker_via_section_qa_gate(tmp_path, monkeypatch):
    """Fix A regression: monkeypatching video_analysis_engine.assemble_draft_report_slice
    must reach report_markdown via the dynamic wrapper."""
    import video_analysis_engine

    original_assemble = video_analysis_engine.assemble_draft_report_slice

    def fake_assemble_with_blocker(report, section_ids=("1", "5"), provider=None,
                                   claim_qa_gate=False, depth_profile="v24-full"):
        draft = original_assemble(report, section_ids=section_ids, provider=provider,
                                  claim_qa_gate=claim_qa_gate, depth_profile=depth_profile)
        if draft.qa_results.get("3"):
            draft.qa_results["3"].blockers.append("D5 no-skeleton: injected-blocker")
            draft.qa_results["3"].overall_passed = False
        return draft

    monkeypatch.setattr(video_analysis_engine, "assemble_draft_report_slice", fake_assemble_with_blocker)

    out = tmp_path / "blocker_report.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(P2E_FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        section_qa_gate=True,
    )

    assert summary["section_qa_gate"] is True
    assert summary["section_qa_gate_passed"] is False, (
        "injected §3 blocker must cause section_qa_gate_passed=False"
    )
    blockers_3 = (summary.get("section_qa") or {}).get("3", {}).get("blockers", [])
    assert any("injected-blocker" in b for b in blockers_3), (
        f"injected blocker must appear in section_qa §3; got {blockers_3}"
    )
    assert passed is False


def test_bad_provider_fallback_warning_detected_via_draft_warnings(tmp_path, monkeypatch):
    """Fix B regression: writer validation failure in assembly path must surface
    as fallback_warning so fail_on_fallback_warning=True fails the gate."""

    def bad_fixture_provider(system, user):
        return "这段输出没有合法小节格式，也没有证据引用。"

    monkeypatch.setattr(run_quality_gate, "fixture_writer_provider", bad_fixture_provider)

    out = tmp_path / "bad_provider_report.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(P2E_FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        fail_on_fallback_warning=True,
    )

    assert summary["fallback_warning_count"] >= 1, (
        f"expected ≥1 fallback warning; warnings={summary['warnings']}"
    )
    assert summary["failed_due_to_fallback_warning"] is True
    assert any("falling back to skeleton" in msg for msg in summary["fallback_warnings"]), (
        f"fallback_warnings must contain 'falling back to skeleton'; got {summary['fallback_warnings']}"
    )
    assert passed is False


def test_auto_sparse_has_no_fallback_warnings(tmp_path):
    """Fix B regression: auto sparse must not generate any writer fallback warnings."""
    input_path = _make_sparse_fetch_all(tmp_path)
    out = tmp_path / "sparse_no_fallback.md"

    passed, summary = run_quality_gate.run_quality_gate(
        input_path,
        str(out),
        writer_provider="fixture",
        mode="auto",
    )

    assert summary["effective_mode"] == "sparse"
    assert summary["fallback_warning_count"] == 0, (
        f"auto sparse must have zero fallback warnings; got {summary['fallback_warnings']}"
    )
    assert not summary["fallback_warnings"]
