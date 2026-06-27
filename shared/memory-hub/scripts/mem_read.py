#!/usr/bin/env python3
"""mem_read.py — Query the memory-hub shards with status reduction.

Reads all shards (issue / evolution / status_event), then for `type=issue`
records computes the CURRENT lifecycle state by reducing every status_event
that targets that issue (payload.issue_id) to the one with the latest `ts`.
An issue with no status_event defaults to `new`.

Filters (all optional, AND-combined): --skill, --type, --status, --since.
Output is JSONL on stdout — for issues, a `current_status` field is injected.
Pure stdlib.

Usage:
    python3 scripts/mem_read.py --skill demo-skill --type issue --status new
    python3 scripts/mem_read.py --since 2026-06-01
    python3 scripts/mem_read.py --type evolution

Exit codes: 0 = ok (even with zero matches), 2 = IO/usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_logs import REFERENCES_DIR, SHARD_FILES, STATUSES  # noqa: E402

DEFAULT_STATUS = "new"


def _parse_ts(ts) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_shard(ref_dir: Path, rec_type: str) -> list[dict]:
    path = ref_dir / SHARD_FILES[rec_type]
    out: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return out
    for raw in lines:
        if raw.strip() == "":
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _reduce_statuses(status_events: list[dict]) -> dict[str, str]:
    """issue_id -> current status (latest status_event by ts wins)."""
    latest: dict[str, tuple[datetime | None, str]] = {}
    for ev in status_events:
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            continue
        iid = payload.get("issue_id")
        st = payload.get("status")
        if not isinstance(iid, str) or not iid or st not in STATUSES:
            continue
        ts = _parse_ts(ev.get("ts"))
        prev = latest.get(iid)
        # Records without a parseable ts sort before any dated one.
        if prev is None or _ts_key(ts) >= _ts_key(prev[0]):
            latest[iid] = (ts, st)
    return {iid: st for iid, (_, st) in latest.items()}


def _ts_key(ts: datetime | None):
    return ts if ts is not None else datetime.min.replace(tzinfo=None)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Query memory-hub shards with issue-status reduction.")
    p.add_argument("--skill", help="Filter by target skill name.")
    p.add_argument("--type", choices=list(SHARD_FILES.keys()), help="Filter by record type.")
    p.add_argument("--status", choices=list(STATUSES), help="Filter issues by current_status (issues only).")
    p.add_argument("--since", help="Only records with ts >= this ISO-8601 datetime.")
    p.add_argument("--references-dir", dest="references_dir", default=str(REFERENCES_DIR),
                   help="Override the shard directory (for testing).")
    args = p.parse_args(argv[1:])

    ref_dir = Path(args.references_dir)
    since_dt = None
    if args.since:
        since_dt = _parse_ts(args.since)
        if since_dt is None:
            print(f"❌ --since {args.since!r} is not a valid ISO-8601 datetime", file=sys.stderr)
            return 2

    issues = _load_shard(ref_dir, "issue")
    evolutions = _load_shard(ref_dir, "evolution")
    status_events = _load_shard(ref_dir, "status_event")
    current = _reduce_statuses(status_events)

    # Build the candidate set respecting --type (default: all).
    candidates: list[dict] = []
    want = args.type
    if want in (None, "issue"):
        for rec in issues:
            enriched = dict(rec)
            enriched["current_status"] = current.get(rec.get("id"), DEFAULT_STATUS)
            candidates.append(enriched)
    if want in (None, "evolution"):
        candidates.extend(evolutions)
    if want in (None, "status_event"):
        candidates.extend(status_events)

    n = 0
    for rec in candidates:
        if args.skill and rec.get("skill") != args.skill:
            continue
        if args.status:
            # --status only applies to issues (records carrying current_status).
            if rec.get("type") != "issue" or rec.get("current_status") != args.status:
                continue
        if since_dt is not None:
            ts = _parse_ts(rec.get("ts"))
            if ts is None or _ts_key(ts) < _ts_key(since_dt):
                continue
        print(json.dumps(rec, ensure_ascii=False, sort_keys=False))
        n += 1

    print(f"# {n} record(s) matched", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
