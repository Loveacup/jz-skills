from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from macdoctor.cli_check import _payload, check_handler, register
from macdoctor.runner import redact
from macdoctor.result import CheckResult, score_results, worst_status


def item(status, category="security", check_id="x"):
    return CheckResult(check_id, category, status, check_id, value=None, unit=None,
                       evidence="", source="fixture", duration_ms=1, recommendation=None)


def test_unknown_error_and_skip_do_not_earn_score():
    baseline = score_results([item("pass")])["security"]
    for status in ("unknown", "error", "skip"):
        assert score_results([item(status)])["security"] == 0
        assert score_results([item("pass"), item(status)])["security"] < baseline


def test_group_without_checks_is_none_not_zero():
    scores = score_results([item("pass", category="storage")])
    assert scores["storage"] == 100.0
    assert scores["security"] is None and scores["performance"] is None



def test_scoring_penalties_and_coverage_math():
    results = [item("pass"), item("warn"), item("crit"), item("unknown")]
    scores = score_results(results)
    assert scores["security"] == 70.2  # (100 + 96 + 85 + 0) / 4
    assert scores["coverage"] == 75.0


def test_worst_status_uses_severity_order():
    assert worst_status([item("pass"), item("warn"), item("crit")]) == "crit"
    assert worst_status([item("pass"), item("error"), item("unknown")]) == "error"
    assert worst_status([]) == "pass"

def test_command_line_credentials_are_redacted():
    assert redact("agent -e ANTHROPIC_API_KEY=do-not-expose") == "agent -e ANTHROPIC_API_KEY=[REDACTED]"
    assert redact("Authorization: Bearer abc.def.ghi") == "Authorization: Bearer [REDACTED]"


def test_human_table_limits_evidence_to_one_short_line(capsys):
    from macdoctor.cli_check import _render_table
    evidence = "x" * 120 + "\nsecond raw line\n"
    finding = CheckResult("table.test", "performance", "pass", "Table test", evidence=evidence)
    _render_table([finding])
    output = capsys.readouterr().out
    evidence_line = output.splitlines()[2].strip()
    assert evidence_line == "x" * 100
    assert "second raw line" not in output
    assert _payload([finding], lambda cmd, timeout=10: (0, "", ""), 2)["results"][0]["evidence"] == evidence
def validate_report(report):
    """Stdlib-only minimal contract validation (no jsonschema dependency)."""
    required = {"schema_version", "tool_version", "collected_at", "host", "results", "scores"}
    assert required <= report.keys()
    assert isinstance(report["schema_version"], str)
    assert isinstance(report["tool_version"], str)
    datetime.fromisoformat(report["collected_at"].replace("Z", "+00:00"))
    assert set(report["host"]) == {"model", "os", "arch"}
    assert all(isinstance(value, str) for value in report["host"].values())
    assert isinstance(report["results"], list)
    assert set(report["scores"]) == {"security", "performance", "storage", "coverage"}
    assert isinstance(report["scores"]["coverage"], (int, float)) and 0 <= report["scores"]["coverage"] <= 100
    assert all(score is None or (isinstance(score, (int, float)) and 0 <= score <= 100)
               for key, score in report["scores"].items() if key != "coverage")
    fields = {"id", "category", "status", "title", "value", "unit", "evidence", "source", "duration_ms", "recommendation", "collected_at"}
    for finding in report["results"]:
        assert fields <= finding.keys()
        assert finding["category"] in ("performance", "storage", "security", "hardware", "network", "devenv")
        assert finding["status"] in ("pass", "warn", "crit", "unknown", "error", "skip")
        assert isinstance(finding["id"], str) and isinstance(finding["title"], str)
        assert isinstance(finding["evidence"], str) and isinstance(finding["source"], str)
        assert isinstance(finding["duration_ms"], int) and finding["duration_ms"] >= 0
        assert finding["unit"] is None or isinstance(finding["unit"], str)
        assert finding["recommendation"] is None or isinstance(finding["recommendation"], str)
        datetime.fromisoformat(finding["collected_at"].replace("Z", "+00:00"))


def test_report_matches_minimal_schema():
    report = _payload([item("pass")], lambda cmd, timeout=10: (0, "", ""), 2)
    validate_report(report)


def test_cli_handler_emits_check_json(monkeypatch, capsys):
    import argparse
    import macdoctor.cli_check as cli
    monkeypatch.setattr(cli, "execute", lambda **kwargs: [item("pass")])
    monkeypatch.setattr(cli, "_host", lambda command, timeout: {"model": "Fixture", "os": "test", "arch": "arm64"})
    args = argparse.Namespace(command_runner=lambda cmd, timeout=10: (0, "", ""), timeout=2, category=None, id=None, json=True)
    assert check_handler(args) == 0
    validate_report(json.loads(capsys.readouterr().out))


def test_cli_registration_exposes_check_and_score():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    register(subparsers)
    assert parser.parse_args(["check", "--json", "--category", "storage", "--timeout", "2"]).func is not None
    assert parser.parse_args(["score", "--json"]).func is not None
