"""CLI adapters for read-only storage scans and gated cleanup plans."""
from __future__ import annotations

import argparse
import json
import sys

from . import clean


def _emit(value, as_json):
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2))


def _storage(args):
    records = clean.scan()
    known = [r["size_bytes"] for r in records if isinstance(r.get("size_bytes"), int)]
    unknown_count = sum(r.get("size_bytes") == "unknown" for r in records)
    report_only = [r for r in records if r.get("class") == "REPORT"]
    summary = {"items": records, "item_count": len(records), "known_size_bytes": sum(known),
               "unknown_size_count": unknown_count, "report_only_count": len(report_only),
               "read_only": True}
    _emit(summary, args.json)
    return 0


def _targets(args):
    _emit(clean.load_targets(), args.json)
    return 0


def _plan(args):
    try:
        plan = clean.make_plan(args.target, include_caution=args.include_caution)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _emit(plan, args.json)
    return 0


def _apply(args):
    try:
        result = clean.apply(args.plan_id, yes=args.yes,
                             renew_if_unchanged=args.renew_if_unchanged)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _emit(result, args.json)
    if result.get("refused") or any(row["result"] == "refused" for row in result.get("items", [])):
        return 2
    if any(row["result"] == "failed" for row in result.get("items", [])):
        return 1
    return 0


def _receipts(args):
    try:
        rows = clean.receipts(args.last)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 3
    _emit(rows, args.json)
    return 0


def register(subparsers):
    storage = subparsers.add_parser("storage", help="Read-only storage target scan")
    storage.add_argument("--json", action="store_true")
    storage.set_defaults(func=_storage)

    clean_parser = subparsers.add_parser("clean", help="Plan and apply safe cleanup")
    commands = clean_parser.add_subparsers(dest="clean_command", required=True)
    plan = commands.add_parser("plan", help="Create a one-hour cleanup plan")
    plan.add_argument("--target", action="append", metavar="ID")
    plan.add_argument("--include-caution", action="store_true")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=_plan)

    apply_parser = commands.add_parser("apply", help="Apply a previously reviewed plan")
    apply_parser.add_argument("plan_id")
    apply_parser.add_argument("--yes", action="store_true", help="Explicitly authorize listed actions")
    apply_parser.add_argument("--renew-if-unchanged", action="store_true",
                              help="Renew an expired SAFE/native plan only if its full manifest is unchanged")
    apply_parser.add_argument("--json", action="store_true")
    apply_parser.set_defaults(func=_apply)

    rec = commands.add_parser("receipts", help="Show recent cleanup receipts")
    rec.add_argument("--last", type=int, default=50)
    rec.add_argument("--json", action="store_true")
    rec.set_defaults(func=_receipts)

    targets = commands.add_parser("targets", help="List cleanup target catalogue")
    targets.add_argument("--json", action="store_true")
    targets.set_defaults(func=_targets)
