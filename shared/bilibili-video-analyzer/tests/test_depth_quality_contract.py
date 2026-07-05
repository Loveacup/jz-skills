# -*- coding: utf-8 -*-
"""RED tests for Depth Quality Contract — Claim/Insight/ClaimBundle infrastructure.

These tests verify the existence and signature of claim-first architecture components.
They should FAIL initially and PASS after implementing Phase A claim infrastructure.
"""

import pytest


class TestClaimDataStructures:
    """Test existence of Claim, Insight, ClaimBundle data structures."""

    def test_claim_class_exists(self):
        """Claim data structure must exist with required fields."""
        try:
            from video_analysis_engine import Claim
        except (ImportError, AttributeError) as e:
            pytest.fail(f"Claim class not found: {e}")

    def test_insight_class_exists(self):
        """Insight data structure must exist with required fields."""
        try:
            from video_analysis_engine import Insight
        except (ImportError, AttributeError) as e:
            pytest.fail(f"Insight class not found: {e}")

    def test_claim_bundle_class_exists(self):
        """ClaimBundle data structure must exist."""
        try:
            from video_analysis_engine import ClaimBundle
        except (ImportError, AttributeError) as e:
            pytest.fail(f"ClaimBundle class not found: {e}")


class TestClaimPipelineFunctions:
    """Test existence of claim-first pipeline functions."""

    def test_extract_claims_from_evidence_exists(self):
        """extract_claims_from_evidence function must exist."""
        try:
            from video_analysis_engine import extract_claims_from_evidence
            assert callable(extract_claims_from_evidence)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"extract_claims_from_evidence not found: {e}")

    def test_synthesize_insights_from_claims_exists(self):
        """synthesize_insights_from_claims function must exist."""
        try:
            from video_analysis_engine import synthesize_insights_from_claims
            assert callable(synthesize_insights_from_claims)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"synthesize_insights_from_claims not found: {e}")

    def test_audit_claims_exists(self):
        """audit_claims function must exist."""
        try:
            from video_analysis_engine import audit_claims
            assert callable(audit_claims)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"audit_claims not found: {e}")

    def test_build_claim_bundle_exists(self):
        """build_claim_bundle function must exist."""
        try:
            from video_analysis_engine import build_claim_bundle
            assert callable(build_claim_bundle)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"build_claim_bundle not found: {e}")


class TestClaimBundleIntegration:
    """Test DraftReport integration with ClaimBundle."""

    def test_draft_report_has_claim_bundle_field(self):
        """DraftReport must have claim_bundle field."""
        try:
            from video_analysis_engine import DraftReport
            # Create minimal DraftReport to check if claim_bundle field exists
            draft = DraftReport(
                report={"bvid": "BV_test", "plan": {}, "evidence": {}}
            )
            # Check if claim_bundle attribute exists (should default to None)
            assert hasattr(draft, "claim_bundle")
        except (ImportError, AttributeError, TypeError) as e:
            pytest.fail(f"DraftReport.claim_bundle field not found or incompatible: {e}")


class TestClaimHelperFunctions:
    """Test helper functions for claim serialization and formatting."""

    def test_claim_bundle_to_dict_exists(self):
        """claim_bundle_to_dict serialization function must exist."""
        try:
            from video_analysis_engine import claim_bundle_to_dict
            assert callable(claim_bundle_to_dict)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"claim_bundle_to_dict not found: {e}")

    def test_format_claims_for_prompt_exists(self):
        """_format_claims_for_prompt helper must exist for writer integration."""
        try:
            from video_analysis_engine import _format_claims_for_prompt
            assert callable(_format_claims_for_prompt)
        except (ImportError, AttributeError) as e:
            pytest.fail(f"_format_claims_for_prompt not found: {e}")
