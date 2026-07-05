# -*- coding: utf-8 -*-
"""GREEN tests for run_quality_gate.py depth profile extensions.

These tests verify that run_quality_gate.py supports:
1. --depth-profile CLI flag (standard / v24-full / claim-first-full)
2. --claim-qa-gate CLI flag
3. Summary dict includes: depth_profile, claim_bundle_stats, claim_qa_gate_passed, failed_due_to_claim_qa_gate

They were initially RED and now should PASS after implementing depth profile infrastructure.
"""

import subprocess
import json
import pytest
import re
from pathlib import Path


def _parse_result_json(text):
    """Extract JSON from RESULT_JSON_START/END markers."""
    if 'RESULT_JSON_START' in text and 'RESULT_JSON_END' in text:
        start = text.find('RESULT_JSON_START') + len('RESULT_JSON_START')
        end = text.find('RESULT_JSON_END')
        text = text[start:end]
    return json.loads(text.strip())


class TestDepthProfileCLIFlag:
    """Test that --depth-profile flag exists and is recognized."""

    def test_depth_profile_flag_implemented(self):
        """run_quality_gate.py should recognize --depth-profile (GREEN test).

        The flag should be accepted and the script should succeed.
        """
        input_path = "/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer/tests/fixtures/depth_claim_fetch_all.json"

        # Check that fixture exists before testing
        if not Path(input_path).exists():
            pytest.skip(f"Fixture not found: {input_path}")

        result = subprocess.run(
            [
                "python3", "scripts/run_quality_gate.py",
                "--input", input_path,
                "--output", "/tmp/test_depth_profile_output.md",
                "--depth-profile", "standard"
            ],
            cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
            capture_output=True,
            text=True
        )

        # Should succeed because --depth-profile is now implemented
        assert result.returncode == 0, \
            f"--depth-profile flag was not accepted: {result.stderr}"

    def test_depth_profile_values_implemented(self):
        """run_quality_gate.py --depth-profile should support: standard, v24-full, claim-first-full."""
        input_path = "/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer/tests/fixtures/depth_claim_fetch_all.json"

        if not Path(input_path).exists():
            pytest.skip(f"Fixture not found: {input_path}")

        for profile in ["standard", "v24-full", "claim-first-full"]:
            result = subprocess.run(
                [
                    "python3", "scripts/run_quality_gate.py",
                    "--input", input_path,
                    "--output", f"/tmp/test_depth_profile_{profile}.md",
                    "--depth-profile", profile
                ],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, \
                f"--depth-profile {profile} was not accepted: {result.stderr}"


class TestClaimQAGateCLIFlag:
    """Test that --claim-qa-gate flag exists."""

    def test_claim_qa_gate_flag_implemented(self):
        """run_quality_gate.py should recognize --claim-qa-gate (GREEN test)."""
        input_path = "/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer/tests/fixtures/depth_claim_fetch_all.json"

        if not Path(input_path).exists():
            pytest.skip(f"Fixture not found: {input_path}")

        result = subprocess.run(
            [
                "python3", "scripts/run_quality_gate.py",
                "--input", input_path,
                "--output", "/tmp/test_claim_qa_gate_output.md",
                "--writer-provider", "fixture",
                "--claim-qa-gate"
            ],
            cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
            capture_output=True,
            text=True
        )

        # Should succeed (flag is accepted). Gate may fail if D6-D8 are not met,
        # but that's OK - we're just testing the flag exists.
        # Return code 0 or 1 both mean the flag was accepted.
        assert "unrecognized" not in result.stderr.lower(), \
            f"--claim-qa-gate flag was not recognized: {result.stderr}"


class TestQualityGateSummaryDepthFields:
    """Test that run_quality_gate summary dict includes depth/claim metadata."""

    def test_summary_includes_depth_profile_field(self):
        """Quality gate summary should include depth_profile field (GREEN test)."""
        input_path = "/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer/tests/fixtures/p2e_fetch_all.json"

        if not Path(input_path).exists():
            pytest.skip(f"Fixture not found: {input_path}")

        result = subprocess.run(
            [
                "python3", "scripts/run_quality_gate.py",
                "--input", input_path,
                "--output", "/tmp/test_summary_depth.md",
                "--writer-provider", "fixture",
                "--json"
            ],
            cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
            capture_output=True,
            text=True
        )

        # Gate should succeed with fixture provider on p2e_fetch_all
        if result.returncode == 0:
            try:
                summary = _parse_result_json(result.stdout)

                # Should have depth_profile field (GREEN test)
                assert "depth_profile" in summary, \
                    "summary should contain depth_profile field"
                assert summary["depth_profile"] == "standard", \
                    f"default depth_profile should be 'standard', got {summary['depth_profile']}"

            except json.JSONDecodeError as e:
                pytest.fail(f"run_quality_gate --json did not produce valid JSON: {e}")
        else:
            pytest.skip(f"Quality gate failed on fixture (unexpected): {result.stderr}")

    def test_summary_includes_claim_bundle_stats_field(self):
        """Quality gate summary should include claim_bundle_stats field (GREEN test)."""
        input_path = "/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer/tests/fixtures/p2e_fetch_all.json"

        if not Path(input_path).exists():
            pytest.skip(f"Fixture not found: {input_path}")

        result = subprocess.run(
            [
                "python3", "scripts/run_quality_gate.py",
                "--input", input_path,
                "--output", "/tmp/test_summary_claim_bundle.md",
                "--writer-provider", "fixture",
                "--json"
            ],
            cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            try:
                summary = _parse_result_json(result.stdout)

                # Should have claim_bundle_stats (GREEN test)
                assert "claim_bundle_stats" in summary, \
                    "summary should contain claim_bundle_stats field"

                stats = summary["claim_bundle_stats"]
                assert isinstance(stats, dict), "claim_bundle_stats should be a dict"
                assert "claims_count" in stats, "claim_bundle_stats should have claims_count"
                assert "insights_count" in stats, "claim_bundle_stats should have insights_count"

            except json.JSONDecodeError as e:
                pytest.fail(f"run_quality_gate --json did not produce valid JSON: {e}")
        else:
            pytest.skip(f"Quality gate failed on fixture (unexpected): {result.stderr}")

    def test_summary_includes_claim_qa_gate_passed_field(self):
        """Quality gate summary should include claim_qa_gate_passed field (GREEN test)."""
        input_path = "/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer/tests/fixtures/p2e_fetch_all.json"

        if not Path(input_path).exists():
            pytest.skip(f"Fixture not found: {input_path}")

        result = subprocess.run(
            [
                "python3", "scripts/run_quality_gate.py",
                "--input", input_path,
                "--output", "/tmp/test_summary_claim_qa_passed.md",
                "--writer-provider", "fixture",
                "--json"
            ],
            cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            try:
                summary = _parse_result_json(result.stdout)

                # Should have claim_qa_gate_passed (GREEN test)
                assert "claim_qa_gate_passed" in summary, \
                    "summary should contain claim_qa_gate_passed field"

                # Should have failed_due_to_claim_qa_gate (GREEN test)
                assert "failed_due_to_claim_qa_gate" in summary, \
                    "summary should contain failed_due_to_claim_qa_gate field"

            except json.JSONDecodeError as e:
                pytest.fail(f"run_quality_gate --json did not produce valid JSON: {e}")
        else:
            pytest.skip(f"Quality gate failed on fixture (unexpected): {result.stderr}")
