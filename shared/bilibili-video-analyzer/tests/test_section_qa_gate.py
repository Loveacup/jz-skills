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


# ========== Phase 4: Section exemptions ==========
class TestSectionExemptions:

    def test_section_1_table_exempts_not_mechanical_and_insight_density(self):
        # §1 是结构章节，大量表格是正常的，免除 not-mechanical 和 insight-density
        body = (
            "| 维度 | 值 |\n| --- | --- |\n"
            "| 时长 | 12:34 |\n"
            "| UP主 | 测试用户 |\n"
            "| 发布时间 | 2025-01-01 |\n"
            "| 简介 | 测试简介 [E1] |\n"
            "\n这段简介说明了主题。\n"
            "表格内容已包含时间锚点和证据引用。"
        )
        result = evaluate_draft_section_quality("1", body)

        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["not-mechanical"].passed is True, "§1 not-mechanical should be exempted"
        assert dims["insight-density"].passed is True, "§1 insight-density should be exempted"
        assert result.overall_passed is True
        assert result.blockers == []

    def test_section_5_blockquotes_exempt_not_mechanical_and_insight_density(self):
        # §5 是引文章节，大量 blockquote 是正常的，免除 not-mechanical 和 insight-density
        body = (
            "> 这是第一句引用 [E1]\n"
            "> 这是第二句引用 [E2]\n"
            "> 这是第三句引用，时间点在 03:45\n"
            "> 这是第四句引用内容\n"
            "\n这段话总结引用的核心论点。\n"
            "引文体现了视频的关键观点。"
        )
        result = evaluate_draft_section_quality("5", body)

        dims = {d.dimension: d for d in result.dimension_results}
        assert dims["not-mechanical"].passed is True, "§5 not-mechanical should be exempted"
        assert dims["insight-density"].passed is True, "§5 insight-density should be exempted"
        assert result.overall_passed is True
        assert result.blockers == []

    def test_section_3_not_exempted(self):
        # §3 不在豁免列表中，表格占比过高会失败
        body = (
            "| 时间 | 内容 |\n| --- | --- |\n"
            "| 00:10 | 开始 |\n"
            "| 01:20 | 中间 |\n"
            "| 02:30 | 结束 |\n"
            "| 03:40 | 总结 |\n"
        )
        result = evaluate_draft_section_quality("3", body)

        dims = {d.dimension: d for d in result.dimension_results}
        # §3 没有豁免，表格占比 100% 应该失败
        assert dims["not-mechanical"].passed is False, "§3 should NOT be exempted from not-mechanical"
