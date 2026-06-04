#!/usr/bin/env python3
"""validate_logs.py — Validate memory-hub append-only JSONL event logs.

Pure stdlib. Mirrors schemas/event.schema.json. This module is the single
source of truth for record validation; mem_write.py imports validate_record()
from here so the writer and the validator can never drift.

Usage:
    python3 scripts/validate_logs.py                       # validate both shards
    python3 scripts/validate_logs.py path/to/foo.jsonl ... # validate given files

Exit codes: 0 = all valid, 1 = at least one hard error, 2 = usage/IO error.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# --- Spec constants (keep in sync with schemas/event.schema.json) ---
TYPES = ("issue", "evolution", "status_event")
SOURCES = ("user", "cc", "agent", "hook", "runtime", "audit")
REQUESTERS = ("user", "cc", "agent", "cron", "kanban")
TRIGGERS = ("manual_review", "runtime_failure", "scheduled_audit", "user_correction")
CHANGE_TYPES = ("rule_add", "rule_edit", "rule_remove", "refactor", "version_bump", "doc")
STATUSES = ("new", "acknowledged", "in_progress", "resolved", "wontfix", "duplicate")
REQUIRED_FIELDS = ("id", "type", "skill", "source", "evidence", "ts")

# type -> shard filename
SHARD_FILES = {
    "issue": "issue-log.jsonl",
    "evolution": "evolution-log.jsonl",
    "status_event": "status-log.jsonl",
}

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def validate_record(rec) -> tuple[list[str], list[str]]:
    """Return (hard_errors, soft_warnings) for a single record.

    HARD (reject the write / fail validation): id, type, skill, source,
    evidence, ts. SOFT (accept but flag): everything else.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(rec, dict):
        return (["record is not a JSON object"], warnings)

    # --- hard: required core fields ---
    for f in ("id", "skill", "evidence"):
        if not _nonempty_str(rec.get(f)):
            errors.append(f"missing/empty required field: {f}")

    if rec.get("type") not in TYPES:
        errors.append(f"invalid type {rec.get('type')!r}; must be one of {TYPES}")

    if rec.get("source") not in SOURCES:
        errors.append(f"invalid source {rec.get('source')!r}; must be one of {SOURCES}")

    ts = rec.get("ts")
    if not _nonempty_str(ts):
        errors.append("missing/empty required field: ts")
    else:
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append(f"ts {ts!r} must include a timezone offset (e.g. +08:00)")
        except ValueError:
            errors.append(f"ts {ts!r} is not a valid ISO-8601 datetime")

    # --- hard: status_event requires payload.issue_id + valid payload.status ---
    if rec.get("type") == "status_event":
        sp = rec.get("payload")
        if not isinstance(sp, dict):
            errors.append("status_event requires a payload object with issue_id and status")
        else:
            if not _nonempty_str(sp.get("issue_id")):
                errors.append("status_event missing/empty required field: payload.issue_id")
            st = sp.get("status")
            if st not in STATUSES:
                errors.append(f"invalid payload.status {st!r}; must be one of {STATUSES}")

    # --- soft: optional fields & payload ---
    if "requester" in rec and rec["requester"] not in REQUESTERS:
        warnings.append(f"unknown requester {rec['requester']!r} (expected {REQUESTERS})")
    if "trigger" in rec and rec["trigger"] not in TRIGGERS:
        warnings.append(f"unknown trigger {rec['trigger']!r} (expected {TRIGGERS})")
    if "source_hash" in rec:
        sh = rec["source_hash"]
        if not (isinstance(sh, str) and sh.startswith("sha256:") and len(sh) == 71):
            warnings.append("source_hash should look like 'sha256:<64 hex>'")

    payload = rec.get("payload")
    if payload is not None and not isinstance(payload, dict):
        warnings.append("payload should be an object")
        payload = None
    if isinstance(payload, dict):
        ct = payload.get("change_type")
        if ct is not None and ct not in CHANGE_TYPES:
            warnings.append(f"unknown payload.change_type {ct!r} (expected {CHANGE_TYPES})")
        vs = payload.get("validation_score")
        if vs is not None and not (isinstance(vs, (int, float)) and 0 <= vs <= 100):
            warnings.append("payload.validation_score should be a number in [0, 100]")
        if rec.get("type") == "evolution" and not _nonempty_str(ct):
            warnings.append("evolution records should set payload.change_type")

    return (errors, warnings)


def validate_file(path: Path) -> tuple[int, int, list[str]]:
    """Validate one JSONL file. Returns (n_ok, n_bad, messages)."""
    msgs: list[str] = []
    n_ok = n_bad = 0
    seen_ids: dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return (0, 0, [f"  ⚠️  {path} not found — skipped"])

    for lineno, raw in enumerate(lines, 1):
        if raw.strip() == "":
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError as e:
            n_bad += 1
            msgs.append(f"  ❌ {path.name}:{lineno} invalid JSON — {e}")
            continue

        errors, warnings = validate_record(rec)
        rid = rec.get("id") if isinstance(rec, dict) else None
        if isinstance(rid, str) and rid:
            if rid in seen_ids:
                warnings.append(f"duplicate id {rid!r} (first seen line {seen_ids[rid]})")
            else:
                seen_ids[rid] = lineno

        if errors:
            n_bad += 1
            for e in errors:
                msgs.append(f"  ❌ {path.name}:{lineno} {e}")
        else:
            n_ok += 1
        for w in warnings:
            msgs.append(f"  ⚠️  {path.name}:{lineno} {w}")

    return (n_ok, n_bad, msgs)


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]]
    if not paths:
        paths = [REFERENCES_DIR / fn for fn in SHARD_FILES.values()]

    total_ok = total_bad = 0
    for p in paths:
        n_ok, n_bad, msgs = validate_file(p)
        total_ok += n_ok
        total_bad += n_bad
        status = "✅" if n_bad == 0 else "❌"
        print(f"{status} {p}  ({n_ok} ok, {n_bad} bad)")
        for m in msgs:
            print(m)

    print(f"\nSummary: {total_ok} valid, {total_bad} invalid across {len(paths)} file(s).")
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
