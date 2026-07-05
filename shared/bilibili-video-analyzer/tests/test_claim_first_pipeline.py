# -*- coding: utf-8 -*-
"""RED tests for Claim-first Pipeline Rules.

These tests verify the behavioral contracts of the claim-first architecture:
1. audit_claims can only keep/downgrade/drop, never raise confidence
2. Insight type → section mapping exists (§3/§4/§7)
3. Comments/danmaku cannot be upgraded to factual claims

They should FAIL initially and PASS after implementing claim pipeline logic.
"""

import pytest


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
