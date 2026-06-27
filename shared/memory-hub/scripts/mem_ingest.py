#!/usr/bin/env python3
"""mem_ingest.py — Batch-ingest CC handoff events into the memory-hub shards.

Reads one or more handoff JSONL files (default: /tmp/cc-cqi-events-*.jsonl) that
Claude Code dropped at end-of-session, validates each line, fills defaults
(id / ts / source), appends valid records to the right shard, then deletes the
handoff file. Pure stdlib.

fail-open: a bad line never blocks the rest of the batch — it is counted as
`degraded` and reported, but the run still exits 0 as long as no IO error
occurred. This way a malformed CC event can never stall the Hermes main task.

After writing, validate_logs.py is run as a final gate over the touched shards.

Usage:
    python3 scripts/mem_ingest.py                         # glob /tmp/cc-cqi-events-*.jsonl
    python3 scripts/mem_ingest.py /tmp/cc-cqi-events-foo.jsonl ...
    python3 scripts/mem_ingest.py --keep --dry-run        # don't write, don't delete

Exit codes: 0 = ingest completed (possibly with degraded lines),
            2 = no handoff files found, 3 = IO error during append.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_logs import REFERENCES_DIR, SHARD_FILES, main as validate_main, validate_record  # noqa: E402
from mem_write import _append_line, _next_id, _now_iso  # noqa: E402

DEFAULT_GLOB = "/tmp/cc-cqi-events-*.jsonl"


def _ingest_file(path: Path, ref_dir: Path, *, dry_run: bool) -> tuple[int, int, list[str]]:
    """Ingest one handoff file. Returns (n_written, n_degraded, messages)."""
    msgs: list[str] = []
    n_written = n_degraded = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return (0, 0, [f"  ⚠️  cannot read {path}: {e} — skipped"])

    for lineno, raw in enumerate(lines, 1):
        if raw.strip() == "":
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError as e:
            n_degraded += 1
            msgs.append(f"  ⚠️  degraded {path.name}:{lineno} invalid JSON — {e}")
            continue
        if not isinstance(rec, dict):
            n_degraded += 1
            msgs.append(f"  ⚠️  degraded {path.name}:{lineno} not a JSON object")
            continue

        # Fill CC-handoff defaults (CC may omit source/ts/id).
        rec.setdefault("source", "cc")
        rec.setdefault("ts", _now_iso())

        rec_type = rec.get("type")
        if rec_type not in SHARD_FILES:
            n_degraded += 1
            msgs.append(f"  ⚠️  degraded {path.name}:{lineno} invalid/missing type {rec_type!r}")
            continue
        shard_path = ref_dir / SHARD_FILES[rec_type]
        if not rec.get("id"):
            rec["id"] = _next_id(shard_path, rec_type, str(rec.get("skill", "unknown")))

        errors, warnings = validate_record(rec)
        for w in warnings:
            msgs.append(f"  ⚠️  {path.name}:{lineno} {w}")
        if errors:
            n_degraded += 1
            for e in errors:
                msgs.append(f"  ⚠️  degraded {path.name}:{lineno} {e}")
            continue

        line = json.dumps(rec, ensure_ascii=False, sort_keys=False) + "\n"
        if dry_run:
            msgs.append(f"  (dry-run) would append {rec['id']} -> {shard_path.name}")
            n_written += 1
            continue
        # IO error here is fatal for the batch (return propagates to caller).
        _append_line(shard_path, line)
        n_written += 1
        msgs.append(f"  ✅ {rec['id']} -> {shard_path.name}")

    return (n_written, n_degraded, msgs)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Batch-ingest CC handoff CQI events into memory-hub shards.")
    p.add_argument("files", nargs="*", help=f"Handoff JSONL files (default glob: {DEFAULT_GLOB}).")
    p.add_argument("--references-dir", dest="references_dir", default=str(REFERENCES_DIR),
                   help="Override the shard directory (for testing).")
    p.add_argument("--keep", action="store_true", help="Do not delete handoff files after ingest.")
    p.add_argument("--dry-run", action="store_true", help="Validate + report; do not write or delete.")
    p.add_argument("--no-gate", action="store_true", help="Skip the final validate_logs.py gate.")
    args = p.parse_args(argv[1:])

    paths = [Path(f) for f in args.files] if args.files else [Path(f) for f in sorted(glob.glob(DEFAULT_GLOB))]
    if not paths:
        print(f"⚠️  no handoff files found ({DEFAULT_GLOB}); nothing to ingest.", file=sys.stderr)
        return 2

    ref_dir = Path(args.references_dir)
    total_written = total_degraded = 0
    touched_shards: set[Path] = set()

    for path in paths:
        print(f"→ ingest {path}")
        try:
            n_written, n_degraded, msgs = _ingest_file(path, ref_dir, dry_run=args.dry_run)
        except OSError as e:
            # IO error appending — degraded for Hermes but report and stop this file.
            print(f"  ❌ IO error during append: {e}", file=sys.stderr)
            return 3
        total_written += n_written
        total_degraded += n_degraded
        for m in msgs:
            print(m)
        if n_written and not args.dry_run:
            # Track which shards got data for the final gate.
            for shard in SHARD_FILES.values():
                touched_shards.add(ref_dir / shard)
        # Delete handoff only after a clean (non-dry) pass over it.
        if not args.dry_run and not args.keep:
            try:
                path.unlink()
                print(f"  🗑️  removed {path}")
            except OSError as e:
                print(f"  ⚠️  could not remove {path}: {e}", file=sys.stderr)

    print(f"\nIngest summary: {total_written} written, {total_degraded} degraded "
          f"across {len(paths)} handoff file(s).")

    # Final gate: validate the shards we touched.
    if not args.no_gate and not args.dry_run and touched_shards:
        print("\n→ final validate_logs.py gate:")
        gate_rc = validate_main(["validate_logs.py", *[str(s) for s in sorted(touched_shards)]])
        if gate_rc != 0:
            print("❌ post-ingest validation gate FAILED.", file=sys.stderr)
            return gate_rc

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
