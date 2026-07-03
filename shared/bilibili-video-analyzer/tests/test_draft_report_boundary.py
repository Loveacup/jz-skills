# -*- coding: utf-8 -*-
"""Minimal DraftReport / PublishedMarkdown boundary tests."""

import pytest

import verify_publishable_report
from test_verify_publishable_report import _good_report
from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    DraftReport,
    PublishedMarkdown,
    PublishableReportError,
    Transcript,
    TranscriptSegment,
    analyze_video,
    build_draft_report,
    publish_markdown,
    render_debug_markdown,
    render_markdown,
)


def _input():
    return AnalysisInput(
        video_id="BVdraftBoundary",
        title="AI 虚拟偶像测试",
        author="测试作者",
        duration=754,
        platform="bilibili",
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, "开场：提出 AI 虚拟偶像为什么会塌房。", end=20.0),
                TranscriptSegment(150.0, "中段：解释人格资产、粉丝信任和商业化边界。", end=180.0),
                TranscriptSegment(305.7, "收尾：讨论虚拟偶像和真人偶像的治理差异。", end=330.0),
            ],
            language="zh",
            source="h200-asr-chunked",
        ),
        comments=[Comment("这个讨论很适合进入知识库", likes=42)],
        danmaku=[Danmaku("学到了", time=151.0)],
    )


def test_build_draft_report_marks_plan_skeleton_as_non_publishable():
    report = analyze_video(_input())

    draft = build_draft_report(report)

    assert isinstance(draft, DraftReport)
    assert draft.publishable is False
    assert draft.artifact_kind == "draft_report"
    assert draft.debug_render_allowed is True
    assert draft.report["report_plan"]["sections"]


def test_render_debug_markdown_is_explicit_skeleton_path_and_legacy_alias_matches():
    report = analyze_video(_input())
    draft = build_draft_report(report)

    debug_md = render_debug_markdown(draft)
    legacy_md = render_markdown(report)

    assert isinstance(debug_md, str)
    assert debug_md == legacy_md
    assert "Skeleton" in debug_md or "_骨架占位" in debug_md
    assert verify_publishable_report.evaluate(debug_md)[1] is False


def test_publish_markdown_refuses_debug_skeleton_output():
    report = analyze_video(_input())
    debug_md = render_debug_markdown(build_draft_report(report))

    with pytest.raises(PublishableReportError) as exc:
        publish_markdown(debug_md)

    assert "P0_NO_SKELETON" in exc.value.failed_codes
    assert isinstance(exc.value.gates, dict)


def test_publish_markdown_returns_published_markdown_for_good_note():
    published = publish_markdown(_good_report())

    assert isinstance(published, PublishedMarkdown)
    assert published.publishable is True
    assert published.markdown.startswith("# B站笔记_优质样例")
    assert all(gate["pass"] for gate in published.gates.values())
