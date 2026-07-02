# -*- coding: utf-8 -*-
"""P3-A: release gate runner tests."""

import json
import subprocess
import sys
from pathlib import Path

import release_gate


def test_build_commands_default_is_fixture_gate_then_pytest():
    commands = release_gate.build_commands()

    assert [cmd.kind for cmd in commands] == ["quality_gate_fixture", "pytest"]
    fixture = commands[0].argv
    assert "scripts/run_quality_gate.py" in fixture
    assert "--writer-provider" in fixture
    assert "fixture" in fixture
    assert "--fail-on-fallback-warning" in fixture
    assert "--json" in fixture

    pytest_cmd = commands[1].argv
    assert pytest_cmd[:3] == [sys.executable, "-m", "pytest"]
    assert "--ignore=tests/test_asr_config.py" in pytest_cmd


def test_build_commands_real_sample_is_opt_in_and_model_backed():
    commands = release_gate.build_commands(
        real_sample=Path("/tmp/BV_sample_fetch_all.json"),
        real_writer_provider="cli",
    )

    assert [cmd.kind for cmd in commands] == [
        "quality_gate_fixture",
        "pytest",
        "quality_gate_real_sample",
    ]
    real = commands[-1].argv
    assert "/tmp/BV_sample_fetch_all.json" in real
    assert "--writer-provider" in real
    assert "cli" in real
    assert "fixture" not in real[real.index("--writer-provider") + 1:]
    assert "--fail-on-fallback-warning" in real


def test_build_commands_rejects_fixture_for_real_sample_api():
    try:
        release_gate.build_commands(
            real_sample=Path("/tmp/BV_sample_fetch_all.json"),
            real_writer_provider="fixture",
        )
    except ValueError as exc:
        assert "model-backed" in str(exc)
    else:
        raise AssertionError("fixture provider must not be accepted for real sample smoke")


def test_run_release_gate_dry_run_does_not_execute():
    commands = release_gate.build_commands(skip_pytest=True)

    summary = release_gate.run_release_gate(commands, dry_run=True)

    assert summary.passed is True
    assert summary.dry_run is True
    assert len(summary.commands) == 1
    assert summary.commands[0].returncode == 0
    assert "scripts/run_quality_gate.py" in summary.commands[0].command


def test_run_release_gate_fail_fast(monkeypatch):
    commands = release_gate.build_commands()
    calls = []

    def fake_run_command(command):
        calls.append(command.kind)
        return release_gate.CommandResult(
            name=command.name,
            kind=command.kind,
            returncode=42,
            command=command.display(),
            stdout="forced failure",
            stderr="",
        )

    monkeypatch.setattr(release_gate, "run_command", fake_run_command)

    summary = release_gate.run_release_gate(commands, dry_run=False)

    assert summary.passed is False
    assert calls == ["quality_gate_fixture"]
    assert [result.kind for result in summary.commands] == ["quality_gate_fixture"]
    assert summary.commands[0].returncode == 42


def test_release_gate_cli_dry_run_outputs_json():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/release_gate.py",
            "--dry-run",
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "release gate DRY RUN PASS" in result.stdout
    payload = result.stdout.split("RESULT_JSON_START", 1)[1].split("RESULT_JSON_END", 1)[0]
    data = json.loads(payload)
    assert data["passed"] is True
    assert data["dry_run"] is True
    assert [cmd["kind"] for cmd in data["commands"]] == ["quality_gate_fixture", "pytest"]
