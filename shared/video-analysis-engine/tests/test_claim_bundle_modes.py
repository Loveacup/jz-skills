#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2: every ready mode owns one deterministic ClaimBundle artifact."""

import copy

import pytest

from video_analysis_engine import (
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    analyze_video,
    assemble_draft_report_slice,
)


def _ready_input():
    return AnalysisInput(
        platform="bilibili",
        video_id="BV_claim_modes",
        title="确定性 ClaimBundle 测试",
        author="tester",
        duration=90,
        transcript=Transcript(
            source="official_subtitle",
            segments=[
                TranscriptSegment(start=0, end=20, text="这个机制会影响系统结果，因为输入约束决定了后续行为。"),
                TranscriptSegment(start=20, end=40, text="第二个观点用于补充边界和应用条件，不能外推到所有情况。"),
            ],
        ),
        comments=[],
        danmaku=[],
        fact_checks=[],
        cross_platform={},
    )


def _non_ready_input():
    return AnalysisInput(
        platform="bilibili",
        video_id="BV_no_claims",
        title="无转录",
        author="tester",
        duration=20,
        transcript=None,
        comments=[],
        danmaku=[],
        fact_checks=[],
        cross_platform={},
    )


@pytest.mark.parametrize("mode", ["sparse", "condensed", "full"])
def test_every_ready_mode_precomputes_finalized_claim_bundle(mode):
    report = analyze_video(_ready_input(), mode_override=mode)
    bundle = report["claim_bundle"]

    assert bundle["schema_version"] == "claim-bundle/1.0"
    assert bundle["claim_bundle_semantic_hash"].startswith("sha256:")
    assert bundle["claims"]
    assert all(claim["claim_uid"].startswith("claim_") for claim in bundle["claims"])
    assert all(claim["evidence_locations"] for claim in bundle["claims"])
    assert all(
        location.split(":", 1)[0].isdigit() and location.split(":", 1)[1].startswith("E")
        for claim in bundle["claims"]
        for location in claim["evidence_locations"]
    )


def test_same_ready_input_and_mode_is_byte_deterministic():
    first = analyze_video(_ready_input(), mode_override="sparse")["claim_bundle"]
    second = analyze_video(_ready_input(), mode_override="sparse")["claim_bundle"]

    assert first == second
    assert first["claim_bundle_semantic_hash"] == second["claim_bundle_semantic_hash"]


def test_non_ready_input_does_not_fabricate_claim_bundle():
    report = analyze_video(_non_ready_input(), mode_override="full")
    assert not report.get("claim_bundle")


def test_standard_draft_reuses_precomputed_bundle_without_rebuilding(monkeypatch):
    report = analyze_video(_ready_input(), mode_override="full")
    original = report["claim_bundle"]

    def forbidden_rebuild(_report):
        raise AssertionError("precomputed ClaimBundle must be reused")

    monkeypatch.setattr("video_analysis_engine.build_claim_bundle", forbidden_rebuild)
    draft = assemble_draft_report_slice(
        report,
        section_ids=("1",),
        depth_profile="standard",
    )

    assert draft.claim_bundle is original
    assert report["claim_bundle"] is original


def test_finalized_bundle_never_contains_placeholder_or_evidence_free_insight():
    bundle = analyze_video(_ready_input(), mode_override="full")["claim_bundle"]
    assert all("E_placeholder" not in insight.get("evidence_ids", []) for insight in bundle["insights"])
    assert all(insight.get("evidence_locations") for insight in bundle["insights"])


def test_semantic_hash_ignores_display_ids_and_unordered_record_order():
    from claim_contract import finalize_claim_bundle_dict

    payload = {
        "evidence_contract_version": 1,
        "claims": [
            {
                "id": "C1",
                "text": "稳定声明 A",
                "confidence": 0.8,
                "evidence_ids": ["E1"],
                "evidence_locations": ["3:E1"],
                "source_type": "transcript",
                "claim_type": "observed",
            },
            {
                "id": "C2",
                "text": "稳定声明 B",
                "confidence": 0.7,
                "evidence_ids": ["E2"],
                "evidence_locations": ["4:E2"],
                "source_type": "transcript",
                "claim_type": "observed",
            },
        ],
        "insights": [],
        "audit_log": [],
    }
    reordered = copy.deepcopy(payload)
    reordered["claims"].reverse()
    reordered["claims"][0]["id"] = "DISPLAY-9"
    reordered["claims"][1]["id"] = "DISPLAY-8"

    left = finalize_claim_bundle_dict(payload)
    right = finalize_claim_bundle_dict(reordered)
    assert left["claim_bundle_semantic_hash"] == right["claim_bundle_semantic_hash"]


def test_missing_canonical_location_and_duplicate_uid_fail_closed():
    from claim_contract import ClaimContractViolation, finalize_claim_bundle_dict

    base_claim = {
        "id": "C1",
        "text": "同一声明",
        "confidence": 0.8,
        "evidence_ids": ["E1"],
        "evidence_locations": ["3:E1"],
        "source_type": "transcript",
        "claim_type": "observed",
    }
    with pytest.raises(ClaimContractViolation, match="evidence_locations"):
        finalize_claim_bundle_dict({
            "claims": [{**base_claim, "evidence_locations": []}],
            "insights": [],
            "audit_log": [],
        })
    with pytest.raises(ClaimContractViolation, match="duplicate claim_uid"):
        finalize_claim_bundle_dict({
            "claims": [copy.deepcopy(base_claim), copy.deepcopy(base_claim)],
            "insights": [],
            "audit_log": [],
        })


def test_audience_claim_is_explicitly_non_factual_support():
    from claim_contract import finalize_claim_bundle_dict

    bundle = finalize_claim_bundle_dict({
        "claims": [{
            "id": "C1",
            "text": "观众认为内容很有启发",
            "confidence": 0.3,
            "evidence_ids": ["E1"],
            "evidence_locations": ["7:E1"],
            "source_type": "comment",
            "claim_type": "observed",
        }],
        "insights": [],
        "audit_log": [],
    })
    claim = bundle["claims"][0]
    assert claim["support_scope"] == "audience_signal"
    assert claim["risk"] == "P3"


def test_placeholder_marker_is_rejected_in_any_claim_or_insight_field():
    from claim_contract import ClaimContractViolation, finalize_claim_bundle_dict

    claim = {
        "id": "C1",
        "text": "真实声明",
        "confidence": 0.8,
        "evidence_ids": ["E1"],
        "evidence_locations": ["3:E1"],
        "source_type": "transcript",
        "claim_type": "observed",
        "backing": "等待 E_placeholder 补证",
    }
    with pytest.raises(ClaimContractViolation, match="placeholder"):
        finalize_claim_bundle_dict({"claims": [claim], "insights": [], "audit_log": []})


def test_audit_log_display_ids_do_not_change_semantic_hash():
    from claim_contract import finalize_claim_bundle_dict

    base_claim = {
        "id": "C1",
        "text": "稳定声明",
        "confidence": 0.8,
        "evidence_ids": ["E1"],
        "evidence_locations": ["3:E1"],
        "source_type": "transcript",
        "claim_type": "observed",
    }
    left = finalize_claim_bundle_dict({
        "claims": [base_claim],
        "insights": [],
        "audit_log": [{"id": "A1", "claim_id": "C1", "action": "keep", "reason": "grounded"}],
    })
    right = finalize_claim_bundle_dict({
        "claims": [{**base_claim, "id": "DISPLAY-9"}],
        "insights": [],
        "audit_log": [{"id": "DISPLAY-A", "claim_id": "DISPLAY-9", "action": "keep", "reason": "grounded"}],
    })
    assert left["claim_bundle_semantic_hash"] == right["claim_bundle_semantic_hash"]
