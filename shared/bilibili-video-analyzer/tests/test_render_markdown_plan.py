# -*- coding: utf-8 -*-
"""render_markdown plan-aware skeleton（P2-B2）。

约束：
  - report 含 report_plan.sections 时，render_markdown 按 SectionSpec 顺序输出
    老版 §0–§8 headings（## 0. / ## 1. / ... / ## 8.），不再只输出 ## §1 基本信息。
  - evidence_map.by_section 前 1-3 条注入 skeleton：
      有 url → `> [timestamp](url) text`
      无 url → `> {source_type}证据：text`
    并保留 reason / source_type 标记。
  - verify_report 关注的 §3/§4/§5/§7 给最小子结构，使其不再 "section missing"。
  - 无 report_plan 时退回旧渲染（report['sections']）。
"""

import re

import verify_report
from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    Transcript,
    TranscriptSegment,
    analyze_video,
    render_markdown,
)


OLD_SECTION_NUMS = ["0", "1", "2", "2.5", "3", "4", "5", "6", "7", "8"]


def _input(duration=754):
    return AnalysisInput(
        video_id="BV1xx411c7mD",
        title="AI 应用能融下一轮吗？",
        author="马克汤",
        duration=duration,
        platform="bilibili",
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, "开场：AI 应用融资和 ARR 的现状。", end=20.0),
                TranscriptSegment(150.0, "中段：Cursor、Claude Code 和 wrapper 经济。", end=180.0),
                TranscriptSegment(305.7, "收尾：下一轮估值逻辑会怎么走。", end=330.0),
            ],
            language="zh",
            source="h200-asr-chunked",
        ),
        comments=[Comment("热评补充观点，信息增量很大", likes=42)],
        danmaku=[Danmaku("前排", time=3.0), Danmaku("学到了", time=151.0)],
    )


def _render():
    return render_markdown(analyze_video(_input()))


def test_emits_old_section_headings_not_legacy_only():
    md = _render()
    for num in OLD_SECTION_NUMS:
        pat = re.compile(r"^##\s+" + re.escape(num) + r"\.", re.M)
        assert pat.search(md), f"missing heading ## {num}."
    # 不再只输出旧 demo 的 ## §1 基本信息
    assert "## §1 基本信息" not in md


def test_headings_follow_section_spec_order():
    md = _render()
    nums = re.findall(r"^##\s+([0-9.]+)\.", md, re.M)
    assert nums == OLD_SECTION_NUMS


def test_transcript_evidence_injected_with_timestamp_url():
    md = _render()
    # P5-1: §1 现在走 write_logic_chain_section，输出结构化表格
    assert "### 逻辑链总览" in md
    assert "| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |" in md
    assert "[2:30](https://www.bilibili.com/video/BV1xx411c7mD?t=150)" in md
    assert "transcript" in md


def test_comment_evidence_injected_without_url():
    md = _render()
    # P5-3: §2.5 现在走 write_comments_section，输出热评观点列表
    assert '### 热评观点' in md
    assert '热评补充观点，信息增量很大' in md


def test_section_substructure_present():
    md = _render()
    assert "### 💡" in md            # §3 至少一个洞察小节
    assert re.search(r"###\s*模块\s*1", md)  # §4 至少一个模块
    # §7 现为 LLM writer，无 provider 时 fallback 到 "### 观众反馈 Skeleton"
    assert "### 观众反馈 Skeleton" in md or "### 观众" in md  # §7


def test_verify_report_no_section_missing():
    md = _render()
    results, _overall = verify_report.evaluate(md, "condensed")
    for gid in ["G1", "G3", "G4", "G5", "G7"]:
        measured = results[gid]["measured"]
        assert "section missing" not in measured, f"{gid}: {measured}"
        assert "缺失" not in measured, f"{gid}: {measured}"


def test_section_5_has_blockquote():
    md = _render()
    lines = verify_report.split_into_lines(md)
    start, end = verify_report.find_section(lines, 5)
    assert start is not None
    assert any(ln.lstrip().startswith(">") for ln in lines[start:end])


def test_fallback_without_report_plan_uses_legacy_sections():
    report = {
        "frontmatter": {"title": "x"},
        "sections": {"§1 基本信息": "- 标题: x"},
    }
    md = render_markdown(report)
    assert "## §1 基本信息" in md
    assert "- 标题: x" in md
