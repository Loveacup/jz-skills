#!/usr/bin/env python3
"""cqi_runtime.py — Thin CQI runtime layer over the memory-hub shards.

One job, and only one: pick up issues whose current status is `new` and
auto-acknowledge them by appending a status_event (new -> acknowledged,
by=cqi-auto). It NEVER auto-transitions to resolved / wontfix / duplicate —
those terminal verdicts require the human/judge panel (architecture decision E).

It reuses mem_read.py for status reduction and mem_write.py for the append, so
the status machine and append-only invariants can never drift. Pure stdlib.

Usage:
    python3 scripts/cqi_runtime.py                 # acknowledge all new issues
    python3 scripts/cqi_runtime.py --skill demo    # scope to one skill
    python3 scripts/cqi_runtime.py --dry-run       # report only, write nothing

Exit codes: 0 = ok (even when nothing to do), 2 = IO/usage error.
"""
from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_logs import REFERENCES_DIR  # noqa: E402
import mem_read  # noqa: E402
import mem_write  # noqa: E402

ACK_BY = "cqi-auto"


def _fetch_new_issues(ref_dir: Path, skill: str | None) -> list[dict]:
    """Run mem_read --type issue --status new and parse its JSONL stdout."""
    argv = ["mem_read.py", "--type", "issue", "--status", "new",
            "--references-dir", str(ref_dir)]
    if skill:
        argv += ["--skill", skill]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mem_read.main(argv)
    if rc != 0:
        raise RuntimeError(f"mem_read exited {rc}")
    import json
    issues: list[dict] = []
    for line in buf.getvalue().splitlines():
        if line.strip() and not line.startswith("#"):
            issues.append(json.loads(line))
    return issues


def _acknowledge(ref_dir: Path, issue: dict, *, dry_run: bool) -> bool:
    """Append a new->acknowledged status_event for one issue."""
    iid = issue.get("id")
    skill = issue.get("skill", "unknown")
    argv = ["mem_write.py", "--type", "status_event", "--skill", str(skill),
            "--source", "runtime", "--requester", "cron",
            "--evidence", f"CQI runtime auto-acknowledged {iid} (new -> acknowledged)",
            "--issue-id", str(iid), "--status", "acknowledged", "--by", ACK_BY,
            "--references-dir", str(ref_dir)]
    if dry_run:
        argv.append("--dry-run")
    rc = mem_write.main(argv)
    return rc == 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="CQI runtime: auto-acknowledge new issues (new -> acknowledged).")
    p.add_argument("--skill", help="Scope to a single skill.")
    p.add_argument("--references-dir", dest="references_dir", default=str(REFERENCES_DIR),
                   help="Override the shard directory (for testing).")
    p.add_argument("--dry-run", action="store_true", help="Report only; append nothing.")
    p.add_argument("--quiet", action="store_true", help="Silence 'nothing to do' output (for cron/no_agent).")
    args = p.parse_args(argv[1:])

    ref_dir = Path(args.references_dir)
    try:
        new_issues = _fetch_new_issues(ref_dir, args.skill)
    except (RuntimeError, OSError) as e:
        print(f"❌ failed to read new issues: {e}", file=sys.stderr)
        return 2

    if not new_issues:
        if not args.quiet:
            print("✓ no new issues to acknowledge.")
        return 0

    print(f"→ {len(new_issues)} new issue(s) to acknowledge:")
    acked = failed = 0
    for issue in new_issues:
        ok = _acknowledge(ref_dir, issue, dry_run=args.dry_run)
        mark = "→ acknowledged" if ok else "✗ FAILED"
        if ok:
            acked += 1
        else:
            failed += 1
        print(f"  {issue.get('id')}  [{issue.get('skill')}]  {mark}")

    verb = "would acknowledge" if args.dry_run else "acknowledged"
    print(f"\nCQI runtime summary: {verb} {acked}, failed {failed} "
          f"(resolved/wontfix left to the judge panel).")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
