# -*- coding: utf-8 -*-
"""RED tests for verify_report.py claim-first extensions.

These tests verify that verify_report.py supports:
1. --depth full/condensed as an alias for --mode
2. --claim-first flag for enabling claim-specific gates (G8/G9/G10)
3. G8: §3 insights have claim/evidence/warrant/boundary
4. G9: §4 modules have explicit/implicit/meta-narrative structure
5. G10: §7 action items have evidence refs or claim IDs

They should FAIL initially and PASS after implementing claim-first gates.
"""

import subprocess
import tempfile
import json
import pytest
from pathlib import Path


class TestVerifyReportDepthAlias:
    """Test that --depth full/condensed works as alias for --mode."""

    def test_depth_full_flag_recognized(self):
        """verify_report.py --depth full should be accepted (alias for --mode full).

        GREEN: The flag is now implemented and should work as an alias for --mode full.
        """
        # Create a minimal valid report
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# 视频分析报告\n\n## 1. 逻辑链\n\n内容\n")
            report_path = f.name

        try:
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--depth", "full"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            # Should run successfully (exit code 0 or 1 depending on gate results)
            assert result.returncode in (0, 1), \
                f"--depth full should be recognized, got returncode {result.returncode}"

            # Should mention mode=full in output
            assert "mode=full" in result.stdout, \
                f"Expected mode=full in output, got: {result.stdout[:200]}"

            # Should not have unrecognized argument error
            assert "unrecognized" not in result.stderr.lower(), \
                f"Should not have unrecognized argument error: {result.stderr}"

        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_depth_condensed_flag_recognized(self):
        """verify_report.py --depth condensed should be accepted.

        GREEN: The flag is now implemented and should work as an alias for --mode condensed.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# 视频分析报告\n\n## 1. 逻辑链\n\n内容\n")
            report_path = f.name

        try:
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--depth", "condensed"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            # Should run successfully
            assert result.returncode in (0, 1), \
                f"--depth condensed should be recognized, got returncode {result.returncode}"

            # Should mention mode=condensed in output
            assert "mode=condensed" in result.stdout, \
                f"Expected mode=condensed in output, got: {result.stdout[:200]}"

        finally:
            Path(report_path).unlink(missing_ok=True)


class TestVerifyReportClaimFirstFlag:
    """Test that --claim-first flag exists and enables claim-specific gates."""

    def test_claim_first_flag_recognized(self):
        """verify_report.py --claim-first should be a valid flag.

        GREEN: The flag is now implemented and enables G8/G9/G10 gates.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# 视频分析报告\n\n## 1. 逻辑链\n\n内容\n")
            report_path = f.name

        try:
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--claim-first"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            # Should run successfully
            assert result.returncode in (0, 1), \
                f"--claim-first should be recognized, got returncode {result.returncode}"

            # Should mention claim-first=on in output
            assert "claim-first=on" in result.stdout, \
                f"Expected claim-first=on in output, got: {result.stdout[:200]}"

            # Should not have unrecognized argument error
            assert "unrecognized" not in result.stderr.lower(), \
                f"Should not have unrecognized argument error: {result.stderr}"

        finally:
            Path(report_path).unlink(missing_ok=True)


class TestClaimFirstGatesG8G9G10:
    """Test claim-first quality gates G8/G9/G10 (currently unimplemented)."""

    def test_g8_section3_warrant_boundary_gate_implemented(self):
        """G8: §3 insights must have claim/warrant/rebuttal structure.

        GREEN: When --claim-first is enabled, verify_report.py checks that each
        §3 insight subsection contains claim/warrant/evidence/boundary keywords.
        """
        # Create a report with §3 insights that have claim-first structure
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# 视频分析报告

## 1. 逻辑链

内容

## 3. 核心洞察

### 💡 洞察 1：主张示例

这是一个主张 [E1]。因为有证据支持，所以我们可以推理出这个结论。但是需要注意边界条件。

### 💡 洞察 2：含 warrant

基于 [E2] 的证据，我们可以得出结论。这个推理是有许可的。

### 💡 洞察 3：含反证

主张 [E3]。然而也存在反证。
""")
            report_path = f.name

        try:
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--claim-first", "--json"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            # Should include G8 gate in output
            assert "G8" in result.stdout, "G8 gate should appear when --claim-first is used"

            # Parse JSON output to check g8_passed field
            if "RESULT_JSON_START" in result.stdout:
                json_start = result.stdout.index("RESULT_JSON_START") + len("RESULT_JSON_START")
                json_end = result.stdout.index("RESULT_JSON_END")
                json_str = result.stdout[json_start:json_end].strip()
                output = json.loads(json_str)

                assert "g8_passed" in output, "JSON output should include g8_passed field"
                assert output["g8_passed"] is True, "G8 should pass with claim-first keywords"

        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_g9_section4_narrative_layers_gate_implemented(self):
        """G9: §4 modules must have explicit/implicit/meta-narrative structure.

        GREEN: When --claim-first is enabled, verify_report.py checks that each
        §4 module subsection contains narrative layer keywords.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# 视频分析报告

## 1. 逻辑链

内容

## 4. 内容深度拆解

### 模块 1：显性逻辑分析

表层逻辑显示了明确的因果关系。

### 模块 2：隐性动力

隐性假设揭示了深层机制。

### 模块 3：元叙事

系统性视角下的结构分析。
""")
            report_path = f.name

        try:
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--claim-first", "--json"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            assert "G9" in result.stdout, "G9 gate should appear when --claim-first is used"

            if "RESULT_JSON_START" in result.stdout:
                json_start = result.stdout.index("RESULT_JSON_START") + len("RESULT_JSON_START")
                json_end = result.stdout.index("RESULT_JSON_END")
                json_str = result.stdout[json_start:json_end].strip()
                output = json.loads(json_str)

                assert "g9_passed" in output, "JSON output should include g9_passed field"
                assert output["g9_passed"] is True, "G9 should pass with narrative layer keywords"

        finally:
            Path(report_path).unlink(missing_ok=True)

    def test_g10_section7_action_evidence_gate_implemented(self):
        """G10: §7 action items must reference evidence or claim IDs.

        GREEN: When --claim-first is enabled, verify_report.py checks that each
        行动项 in §7 contains evidence/claim references.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# 视频分析报告

## 1. 逻辑链

内容

## 7. 批判与行动

### 独特价值

- 价值 1
- 价值 2
- 价值 3

### 局限与偏见

- 局限 1
- 局限 2

### 可行动项

- 立即执行：基于 [E1] 的发现采取行动
- 短期跟进：参考 [C2] 制定计划
- 长期探索：根据 12:34 时间点的内容
""")
            report_path = f.name

        try:
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--claim-first", "--json"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            assert "G10" in result.stdout, "G10 gate should appear when --claim-first is used"

            if "RESULT_JSON_START" in result.stdout:
                json_start = result.stdout.index("RESULT_JSON_START") + len("RESULT_JSON_START")
                json_end = result.stdout.index("RESULT_JSON_END")
                json_str = result.stdout[json_start:json_end].strip()
                output = json.loads(json_str)

                assert "g10_passed" in output, "JSON output should include g10_passed field"
                assert output["g10_passed"] is True, "G10 should pass with evidence references"

        finally:
            Path(report_path).unlink(missing_ok=True)


class TestClaimFirstJSONOutput:
    """Test that --claim-first results appear in JSON output."""

    def test_json_output_includes_claim_first_status(self):
        """When --claim-first --json is used, output should include claim_first_enabled field.

        GREEN: verify_report.py now tracks claim-first status in JSON output.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# 视频分析报告\n\n## 1. 逻辑链\n\n内容\n")
            report_path = f.name

        try:
            # Test with --claim-first
            result = subprocess.run(
                ["python3", "scripts/verify_report.py", report_path, "--claim-first", "--json"],
                cwd="/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer",
                capture_output=True,
                text=True
            )

            if result.returncode in (0, 1):
                # Parse JSON output
                if "RESULT_JSON_START" in result.stdout:
                    json_start = result.stdout.index("RESULT_JSON_START") + len("RESULT_JSON_START")
                    json_end = result.stdout.index("RESULT_JSON_END")
                    json_str = result.stdout[json_start:json_end].strip()

                    try:
                        output = json.loads(json_str)

                        # Should have claim_first fields
                        assert "claim_first_enabled" in output, \
                            "claim_first_enabled should be in JSON output"
                        assert output["claim_first_enabled"] is True, \
                            "claim_first_enabled should be True when --claim-first is used"

                        assert "g8_passed" in output, \
                            "g8_passed should be in JSON output when --claim-first is used"
                        assert "g9_passed" in output, \
                            "g9_passed should be in JSON output when --claim-first is used"
                        assert "g10_passed" in output, \
                            "g10_passed should be in JSON output when --claim-first is used"

                    except json.JSONDecodeError as e:
                        pytest.fail(f"verify_report.py --json did not produce valid JSON: {e}\n{json_str}")
                else:
                    pytest.fail("No RESULT_JSON_START found in output")

        finally:
            Path(report_path).unlink(missing_ok=True)
