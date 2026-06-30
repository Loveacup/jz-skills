# -*- coding: utf-8 -*-
"""ReportPlan / SectionSpec：内容引擎规划层契约。

这层的任务不是替换老版报告框架，而是把老版 §0–§8 显式建模，
让后续生成、WRR扩展和质量门都围绕这份 plan 工作。
"""

from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    Transcript,
    TranscriptSegment,
    analyze_video,
    build_evidence_source_gate,
    build_report_plan,
)


OLD_FULL_SECTION_IDS = ["0", "1", "2", "2.5", "3", "4", "5", "6", "7", "8"]


def _input_with_transcript(duration=3600, comments=True, danmaku=True):
    return AnalysisInput(
        video_id="BVplan",
        title="AI 应用能融下一轮吗？",
        author="马克汤",
        duration=duration,
        transcript=Transcript(
            segments=[
                TranscriptSegment(0, "第一段讲 AI 应用融资和 ARR。"),
                TranscriptSegment(60, "第二段讲 Cursor、Claude Code 和 wrapper 经济。"),
            ],
            language="zh",
            source="h200-asr-chunked",
        ),
        comments=[Comment("评论补充", likes=10)] if comments else [],
        danmaku=[Danmaku("弹幕反馈", time=10)] if danmaku else [],
    )


def test_full_report_plan_preserves_old_section_framework():
    """全量版必须以老版 §0–§8 为基底，而不是 BiliNote 的 generic note template。"""
    inp = _input_with_transcript(duration=6300)
    gate = build_evidence_source_gate(inp)

    plan = build_report_plan(inp, gate)

    assert plan.mode == "full"
    assert plan.baseline == "old_bilibili_v3_framework"
    assert [s.id for s in plan.sections] == OLD_FULL_SECTION_IDS
    assert plan.sections[0].title == "元信息 (Meta)"
    assert plan.sections[1].title == "逻辑链 (Logic Chain)"
    assert plan.sections[4].title == "核心洞察 (Key Insights)"
    assert plan.sections[5].min_items >= 3  # Deep Dive modules
    assert plan.sections[5].min_words_per_item >= 500
    assert "BiliNote: RequestChunker/checkpoint as long-context inspiration" in plan.absorbed_patterns
    assert "OpenNote: timestamped retrieval/citation for evidence-backed sections" in plan.absorbed_patterns
    assert "NoteTaker-py: chunk salience + clustering as future section planner" in plan.absorbed_patterns


def test_condensed_plan_keeps_g7_full_and_marks_sparse_social_sections_optional():
    """精简版可以收缩弹幕/评论/Deep Dive，但 §7 批判行动不能削弱。"""
    inp = _input_with_transcript(duration=900, comments=False, danmaku=False)
    gate = build_evidence_source_gate(inp)

    plan = build_report_plan(inp, gate)

    assert plan.mode == "condensed"
    by_id = {s.id: s for s in plan.sections}
    assert by_id["2"].required is False
    assert by_id["2.5"].required is False
    assert by_id["4"].min_items == 2
    assert by_id["7"].required is True
    assert by_id["7"].quality_gate == "G7"
    assert by_id["7"].min_items == 8  # 3价值 + 2局限 + 3行动


def test_plan_blocks_formal_report_without_transcript_but_keeps_preanalysis_shape():
    """无 transcript 时不允许正式稿，但 plan 仍可说明只能做预分析。"""
    inp = AnalysisInput(video_id="BVnoasr", title="无字幕视频")
    gate = build_evidence_source_gate(inp)

    plan = build_report_plan(inp, gate)

    assert plan.can_generate_formal_report is False
    assert plan.blocking_reason == "missing_transcript"
    assert plan.mode == "preanalysis"
    assert [s.id for s in plan.sections] == ["0", "8"]
    assert all(s.allowed for s in plan.sections)


def test_analyze_video_exposes_report_plan_dict():
    inp = _input_with_transcript(duration=6300)

    report = analyze_video(inp)

    assert report["report_plan"]["mode"] == "full"
    assert report["report_plan"]["baseline"] == "old_bilibili_v3_framework"
    assert [s["id"] for s in report["report_plan"]["sections"]] == OLD_FULL_SECTION_IDS
