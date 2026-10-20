#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release gate runner for video-analysis-engine.

P3-A: one stable entry point for pre-release validation.

Default mode runs two deterministic fixture lanes then pytest:
  1. full fixture lane: run_quality_gate.py with fixture provider, claim-first-full
     depth profile, all publish/QA gates, and --mode full.
  2. sparse fixture lane: same fixture, no writer provider, --mode sparse, standard
     depth profile, publish + section-QA gates (no claim-QA, no model dependency).
  3. pytest excluding tests/test_asr_config.py

Both deterministic lanes always run; skip_pytest skips only the pytest step.

Real sample smoke is opt-in via --real-sample because it may call a model-backed
writer provider and spend time/tokens. It uses --mode auto so sparse evidence budgets
suppress the provider internally while long samples keep the model-backed path.
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
DEFAULT_SPARSE_OUTPUT = Path("/tmp/video_analysis_engine_sparse_release_gate_report.md")

# S8-B offline research fixture lane. The full fixture lane exercises the offline
# research provider so the release gate proves the research P0 gates hold. Inputs are
# sanitized public fixtures; the archive lands in a deterministic /tmp directory so raw
# research sources never touch the repo working tree.
DEFAULT_RESEARCH_CONTEXT = Path("tests/fixtures/research/release_context.json")
DEFAULT_RESEARCH_FIXTURE = Path("tests/fixtures/research/release_fixture.json")
DEFAULT_RESEARCH_ARCHIVE_DIR = Path("/tmp/video-analysis-engine-release-gate/research")


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
    sparse_output: Path = DEFAULT_SPARSE_OUTPUT,
    research_context: Path = DEFAULT_RESEARCH_CONTEXT,
    research_fixture: Path = DEFAULT_RESEARCH_FIXTURE,
    research_archive_dir: Path = DEFAULT_RESEARCH_ARCHIVE_DIR,
    real_sample: Optional[Path] = None,
    real_output: Optional[Path] = None,
    real_writer_provider: str = "cli",
    skip_pytest: bool = False,
) -> List[GateCommand]:
    """Build the ordered release-gate command list.

    Order: full fixture lane → sparse fixture lane → pytest (unless skipped) → real sample (if set).
    Both deterministic fixture lanes always run regardless of skip_pytest.
    """
    if real_sample and real_writer_provider not in {"cli", "deepseek"}:
        raise ValueError("real sample writer provider must be model-backed: cli or deepseek")

    py = sys.executable

    # Lane 1: full fixture — claim-first-full, all gates, mode full
    commands = [
        GateCommand(
            name="fixture quality gate (full)",
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
                "--mode",
                "full",
                "--fail-on-fallback-warning",
                "--publishable",
                "--section-qa-gate",
                "--depth-profile",
                "claim-first-full",
                "--claim-qa-gate",
                # S8-B: offline research fixture lane. Deterministic, network-free, and
                # archived under /tmp so raw sources never enter the repo working tree.
                "--research-provider",
                "fixture",
                "--research-context",
                str(research_context),
                "--research-fixture",
                str(research_fixture),
                "--research-archive-dir",
                str(research_archive_dir),
                "--json",
            ],
        ),
        # Lane 2: sparse fixture — same input, no model, mode sparse, no claim-QA,
        # and deliberately no research/network flags (fully offline evidence-only lane).
        GateCommand(
            name="fixture quality gate (sparse)",
            kind="quality_gate_sparse_fixture",
            argv=[
                py,
                "scripts/run_quality_gate.py",
                "--input",
                str(fixture_input),
                "--output",
                str(sparse_output),
                "--writer-provider",
                "none",
                "--mode",
                "sparse",
                "--publishable",
                "--section-qa-gate",
                "--depth-profile",
                "standard",
                "--json",
            ],
        ),
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
                    "--mode",
                    "auto",
                    "--fail-on-fallback-warning",
                    "--publishable",
                    "--section-qa-gate",
                    "--depth-profile",
                    "claim-first-full",
                    "--claim-qa-gate",
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
    parser = argparse.ArgumentParser(description="Run video-analysis-engine release gates.")
    parser.add_argument(
        "--fixture-input",
        default=str(DEFAULT_FIXTURE),
        help="Deterministic fetch_all fixture for the cheap gate.",
    )
    parser.add_argument(
        "--fixture-output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the full fixture report.",
    )
    parser.add_argument(
        "--sparse-output",
        default=str(DEFAULT_SPARSE_OUTPUT),
        help="Output path for the sparse fixture report.",
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
        sparse_output=Path(args.sparse_output),
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
