# -*- coding: utf-8 -*-
"""DraftReport deterministic writer slice for §1 logic chain and §5 highlights."""

import re

import verify_publishable_report
from test_verify_publishable_report import _good_report
from video_analysis_engine import (
    AnalysisInput,
    Transcript,
    TranscriptSegment,
    analyze_video,
    assemble_draft_report_slice,
    write_highlights_section,
    write_logic_chain_section,
)


def _logic_candidate(text, start=0, url=None, timestamp=None, reason="logic_candidate", source_type="transcript"):
    return {
        "source_type": source_type,
        "section_id": "1",
        "start": start,
        "timestamp": timestamp or f"0:{int(start):02d}",
        "url": url or f"https://www.bilibili.com/video/BVtest?t={int(start)}",
        "text": text,
        "reason": reason,
    }


def _quote_candidate(text, start=0, reason="quote_candidate", source_type="transcript"):
    return {
        "source_type": source_type,
        "section_id": "5",
        "start": start,
        "timestamp": f"0:{int(start):02d}",
        "url": f"https://www.bilibili.com/video/BVtest?t={int(start)}",
        "text": text,
        "reason": reason,
    }


def _replace_section(md: str, sid: str, body: str) -> str:
    pattern = re.compile(rf"(^##\s+{re.escape(sid)}\.\s+.*?$)(.*?)(?=^##\s+(?:\d|2\.5)\.|\Z)", re.M | re.S)
    return pattern.sub(lambda m: m.group(1) + "\n\n" + body.strip() + "\n\n", md)


def test_logic_chain_writer_outputs_table_not_blockquotes():
    body = write_logic_chain_section({
        "evidence": [
            _logic_candidate("开场先提出 AI 虚拟偶像为什么会引发信任问题。", 0),
            _logic_candidate("中段转向粉丝关系、人格资产和商业化之间的张力。", 150),
            _logic_candidate("结尾收束到治理边界：不能把虚拟偶像直接等同真人偶像。", 305),
        ]
    })

    assert "| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |" in body
    assert not any(line.lstrip().startswith(">") for line in body.splitlines())
    ok, reason = verify_publishable_report._logic_chain_structured(body)
    assert ok, reason


def test_logic_chain_writer_filters_non_logic_candidates():
    body = write_logic_chain_section({
        "evidence": [
            _logic_candidate("应该保留的逻辑链候选。", 20),
            _logic_candidate("不应保留的高光候选。", 30, reason="quote_candidate"),
            _logic_candidate("不应保留的评论。", 40, source_type="comments"),
            _logic_candidate("", 50),
        ]
    })

    assert "应该保留的逻辑链候选" in body
    assert "不应保留的高光候选" not in body
    assert "不应保留的评论" not in body


def test_logic_chain_writer_is_deterministic_and_time_sorted():
    evidence = [
        _logic_candidate("晚出现的收束观点。", 150),
        _logic_candidate("早出现的问题提出。", 10),
    ]

    first = write_logic_chain_section({"evidence": evidence})
    second = write_logic_chain_section({"evidence": list(reversed(evidence))})

    assert first == second
    assert first.index("?t=10") < first.index("?t=150")


def test_logic_chain_writer_empty_evidence_is_non_publishable_placeholder():
    body = write_logic_chain_section({"evidence": []})

    assert "_骨架占位" in body
    md = _replace_section(_good_report(), "1", body)
    results, passed = verify_publishable_report.evaluate(md)
    assert passed is False
    assert results["P0_NO_SKELETON"]["pass"] is False


def test_highlights_writer_never_emits_overlong_quote_groups():
    very_long = "这是一句没有明显标点但非常长的高光内容" * 35

    body = write_highlights_section({
        "quality_gate": "G5",
        "evidence": [_quote_candidate(very_long, 12)],
    })

    md = _replace_section(_good_report(), "5", body)
    results, _passed = verify_publishable_report.evaluate(md)
    assert results["P1_SHORT_HIGHLIGHTS"]["pass"] is True
    for group in verify_publishable_report._blockquote_groups(body):
        assert len(group) <= 300


def test_assemble_draft_report_slice_only_writes_1_and_5():
    inp = AnalysisInput(
        video_id="BVslice",
        title="Draft slice test",
        duration=360,
        platform="bilibili",
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, "开场提出问题：为什么虚拟偶像需要不同治理。", end=20.0),
                TranscriptSegment(120.0, "中段展开机制：粉丝信任来自连续人格资产。", end=150.0),
                TranscriptSegment(300.0, "结尾形成结论：商业化必须保留边界。", end=330.0),
            ],
            language="zh",
            source="h200-asr-chunked",
        ),
    )
    report = analyze_video(inp)

    draft = assemble_draft_report_slice(report)

    assert draft.publishable is False
    assert set(draft.draft_sections) == {"1", "5"}
    assert "| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |" in draft.draft_sections["1"]
    assert "### 高光时刻" in draft.draft_sections["5"]


def test_draft_report_qa_gate_non_skeleton_failing_section_inserted_with_warning(monkeypatch):
    """Phase 2: QA-failing but non-skeleton section 1 is inserted with warning."""
    failing_body = "| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |\n|---|---|---|---|---|\n| 0:00 | 开场 | 提出问题 | 虚拟偶像为什么需要治理 | [链接](https://example.com) |"

    def mock_write_logic_chain(ctx):
        return failing_body

    monkeypatch.setattr("video_analysis_engine.write_logic_chain_section", mock_write_logic_chain)

    inp = AnalysisInput(
        video_id="BVqa1",
        title="QA gate test 1",
        duration=360,
        platform="bilibili",
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, "开场提出问题", end=20.0)],
            language="zh",
            source="test",
        ),
    )
    report = analyze_video(inp)
    draft = assemble_draft_report_slice(report, section_ids=("1",))

    assert "1" in draft.draft_sections
    assert draft.draft_sections["1"] == failing_body
    assert "1" in draft.qa_results
    assert not draft.qa_results["1"].overall_passed
    assert any("§1" in w and "QA" in w for w in draft.warnings)


def test_draft_report_qa_gate_skeleton_section_blocked_from_insertion(monkeypatch):
    """Phase 2: skeleton section 5 is blocked from insertion with blocker warning."""
    skeleton_body = "### 高光时刻 Draft Placeholder\n\n_骨架占位：高光时刻 待 writer 基于证据填充。_"

    def mock_write_highlights(ctx):
        return skeleton_body

    monkeypatch.setattr("video_analysis_engine.write_highlights_section", mock_write_highlights)

    inp = AnalysisInput(
        video_id="BVqa5",
        title="QA gate test 5",
        duration=360,
        platform="bilibili",
        transcript=Transcript(
            segments=[TranscriptSegment(0.0, "测试内容", end=20.0)],
            language="zh",
            source="test",
        ),
    )
    report = analyze_video(inp)
    draft = assemble_draft_report_slice(report, section_ids=("5",))

    assert "5" not in draft.draft_sections
    assert "5" in draft.qa_results
    assert draft.qa_results["5"].blockers
    assert "D5" in draft.qa_results["5"].blockers[0] or "no-skeleton" in draft.qa_results["5"].blockers[0]
    assert any("§5" in w and "QA" in w and "blocked" in w for w in draft.warnings)
