# -*- coding: utf-8 -*-
"""test_published_markdown_boundary.py — publish_markdown() signature boundary tests.

Verifies that the updated publish_markdown(markdown, report=None) preserves
backward-compatible Markdown-only behavior and integrates the report-aware gate.
"""

import pytest

from video_analysis_engine import (
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    PublishedMarkdown,
    PublishableReportError,
    analyze_video,
    render_debug_markdown,
    publish_markdown,
)


def _good_markdown() -> str:
    """Minimal markdown satisfying all Markdown-only publishable gates."""
    return (
        "## 0. 元信息\n\n### 视频元信息\n\n- **标题**：示例\n\n"
        "## 1. 逻辑链\n\n| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |\n"
        "| --- | --- | --- | --- | --- |\n| 0:00 | 起点 | 提出问题 | 示例 |  |\n\n"
        "## 2. 弹幕信号\n\n正文示例。\n\n"
        "## 2.5 评论\n\n正文示例。\n\n"
        "## 3. 核心洞察\n\n### 💡 洞察：内容直接反映用户体验\n\n"
        "这个内容用了超过二十个汉字进行描述让它能够超过最低门槛要求符合稀疏模式的洞察标准。\n\n"
        "## 4. 深度拆解\n\n### 模块 1: 主要功能模块\n\n"
        "这个模块同样使用了超过二十个汉字进行描述让它能够超过最低词数门槛要求符合稀疏模式。\n\n"
        "## 5. 高光时刻\n\n> \"这是一个高光引用段落，展示了视频核心内容。\"\n\n"
        "## 6. 知识图谱\n\n- [[示例概念]]\n\n"
        "## 7. 批判与行动\n\n### 独特价值\n\n- 独特视角展示\n\n"
        "### 局限\n\n- 证据来源单一\n\n"
        "### 可行动\n\n- 立即尝试该方法\n\n"
        "## 8. 附录\n\n正文示例。\n"
    )


def _sparse_report():
    text = (
        '长征十号乙运载火箭完成一子级发射回收，标志着中国商业航天实现重要突破。'
    )
    inp = AnalysisInput(
        video_id='DY_ROCKET_BND_001',
        title='长征十号乙运载火箭发射回收',
        description='发射回收现场实录。',
        author='直播号',
        duration=92,
        platform='douyin',
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, text)],
            language='zh',
            source='h200-asr',
        ),
    )
    report = analyze_video(inp)
    md = render_debug_markdown(report)
    return report, md


# ─── Backward compatibility: no report argument ───────────────────────────────

def test_publish_markdown_no_report_returns_published_markdown():
    """publish_markdown(md) without report must still work (backward compat)."""
    pm = publish_markdown(_good_markdown())

    assert isinstance(pm, PublishedMarkdown)
    assert pm.publishable is True
    assert 'P0_SPARSE_REPORT_FIDELITY' not in pm.gates


def test_publish_markdown_no_report_raises_for_skeleton():
    bad = "## 0. 元信息\n\n_骨架占位：待填充。_\n"

    with pytest.raises(PublishableReportError) as exc_info:
        publish_markdown(bad)

    assert 'P0_NO_SKELETON' in exc_info.value.failed_codes
    assert exc_info.value.gates['P0_NO_SKELETON']['pass'] is False


def test_publish_markdown_no_report_raises_for_missing_sections():
    with pytest.raises(PublishableReportError) as exc_info:
        publish_markdown("# 只有标题\n\n没有分节。\n")

    assert 'P0_REQUIRED_SECTIONS' in exc_info.value.failed_codes


# ─── Report-aware path ────────────────────────────────────────────────────────

def test_publish_markdown_with_sparse_report_adds_fidelity_gate():
    report, md = _sparse_report()

    pm = publish_markdown(md, report)

    assert isinstance(pm, PublishedMarkdown)
    assert 'P0_SPARSE_REPORT_FIDELITY' in pm.gates
    assert pm.gates['P0_SPARSE_REPORT_FIDELITY']['pass'] is True


def test_publish_markdown_with_report_none_equal_to_no_report():
    """publish_markdown(md, report=None) must behave identically to publish_markdown(md)."""
    md = _good_markdown()

    pm1 = publish_markdown(md)
    pm2 = publish_markdown(md, report=None)

    assert pm1.markdown == pm2.markdown
    assert set(pm1.gates.keys()) == set(pm2.gates.keys())


def test_publish_markdown_with_non_sparse_report_skips_fidelity_gate():
    """For full/condensed report, the fidelity gate must be skipped (absent from gates)."""
    full_report = {'report_plan': {'mode': 'full'}}
    md = _good_markdown()

    pm = publish_markdown(md, full_report)

    assert 'P0_SPARSE_REPORT_FIDELITY' not in pm.gates


def test_publish_markdown_raises_publishable_report_error_with_failed_codes():
    """PublishableReportError must expose failed_codes and gates on failure."""
    bad = "## 0. 元信息\n\n_骨架占位：待填充。_\n"

    with pytest.raises(PublishableReportError) as exc_info:
        publish_markdown(bad, report=None)

    err = exc_info.value
    assert isinstance(err.failed_codes, list)
    assert isinstance(err.gates, dict)
    assert len(err.failed_codes) >= 1
