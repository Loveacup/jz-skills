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
    build_typed_writer_section_contexts,
    build_writer_section_context,
    render_research_projection_records,
    render_markdown,
    write_sparse_analysis_sections,
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


def _materialized_projection():
    return {
        "3": [{
            "entry_uid": "pe-1", "target_section": "3",
            "object_type": "research_claim", "object_uid": "rc-1",
            "object_label": "RC1", "citation_labels": ["[R1]"],
            "display_text": "经外部资料核验的结论", "quote_texts": ["原文证据"],
            "purpose": "surface_key_insight",
            "deterministic_template_id": "rc_key_insight",
        }],
        "6": [{
            "entry_uid": "pe-2", "target_section": "6",
            "object_type": "entity_result", "object_uid": "ent-1",
            "object_label": "ENT-ent-1", "citation_labels": ["[S1]"],
            "display_text": "社区术语", "quote_texts": [],
            "purpose": "knowledge_graph_node",
            "deterministic_template_id": "kg_node",
        }],
    }


def _attach_projection(report):
    records = _materialized_projection()
    report["research_artifacts"] = {
        "research_projection_records": records,
        "research_projection": {
            "section_budgets": {
                "3": {"max_chars": 220},
                "6": {"max_chars": 260},
            }
        },
    }
    return report


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


def test_materialized_research_is_injected_only_into_target_sections():
    report = _attach_projection(
        analyze_video(_input_with_transcript(), mode_override="sparse")
    )
    ctx = build_writer_section_context(report)
    by_id = {section["id"]: section for section in ctx["sections"]}
    assert by_id["3"]["research_projection"][0]["object_uid"] == "rc-1"
    assert by_id["6"]["research_projection"][0]["citation_labels"] == ["[S1]"]
    assert "research_projection" not in by_id["4"]
    assert "raw_research" not in json.dumps(ctx, ensure_ascii=False)


def test_projection_records_render_provider_free_and_feed_sparse_writer():
    projection = _materialized_projection()
    rendered = render_research_projection_records(projection["3"])
    assert "经外部资料核验的结论" in rendered
    assert "[R1]" in rendered

    report = _attach_projection(
        analyze_video(_input_with_transcript(), mode_override="sparse")
    )
    sections = write_sparse_analysis_sections(report)
    assert "经外部资料核验的结论" in sections["3"]
    assert "[R1]" in sections["3"]


def test_typed_writer_receives_allowlisted_research_context_only():
    report = _attach_projection(
        analyze_video(_input_with_transcript(), mode_override="full")
    )
    contexts = build_typed_writer_section_contexts(report)
    section3 = next(context for context in contexts if context.section_id == "3")
    assert section3.research_context
    assert "经外部资料核验的结论" in section3.research_context
    assert "raw_research" not in section3.research_context


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
    # 公共 writer context 与公开 Markdown 使用同一安全口径：仅保留 basename，
    # 不暴露本机/容器绝对路径。
    assert tr_row["json_path"] == "BV1xx411c7mD.json"
    assert tr_row["txt_path"] == "BV1xx411c7mD.txt"
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


def test_research_need_is_not_confused_with_capability_or_evidence(monkeypatch):
    """ReportPlan 描述内容需求；WRR 能力/证据状态由 evidence gate 单独表达。"""
    monkeypatch.setattr("video_analysis_engine.os.path.exists", lambda _p: False)
    report = analyze_video(_input_with_transcript(), mode_override="full")

    external = report["evidence_gate"]["sources"]["external_research"]
    assert external["capability_available"] is False
    assert external["executed"] is False
    assert external["evidence_available"] is False

    sections = {section["id"]: section for section in report["report_plan"]["sections"]}
    for section_id in ("4", "6", "7"):
        assert sections[section_id]["needs_external_research"] is True


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
