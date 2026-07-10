# -*- coding: utf-8 -*-
"""RED tests for Claim-first Pipeline Rules.

These tests verify the behavioral contracts of the claim-first architecture:
1. audit_claims can only keep/downgrade/drop, never raise confidence
2. Insight type → section mapping exists (§3/§4/§7)
3. Comments/danmaku cannot be upgraded to factual claims

They should FAIL initially and PASS after implementing claim pipeline logic.
"""

import pytest
import sys
import os

# Ensure scripts/ is in sys.path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestAuditClaimsContract:
    """Test audit_claims behavioral contract: only downgrade or keep, never upgrade."""

    def test_audit_claims_cannot_raise_confidence(self):
        """audit_claims must only keep/downgrade/drop confidence, never raise it.

        Rule: If a claim starts with confidence=0.3, audit cannot return confidence > 0.3.
        This is a RED test — it will fail until audit_claims is implemented with this constraint.
        """
        try:
            from video_analysis_engine import Claim, audit_claims

            # Create a low-confidence claim
            low_conf_claim = Claim(
                id="C1",
                text="这是一个低置信度主张",
                confidence=0.3,
                evidence_ids=["E1"],
                source_type="transcript"
            )

            # Mock evidence map
            evidence_map = {
                "E1": {"text": "字幕内容", "type": "subtitle"}
            }

            # Audit the claim
            audited = audit_claims([low_conf_claim], evidence_map)

            # Find the audited version of C1
            c1_audited = next((c for c in audited if c.id == "C1"), None)

            # If claim still exists after audit, its confidence must not increase
            if c1_audited is not None:
                assert c1_audited.confidence <= 0.3, \
                    f"audit_claims raised confidence from 0.3 to {c1_audited.confidence} — violates contract"

        except (ImportError, AttributeError, TypeError) as e:
            pytest.fail(f"audit_claims contract test failed due to missing implementation: {e}")

    def test_audit_claims_comment_cannot_become_fact(self):
        """Claims sourced from comments/danmaku cannot be upgraded to factual claims.

        Rule: source_type="comment" or "danmaku" claims must remain audience signals,
        cannot have confidence raised or source_type changed to "transcript" or "official".
        """
        try:
            from video_analysis_engine import Claim, audit_claims

            # Create a comment-sourced claim
            comment_claim = Claim(
                id="C2",
                text="观众认为这个案例很有启发性",
                confidence=0.5,
                evidence_ids=["E2"],
                source_type="comment"
            )

            evidence_map = {
                "E2": {"text": "这个案例很有启发性", "type": "comment"}
            }

            audited = audit_claims([comment_claim], evidence_map)
            c2_audited = next((c for c in audited if c.id == "C2"), None)

            if c2_audited is not None:
                # Confidence cannot increase
                assert c2_audited.confidence <= 0.5, \
                    "audit_claims raised comment claim confidence — violates contract"

                # Source type must remain audience signal
                assert c2_audited.source_type in ["comment", "danmaku", "audience"], \
                    f"audit_claims changed comment source_type to {c2_audited.source_type} — violates contract"

        except (ImportError, AttributeError, TypeError) as e:
            pytest.fail(f"audit_claims comment contract test failed: {e}")


class TestInsightSectionMapping:
    """Test that Insight types are correctly mapped to sections §3/§4/§7."""

    def test_insight_to_section_mapper_exists(self):
        """A function must exist to map Insight.type → section_id (3/4/7)."""
        try:
            from video_analysis_engine import map_insight_to_section
            assert callable(map_insight_to_section)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"map_insight_to_section function not found: {e}")

    def test_insight_type_coverage(self):
        """All expected insight types must map to valid sections.

        Expected types:
        - "核心洞察" → section 3
        - "深度挖掘" → section 4
        - "价值评估" / "行动建议" → section 7
        """
        try:
            from video_analysis_engine import map_insight_to_section

            mappings = {
                "核心洞察": "3",
                "深度挖掘": "4",
                "价值评估": "7",
                "行动建议": "7"
            }

            for insight_type, expected_section in mappings.items():
                result = map_insight_to_section(insight_type)
                assert result == expected_section, \
                    f"Insight type '{insight_type}' mapped to section {result}, expected {expected_section}"

        except (ImportError, AttributeError, TypeError) as e:
            pytest.fail(f"Insight type mapping test failed: {e}")


class TestClaimEvidencePointer:
    """Test that Claims must have evidence_ids and cannot float without grounding."""

    def test_claim_requires_evidence_ids(self):
        """Claim data structure must require evidence_ids (non-empty).

        Rule: A claim without evidence_ids should be invalid or rejected during construction.
        This test checks if the Claim class enforces this constraint.
        """
        try:
            from video_analysis_engine import Claim

            # Try to create a claim with empty evidence_ids
            with pytest.raises((ValueError, TypeError, AssertionError)):
                claim = Claim(
                    id="C_invalid",
                    text="无证据的主张",
                    confidence=0.8,
                    evidence_ids=[],  # Empty — should be rejected
                    source_type="transcript"
                )

        except (ImportError, AttributeError) as e:
            pytest.fail(f"Claim evidence_ids constraint test failed: {e}")

    def test_extract_claims_returns_grounded_claims(self):
        """extract_claims_from_evidence must return claims with valid evidence_ids.

        All returned claims must have non-empty evidence_ids arrays.
        """
        try:
            from video_analysis_engine import extract_claims_from_evidence

            # Create minimal report dict with evidence
            report = {
                "bvid": "BV_test",
                "plan": {"mode": "full"},
                "subtitle": "字幕证据内容",
                "comments": [{"content": "评论内容"}]
            }

            claims = extract_claims_from_evidence(report, max_claims=5)

            # All claims must have evidence_ids
            for claim in claims:
                assert hasattr(claim, "evidence_ids"), f"Claim {claim.id} missing evidence_ids"
                assert len(claim.evidence_ids) > 0, f"Claim {claim.id} has empty evidence_ids"

        except (ImportError, AttributeError, TypeError) as e:
            pytest.fail(f"extract_claims evidence grounding test failed: {e}")


class TestExtractClaimsFromEvidenceMap:
    """Test that extract_claims_from_evidence correctly reads from evidence_map.by_section."""

    def test_extract_claims_from_evidence_map_transcript(self):
        """extract_claims should read transcript candidates from evidence_map.by_section['3'].

        Verifies:
        - Claims are extracted from evidence_map structure
        - Evidence IDs use E1, E2, E3 format
        - source_type is 'transcript'
        """
        from video_analysis_engine import extract_claims_from_evidence

        # Construct report with evidence_map.by_section['3']
        report = {
            "bvid": "BV_test",
            "evidence_map": {
                "by_section": {
                    "3": [
                        {"source_type": "transcript", "text": "这是第一段字幕内容，包含核心信息点", "score": 0.8},
                        {"source_type": "transcript", "text": "这是第二段字幕内容，提供了详细说明", "score": 0.7},
                        {"source_type": "transcript", "text": "这是第三段字幕内容，总结了关键观点", "score": 0.75}
                    ]
                }
            }
        }

        claims = extract_claims_from_evidence(report, max_claims=5)

        # Should extract 3 claims
        assert len(claims) >= 3, f"Expected at least 3 claims, got {len(claims)}"

        # Check first 3 claims
        for i in range(3):
            claim = claims[i]
            assert claim.source_type == "transcript", f"Claim {i+1} source_type should be transcript"
            assert claim.evidence_ids == [f"E{i+1}"], f"Claim {i+1} evidence_ids should be ['E{i+1}'], got {claim.evidence_ids}"
            assert len(claim.text) > 0, f"Claim {i+1} has empty text"

    def test_build_claim_bundle_distributes_insights_to_sections(self):
        """build_claim_bundle should distribute insights to §3, §4, §7.

        Verifies:
        - Insights are created for multiple target sections
        - At least one insight per section (3, 4, 7)
        - Claims count >= 3, insights count >= 3
        """
        from video_analysis_engine import build_claim_bundle

        # Construct report with mixed evidence
        report = {
            "bvid": "BV_test",
            "evidence_map": {
                "by_section": {
                    "3": [
                        {"source_type": "transcript", "text": "这是核心观点内容，非常重要且有价值", "score": 0.8},
                        {"source_type": "transcript", "text": "为什么会出现这种现象？这是因为底层机制决定的", "score": 0.85}
                    ],
                    "4": [
                        {"source_type": "transcript", "text": "深层机制分析：导致这种结果的逻辑链条", "score": 0.9}
                    ],
                    "7": [
                        {"source_type": "comment", "text": "观众反馈：这个视频很有启发性", "score": 0.6}
                    ]
                }
            }
        }

        bundle = build_claim_bundle(report)

        # Check basic counts
        assert len(bundle.claims) >= 3, f"Expected at least 3 claims, got {len(bundle.claims)}"
        assert len(bundle.insights) >= 3, f"Expected at least 3 insights, got {len(bundle.insights)}"

        # Check target_section distribution
        targets = {insight.target_section for insight in bundle.insights}
        assert "3" in targets, "No insights for section 3"
        assert "4" in targets, "No insights for section 4"
        assert "7" in targets, "No insights for section 7"


class TestAtomicClaimEvidenceGate:
    """P6-A: claim evidence locations are internal, unique, and publishable-gate ready."""

    def _report_with_sections(self):
        return {
            "evidence_map": {
                "by_section": {
                    "3": [
                        {"source_type": "transcript", "text": "§3 的第一条转录证据足够长，能够支撑核心判断。", "score": 0.8},
                        {"source_type": "transcript", "text": "§3 的第二条转录证据足够长，能够支撑后续判断。", "score": 0.8},
                    ],
                    "4": [
                        {"source_type": "transcript", "text": "§4 的第一条转录证据同样足够长，但它不是 §3 的 E1。", "score": 0.9},
                    ],
                }
            }
        }

    def test_extracted_claims_keep_display_id_but_add_unique_internal_location(self):
        from video_analysis_engine import build_claim_bundle, claim_bundle_to_dict

        bundle = build_claim_bundle(self._report_with_sections())
        serialized = claim_bundle_to_dict(bundle)
        locations = {claim["evidence_locations"][0] for claim in serialized["claims"]}

        assert serialized["evidence_contract_version"] == 1
        assert "3:E1" in locations
        assert "4:E1" in locations
        assert all(claim["evidence_ids"][0].startswith("E") for claim in serialized["claims"])

    def test_versioned_bundle_with_missing_location_fails_closed(self):
        from video_analysis_engine import evaluate_claim_evidence_gate

        report = self._report_with_sections()
        report["claim_bundle"] = {
            "evidence_contract_version": 1,
            "claims": [
                {"id": "C1", "source_type": "transcript", "evidence_ids": ["E1"], "evidence_locations": []},
            ],
        }

        result = evaluate_claim_evidence_gate(report)
        assert result["passed"] is False
        assert result["unsupported_claim_ids"] == ["C1"]

    def test_versioned_bundle_with_unresolvable_location_fails_closed(self):
        from video_analysis_engine import evaluate_claim_evidence_gate

        report = self._report_with_sections()
        report["claim_bundle"] = {
            "evidence_contract_version": 1,
            "claims": [
                {
                    "id": "C-missing-index",
                    "source_type": "transcript",
                    "evidence_ids": ["E99"],
                    "evidence_locations": ["3:E99"],
                },
            ],
        }

        result = evaluate_claim_evidence_gate(report)
        assert result["passed"] is False
        assert result["unsupported_claim_ids"] == ["C-missing-index"]
        assert result["claim_scores"][0]["reason"] == "unresolvable_location"

    def test_legacy_bundle_without_contract_version_skips_for_compatibility(self):
        from video_analysis_engine import evaluate_claim_evidence_gate

        report = self._report_with_sections()
        report["claim_bundle"] = {"claims": [{"id": "legacy", "evidence_ids": ["E1"]}]}

        result = evaluate_claim_evidence_gate(report)
        assert result["passed"] is True
        assert result["skipped"] is True
        assert result["reason"] == "legacy_claim_bundle"

    def test_audience_signal_is_partial_not_supported_fact(self):
        from video_analysis_engine import evaluate_claim_evidence_gate

        report = self._report_with_sections()
        report["claim_bundle"] = {
            "evidence_contract_version": 1,
            "claims": [
                {
                    "id": "C-audience",
                    "source_type": "comment",
                    "evidence_ids": ["E1"],
                    "evidence_locations": ["3:E1"],
                },
            ],
        }

        result = evaluate_claim_evidence_gate(report)
        assert result["passed"] is False
        assert result["partial_count"] == 1
        assert result["supported_count"] == 0
