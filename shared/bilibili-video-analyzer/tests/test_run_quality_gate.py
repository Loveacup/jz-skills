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
