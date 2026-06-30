# -*- coding: utf-8 -*-
"""render §0/§8 Source Appendix（P2-B5）。

约束：
  - render_markdown(analyze_video(inp)) 在 ## 0. 与 ## 8. 都展示
    `### Source Appendix`，数据只读 evidence_gate.sources，不依赖
    evidence_map.by_section。
  - §0 精简：只给 transcript_available 与 method/language/segments/chars，
    绝不出现 json_path= / txt_path= / parts= / failed_parts= 原始串。
  - §8 升级为确定性 Markdown 表格：固定列头、固定行顺序
    （transcript / comments / danmaku / fact_checks / external_research），
    transcript.source 编码串解析进各单元格。
  - 无 transcript：transcript_available=false，且全文不伪造
    json_path= / txt_path= / parts= / failed_parts=。
"""

import re

from video_analysis_engine import (
    AnalysisInput,
    Comment,
    Danmaku,
    Transcript,
    TranscriptSegment,
    analyze_video,
    render_markdown,
)


# P2-B3 source 编码：method|json_path=...|txt_path=...|parts=2/3|failed_parts=...
ENCODED_SOURCE = (
    "mlx-whisper|json_path=/data/BV1xx411c7mD.json|"
    "txt_path=/data/BV1xx411c7mD.txt|parts=2/3|failed_parts=P3: download failed"
)

# §8 固定列头与固定行顺序
EXPECTED_COLUMNS = [
    "source_type", "available", "method", "language", "segments", "chars",
    "count", "json_path", "txt_path", "parts", "failed_parts", "notes",
]
EXPECTED_ROW_ORDER = [
    "transcript", "comments", "danmaku", "fact_checks", "external_research",
]


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
                TranscriptSegment(150.0, "中段：wrapper 经济。", end=180.0),
                TranscriptSegment(305.7, "收尾：下一轮估值逻辑。", end=330.0),
            ],
            language="zh",
            source=ENCODED_SOURCE,
        ),
        comments=[Comment("热评", likes=42)],
        danmaku=[Danmaku("前排", time=3.0)],
    )


def _input_without_transcript():
    return AnalysisInput(
        video_id="BVnotr",
        title="无字幕视频",
        author="某UP",
        duration=120,
        platform="bilibili",
        transcript=None,
        comments=[Comment("评论", likes=1)],
    )


def _render(inp):
    return render_markdown(analyze_video(inp))


def _section_block(md, num):
    """截取 ## {num}. 到下一个 ## 之间的正文。"""
    lines = md.splitlines()
    head = re.compile(r"^##\s+" + re.escape(num) + r"\.")
    start = None
    for i, ln in enumerate(lines):
        if head.match(ln):
            start = i
            break
    assert start is not None, f"missing heading ## {num}."
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^##\s+", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def _table_rows(block):
    """返回 §8 表格的数据行（拆成单元格列表），跳过表头与分隔行。"""
    rows = []
    for ln in block.splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set(cells) <= {"---", ""}:  # 分隔行
            continue
        rows.append(cells)
    return rows


# ---------- 1) §0 与 §8 都有 Source Appendix ----------
def test_section_0_has_source_appendix():
    md = _render(_input_with_transcript())
    assert "### Source Appendix" in _section_block(md, "0")


def test_section_8_has_source_appendix():
    md = _render(_input_with_transcript())
    assert "### Source Appendix" in _section_block(md, "8")


# ---------- 2) §0 精简：method/language/segments/chars，无路径串 ----------
def test_section_0_concise_fields():
    inp = _input_with_transcript()
    report = analyze_video(inp)
    tr = report["evidence_gate"]["sources"]["transcript"]
    block = _section_block(render_markdown(report), "0")

    assert "transcript_available=true" in block
    assert "method: mlx-whisper" in block
    assert f"language: {tr['language']}" in block
    assert f"segments: {tr['segments']}" in block
    assert f"chars: {tr['chars']}" in block


def test_section_0_does_not_expose_path_encoding():
    block = _section_block(_render(_input_with_transcript()), "0")
    for needle in ("json_path=", "txt_path=", "parts=", "failed_parts="):
        assert needle not in block, f"§0 不应展开 {needle}"


# ---------- 3) §8 确定性表格：固定列头与固定行顺序 ----------
def test_section_8_table_header_is_stable():
    block = _section_block(_render(_input_with_transcript()), "8")
    rows = _table_rows(block)
    assert rows, "§8 应有表格行"
    assert rows[0] == EXPECTED_COLUMNS


def test_section_8_table_row_order_is_fixed():
    block = _section_block(_render(_input_with_transcript()), "8")
    rows = _table_rows(block)
    data_rows = rows[1:]
    assert [r[0] for r in data_rows] == EXPECTED_ROW_ORDER


# ---------- 4) §8 transcript 行：编码串解析进单元格 ----------
def test_section_8_transcript_row_parsed_cells():
    block = _section_block(_render(_input_with_transcript()), "8")
    rows = _table_rows(block)
    header = rows[0]
    tr_row = next(r for r in rows[1:] if r[0] == "transcript")
    cell = dict(zip(header, tr_row))

    assert cell["available"] == "true"
    assert cell["method"] == "mlx-whisper"
    assert cell["language"] == "zh"
    assert cell["segments"] == "3"
    assert cell["json_path"] == "/data/BV1xx411c7mD.json"
    assert cell["txt_path"] == "/data/BV1xx411c7mD.txt"
    assert cell["parts"] == "2/3"
    assert cell["failed_parts"] == "P3: download failed"


def test_section_8_non_transcript_source_rows():
    block = _section_block(_render(_input_with_transcript()), "8")
    rows = _table_rows(block)
    header = rows[0]
    by_type = {r[0]: dict(zip(header, r)) for r in rows[1:]}

    assert by_type["comments"]["available"] == "true"
    assert by_type["comments"]["count"] == "1"
    assert by_type["danmaku"]["available"] == "true"
    assert by_type["danmaku"]["count"] == "1"
    # 非 transcript 行不应带路径单元格内容
    for name in ("comments", "danmaku", "fact_checks", "external_research"):
        assert by_type[name]["json_path"] == ""
        assert by_type[name]["txt_path"] == ""


# ---------- 5) appendix 不依赖 evidence_map.by_section ----------
def test_appendix_does_not_depend_on_evidence_map_by_section():
    inp = _input_with_transcript()
    report = analyze_video(inp)
    report["evidence_map"]["by_section"] = {}
    block = _section_block(render_markdown(report), "8")
    rows = _table_rows(block)
    tr_row = next(r for r in rows[1:] if r[0] == "transcript")
    assert tr_row[1] == "true"  # available 仍为 true


# ---------- 6) 无 transcript ----------
def test_appendix_false_when_no_transcript():
    md = _render(_input_without_transcript())
    for num in ("0", "8"):
        block = _section_block(md, num)
        assert "### Source Appendix" in block
        assert "transcript_available=false" in block


def test_appendix_does_not_fabricate_paths_when_no_transcript():
    md = _render(_input_without_transcript())
    assert "json_path=" not in md
    assert "txt_path=" not in md
    assert "failed_parts=" not in md
    assert "parts=" not in md


def test_section_8_transcript_row_empty_when_no_transcript():
    block = _section_block(_render(_input_without_transcript()), "8")
    rows = _table_rows(block)
    header = rows[0]
    tr_row = next(r for r in rows[1:] if r[0] == "transcript")
    cell = dict(zip(header, tr_row))
    assert cell["available"] == "false"
    for col in ("method", "json_path", "txt_path", "parts", "failed_parts"):
        assert cell[col] == "", f"无 transcript 时 {col} 不应被伪造"
