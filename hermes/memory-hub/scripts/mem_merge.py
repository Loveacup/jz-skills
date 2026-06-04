#!/usr/bin/env python3
"""mem_merge.py — Merge memory-hub issues into the Obsidian CQI audit doc.

Pulls issues newer than the last merge (waterline mechanism), reduces each to
its current lifecycle status (reusing mem_read), and appends a dated batch
section to the Obsidian doc. Append-only, idempotent, dedup-by-issue-id.

Invariants (mirror the storage铁律):
  - NEVER overwrites or deletes — only appends a new `## 批次 …` section.
  - Idempotent: an issue_id already present in the doc is skipped; a run that
    finds nothing new appends nothing.
  - Waterline (`.merge_waterline`) records the max issue ts merged so far; the
    next run only considers issues with ts > waterline. Missing waterline →
    full merge but capped to the last 30 days.
  - fail-open: any IO/parse problem reports and degrades, never raises into the
    caller's main task.
  - Zero new deps (python3 stdlib).

Usage:
    python3 scripts/mem_merge.py                 # merge new issues into the doc
    python3 scripts/mem_merge.py --skill demo     # scope to one skill
    python3 scripts/mem_merge.py --dry-run        # report only; write nothing
    python3 scripts/mem_merge.py --doc /path.md   # override the target doc

Exit codes: 0 = ok (even when nothing to merge), 3 = IO error (fail-open).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_logs import REFERENCES_DIR  # noqa: E402
from mem_read import (  # noqa: E402
    DEFAULT_STATUS,
    _load_shard,
    _parse_ts,
    _reduce_statuses,
    _ts_key,
)

WATERLINE_PATH = Path(__file__).resolve().parent.parent / ".merge_waterline"
DEFAULT_DOC = (
    Path.home() / "Documents" / "Obsidian" / "AlexCai" / "02-Plan&CQI"
    / "memory-hub CQI 持续审计.md"
)
FULL_MERGE_WINDOW_DAYS = 30
EVIDENCE_MAX = 240

DOC_HEADER = """---
title: memory-hub CQI 持续审计
type: cqi-audit
skill: memory-hub
tags: [CQI, memory-hub, 持续审计]
---

# memory-hub CQI 持续审计

> 由 `memory-hub/scripts/mem_merge.py` 自动追加。每个批次对应一次合并，逐条列出 issue 当前状态与简要。
> 只追加、不覆盖、不删除；issue_id 已存在则跳过（幂等）。机器可读真相源在 `references/issue-log.jsonl`。
"""


def _read_waterline(path: Path) -> datetime | None:
    """Return the last-merged max ts, or None if absent/unreadable."""
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None
    return _parse_ts(raw)


def _write_waterline(path: Path, ts: datetime) -> None:
    path.write_text(ts.isoformat(), encoding="utf-8")


def _truncate(text: str, limit: int = EVIDENCE_MAX) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _format_issue(issue: dict) -> str:
    """Render one issue as a markdown bullet block."""
    iid = issue.get("id", "?")
    status = issue.get("current_status", DEFAULT_STATUS)
    skill = issue.get("skill", "unknown")
    payload = issue.get("payload") if isinstance(issue.get("payload"), dict) else {}
    rule = payload.get("implicated_rule")
    severity = payload.get("severity")
    location = payload.get("location")
    fix = payload.get("fix")

    head_bits = [f"`{status}`", f"[{skill}]"]
    if severity:
        head_bits.append(f"severity={severity}")
    if rule:
        head_bits.append(f"rule={rule}")
    lines = [f"- **{iid}** — {' · '.join(head_bits)}"]
    ev = _truncate(issue.get("evidence", ""))
    if ev:
        lines.append(f"  - evidence: {ev}")
    if location:
        lines.append(f"  - location: {location}")
    if fix:
        lines.append(f"  - fix: {_truncate(str(fix))}")
    return "\n".join(lines)


def _existing_ids(doc_path: Path) -> set[str]:
    """Issue ids already written into the doc (for dedup)."""
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return set()
    ids: set[str] = set()
    for token in text.replace("*", " ").split():
        t = token.strip("`*,.:;()[]")
        if t.startswith("ISSUE-"):
            ids.add(t)
    return ids


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        description="Merge memory-hub issues into the Obsidian CQI audit doc (append-only, idempotent)."
    )
    p.add_argument("--skill", help="Scope to a single skill.")
    p.add_argument("--references-dir", dest="references_dir", default=str(REFERENCES_DIR),
                   help="Override the shard directory (for testing).")
    p.add_argument("--doc", default=str(DEFAULT_DOC), help="Override the target Obsidian doc.")
    p.add_argument("--waterline", default=str(WATERLINE_PATH), help="Override the waterline file.")
    p.add_argument("--dry-run", action="store_true", help="Report only; write nothing.")
    args = p.parse_args(argv[1:])

    ref_dir = Path(args.references_dir)
    doc_path = Path(args.doc)
    waterline_path = Path(args.waterline)

    try:
        issues = _load_shard(ref_dir, "issue")
        status_events = _load_shard(ref_dir, "status_event")
    except OSError as e:
        print(f"⚠️  fail-open: cannot read shards: {e}", file=sys.stderr)
        return 3
    current = _reduce_statuses(status_events)

    # Enrich with current_status and optionally scope to a skill.
    enriched: list[dict] = []
    for rec in issues:
        if args.skill and rec.get("skill") != args.skill:
            continue
        e = dict(rec)
        e["current_status"] = current.get(rec.get("id"), DEFAULT_STATUS)
        enriched.append(e)

    if not enriched:
        print("✓ no issues in scope; nothing to merge.")
        return 0

    # Determine the ts cutoff: waterline if present, else last 30 days.
    waterline = _read_waterline(waterline_path)
    if waterline is None:
        cutoff = datetime.now().astimezone() - timedelta(days=FULL_MERGE_WINDOW_DAYS)
        print(f"→ no waterline; full merge capped to last {FULL_MERGE_WINDOW_DAYS} days "
              f"(cutoff {cutoff.isoformat(timespec='seconds')}).")
    else:
        cutoff = waterline
        print(f"→ waterline at {waterline.isoformat(timespec='seconds')}; merging newer issues.")

    # Candidates: ts strictly newer than the cutoff (waterline) or >= cutoff (30d window).
    strict = waterline is not None
    candidates: list[dict] = []
    max_ts = waterline
    for e in enriched:
        ts = _parse_ts(e.get("ts"))
        if ts is None:
            continue
        if max_ts is None or _ts_key(ts) > _ts_key(max_ts):
            max_ts = ts
        if strict:
            if _ts_key(ts) > _ts_key(cutoff):
                candidates.append(e)
        else:
            if _ts_key(ts) >= _ts_key(cutoff):
                candidates.append(e)

    # Dedup against ids already in the doc.
    already = _existing_ids(doc_path)
    fresh = [e for e in candidates if e.get("id") not in already]

    if not fresh:
        print(f"✓ {len(candidates)} candidate(s), all already in the doc; nothing appended (idempotent).")
        # Still advance the waterline so future scans stay cheap.
        if not args.dry_run and max_ts is not None and max_ts != waterline:
            try:
                _write_waterline(waterline_path, max_ts)
            except OSError as e:
                print(f"⚠️  fail-open: could not update waterline: {e}", file=sys.stderr)
        return 0

    # Build the batch section.
    fresh.sort(key=lambda e: _ts_key(_parse_ts(e.get("ts"))))
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    section = [f"\n## 批次 {stamp}", f"\n> {len(fresh)} 条 issue（来源 `references/issue-log.jsonl`）。\n"]
    section += [_format_issue(e) for e in fresh]
    block = "\n".join(section) + "\n"

    if args.dry_run:
        print(f"(dry-run) would append {len(fresh)} issue(s) to {doc_path}:")
        print(block)
        return 0

    try:
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        if not doc_path.exists():
            doc_path.write_text(DOC_HEADER, encoding="utf-8")
            print(f"→ created new doc {doc_path}")
        with doc_path.open("a", encoding="utf-8") as f:
            f.write(block)
        print(f"✅ appended {len(fresh)} issue(s) to {doc_path}")
    except OSError as e:
        print(f"⚠️  fail-open: could not write doc: {e}", file=sys.stderr)
        return 3

    if max_ts is not None:
        try:
            _write_waterline(waterline_path, max_ts)
            print(f"→ waterline advanced to {max_ts.isoformat(timespec='seconds')}.")
        except OSError as e:
            print(f"⚠️  fail-open: could not update waterline: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
