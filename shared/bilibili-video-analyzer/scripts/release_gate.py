#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release gate runner for bilibili-video-analyzer.

P3-A: one stable entry point for pre-release validation.

Default mode is intentionally cheap and deterministic:
  1. run_quality_gate.py with fixture provider and fallback guard
  2. pytest excluding tests/test_asr_config.py

Real sample smoke is opt-in via --real-sample because it may call a model-backed
writer provider and spend time/tokens.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_FIXTURE = Path("tests/fixtures/p2e_fetch_all.json")
DEFAULT_OUTPUT = Path("/tmp/bili_release_gate_fixture_report.md")


@dataclass
class GateCommand:
    name: str
    argv: List[str]
    kind: str

    def display(self) -> str:
        return " ".join(_quote_arg(arg) for arg in self.argv)


@dataclass
class CommandResult:
    name: str
    kind: str
    returncode: int
    command: str
    stdout: str = ""
    stderr: str = ""


@dataclass
class ReleaseGateSummary:
    passed: bool
    dry_run: bool
    commands: List[CommandResult]


def _quote_arg(arg: str) -> str:
    if not arg:
        return "''"
    if any(ch.isspace() or ch in "'\"$`\\" for ch in arg):
        return "'" + arg.replace("'", "'\\''") + "'"
    return arg


def build_commands(
    *,
    fixture_input: Path = DEFAULT_FIXTURE,
    fixture_output: Path = DEFAULT_OUTPUT,
    real_sample: Optional[Path] = None,
    real_output: Optional[Path] = None,
    real_writer_provider: str = "cli",
    skip_pytest: bool = False,
) -> List[GateCommand]:
    """Build the ordered release-gate command list."""
    if real_sample and real_writer_provider not in {"cli", "deepseek"}:
        raise ValueError("real sample writer provider must be model-backed: cli or deepseek")

    py = sys.executable
    commands = [
        GateCommand(
            name="fixture quality gate",
            kind="quality_gate_fixture",
            argv=[
                py,
                "scripts/run_quality_gate.py",
                "--input",
                str(fixture_input),
                "--output",
                str(fixture_output),
                "--writer-provider",
                "fixture",
                "--fail-on-fallback-warning",
                "--json",
            ],
        )
    ]

    if not skip_pytest:
        commands.append(
            GateCommand(
                name="pytest full suite excluding ASR config",
                kind="pytest",
                argv=[
                    py,
                    "-m",
                    "pytest",
                    "-q",
                    "tests",
                    "--ignore=tests/test_asr_config.py",
                ],
            )
        )

    if real_sample:
        if real_output is None:
            stem = real_sample.stem.replace("_fetch_all", "")
            real_output = Path(f"/tmp/{stem}_real_sample_gate_report.md")
        commands.append(
            GateCommand(
                name="real sample quality gate",
                kind="quality_gate_real_sample",
                argv=[
                    py,
                    "scripts/run_quality_gate.py",
                    "--input",
                    str(real_sample),
                    "--output",
                    str(real_output),
                    "--writer-provider",
                    real_writer_provider,
                    "--fail-on-fallback-warning",
                    "--json",
                ],
            )
        )

    return commands


def run_command(command: GateCommand) -> CommandResult:
    env = os.environ.copy()
    scripts_path = str(SCRIPT_DIR)
    old_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = scripts_path if not old_pythonpath else f"{scripts_path}{os.pathsep}{old_pythonpath}"
    proc = subprocess.run(
        command.argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        name=command.name,
        kind=command.kind,
        returncode=proc.returncode,
        command=command.display(),
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_release_gate(commands: List[GateCommand], *, dry_run: bool = False) -> ReleaseGateSummary:
    results: List[CommandResult] = []
    if dry_run:
        for command in commands:
            results.append(
                CommandResult(
                    name=command.name,
                    kind=command.kind,
                    returncode=0,
                    command=command.display(),
                )
            )
        return ReleaseGateSummary(passed=True, dry_run=True, commands=results)

    for command in commands:
        result = run_command(command)
        results.append(result)
        if result.returncode != 0:
            return ReleaseGateSummary(passed=False, dry_run=False, commands=results)
    return ReleaseGateSummary(passed=True, dry_run=False, commands=results)


def print_summary(summary: ReleaseGateSummary, *, as_json: bool = False) -> None:
    mark = "✅" if summary.passed else "❌"
    mode = "DRY RUN" if summary.dry_run else "RUN"
    print(f"{mark} release gate {mode} {'PASS' if summary.passed else 'FAIL'}")
    for result in summary.commands:
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"\n[{status}] {result.name}")
        print(f"  kind   : {result.kind}")
        print(f"  command: {result.command}")
        print(f"  exit   : {result.returncode}")
        if result.stdout:
            print("  stdout:")
            print(_indent(result.stdout.rstrip()))
        if result.stderr:
            print("  stderr:")
            print(_indent(result.stderr.rstrip()))

    if as_json:
        print("\nRESULT_JSON_START")
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.splitlines())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bilibili-video-analyzer release gates.")
    parser.add_argument(
        "--fixture-input",
        default=str(DEFAULT_FIXTURE),
        help="Deterministic fetch_all fixture for the cheap gate.",
    )
    parser.add_argument(
        "--fixture-output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the deterministic fixture report.",
    )
    parser.add_argument(
        "--real-sample",
        help="Optional real fetch_all JSON path; enables model-backed real sample smoke.",
    )
    parser.add_argument(
        "--real-output",
        help="Optional output path for the real sample report.",
    )
    parser.add_argument(
        "--real-writer-provider",
        choices=("cli", "deepseek"),
        default="cli",
        help="Writer provider for --real-sample. Keep model-backed; fixture is intentionally not allowed here.",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip pytest. Intended only for local debugging; release usage should not set this.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the command plan without executing.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    commands = build_commands(
        fixture_input=Path(args.fixture_input),
        fixture_output=Path(args.fixture_output),
        real_sample=Path(args.real_sample) if args.real_sample else None,
        real_output=Path(args.real_output) if args.real_output else None,
        real_writer_provider=args.real_writer_provider,
        skip_pytest=args.skip_pytest,
    )
    summary = run_release_gate(commands, dry_run=args.dry_run)
    print_summary(summary, as_json=args.as_json)
    sys.exit(0 if summary.passed else 1)


if __name__ == "__main__":
    main()
