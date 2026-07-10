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
from typing import Dict, Tuple, List, Optional, Any


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


_CITATION_RE = re.compile(r"\[E(\d+)\]")
_FENCED_CODE_RE = re.compile(r"```.*?```", re.S)


def _without_fenced_code(markdown: str) -> str:
    """Exclude fenced examples so `[E#]` samples do not count as evidence use."""
    return _FENCED_CODE_RE.sub("", markdown or "")


def evaluate_video_evidence_usage(
    markdown: str,
    report: Dict[str, Any],
    *,
    target_sections: Tuple[str, ...] = ("3", "4"),
) -> Dict[str, Any]:
    """Check deterministic citation coverage for final video-report sections.

    This validates only that final Markdown uses resolvable, local transcript
    evidence. It is deliberately not an entailment or factuality evaluator.
    """
    bundle = (report or {}).get("claim_bundle") or {}
    if not isinstance(bundle, dict) or bundle.get("evidence_contract_version") != 1:
        return {
            "passed": True,
            "skipped": True,
            "reason": "legacy_claim_bundle",
            "sections": {},
        }

    by_section = ((report.get("evidence_map") or {}).get("by_section") or {})
    markdown_sections = split_sections(markdown)
    section_results: Dict[str, Dict[str, Any]] = {}

    for section_id in target_sections:
        candidates = list(by_section.get(section_id, []) or [])
        candidate_by_ref = {f"E{idx}": candidate for idx, candidate in enumerate(candidates, start=1)}
        transcript_refs = {
            ref for ref, candidate in candidate_by_ref.items()
            if isinstance(candidate, dict) and candidate.get("source_type") == "transcript"
        }
        body = _without_fenced_code(markdown_sections.get(section_id, ""))
        citation_refs = [f"E{number}" for number in _CITATION_RE.findall(body)]
        unresolved_refs = []
        for ref in citation_refs:
            if ref not in candidate_by_ref and ref not in unresolved_refs:
                unresolved_refs.append(ref)
        resolved_refs = [ref for ref in citation_refs if ref in candidate_by_ref]
        resolved_locations = [f"{section_id}:{ref}" for ref in resolved_refs]
        resolved_transcript_refs = [ref for ref in resolved_refs if ref in transcript_refs]
        coverage_required = bool(transcript_refs)
        coverage_passed = not coverage_required or bool(resolved_transcript_refs)

        starts = []
        for ref in resolved_refs:
            candidate = candidate_by_ref[ref]
            start = candidate.get("start") if isinstance(candidate, dict) else None
            if isinstance(start, (int, float)):
                starts.append(float(start))
        temporal_order_warning = any(
            later < earlier for earlier, later in zip(starts, starts[1:])
        )
        section_passed = coverage_passed and not unresolved_refs
        section_results[section_id] = {
            "evidence_available": bool(candidates),
            "transcript_evidence_available": coverage_required,
            "citation_refs": citation_refs,
            "resolved_locations": resolved_locations,
            "unresolved_refs": unresolved_refs,
            "coverage_passed": coverage_passed,
            "temporal_order_warning": temporal_order_warning,
            "passed": section_passed,
        }

    return {
        "passed": all(section["passed"] for section in section_results.values()),
        "skipped": False,
        "reason": "",
        "sections": section_results,
    }


def evaluate_sparse_social_evidence(markdown: str, report: Dict[str, Any]) -> Dict[str, Any]:
    """Reject invented danmaku consensus when the source has no danmaku."""
    frontmatter = (report or {}).get("frontmatter") or {}
    if "danmaku_count" not in frontmatter:
        return {"passed": True, "skipped": True, "reason": "legacy_danmaku_metadata"}
    try:
        danmaku_count = int(frontmatter.get("danmaku_count") or 0)
    except (TypeError, ValueError):
        danmaku_count = 0
    if danmaku_count > 0:
        return {"passed": True, "skipped": True, "reason": "danmaku_available"}

    section = split_sections(markdown).get("3", "")
    match = re.search(
        r"\*\*弹幕反馈\*\*：(?P<body>.*?)(?=\n\s*\*\*|\n\s*证据：|\Z)",
        section,
        re.S,
    )
    feedback = match.group("body").strip() if match else ""
    passed = "弹幕数据不足" in feedback and ("无法判断" in feedback or "不能判断" in feedback)
    return {
        "passed": passed,
        "skipped": False,
        "reason": "zero_danmaku_requires_explicit_disclaimer" if not passed else "ok",
        "danmaku_count": danmaku_count,
        "feedback": feedback,
    }


def evaluate_transcript_time_resolution(report: Dict[str, Any]) -> Dict[str, Any]:
    """Require multiple transcript candidates to retain more than one time anchor."""
    by_section = ((report or {}).get("evidence_map") or {}).get("by_section") or {}
    anchors = []
    for section_id in ("3", "4"):
        for candidate in by_section.get(section_id, []) or []:
            if not isinstance(candidate, dict) or candidate.get("source_type") != "transcript":
                continue
            start = candidate.get("start")
            if isinstance(start, (int, float)):
                anchors.append(float(start))
    if len(anchors) < 2:
        return {"passed": True, "skipped": True, "reason": "insufficient_transcript_anchors"}
    distinct_starts = sorted(set(anchors))
    return {
        "passed": len(distinct_starts) > 1,
        "skipped": False,
        "reason": "collapsed_transcript_timestamps" if len(distinct_starts) <= 1 else "ok",
        "distinct_starts": distinct_starts,
        "anchor_count": len(anchors),
    }


def evaluate_publishable_report(
    markdown: str,
    report: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, dict], bool]:
    """Combine the stable Markdown gates with P6-A claim-pointer integrity.

    ``evaluate(markdown)`` remains Markdown-only for CLI and backward
    compatibility. The report-level gate participates only when the caller
    supplies a versioned claim bundle.
    """
    results, markdown_passed = evaluate(markdown)
    if report is None:
        return results, markdown_passed

    from video_analysis_engine import evaluate_claim_evidence_gate

    claim_result = evaluate_claim_evidence_gate(report)
    if not claim_result["skipped"]:
        results["P0_CLAIM_EVIDENCE_SCORE"] = _result(
            claim_result["passed"],
            claim_result,
            "claim evidence locations must resolve to source evidence",
        )

    video_result = evaluate_video_evidence_usage(markdown, report)
    if not video_result["skipped"]:
        results["P0_VIDEO_EVIDENCE_USAGE"] = _result(
            video_result["passed"],
            video_result,
            "final §3/§4 citations must resolve to local transcript evidence",
        )

    social_result = evaluate_sparse_social_evidence(markdown, report)
    if not social_result["skipped"]:
        results["P0_SPARSE_SOCIAL_EVIDENCE"] = _result(
            social_result["passed"],
            social_result,
            "zero danmaku requires an explicit data-insufficiency disclaimer in §3",
        )

    time_result = evaluate_transcript_time_resolution(report)
    if not time_result["skipped"]:
        results["P0_TRANSCRIPT_TIME_RESOLUTION"] = _result(
            time_result["passed"],
            time_result,
            "multiple transcript candidates cannot collapse to one timestamp",
        )

    passed = (
        markdown_passed
        and claim_result["passed"]
        and video_result["passed"]
        and social_result["passed"]
        and time_result["passed"]
    )
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
