# -*- coding: utf-8 -*-
"""render §0/§8 transcript Source Appendix（P2-B4）。

约束：
  - render_markdown(analyze_video(inp)) 在 ## 0. 与 ## 8. 都用户可见展示
    `### Source Appendix`。
  - appendix 从 report["evidence_gate"]["sources"]["transcript"] 读
    available / source / language / segments / chars，不依赖 evidence_map.by_section。
  - source 完整保留 P2-B3 编码字符串：method / json_path / txt_path /
    parts=2/3 / failed_parts=...。
  - 无 transcript 时显示 transcript_available=false，且不伪造
    json_path / txt_path / failed_parts。
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


# ---------- 1) §0 与 §8 都有 Source Appendix ----------
def test_section_0_has_source_appendix():
    md = _render(_input_with_transcript())
    assert "### Source Appendix" in _section_block(md, "0")


def test_section_8_has_source_appendix():
    md = _render(_input_with_transcript())
    assert "### Source Appendix" in _section_block(md, "8")


# ---------- 2) appendix 字段来自 evidence_gate.sources.transcript ----------
def test_appendix_reflects_gate_transcript_fields():
    inp = _input_with_transcript()
    report = analyze_video(inp)
    tr = report["evidence_gate"]["sources"]["transcript"]
    md = render_markdown(report)

    for num in ("0", "8"):
        block = _section_block(md, num)
        assert "transcript_available=true" in block
        assert f"language: {tr['language']}" in block
        assert f"segments: {tr['segments']}" in block
        assert f"chars: {tr['chars']}" in block


def test_appendix_does_not_depend_on_evidence_map_by_section():
    """清空 evidence_map.by_section 后，appendix 仍完整渲染。"""
    inp = _input_with_transcript()
    report = analyze_video(inp)
    report["evidence_map"]["by_section"] = {}
    md = render_markdown(report)

    block = _section_block(md, "8")
    assert "### Source Appendix" in block
    assert "transcript_available=true" in block
    assert f"segments: {report['evidence_gate']['sources']['transcript']['segments']}" in block


# ---------- 3) source 完整保留 P2-B3 编码字符串 ----------
def test_appendix_preserves_encoded_source_string():
    md = _render(_input_with_transcript())
    for num in ("0", "8"):
        block = _section_block(md, num)
        assert "mlx-whisper" in block
        assert "json_path=/data/BV1xx411c7mD.json" in block
        assert "txt_path=/data/BV1xx411c7mD.txt" in block
        assert "parts=2/3" in block
        assert "failed_parts=P3: download failed" in block


# ---------- 4) 无 transcript ----------
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
