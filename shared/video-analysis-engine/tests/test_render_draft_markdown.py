# -*- coding: utf-8 -*-
"""DraftReport non-publishable preview renderer tests."""

import verify_publishable_report
from video_analysis_engine import (
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    analyze_video,
    build_draft_report,
    render_debug_markdown,
    render_draft_markdown,
    render_markdown,
)


def _draft_with_sections():
    inp = AnalysisInput(
        video_id="BVdraftPreview",
        title="Draft preview test",
        author="测试作者",
        duration=600,
        platform="bilibili",
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, "问题起点。", end=10.0),
                TranscriptSegment(20.0, "机制推进。", end=30.0),
                TranscriptSegment(40.0, "结论收束。", end=50.0),
            ],
            language="zh",
            source="h200-asr",
        ),
    )
    report = analyze_video(inp)
    draft = build_draft_report(report)
    draft.draft_sections["1"] = "| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |\n| --- | --- | --- | --- | --- |\n| 00:00 | 起点 | 提出问题 | 手写 §1 preview |  |"
    draft.draft_sections["3"] = "### 💡 洞察 1：手写 preview [E1]\n这是一段手写的 DraftReport preview 内容，用于验证覆盖 legacy skeleton。"
    draft.draft_sections["5"] = "> \"手写高光 preview。\" — [00:40](https://example.com)"
    return report, draft


def test_render_draft_markdown_overlays_draft_sections_without_publishing():
    _report, draft = _draft_with_sections()

    preview = render_draft_markdown(draft)

    assert "<!-- artifact_kind: draft_markdown_preview; publishable: false -->" in preview
    assert "| 00:00 | 起点 | 提出问题 | 手写 §1 preview |" in preview
    assert "### 💡 洞察 1：手写 preview" in preview
    assert "> \"手写高光 preview。\"" in preview
    assert "## 1. 逻辑链" in preview
    assert "## 3. 核心洞察" in preview
    assert "## 5. 高光时刻" in preview
    assert verify_publishable_report.evaluate(preview)[1] is False


def test_render_draft_markdown_does_not_mutate_legacy_debug_renderer():
    report, draft = _draft_with_sections()

    preview = render_draft_markdown(draft)
    debug_md = render_debug_markdown(draft)
    legacy_md = render_markdown(report)

    assert "手写 §1 preview" in preview
    assert "手写 §1 preview" not in debug_md
    assert debug_md == legacy_md


def test_render_draft_markdown_requires_draft_report():
    report, _draft = _draft_with_sections()

    try:
        render_draft_markdown(report)
        assert False, "expected TypeError"
    except TypeError as e:
        assert "DraftReport" in str(e)
