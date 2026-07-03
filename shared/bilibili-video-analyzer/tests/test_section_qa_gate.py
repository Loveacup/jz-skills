# -*- coding: utf-8 -*-
"""Unit tests for Section QA gate (Phase 1)."""

from video_analysis_engine import evaluate_draft_section_quality, SectionQualityResult, DimensionResult


class TestEvaluateDraftSectionQuality:

    def test_passing_with_evidence_refs(self):
        body = "这是一个有证据引用的分析段落 [E1]，它说明了因果关系并且包含多个完整句子。这是第二句。"
        result = evaluate_draft_section_quality("3", body)

        assert result.overall_passed is True
        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["evidence-grounded"].passed is True
        assert dims["no-skeleton"].passed is True
        assert result.blockers == []

    def test_passing_mixed_format(self):
        body = (
            "| 时间 | 阶段 | 动作 |\n| --- | --- | --- |\n| 00:10 | 起点 | 提出问题 |\n\n"
            "这段散文说明表格背后的逻辑关系。\n"
            "第二个散文段落包含因果分析。\n"
            "第三个散文段落增加更多正文内容以降低表格占比。\n"
            "第四个散文段落进一步充实可读性。"
        )
        result = evaluate_draft_section_quality("3", body)

        assert result.dimension_results[0].passed  # D1 evidence-grounded (has 00:10)
        assert result.dimension_results[1].passed  # D2 not-mechanical (< 70% table)

    def test_failing_empty_section(self):
        result = evaluate_draft_section_quality("3", "   \n  \n")

        assert result.overall_passed is False
        assert len(result.blockers) >= 1
        assert any("no-skeleton" in b.lower() or "空" in b for b in result.blockers)

    def test_failing_skeleton_residue(self):
        result = evaluate_draft_section_quality("3", "_骨架占位：暂无可用证据。_")

        assert result.overall_passed is False
        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["no-skeleton"].passed is False
        assert any("骨架" in b for b in result.blockers)

    def test_failing_no_evidence(self):
        body = "这是一段散文但没有证据引用也没有时间戳，只是泛泛而谈。这是第二个句子。"
        result = evaluate_draft_section_quality("3", body)

        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["evidence-grounded"].passed is False

    def test_failing_table_only(self):
        body = "| col | col |\n| --- | --- |\n| a | b |\n| c | d |\n| e | f |\n| g | h |\n| i | j |\n| k | l |"
        result = evaluate_draft_section_quality("3", body)

        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["not-mechanical"].passed is False

    def test_mixed_pass_fail_dimensions(self):
        body = "这是一句有观点的话 [E1]但没有句号分隔无法形成两个完整句子因此可读性会失败"
        result = evaluate_draft_section_quality("3", body)

        assert result.overall_passed is False
        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["evidence-grounded"].passed is True
        assert dims["human-readable"].passed is False

    def test_result_structure(self):
        result = evaluate_draft_section_quality("3", "完整段落包含证据 [E1] 和因果关系因此它是可读的。")

        assert result.section_id == "3"
        assert isinstance(result.overall_passed, bool)
        assert len(result.dimension_results) == 5
        assert isinstance(result.word_count, int)
        assert isinstance(result.evidence_refs_count, int)
        assert isinstance(result.time_anchor_count, int)

    def test_issues_sorted_by_priority(self):
        body = "_骨架占位：Skeleton。"  # D5 fail (P0), D1 fail (P1)
        result = evaluate_draft_section_quality("3", body)

        assert len(result.blockers) >= 1
        # blockers are P0; critical_issues P1; improvements P2
        for blocker in result.blockers:
            assert blocker not in result.critical_issues and blocker not in result.improvements
