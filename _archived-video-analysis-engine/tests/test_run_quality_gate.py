# -*- coding: utf-8 -*-
"""P2-E: one-command report quality gate regression tests."""

import json
import subprocess
import sys
from pathlib import Path

import run_quality_gate


FIXTURE = Path("tests/fixtures/p2e_fetch_all.json")


def test_fixture_quality_provider_runs_full_pipeline(tmp_path):
    out = tmp_path / "p2e_report.md"

    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
    )

    assert passed is True
    assert out.exists()
    assert summary["verify_passed"] is True
    assert summary["coherence_passed"] is True
    assert summary["verify_gates"]["G3"]["pass"] is True
    assert summary["verify_gates"]["G4"]["pass"] is True
    assert summary["verify_gates"]["G5"]["pass"] is True
    assert summary["verify_gates"]["G7"]["pass"] is True
    assert summary["fallback_warning_count"] == 0

    md = out.read_text(encoding="utf-8")
    assert "### 💡 洞察 1" in md
    assert "### 模块 1" in md
    assert "### 独特价值" in md
    assert "## P1" not in md
    assert "后来发生了什么？" not in md


def test_quality_gate_cli_outputs_json_and_exit_zero(tmp_path):
    out = tmp_path / "cli_report.md"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_quality_gate.py",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--writer-provider",
            "fixture",
            "--fail-on-fallback-warning",
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "quality gate PASS" in result.stdout
    assert out.exists()
    payload = result.stdout.split("RESULT_JSON_START", 1)[1].split("RESULT_JSON_END", 1)[0]
    data = json.loads(payload)
    assert data["passed"] is True
    assert data["verify_passed"] is True
    assert data["coherence_passed"] is True
    assert data["fail_on_fallback_warning"] is True
    assert data["fallback_warning_count"] == 0


def test_quality_gate_none_provider_fails_full_gates(tmp_path):
    out = tmp_path / "none_report.md"

    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="none",
        mode="full",
        run_fact_check=False,
    )

    assert passed is False
    assert summary["verify_passed"] is False or summary["coherence_passed"] is False


def test_quality_gate_can_fail_on_writer_fallback_warning(monkeypatch, tmp_path):
    """真实样片 smoke 可要求 LLM writer fallback warning 直接失败。"""
    out = tmp_path / "fallback_report.md"

    def bad_fixture_provider(system, user):
        return "这段输出没有合法小节格式，也没有证据引用。"

    monkeypatch.setattr(run_quality_gate, "fixture_writer_provider", bad_fixture_provider)

    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        fail_on_fallback_warning=True,
    )

    assert passed is False
    assert summary["fallback_warning_count"] >= 1
    assert summary["failed_due_to_fallback_warning"] is True
    assert any("falling back to skeleton" in msg for msg in summary["fallback_warnings"])


def test_quality_gate_can_run_publishable_gate_as_stricter_layer(tmp_path):
    """Publish gate is opt-in and stricter than engineering structure gates."""
    out = tmp_path / "fixture_publish_report.md"

    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        fail_on_fallback_warning=True,
        publishable_gate=True,
    )

    assert passed is True
    assert summary["verify_passed"] is True
    assert summary["coherence_passed"] is True
    assert summary["publishable_passed"] is True
    assert summary["publishable_failed_codes"] == []


def test_fixture_passes_claim_first_blocking_profile(tmp_path):
    out = tmp_path / "strict_claim_first_report.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        fail_on_fallback_warning=True,
        publishable_gate=True,
        section_qa_gate=True,
        depth_profile="claim-first-full",
        claim_qa_gate=True,
    )
    assert passed is True
    assert summary["publishable_passed"] is True
    assert summary["section_qa_gate_passed"] is True
    assert summary["claim_qa_gate_passed"] is True


def test_publishable_quality_gate_passes_report_to_p6_report_level_gates(tmp_path, monkeypatch):
    out = tmp_path / "report_aware_publishable.md"
    markdown = "# test markdown"
    report = {
        "claim_bundle": {"evidence_contract_version": 1, "claims": []},
        "evidence_map": {"by_section": {}},
    }
    captured = {}

    monkeypatch.setattr(run_quality_gate.generate_report, "report_markdown", lambda *_args, **_kwargs: (markdown, report))
    monkeypatch.setattr(run_quality_gate.verify_report, "evaluate", lambda *_args: ({"G1": {"pass": True}}, True))
    monkeypatch.setattr(
        run_quality_gate,
        "check_report_coherence",
        lambda _markdown: type("Coherence", (), {"passed": True, "issues": []})(),
    )
    monkeypatch.setattr(run_quality_gate.verify_publishable_report, "evaluate", lambda _markdown: ({"P0_MARKDOWN": {"pass": True}}, True))

    def fake_report_aware(markdown_arg, report_arg):
        captured["markdown"] = markdown_arg
        captured["report"] = report_arg
        return {"P0_CLAIM_EVIDENCE_SCORE": {"pass": False, "reason": "missing"}}, False

    monkeypatch.setattr(run_quality_gate.verify_publishable_report, "evaluate_publishable_report", fake_report_aware)

    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE), str(out), writer_provider="fixture", publishable_gate=True,
    )

    assert passed is False
    assert captured == {"markdown": markdown, "report": report}
    assert summary["publishable_failed_codes"] == ["P0_CLAIM_EVIDENCE_SCORE"]


def test_quality_gate_summary_includes_section_qa_metadata(tmp_path):
    """Phase 3: run_quality_gate() summary 包含 section_qa JSON-able 元数据。"""
    import json

    out = tmp_path / "qa_meta_report.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
    )

    # section_qa 字段存在且可序列化
    assert "section_qa" in summary
    section_qa = summary["section_qa"]
    assert isinstance(section_qa, dict)
    json.dumps(section_qa)  # 验证 JSON 可序列化

    # 至少包含 §1 的 QA 结果（§5 也应存在，但 fixture provider 只写 §3/§4/§7）
    assert len(section_qa) > 0

    # 每个 section QA 包含必需字段
    for sid, qa in section_qa.items():
        assert "overall_passed" in qa
        assert "blockers" in qa
        assert "critical_issues" in qa
        assert "improvements" in qa
        assert "word_count" in qa
        assert "evidence_refs_count" in qa
        assert "time_anchor_count" in qa

    # passed 仍由 verify/coherence/publishable 控制，不受 section_qa 影响
    assert summary["passed"] is True
    assert summary["verify_passed"] is True
    assert summary["coherence_passed"] is True


# ========== Phase 4: --section-qa-gate flag ==========
def test_section_qa_gate_disabled_keeps_existing_behavior(tmp_path, monkeypatch):
    """section_qa_gate=False（默认）时，即使有 blockers 也不影响 passed 计算。"""
    import video_analysis_engine

    # 保存原始函数
    original_assemble = video_analysis_engine.assemble_draft_report_slice

    # 伪造一个 section_qa 包含 blocker
    def fake_assemble_with_blocker(report, section_ids=("1", "5"), provider=None, claim_qa_gate=False, depth_profile="standard"):
        # 调用真实函数获取报告
        draft = original_assemble(report, section_ids, provider, claim_qa_gate, depth_profile)
        # 注入一个假的 blocker 到 §3
        if draft.qa_results.get("3"):
            draft.qa_results["3"].blockers.append("FAKE_BLOCKER_FOR_TEST")
        return draft

    monkeypatch.setattr(video_analysis_engine, "assemble_draft_report_slice", fake_assemble_with_blocker)

    out = tmp_path / "qa_gate_disabled.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        section_qa_gate=False,  # Phase 4: 显式关闭 section QA gate
    )

    # passed 仍由 verify/coherence/publishable 控制，不受 section_qa blocker 影响
    assert summary["verify_passed"] is True
    assert summary["coherence_passed"] is True
    assert summary["section_qa_gate"] is False
    assert "section_qa_gate_passed" in summary
    # 当 gate 关闭时，passed 不受 section_qa 影响
    assert summary["passed"] == (
        summary["verify_passed"]
        and summary["coherence_passed"]
        and not summary.get("failed_due_to_fallback_warning", False)
        and not summary.get("failed_due_to_publishable_gate", False)
    )


def test_section_qa_gate_enabled_fails_on_p0_blockers(tmp_path, monkeypatch):
    """section_qa_gate=True 时，任何 blocker 导致 section_qa_gate_passed=False，最终 passed=False。"""
    import video_analysis_engine

    # 保存原始函数
    original_assemble = video_analysis_engine.assemble_draft_report_slice

    # 伪造一个包含 blocker 的 section_qa
    def fake_assemble_with_blocker(report, section_ids=("1", "5"), provider=None, claim_qa_gate=False, depth_profile="standard"):
        draft = original_assemble(report, section_ids, provider, claim_qa_gate, depth_profile)
        # 注入 blocker 到 §3
        if draft.qa_results.get("3"):
            draft.qa_results["3"].blockers.append("D5 no-skeleton: 骨架占位: ['_骨架占位']")
            draft.qa_results["3"].overall_passed = False
        return draft

    monkeypatch.setattr(video_analysis_engine, "assemble_draft_report_slice", fake_assemble_with_blocker)

    out = tmp_path / "qa_gate_enabled_fail.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        section_qa_gate=True,  # Phase 4: 开启 section QA gate
    )

    assert summary["section_qa_gate"] is True
    assert summary["section_qa_gate_passed"] is False  # 有 blocker
    assert summary["failed_due_to_section_qa_gate"] is True
    # verify/coherence 可能都通过，但 section_qa_gate 失败导致整体 passed=False
    assert summary["passed"] is False


def test_section_qa_gate_enabled_passes_without_blockers(tmp_path):
    """section_qa_gate=True 时，正常 fixture 无 P0 blocker，应通过。"""
    out = tmp_path / "qa_gate_enabled_pass.md"
    passed, summary = run_quality_gate.run_quality_gate(
        str(FIXTURE),
        str(out),
        writer_provider="fixture",
        mode="full",
        run_fact_check=False,
        section_qa_gate=True,  # Phase 4: 开启 section QA gate
    )

    assert summary["section_qa_gate"] is True
    assert summary["section_qa_gate_passed"] is True
    assert summary["failed_due_to_section_qa_gate"] is False
    assert summary["passed"] is True
    assert all(not qa.get("blockers") for qa in summary["section_qa"].values())
