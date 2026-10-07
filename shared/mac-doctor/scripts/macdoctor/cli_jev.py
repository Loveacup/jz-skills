"""CLI commands for previewing and evaluating the optional Jev push gate."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import jev
from . import paths


def _config():
    try:
        return json.loads(paths.config_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _findings_from_collector(payload):
    findings = []
    for alert in payload.get("alerts", []):
        if not isinstance(alert, dict):
            continue
        text = alert.get("text", "")
        kind = "anomaly" if alert.get("is_anomaly") else "threshold"
        findings.append({"kind": kind, "severity": alert.get("severity", "yellow"), "summary": text})
    return findings


def _collect():
    script = paths.SKILL_DIR / "scripts" / "collector-daemon.py"
    config_source = paths.config_file()
    try:
        with tempfile.TemporaryDirectory(prefix="mac-doctor-jev-preview-") as scratch:
            copied_config = Path(scratch) / "config.json"
            if config_source.is_file():
                copied_config.write_bytes(config_source.read_bytes())
            child_env = os.environ.copy()
            child_env["MAC_DOCTOR_DATA_DIR"] = scratch
            result = subprocess.run([sys.executable, str(script), "--json"], capture_output=True,
                                    text=True, timeout=30, check=False, env=child_env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise jev.JevError(f"collector unavailable: {type(exc).__name__}") from exc
    if result.returncode != 0:
        raise jev.JevError(f"collector unavailable: exit {result.returncode}")
    try:
        return _findings_from_collector(json.loads(result.stdout))
    except (ValueError, TypeError) as exc:
        raise jev.JevError("collector returned invalid JSON") from exc


def _prefs():
    try:
        import preferences
        return preferences.load_preferences()
    except (ImportError, OSError, ValueError):
        return {"interpretations": [], "suppressions": []}


def _emit(value, as_json):
    print(json.dumps(value, ensure_ascii=False, indent=2))

def _preview(args):
    settings = jev.load_settings(_config())
    try:
        findings = _collect()
    except jev.JevError as exc:
        print(f"Jev preview unavailable: {exc}", file=sys.stderr)
        return 1
    request = jev.build_request(findings, jev.collect_notes(_prefs(), settings), settings["model"])
    reason = jev.inactive_reason(settings)
    result = {"request": request, "gate": {"active": reason is None, "mode": settings.get("mode"),
              "reason": reason or "active"}}
    _emit(result, args.json)
    return 0


def _ask(args):
    settings = jev.load_settings(_config())
    # A manual `ask` is an explicit user action: it needs a key, not `jev.enabled`.
    if not jev.api_key():
        print(f"Jev unavailable: no API key (TYPESAFE_API_KEY or {jev.key_file()})", file=sys.stderr)
        return 2
    try:
        findings = _collect()
        request = jev.build_request(findings, jev.collect_notes(_prefs(), settings), settings["model"])
        response = jev.ask(request, settings)
        decision = jev.decide(findings, response["answers"], settings)
    except jev.JevError as exc:
        print(f"Jev unavailable: {exc}", file=sys.stderr)
        return 1
    _emit({"answers": response["answers"], "usage": response["usage"], "decision": decision}, args.json)
    return 0


def register(subparsers):
    parser = subparsers.add_parser("jev", help="Preview or evaluate optional Jev push gate")
    commands = parser.add_subparsers(dest="jev_command", required=True)
    preview = commands.add_parser("preview", help="Build the request without network access")
    preview.add_argument("--json", action="store_true")
    preview.set_defaults(func=_preview)
    ask = commands.add_parser("ask", help="Call Jev and evaluate the push decision")
    ask.add_argument("--json", action="store_true")
    ask.set_defaults(func=_ask)
