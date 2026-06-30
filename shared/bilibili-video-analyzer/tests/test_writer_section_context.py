# -*- coding: utf-8 -*-
"""Writer section context adapter（P2-C1）。

约束：
  - build_writer_section_context(report, top_n) 是确定性投影，不调用 LLM。
  - 顶层 schema 稳定且 JSON 可序列化。
  - 有 transcript：sections 顺序保持老版 0/1/2/2.5/3/4/5/6/7/8。
  - §1/§3/§4/§5/§7 注入 evidence_map 候选，字段保留，top_n 钳制每节条数。
  - source_appendix.table_rows 复用 P2-B5 §8 表契约；transcript_summary 精简，
    不暴露 json_path= / txt_path= / parts= / failed_parts= 原始串。
  - 无 transcript：阻断正式稿，sections 仅 0/8，不伪造 path/evidence。
  - render_markdown 契约不变：verify_report.evaluate(md, "condensed") 无 section missing。
"""

import json

import verify_report
from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    Transcript,
    TranscriptSegment,
    analyze_video,
    build_writer_section_context,
    render_markdown,
)


ENCODED_SOURCE = (
    "mlx-whisper|json_path=/data/BV1xx411c7mD.json|"
    "txt_path=/data/BV1xx411c7mD.txt|parts=2/3|failed_parts=P3: download failed"
)

RAW_PATH_MARKERS = ("json_path=", "txt_path=", "parts=", "failed_parts=")

TOP_LEVEL_KEYS = {
    "baseline",
    "mode",
    "can_generate_formal_report",
    "blocking_reason",
    "source_appendix",
    "sections",
    "warnings",
}

SECTION_KEYS = {
    "id",
    "heading",
    "purpose",
    "quality_gate",
    "min_items",
    "min_words_per_item",
    "needs_external_research",
    "evidence",
    "draft_placeholder",
    "writer_contract",
}


def _input_with_transcript():
    return AnalysisInput(
        video_id="BV1xx411c7mD",
        title="AI 应用能融下一轮吗？",
        author="马克汤",
        duration=754,
        platform="bilibili",
        transcript=Transcript(
            segments=[
                TranscriptSegment(0.0, "开场：AI 应用融资和 ARR 的现状。", end=20.0),
                TranscriptSegment(150.0, "中段：wrapper 经济和护城河。", end=180.0),
                TranscriptSegment(305.7, "收尾：下一轮估值逻辑。", end=330.0),
            ],
            language="zh",
            source=ENCODED_SOURCE,
        ),
        comments=[
            Comment("讲得太好了", likes=120, author="观众A", platform="bilibili"),
        ],
        danmaku=[Danmaku("前排", 1.2), Danmaku("学到了", 30.0)],
        fact_checks={
            "claims": [
                {"claim": "AI 应用 ARR 增长", "type": "number",
                 "verdict": "uncertain", "sources": []},
            ],
        },
    )


def _input_without_transcript():
    return AnalysisInput(
        video_id="BV2no2transcript",
        title="无字幕视频",
        author="某UP",
        duration=600,
        platform="bilibili",
        transcript=None,
        comments=[Comment("沙发", likes=3, author="路人", platform="bilibili")],
        danmaku=[Danmaku("?", 2.0)],
    )


# ---- 1. 顶层 schema 稳定 + JSON 可序列化 ----
def test_top_level_schema_stable_and_serializable():
    ctx = build_writer_section_context(analyze_video(_input_with_transcript()))
    assert set(ctx.keys()) == TOP_LEVEL_KEYS
    assert isinstance(ctx["can_generate_formal_report"], bool)
    assert isinstance(ctx["sections"], list)
    assert isinstance(ctx["warnings"], list)
    assert set(ctx["source_appendix"].keys()) == {"transcript_summary", "table_rows"}
    # 每节 schema 固定
    for sec in ctx["sections"]:
        assert set(sec.keys()) == SECTION_KEYS
    # JSON 可序列化（无非序列化对象）
    dumped = json.dumps(ctx, ensure_ascii=False)
    assert isinstance(dumped, str)


# ---- 2. 有 transcript：老版章节顺序保持 ----
def test_section_headings_and_order_preserved():
    ctx = build_writer_section_context(analyze_video(_input_with_transcript()))
    ids = [sec["id"] for sec in ctx["sections"]]
    assert ids == ["0", "1", "2", "2.5", "3", "4", "5", "6", "7", "8"]
    for sec in ctx["sections"]:
        assert sec["heading"] == f'## {sec["id"]}. {sec["heading"].split(". ", 1)[1]}'
        assert sec["heading"].startswith(f'## {sec["id"]}. ')


# ---- 3. evidence 注入 + top_n 钳制 ----
def test_evidence_injected_and_top_n_clamp():
    report = analyze_video(_input_with_transcript())
    ctx = build_writer_section_context(report, top_n=1)
    by_id = {sec["id"]: sec for sec in ctx["sections"]}
    for sid in ("1", "3", "4", "5", "7"):
        cands = by_id[sid]["evidence"]
        assert len(cands) == 1, f"§{sid} should be clamped to 1 by top_n"
        cand = cands[0]
        # 字段保留
        for key in ("source_type", "section_id", "text", "score", "reason"):
            assert key in cand
        assert cand["section_id"] == sid

    # top_n 更大时每节多于 1 条（transcript 有 3 段）
    ctx5 = build_writer_section_context(report, top_n=5)
    by_id5 = {sec["id"]: sec for sec in ctx5["sections"]}
    assert len(by_id5["1"]["evidence"]) == 3


# ---- 4. source_appendix 复用 §8 契约 + transcript_summary 不泄露原始路径串 ----
def test_source_appendix_reuses_table_contract_and_summary_safe():
    report = analyze_video(_input_with_transcript())
    ctx = build_writer_section_context(report)
    appendix = ctx["source_appendix"]

    # table_rows 复用 P2-B5 行顺序
    row_order = [row["source_type"] for row in appendix["table_rows"]]
    assert row_order == ["transcript", "comments", "danmaku",
                         "fact_checks", "external_research"]
    tr_row = appendix["table_rows"][0]
    assert tr_row["method"] == "mlx-whisper"
    assert tr_row["json_path"] == "/data/BV1xx411c7mD.json"
    assert tr_row["txt_path"] == "/data/BV1xx411c7mD.txt"
    assert tr_row["parts"] == "2/3"
    assert tr_row["failed_parts"] == "P3: download failed"

    # transcript_summary 精简，绝不暴露原始 key=value 编码串
    summary = appendix["transcript_summary"]
    assert summary["transcript_available"] is True
    assert summary["method"] == "mlx-whisper"
    assert summary["language"] == "zh"
    assert summary["segments"] == 3
    summary_blob = json.dumps(summary, ensure_ascii=False)
    for marker in RAW_PATH_MARKERS:
        assert marker not in summary_blob


# ---- 5. 无 transcript：阻断 + 仅 0/8 + 不伪造 ----
def test_no_transcript_blocks_and_limits_sections():
    report = analyze_video(_input_without_transcript())
    ctx = build_writer_section_context(report)

    assert ctx["can_generate_formal_report"] is False
    assert ctx["blocking_reason"] == "missing_transcript"
    ids = [sec["id"] for sec in ctx["sections"]]
    assert ids == ["0", "8"]
    # 无伪造 evidence
    for sec in ctx["sections"]:
        assert sec["evidence"] == []
    # transcript_summary 不伪造 path
    summary = ctx["source_appendix"]["transcript_summary"]
    assert summary["transcript_available"] is False
    assert summary["method"] == ""
    # 全 context 无路径泄露
    blob = json.dumps(ctx, ensure_ascii=False)
    for marker in RAW_PATH_MARKERS:
        assert marker not in blob
    # warnings 含 missing_transcript blocker
    assert any("missing_transcript" in w for w in ctx["warnings"])


# ---- 6. render_markdown 契约不变 ----
def test_render_markdown_contract_unchanged():
    report = analyze_video(_input_with_transcript())
    # 调用 adapter 不影响 render（adapter 是只读投影）
    build_writer_section_context(report)
    md = render_markdown(report)
    results, _ = verify_report.evaluate(md, "condensed")
    for gate, res in results.items():
        assert "缺失" not in res["measured"], f"{gate} reports section missing: {res['measured']}"
        assert "section missing" not in res["measured"]
