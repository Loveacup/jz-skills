# -*- coding: utf-8 -*-
"""P3-A: release gate runner tests."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import release_gate


def test_build_commands_default_is_full_fixture_sparse_fixture_pytest():
    commands = release_gate.build_commands()

    assert [cmd.kind for cmd in commands] == [
        "quality_gate_fixture",
        "quality_gate_sparse_fixture",
        "pytest",
    ]

    # full fixture lane
    full = commands[0].argv
    assert "scripts/run_quality_gate.py" in full
    assert "--writer-provider" in full
    assert full[full.index("--writer-provider") + 1] == "fixture"
    assert full[full.index("--mode") + 1] == "full"
    assert "--fail-on-fallback-warning" in full
    assert "--publishable" in full
    assert "--section-qa-gate" in full
    assert full[full.index("--depth-profile") + 1] == "claim-first-full"
    assert "--claim-qa-gate" in full
    assert "--json" in full

    # sparse fixture lane
    sparse = commands[1].argv
    assert "scripts/run_quality_gate.py" in sparse
    assert sparse[sparse.index("--writer-provider") + 1] == "none"
    assert sparse[sparse.index("--mode") + 1] == "sparse"
    assert "--publishable" in sparse
    assert "--section-qa-gate" in sparse
    assert sparse[sparse.index("--depth-profile") + 1] == "standard"
    assert "--json" in sparse
    assert "--claim-qa-gate" not in sparse
    assert "--fail-on-fallback-warning" not in sparse
    # same input fixture as full lane
    assert str(release_gate.DEFAULT_FIXTURE) in sparse

    # pytest
    pytest_cmd = commands[2].argv
    assert pytest_cmd[:3] == [sys.executable, "-m", "pytest"]
    assert "--ignore=tests/test_asr_config.py" in pytest_cmd


_RESEARCH_FLAGS = (
    "--research-provider",
    "--research-context",
    "--research-fixture",
    "--research-archive-dir",
    "--allow-network-research",
)


def test_full_fixture_lane_appends_offline_research_flags():
    """S8-B: the full fixture lane must exercise the offline research fixture lane."""
    commands = release_gate.build_commands()
    full = commands[0].argv

    assert full[full.index("--research-provider") + 1] == "fixture"
    assert full[full.index("--research-context") + 1] == str(release_gate.DEFAULT_RESEARCH_CONTEXT)
    assert full[full.index("--research-fixture") + 1] == str(release_gate.DEFAULT_RESEARCH_FIXTURE)
    assert full[full.index("--research-archive-dir") + 1] == str(release_gate.DEFAULT_RESEARCH_ARCHIVE_DIR)

    # Deterministic archive under /tmp, never inside the repo (would leak private raw sources).
    assert str(release_gate.DEFAULT_RESEARCH_ARCHIVE_DIR) == "/tmp/video-analysis-engine-release-gate/research"
    assert str(release_gate.DEFAULT_RESEARCH_CONTEXT) == "tests/fixtures/research/release_context.json"
    assert str(release_gate.DEFAULT_RESEARCH_FIXTURE) == "tests/fixtures/research/release_fixture.json"


def test_sparse_lane_has_no_research_or_network_flags():
    """The sparse lane stays fully offline and model-free: no research/network flags."""
    commands = release_gate.build_commands()
    sparse = commands[1].argv
    for flag in _RESEARCH_FLAGS:
        assert flag not in sparse, f"sparse lane must not contain {flag}"


def test_dry_run_does_not_create_research_archive_dir():
    """Building/printing the plan must never touch the deterministic archive directory."""
    archive_root = release_gate.DEFAULT_RESEARCH_ARCHIVE_DIR.parent
    if archive_root.exists():
        shutil.rmtree(archive_root)

    commands = release_gate.build_commands(skip_pytest=True)
    summary = release_gate.run_release_gate(commands, dry_run=True)

    assert summary.dry_run is True
    assert not release_gate.DEFAULT_RESEARCH_ARCHIVE_DIR.exists()
    assert not archive_root.exists()


def test_build_commands_skip_pytest_returns_both_deterministic_lanes():
    commands = release_gate.build_commands(skip_pytest=True)

    assert [cmd.kind for cmd in commands] == [
        "quality_gate_fixture",
        "quality_gate_sparse_fixture",
    ]


def test_build_commands_real_sample_is_opt_in_and_model_backed():
    commands = release_gate.build_commands(
        real_sample=Path("/tmp/BV_sample_fetch_all.json"),
        real_writer_provider="cli",
    )

    assert [cmd.kind for cmd in commands] == [
        "quality_gate_fixture",
        "quality_gate_sparse_fixture",
        "pytest",
        "quality_gate_real_sample",
    ]
    real = commands[-1].argv
    assert "/tmp/BV_sample_fetch_all.json" in real
    assert real[real.index("--writer-provider") + 1] == "cli"
    assert real[real.index("--mode") + 1] == "auto"
    assert "--fail-on-fallback-warning" in real
    assert "--publishable" in real
    assert "--section-qa-gate" in real
    assert real[real.index("--depth-profile") + 1] == "claim-first-full"
    assert "--claim-qa-gate" in real


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
    # skip_pytest keeps both deterministic lanes
    assert len(summary.commands) == 2
    assert summary.commands[0].returncode == 0
    assert summary.commands[1].returncode == 0
    assert "scripts/run_quality_gate.py" in summary.commands[0].command
    assert "scripts/run_quality_gate.py" in summary.commands[1].command


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
    # fail-fast stops at first failure (full fixture)
    assert calls == ["quality_gate_fixture"]
    assert [result.kind for result in summary.commands] == ["quality_gate_fixture"]
    assert summary.commands[0].returncode == 42


def test_run_release_gate_fail_fast_at_sparse(monkeypatch):
    commands = release_gate.build_commands()
    calls = []

    def fake_run_command(command):
        calls.append(command.kind)
        rc = 0 if command.kind == "quality_gate_fixture" else 42
        return release_gate.CommandResult(
            name=command.name,
            kind=command.kind,
            returncode=rc,
            command=command.display(),
            stdout="forced failure" if rc else "",
            stderr="",
        )

    monkeypatch.setattr(release_gate, "run_command", fake_run_command)

    summary = release_gate.run_release_gate(commands, dry_run=False)

    assert summary.passed is False
    assert calls == ["quality_gate_fixture", "quality_gate_sparse_fixture"]
    assert [r.kind for r in summary.commands] == [
        "quality_gate_fixture",
        "quality_gate_sparse_fixture",
    ]


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
    assert [cmd["kind"] for cmd in data["commands"]] == [
        "quality_gate_fixture",
        "quality_gate_sparse_fixture",
        "pytest",
    ]
