# -*- coding: utf-8 -*-
"""EvidenceMap：把 transcript 片段直接转成带时间戳的引用候选。

约束（来自 P2-B mandate / Codex 执行包 schema）：
  - 候选必须直接来自 transcript 片段，禁止 LLM 合成 / embedding / 外部检索。
  - B站时间戳 URL 用秒数公式 https://www.bilibili.com/video/{BV}?t={int(start)}。
  - 按 SectionSpec.id 分组，覆盖 transcript 支撑的 §1/§3/§4/§5/§7。
  - 无 comments/danmaku 时，不为 §2/§2.5 伪造候选。
  - EvidenceCandidate 字段：source_type, section_id, start, end, timestamp,
    url, text, context, score, reason。
  - EvidenceMap 字段：video_id, baseline, by_section, warnings + to_dict()。
"""

import json
from dataclasses import asdict

from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    EvidenceCandidate,
    EvidenceMap,
    Transcript,
    TranscriptSegment,
    analyze_video,
    build_evidence_map,
    build_report_plan,
)


TRANSCRIPT_SECTIONS = ["1", "3", "4", "5", "7"]
CANDIDATE_FIELDS = {
    "source_type", "section_id", "start", "end", "timestamp",
    "url", "text", "context", "score", "reason",
}
MAP_FIELDS = {"video_id", "baseline", "by_section", "warnings"}


def _input(duration=3600, comments=True, danmaku=True):
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
        comments=[Comment("热评补充观点", likes=42)] if comments else [],
        danmaku=[Danmaku("前排", time=3.0), Danmaku("学到了", time=151.0)] if danmaku else [],
    )


def test_evidence_map_top_level_schema():
    inp = _input(duration=6300)
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    assert isinstance(emap, EvidenceMap)
    assert emap.video_id == "BV1xx411c7mD"
    assert emap.baseline == plan.baseline == "old_bilibili_v3_framework"
    assert isinstance(emap.by_section, dict)
    assert isinstance(emap.warnings, list)
    # to_dict 完整且可 JSON 序列化
    d = emap.to_dict()
    assert set(d.keys()) == MAP_FIELDS
    json.dumps(d, ensure_ascii=False)


def test_candidate_schema_fields_present_and_serializable():
    inp = _input(duration=6300)
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    c = emap.by_section["1"][0]
    assert isinstance(c, EvidenceCandidate)
    assert set(asdict(c).keys()) == CANDIDATE_FIELDS
    json.dumps(asdict(c), ensure_ascii=False)


def test_build_evidence_map_covers_transcript_sections():
    inp = _input(duration=6300)
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    for sid in TRANSCRIPT_SECTIONS:
        cands = emap.by_section.get(sid, [])
        assert cands, f"section {sid} should have transcript candidates"
        for c in cands:
            assert c.section_id == sid
            assert c.source_type == "transcript"
            assert c.start is not None
            assert c.text
            assert c.context == c.text
            assert c.score > 0
            assert c.reason  # section purpose marker


def test_transcript_end_and_reason_markers():
    inp = _input()
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    # end 来自 segment.end
    ends = {int(c.start): c.end for c in emap.by_section["1"]}
    assert ends[0] == 20.0
    assert ends[150] == 180.0
    # reason 标明各节用途
    assert {c.reason for c in emap.by_section["1"]} == {"logic_candidate"}
    assert {c.reason for c in emap.by_section["4"]} == {"deep_dive_candidate"}
    assert {c.reason for c in emap.by_section["5"]} == {"quote_candidate"}


def test_url_uses_seconds_formula_not_mmss():
    """start=150 必须是 ?t=150，不是 ?t=230。"""
    inp = _input()
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    by_start = {int(c.start): c for c in emap.by_section["1"]}
    assert by_start[150].url == "https://www.bilibili.com/video/BV1xx411c7mD?t=150"
    assert "?t=230" not in by_start[150].url
    # 浮点起点向下取整
    assert by_start[305].url == "https://www.bilibili.com/video/BV1xx411c7mD?t=305"


def test_timestamp_label_is_mmss():
    inp = _input()
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    labels = {c.timestamp for c in emap.by_section["1"]}
    assert "2:30" in labels  # 150 秒
    assert "0:00" in labels


def test_no_social_does_not_fabricate_2_and_2_5():
    inp = _input(comments=False, danmaku=False)
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    assert not emap.by_section.get("2")
    assert not emap.by_section.get("2.5")
    assert emap.by_section.get("1")


def test_social_present_populates_2_and_2_5():
    inp = _input(comments=True, danmaku=True)
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    danmaku_cands = emap.by_section.get("2", [])
    assert danmaku_cands
    assert all(c.source_type == "danmaku" for c in danmaku_cands)
    dm = {int(c.start): c for c in danmaku_cands}
    assert dm[151].url == "https://www.bilibili.com/video/BV1xx411c7mD?t=151"
    assert dm[151].score > 0

    comment_cands = emap.by_section.get("2.5", [])
    assert comment_cands
    for c in comment_cands:
        assert c.source_type == "comments"
        assert c.start is None and c.end is None
        assert c.url == "" and c.timestamp == ""
        assert c.text and c.score > 0


def test_no_transcript_yields_empty_sections_and_warning():
    inp = AnalysisInput(video_id="BVnoasr", title="无字幕")
    plan = build_report_plan(inp)

    emap = build_evidence_map(inp, plan)

    for sid in TRANSCRIPT_SECTIONS:
        assert not emap.by_section.get(sid)
    assert any("no_transcript" in w for w in emap.warnings)


def test_analyze_video_exposes_evidence_map():
    inp = _input(duration=6300)

    report = analyze_video(inp)

    assert "evidence_map" in report
    em = report["evidence_map"]
    assert set(em.keys()) == MAP_FIELDS
    assert em["video_id"] == "BV1xx411c7mD"
    assert em["baseline"] == "old_bilibili_v3_framework"
    first = em["by_section"]["1"][0]
    assert set(first.keys()) == CANDIDATE_FIELDS
    assert first["section_id"] == "1"
    assert first["url"].startswith("https://www.bilibili.com/video/BV1xx411c7mD?t=")
    json.dumps(em, ensure_ascii=False)
