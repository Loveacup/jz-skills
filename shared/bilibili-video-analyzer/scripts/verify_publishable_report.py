#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_publishable_report.py — publish gate for Obsidian-ready video notes.

This is intentionally stricter than verify_report.py. verify_report is an
engineering/depth-structure gate; this module blocks skeleton/debug artifacts
from being treated as publishable Obsidian notes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Tuple, List


_SECTION_RE = re.compile(r"^##\s+(2\.5|\d+)(?:\.)?(?=\s)", re.M)
_REQUIRED_SECTIONS = ["0", "1", "2", "2.5", "3", "4", "5", "6", "7", "8"]
_SKELETON_TOKENS = ["_骨架占位", "骨架占位", "Skeleton", "skeleton placeholder"]


def split_sections(md: str) -> Dict[str, str]:
    matches = list(_SECTION_RE.finditer(md or ""))
    sections: Dict[str, str] = {}
    for idx, match in enumerate(matches):
        sid = match.group(1)
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md)
        sections[sid] = md[start:end]
    return sections


def _result(passed: bool, measured, reason: str = "") -> dict:
    return {"pass": bool(passed), "measured": measured, "reason": reason}


def _blockquote_groups(section: str) -> List[str]:
    groups: List[List[str]] = []
    current: List[str] = []
    for line in section.splitlines():
        if line.lstrip().startswith(">"):
            current.append(line.lstrip()[1:].strip())
        else:
            if current:
                groups.append(current)
                current = []
    if current:
        groups.append(current)
    return ["\n".join(group).strip() for group in groups]


def _logic_chain_structured(section: str) -> Tuple[bool, str]:
    if not section.strip():
        return False, "§1 missing"
    has_table = "|" in section and re.search(r"^\s*\|\s*[-:]+", section, re.M)
    has_mermaid = "```mermaid" in section
    has_timeline = bool(re.search(r"\b\d{1,2}:\d{2}\b", section)) and ("->" in section or "→" in section or "步骤" in section)
    quote_lines = [ln for ln in section.splitlines() if ln.lstrip().startswith(">")]
    non_quote_text = "\n".join(
        ln for ln in section.splitlines()
        if ln.strip() and not ln.lstrip().startswith(">") and not ln.startswith("##")
    )
    if quote_lines and len(non_quote_text.strip()) < 80 and not (has_table or has_mermaid or has_timeline):
        return False, "§1 is mostly raw blockquotes"
    ok = bool(has_table or has_mermaid or has_timeline)
    reason = "has table/mermaid/timeline" if ok else "§1 lacks table, mermaid, or timeline structure"
    return ok, reason


def evaluate(md: str) -> Tuple[Dict[str, dict], bool]:
    """Return (gate_results, passed)."""
    md = md or ""
    sections = split_sections(md)
    lines = md.splitlines()
    results: Dict[str, dict] = {}

    skeleton_hits = [token for token in _SKELETON_TOKENS if token in md]
    results["P0_NO_SKELETON"] = _result(
        not skeleton_hits,
        skeleton_hits,
        "skeleton/debug placeholders are not publishable" if skeleton_hits else "ok",
    )

    missing = [sid for sid in _REQUIRED_SECTIONS if sid not in sections]
    results["P0_REQUIRED_SECTIONS"] = _result(
        not missing,
        missing,
        "missing required sections" if missing else "ok",
    )

    long_lines = [
        {"line": idx, "chars": len(line)}
        for idx, line in enumerate(lines, start=1)
        if len(line) > 1000
    ]
    results["P0_NO_LONG_LINES"] = _result(
        not long_lines,
        long_lines[:10],
        "raw transcript dump lines exceed 1000 chars" if long_lines else "ok",
    )

    logic_ok, logic_reason = _logic_chain_structured(sections.get("1", ""))
    results["P1_LOGIC_CHAIN_STRUCTURED"] = _result(
        logic_ok,
        logic_reason,
        logic_reason,
    )

    quote_groups = _blockquote_groups(sections.get("5", ""))
    overlong_quotes = [
        {"index": idx, "chars": len(q), "preview": q[:80]}
        for idx, q in enumerate(quote_groups, start=1)
        if len(q) > 300
    ]
    results["P1_SHORT_HIGHLIGHTS"] = _result(
        not overlong_quotes,
        overlong_quotes[:10],
        "highlight quotes must be short, curated, and readable" if overlong_quotes else "ok",
    )

    appendix_only = []
    for sid in ["3", "4", "6", "7"]:
        section = sections.get(sid, "")
        body_lines = [
            ln.strip() for ln in section.splitlines()
            if ln.strip() and not ln.startswith("##")
        ]
        if body_lines and all(
            ln.startswith(">") or ln.startswith("|") or ln.startswith("---") or "Source Appendix" in ln
            for ln in body_lines
        ):
            appendix_only.append(sid)
    results["P1_NO_APPENDIX_ONLY_SECTIONS"] = _result(
        not appendix_only,
        appendix_only,
        "required sections cannot be only blockquotes/tables/source appendix" if appendix_only else "ok",
    )

    passed = all(item["pass"] for item in results.values())
    return results, passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a report is publishable, not merely structurally deep.")
    parser.add_argument("report", help="Markdown report path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        md = Path(args.report).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"❌ cannot read report: {exc}", file=sys.stderr)
        sys.exit(2)
    results, passed = evaluate(md)
    print(f"{'✅' if passed else '❌'} publishable gate {'PASS' if passed else 'FAIL'}")
    for code, gate in results.items():
        print(f"  {code}: {'PASS' if gate['pass'] else 'FAIL'} — {gate['measured']}")
    if args.as_json:
        print("RESULT_JSON_START")
        print(json.dumps({"passed": passed, "gates": results}, ensure_ascii=False, indent=2))
        print("RESULT_JSON_END")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
