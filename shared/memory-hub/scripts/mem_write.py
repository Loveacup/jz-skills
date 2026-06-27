#!/usr/bin/env python3
"""mem_write.py — Single write entry for the memory-hub append-only log loop.

One entry point; sharded output. A validated record with type=issue is
appended to references/issue-log.jsonl; type=evolution to evolution-log.jsonl.
The writer ONLY appends — it never rewrites existing lines.

Pure stdlib. Validation is delegated to validate_logs.validate_record() so the
writer and validator can never drift.

Examples:
    python3 scripts/mem_write.py --type issue --skill skill-authoring \\
        --source user --trigger user_correction \\
        --evidence "用户原话：'以后不要这样'" --implicated-rule progress-reporting

    echo '{"id":"X","type":"issue","skill":"s","source":"cc","evidence":"e",
           "ts":"2026-06-04T13:40:00+08:00"}' | python3 scripts/mem_write.py --stdin

Exit codes: 0 = appended, 2 = validation error (nothing written), 3 = IO error.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_logs import (  # noqa: E402
    REFERENCES_DIR,
    SHARD_FILES,
    validate_record,
)


def _now_iso() -> str:
    """Local-time ISO-8601 with timezone offset, second precision."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _next_id(shard_path: Path, rec_type: str, skill: str) -> str:
    """Generate a stable sequential id: ISSUE-/EVO-/STATUS-<skill>-NNN."""
    prefix = {"issue": "ISSUE", "evolution": "EVO", "status_event": "STATUS"}.get(rec_type, "REC")
    count = 0
    if shard_path.exists():
        for raw in shard_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                r = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if r.get("skill") == skill and r.get("type") == rec_type:
                count += 1
    return f"{prefix}-{skill}-{count + 1:03d}"


def _build_record(args) -> dict:
    rec: dict = {}
    if args.payload_json:
        payload = json.loads(args.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("--payload-json must decode to an object")
        rec["payload"] = payload

    rec["type"] = args.type
    if args.skill:
        rec["skill"] = args.skill
    if args.source:
        rec["source"] = args.source
    if args.evidence:
        rec["evidence"] = args.evidence
    if args.requester:
        rec["requester"] = args.requester
    if args.trigger:
        rec["trigger"] = args.trigger
    if args.source_hash:
        rec["source_hash"] = args.source_hash
    if args.skill_version:
        rec["skill_version"] = args.skill_version
    if args.session_id:
        rec["session_id"] = args.session_id

    payload = rec.setdefault("payload", {})
    if args.implicated_rule:
        payload["implicated_rule"] = args.implicated_rule
    if args.change_type:
        payload["change_type"] = args.change_type
    if args.validation_score is not None:
        payload["validation_score"] = args.validation_score
    if args.changelog_ref:
        payload["changelog_ref"] = args.changelog_ref
    if args.issue_id:
        payload["issue_id"] = args.issue_id
    if args.status:
        payload["status"] = args.status
    if args.by:
        payload["by"] = args.by
    if not payload:
        rec.pop("payload")

    return rec


def _append_line(shard_path: Path, line: str) -> None:
    """Append one line under an exclusive lock; never rewrites existing data."""
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(shard_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Append a validated record to the memory-hub log shards.")
    p.add_argument("--stdin", action="store_true", help="Read a full JSON record from stdin.")
    p.add_argument("--type", choices=list(SHARD_FILES.keys()), help="issue | evolution")
    p.add_argument("--skill")
    p.add_argument("--source", help="user|cc|agent|hook|runtime|audit")
    p.add_argument("--evidence", help="Verbatim original wording / pointer / trace.")
    p.add_argument("--id", help="Override id (default: auto ISSUE-/EVO-<skill>-NNN).")
    p.add_argument("--ts", help="Override timestamp (default: now, ISO-8601 +offset).")
    p.add_argument("--requester")
    p.add_argument("--trigger")
    p.add_argument("--source-hash", dest="source_hash")
    p.add_argument("--skill-version", dest="skill_version")
    p.add_argument("--session-id", dest="session_id")
    p.add_argument("--implicated-rule", dest="implicated_rule")
    p.add_argument("--change-type", dest="change_type")
    p.add_argument("--validation-score", dest="validation_score", type=float)
    p.add_argument("--changelog-ref", dest="changelog_ref")
    p.add_argument("--issue-id", dest="issue_id", help="status_event: id of the issue being transitioned.")
    p.add_argument("--status", dest="status",
                   help="status_event: new|acknowledged|in_progress|resolved|wontfix|duplicate")
    p.add_argument("--by", dest="by", help="status_event: who performed the transition (e.g. cqi-auto).")
    p.add_argument("--payload-json", dest="payload_json", help="JSON object merged into payload.")
    p.add_argument("--references-dir", dest="references_dir", default=str(REFERENCES_DIR),
                   help="Override the shard directory (for testing).")
    p.add_argument("--dry-run", action="store_true", help="Validate and print; do not write.")
    args = p.parse_args(argv[1:])

    # 1) Assemble the record.
    try:
        if args.stdin:
            rec = json.loads(sys.stdin.read())
            if not isinstance(rec, dict):
                raise ValueError("stdin must contain a single JSON object")
        else:
            if not args.type:
                p.error("--type is required unless --stdin is given")
            rec = _build_record(args)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ bad input: {e}", file=sys.stderr)
        return 2

    rec_type = rec.get("type")
    if rec_type not in SHARD_FILES:
        print(f"❌ invalid/missing type {rec_type!r}; must be one of {tuple(SHARD_FILES)}", file=sys.stderr)
        return 2

    ref_dir = Path(args.references_dir)
    shard_path = ref_dir / SHARD_FILES[rec_type]

    # 2) Fill defaults (id, ts) — only when not provided.
    if args.id:
        rec["id"] = args.id
    if args.ts:
        rec["ts"] = args.ts
    rec.setdefault("ts", _now_iso())
    if not rec.get("id"):
        rec["id"] = _next_id(shard_path, rec_type, str(rec.get("skill", "unknown")))

    # 3) Validate BEFORE writing. Hard errors -> reject.
    errors, warnings = validate_record(rec)
    for w in warnings:
        print(f"⚠️  {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"❌ {e}", file=sys.stderr)
        print("✋ not written (validation failed).", file=sys.stderr)
        return 2

    line = json.dumps(rec, ensure_ascii=False, sort_keys=False) + "\n"
    if args.dry_run:
        print(f"(dry-run) would append to {shard_path}:")
        print(line, end="")
        return 0

    # 4) Append-only write.
    try:
        _append_line(shard_path, line)
    except OSError as e:
        # Do not block the caller's main task — report degraded logging.
        print(f"❌ IO error appending to {shard_path}: {e}", file=sys.stderr)
        return 3

    print(f"✅ appended {rec['id']} -> {shard_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
