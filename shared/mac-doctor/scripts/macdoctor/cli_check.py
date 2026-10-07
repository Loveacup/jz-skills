"""CLI registration for read-only health checks and scores."""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from datetime import datetime, timezone
from typing import Sequence

from . import __version__
from .result import CheckResult, score_results, worst_status
from .runner import Command, CommandError, CommandTimeout, execute, run


def _host(command: Command, timeout: float) -> dict[str, str]:
    model = "Unknown Mac"
    if sys.platform == "darwin":
        try:
            rc, text, _ = command(["/usr/sbin/system_profiler", "SPHardwareDataType"], min(timeout, 5))
            match = re.search(r"Model Name:\s*(.+)", text)
            if not rc and match:
                model = match.group(1).strip()
        except Exception:
            pass
    return {"model": model, "os": platform.mac_ver()[0] or platform.platform(), "arch": platform.machine()}


def _status_exit(results: list[CheckResult]) -> int:
    status = worst_status(results)
    if status == "crit":
        return 2
    if status in ("warn", "error", "unknown"):
        return 1
    return 0


def _payload(results: list[CheckResult], command: Command, timeout: float) -> dict:
    return {
        "schema_version": "1.0",
        "tool_version": __version__,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "host": _host(command, timeout),
        "results": [item.to_dict() for item in results],
        "scores": score_results(results),
    }


def _render_table(results: list[CheckResult]) -> None:
    print(f"{'STATUS':7} {'ID':38} {'VALUE':20} TITLE")
    for item in results:
        value = json.dumps(item.value, ensure_ascii=False, default=str) if item.value is not None else "—"
        print(f"{item.status:7} {item.id:38} {value[:20]:20} {item.title}")
        if item.evidence:
            print(f"         {item.evidence.splitlines()[0][:100]}")
    print(_format_scores(score_results(results)))


def _format_scores(scores: dict) -> str:
    return "Scores: " + ", ".join(
        f"{key}={'not checked' if value is None else f'{value:.1f}'}" for key, value in scores.items())


def check_handler(args: argparse.Namespace) -> int:
    command = getattr(args, "command_runner", None) or run
    timeout = args.timeout
    try:
        results = execute(categories=set(args.category) if args.category else None,
                          ids=set(args.id) if args.id else None,
                          timeout=timeout, command=command, parallel=True)
        if args.json:
            print(json.dumps(_payload(results, command, timeout), ensure_ascii=False, default=str))
        else:
            _render_table(results)
        return _status_exit(results)
    except Exception as exc:
        print(f"mac-doctor check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3


def score_handler(args: argparse.Namespace) -> int:
    command = getattr(args, "command_runner", None) or run
    timeout = args.timeout
    try:
        results = execute(timeout=timeout, command=command, parallel=True)
        scores = score_results(results)
        if args.json:
            print(json.dumps({"scores": scores, "status": worst_status(results)}, ensure_ascii=False))
        else:
            print(_format_scores(scores))
            print(f"Overall status: {worst_status(results)} ({len(results)} checks)")
        return _status_exit(results)
    except Exception as exc:
        print(f"mac-doctor score failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3


def _timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a number of seconds") from exc
    if seconds <= 0 or seconds > 300:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 300 seconds")
    return seconds


def register(subparsers) -> None:
    parser = subparsers.add_parser("check", help="run read-only macOS health checks")
    parser.add_argument("--category", action="append", choices=("performance", "storage", "security", "hardware", "network", "devenv"), help="limit to a category; repeatable")
    parser.add_argument("--id", action="append", help="limit to a check ID; repeatable")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--timeout", type=_timeout, default=10.0, metavar="S", help="per-command timeout in seconds (default: 10; maximum: 300)")
    parser.set_defaults(func=check_handler)

    score = subparsers.add_parser("score", help="run checks and print score summary only")
    score.add_argument("--json", action="store_true", help="emit score summary as JSON")
    score.add_argument("--timeout", type=_timeout, default=10.0, metavar="S", help="per-command timeout in seconds (default: 10; maximum: 300)")
    score.set_defaults(func=score_handler)
