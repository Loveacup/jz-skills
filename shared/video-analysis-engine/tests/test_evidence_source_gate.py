# -*- coding: utf-8 -*-
"""EvidenceSourceGate：报告生成前的来源充分性契约。

目标：verify_report.py 只管结构深度；EvidenceSourceGate 负责回答“这份报告能引用什么证据”。
"""

import fetch_all
from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    Transcript,
    TranscriptSegment,
    analyze_video,
    build_evidence_source_gate,
)


def test_evidence_gate_blocks_formal_report_without_transcript():
    inp = AnalysisInput(
        video_id="BVgate",
        title="无字幕视频",
        comments=[Comment("热评", likes=3)],
        danmaku=[Danmaku("弹幕")],
    )

    gate = build_evidence_source_gate(inp)

    assert gate["can_generate_formal_report"] is False
    assert gate["blocking_reason"] == "missing_transcript"
    assert gate["sources"]["transcript"]["available"] is False
    assert gate["sections"]["§2 内容分析"]["allowed"] is False
    assert "transcript" in gate["sections"]["§2 内容分析"]["requires"]


def test_evidence_gate_maps_available_sources_to_sections():
    inp = AnalysisInput(
        video_id="BVgate",
        title="有字幕视频",
        transcript=Transcript(
            segments=[TranscriptSegment(0, "第一句话"), TranscriptSegment(5, "第二句话")],
            language="zh",
            source="h200-asr-chunked",
        ),
        comments=[Comment("热评", likes=3)],
        danmaku=[Danmaku("弹幕")],
        fact_checks={"claims": [{"claim": "A", "verdict": "uncertain"}]},
    )

    gate = build_evidence_source_gate(inp)

    assert gate["can_generate_formal_report"] is True
    assert gate["blocking_reason"] == ""
    assert gate["sources"]["transcript"] == {
        "available": True,
        "source": "h200-asr-chunked",
        "language": "zh",
        "segments": 2,
        "chars": 9,
    }
    assert gate["sections"]["§2 内容分析"]["allowed"] is True
    assert gate["sections"]["§3 评论分析"]["evidence"] == ["comments", "danmaku"]
    assert gate["sections"]["§4 关键声明核查"]["allowed"] is True


def test_analyze_video_exposes_evidence_gate_and_frontmatter_summary():
    inp = AnalysisInput(
        video_id="BVgate",
        title="有字幕视频",
        transcript=Transcript(
            segments=[TranscriptSegment(0, "正文")],
            language="zh",
            source="official",
        ),
    )

    report = analyze_video(inp)

    assert report["evidence_gate"]["can_generate_formal_report"] is True
    assert report["frontmatter"]["evidence_transcript_source"] == "official"
    assert report["frontmatter"]["evidence_gate"] == "pass"


def test_fetch_all_report_gate_uses_evidence_gate_over_legacy_has_transcript(monkeypatch):
    """以后 fetch_all 的正式报告 gate 读 evidence_gate，而不是散落判断 has_transcript。"""
    bvid = "BV_EVIDENCE_GATE"

    def fake_report_markdown(results, run_fact_check=True):
        return (
            "# should be blocked\n",
            {
                "frontmatter": {"has_transcript": True},  # legacy 字段即使误报，也不能放行
                "evidence_gate": {
                    "can_generate_formal_report": False,
                    "blocking_reason": "missing_transcript",
                },
            },
        )

    import generate_report
    monkeypatch.setattr(generate_report, "report_markdown", fake_report_markdown)

    assert fetch_all.generate_report({"bvid": bvid}, bvid) is None


def test_evidence_gate_prefers_local_wrr_when_available(monkeypatch):
    """辅助事实核查/扩展信息：本地 WRR 存在时优先走 WRR 路由。"""
    monkeypatch.setattr(
        "video_analysis_engine.os.path.exists",
        lambda p: p.endswith("/code/web-research-router") or p.endswith("/.hermes/plugins/wrr"),
    )

    gate = build_evidence_source_gate(AnalysisInput(
        video_id="BVwrr",
        transcript=Transcript(segments=[TranscriptSegment(0, "2026年 AI 公司融资超过 1 亿美元")]),
    ))

    assert gate["sources"]["external_research"] == {
        "available": True,
        "route": "wrr_local",
        "mode": "grounding",
        "reason": "local WRR detected",
    }
    assert gate["sections"]["§4 关键声明核查"]["evidence"] == ["transcript", "external_research"]


def test_evidence_gate_degrades_to_fallback_search_when_wrr_missing(monkeypatch):
    """本地 WRR 不存在时，不阻塞报告；标记可降级到普通搜索。"""
    monkeypatch.setattr("video_analysis_engine.os.path.exists", lambda p: False)

    gate = build_evidence_source_gate(AnalysisInput(
        video_id="BVwrr",
        transcript=Transcript(segments=[TranscriptSegment(0, "2026年 AI 公司融资超过 1 亿美元")]),
    ))

    assert gate["sources"]["external_research"] == {
        "available": True,
        "route": "fallback_search",
        "mode": "grounding",
        "reason": "local WRR not detected; use configured web/search tools",
    }
