#!/usr/bin/env python3
"""Pure report-aware research publication gates (S7)."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Dict

import research_contract as rc
import research_projection as rp


GATE_CODES = (
    "P0_RESEARCH_ARTIFACT_INTEGRITY",
    "P0_RESEARCH_REFERENCE_INTEGRITY",
    "P0_RESEARCH_CLAIM_BINDING",
    "P0_RESEARCH_SOURCE_SUITABILITY",
    "P0_RESEARCH_FRESHNESS",
    "P0_RESEARCH_CONFLICT",
    "P0_RESEARCH_COVERAGE",
    "P0_RESEARCH_PROJECTION_FIDELITY",
    "P0_RESEARCH_ARCHIVE_INTEGRITY",
    "P0_RESEARCH_PUBLIC_PATH_SAFETY",
)

_PRIVATE_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_:/])(?:/(?:Users|home|private|tmp|var/folders)/[^\s`|)\]]+|"
    r"[A-Za-z]:\\[^\s`|)\]]+)"
)


def _gate(passed: bool, measured: Dict[str, Any], requirement: str) -> dict:
    return {"pass": bool(passed), "measured": measured, "requirement": requirement}


def evaluate_research_gates(markdown: str, report: Dict[str, Any]) -> Dict[str, dict]:
    """Return all nine gates without exposing raw candidates or quote text."""
    artifacts = (report or {}).get("research_artifacts") or {}
    summary = (report or {}).get("research") or {}
    plan = artifacts.get("research_plan")
    bundle = artifacts.get("research_bundle")
    projection = artifacts.get("research_projection")
    records = artifacts.get("research_projection_records") or {}
    executed = bool(summary.get("executed"))
    md_source_refs = set(re.findall(r"\[(?:R|S)\d+\]", markdown or ""))
    md_object_refs = set(re.findall(r"\b(?:RC|KX)\d+\b", markdown or ""))
    has_refs = bool(md_source_refs or md_object_refs)

    if bundle is None or projection is None:
        partial_artifacts = any((bundle, projection, records))
        failed = executed or has_refs or partial_artifacts
        reason = (
            "partial_or_executed_or_referenced_without_validated_projection"
            if failed else "no_research"
        )
        return {
            code: _gate(not failed, {
                "reason": reason,
                "executed": executed,
                "research_ref_count": len(md_source_refs) + len(md_object_refs),
            }, "validated research bundle/projection required before publication")
            for code in GATE_CODES
        }

    vr = bundle.validated_research
    sources = list(vr.get("sources", ()) or ())
    quotes = list(vr.get("quotes", ()) or ())
    claim_results = list(vr.get("claim_results", ()) or ())
    source_by_uid = {str(x.get("source_uid") or ""): x for x in sources}
    quote_by_uid = {str(x.get("quote_uid") or ""): x for x in quotes}

    artifact_errors = []
    for validator, value in (
        (rc.validate_research_bundle, bundle),
        (rc.validate_research_projection, projection),
    ):
        try:
            validator(value)
        except Exception as exc:
            artifact_errors.append(type(exc).__name__)
    if plan is None:
        artifact_errors.append("missing_plan")
    else:
        try:
            rc.validate_research_plan(plan)
        except Exception as exc:
            artifact_errors.append(type(exc).__name__)
        if bundle.plan_semantic_hash != plan.plan_semantic_hash:
            artifact_errors.append("plan_hash_mismatch")
        if bundle.evidence_bundle_hash != plan.evidence_bundle_hash:
            artifact_errors.append("evidence_hash_mismatch")
        if bundle.claim_bundle_hash != plan.claim_bundle_hash:
            artifact_errors.append("claim_hash_mismatch")
    if projection.research_bundle_hash != bundle.validated_semantic_hash:
        artifact_errors.append("projection_bundle_hash_mismatch")
    if projection.report_plan_hash != rc.semantic_sha256((report or {}).get("report_plan") or {}):
        artifact_errors.append("report_plan_hash_mismatch")
    if summary.get("validated_semantic_hash") != bundle.validated_semantic_hash:
        artifact_errors.append("summary_semantic_hash_mismatch")
    if summary.get("audit_artifact_hash") != bundle.audit_artifact_hash:
        artifact_errors.append("summary_audit_hash_mismatch")

    flat_records = []
    allowed_source_refs = set()
    allowed_object_refs = set()
    for sid, section_records in records.items():
        if not isinstance(section_records, (tuple, list)):
            continue
        for record in section_records:
            if not isinstance(record, dict):
                continue
            flat_records.append((str(sid), record))
            allowed_source_refs.update(str(x) for x in record.get("citation_labels", ()) or ())
            label = str(record.get("object_label") or "")
            if re.fullmatch(r"(?:RC|KX)\d+", label):
                allowed_object_refs.add(label)
    unknown_refs = sorted(
        (md_source_refs - allowed_source_refs) | (md_object_refs - allowed_object_refs)
    )

    entry_by_uid = {str(x.get("entry_uid") or ""): x for x in projection.entries}
    unbound = []
    for sid, record in flat_records:
        if sid not in {"3", "4", "7"}:
            continue
        entry = entry_by_uid.get(str(record.get("entry_uid") or ""), {})
        kind = str(record.get("object_type") or "")
        if kind != "claim_result" and not entry.get("required_video_evidence_uids"):
            unbound.append(str(record.get("object_uid") or ""))

    unsuitable = []
    for assessment in vr.get("claim_source_assessments", ()) or ():
        verdict = str(
            assessment.get("suitability")
            or assessment.get("suitability_verdict")
            or assessment.get("source_suitability") or ""
        ).lower()
        if verdict in {"reject", "rejected", "unsuitable", "false"}:
            unsuitable.append(str(assessment.get("assessment_uid") or "assessment"))
    for result in claim_results:
        if str(result.get("publication_action") or "") not in {"keep", "qualify"}:
            continue
        if str(result.get("verdict") or "") not in {"supported", "mixed"}:
            continue
        supporting = [quote_by_uid.get(str(uid)) for uid in result.get("supporting_quote_uids", ()) or ()]
        support_sources = [
            source_by_uid.get(str(quote.get("source_uid") or ""))
            for quote in supporting if quote is not None
        ]
        kinds = {
            str(source.get("source_kind") or "").lower()
            for source in support_sources if source is not None
        }
        if kinds and kinds <= {"social", "community", "forum"}:
            unsuitable.append(str(result.get("claim_uid") or "claim"))

    stale = sorted(
        str(x.get("claim_uid") or "") for x in claim_results
        if str(x.get("publication_action") or "") in {"keep", "qualify"}
        and (
            str(x.get("verdict") or "") == "stale"
            or str(x.get("freshness_status") or "").lower() in {"stale", "expired", "failed"}
        )
    )

    conflicts = list(bundle.conflicts or ())
    conflict_uids = {
        str(x.get("subject_uid") or x.get("claim_uid") or "")
        for x in conflicts if isinstance(x, Mapping)
    }
    flattened = sorted(
        str(x.get("claim_uid") or "") for x in claim_results
        if str(x.get("claim_uid") or "") in conflict_uids
        and str(x.get("publication_action") or "") == "keep"
    )
    conflict_ok = not conflicts or (
        bundle.publication_disposition == "degraded" and not flattened
    )

    coverage_blockers = []
    if bundle.publication_disposition in {"block", "blocked"} or bundle.status in {"blocked", "invalid"}:
        coverage_blockers.append("bundle_blocked")
    verification = bundle.coverage.get("verification") if isinstance(bundle.coverage, Mapping) else None
    required_coverage_keys = {
        "p0_total", "p0_resolved", "adopted_p1_total", "adopted_p1_resolved",
        "p2_total", "p2_resolved", "p2_ratio", "gate_passed",
    }
    if not isinstance(verification, Mapping) or not required_coverage_keys <= set(verification):
        coverage_blockers.append("missing_verification_coverage")
    elif verification.get("gate_passed") is not True:
        coverage_blockers.append("verification_coverage_failed")
    if bundle.publication_disposition == "degraded":
        for result in claim_results:
            action = str(result.get("publication_action") or "")
            verdict = str(result.get("verdict") or "")
            claim_uid = str(result.get("claim_uid") or "claim")
            if action == "qualify" and not str(result.get("qualifier") or "").strip():
                coverage_blockers.append(f"missing_qualifier:{claim_uid}")
            qualifier = str(result.get("qualifier") or "").strip()
            if action == "qualify" and qualifier and qualifier not in (markdown or ""):
                coverage_blockers.append(f"qualifier_not_rendered:{claim_uid}")
            if verdict in {"unresolved", "stale", "mixed", "contradicted"} and action == "keep":
                coverage_blockers.append(f"unsafe_retained_claim:{claim_uid}")
    if plan is not None and plan.research_policy in {"force", "deep"}:
        by_claim = {str(x.get("claim_uid") or ""): x for x in claim_results}
        for claim in plan.claims:
            if not claim.get("required_for_publication"):
                continue
            result = by_claim.get(str(claim.get("claim_uid") or ""), {})
            if str(result.get("publication_action") or "") not in {"keep", "qualify"}:
                coverage_blockers.append(str(claim.get("claim_uid") or ""))

    projection_errors = []
    try:
        expected = rp.materialize_research_projection(projection, bundle)
        if rc.canonical_json_bytes(expected) != rc.canonical_json_bytes(records):
            projection_errors.append("materialization_mismatch")
        # Compare the actual public section text, not merely its citation tags.
        # Use the same deterministic renderer and frozen per-section budgets as
        # publication, including condensed-mode truncation.
        from video_analysis_engine import _render_research_projection_section
        actual_sections = {}
        current_sid = None
        for match in re.finditer(
            r"(?m)^##\s+(\d+(?:\.\d+)?)\.[^\n]*|^### 外部研究补充\s*$",
            markdown or "",
        ):
            if match.group(1) is not None:
                current_sid = match.group(1)
                continue
            end = re.search(r"(?m)^#{1,3}\s+", (markdown or "")[match.end():])
            stop = match.end() + end.start() if end else len(markdown or "")
            actual_sections.setdefault(current_sid, []).append(
                (markdown or "")[match.start():stop].strip()
            )
        for sid in set(records) | set(actual_sections):
            rendered = _render_research_projection_section(report, str(sid)).strip()
            actual = actual_sections.get(str(sid), [])
            if actual != ([rendered] if rendered else []):
                projection_errors.append(f"markdown_projection_mismatch:{sid}")
    except Exception as exc:
        projection_errors.append(type(exc).__name__)
    missing_labels = sorted(allowed_source_refs - md_source_refs)
    if missing_labels:
        projection_errors.append("projected_labels_missing_from_markdown")

    archive_bundle_hash = str(artifacts.get("archive_bundle_hash") or "")
    archive_source_hashes = {
        str(x) for x in artifacts.get("archive_source_hashes", ()) or ()
    }
    expected_source_hashes = {
        str(x.get("content_hash") or "") for x in sources if x.get("content_hash")
    }
    archive_errors = []
    if not archive_bundle_hash.startswith("sha256:"):
        archive_errors.append("missing_archive_bundle_hash")
    if not expected_source_hashes <= archive_source_hashes:
        archive_errors.append("missing_archive_source_hash")
    private_paths = sorted(set(_PRIVATE_ABSOLUTE_PATH_RE.findall(markdown or "")))

    return {
        "P0_RESEARCH_ARTIFACT_INTEGRITY": _gate(
            not artifact_errors, {"errors": sorted(set(artifact_errors))},
            "research schemas and semantic/input hashes must close"),
        "P0_RESEARCH_REFERENCE_INTEGRITY": _gate(
            not unknown_refs, {"unknown_refs": unknown_refs,
                               "resolved_ref_count": len(md_source_refs | md_object_refs)},
            "every R/S/RC/KX reference must resolve through projection"),
        "P0_RESEARCH_CLAIM_BINDING": _gate(
            not unbound, {"unbound_object_uids": sorted(unbound)},
            "sections 3/4/7 research text must bind to video anchors"),
        "P0_RESEARCH_SOURCE_SUITABILITY": _gate(
            not unsuitable, {"unsuitable_uids": sorted(set(unsuitable))},
            "adopted facts require suitable non-social-only sources"),
        "P0_RESEARCH_FRESHNESS": _gate(
            not stale, {"stale_claim_uids": stale},
            "time-sensitive adopted claims require fresh evidence"),
        "P0_RESEARCH_CONFLICT": _gate(
            conflict_ok, {"conflict_count": len(conflicts),
                          "flattened_claim_uids": flattened},
            "unresolved conflicts cannot be flattened"),
        "P0_RESEARCH_COVERAGE": _gate(
            not coverage_blockers, {"blockers": sorted(set(coverage_blockers)),
                                    "disposition": bundle.publication_disposition},
            "required coverage must be met or safely degraded"),
        "P0_RESEARCH_PROJECTION_FIDELITY": _gate(
            not projection_errors, {"errors": projection_errors,
                                    "entry_count": len(projection.entries)},
            "final research additions must match frozen projection"),
        "P0_RESEARCH_ARCHIVE_INTEGRITY": _gate(
            not archive_errors, {"errors": archive_errors,
                                 "source_hash_count": len(archive_source_hashes)},
            "immutable bundle/source archive hashes must close"),
        "P0_RESEARCH_PUBLIC_PATH_SAFETY": _gate(
            not private_paths, {"private_paths": private_paths},
            "public Markdown must not expose private absolute filesystem paths"),
    }


__all__ = ["GATE_CODES", "evaluate_research_gates"]
