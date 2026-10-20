# -*- coding: utf-8 -*-
"""P2-B3：generate_report 重建 Transcript 时不再丢字幕 metadata。

_build_transcript / build_analysis_input 必须保真：
  1) json body 的 end（item.to / item.end / from+duration）写入 TranscriptSegment.end，
     duration 取 max(end or start)，而非只取 max(start)。
  2) Transcript.language 从 subtitle step 的 language/lang/lan 继承；
     step 缺失时从 json data 的 language/lang/lan 继承。
  3) Transcript.source 保留 method，并编码 json_path / txt_path / 多P parts / failed_parts。
  4) json body 可读时优先 json，但 source 仍同时记录 json_path 和 txt_path。
"""

import json

import generate_report


def _write_json(tmp_path, name, payload):
    p = tmp_path / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(p)


# ---------- 1) json body end + duration ----------
def test_json_body_end_from_to_field(tmp_path):
    jp = _write_json(tmp_path, "BVend_official.json", {
        "body": [
            {"from": 0, "to": 4.5, "content": "第一句"},
            {"from": 4.5, "to": 9.0, "content": "第二句"},
        ],
    })
    sub = {"method": "official", "json_path": jp}

    transcript, duration = generate_report._build_transcript(sub, "BVend")

    assert transcript is not None
    assert [s.end for s in transcript.segments] == [4.5, 9.0]
    # duration 必须用 end，而不是 max(start)=4.5
    assert duration == 9


def test_json_body_end_from_end_field(tmp_path):
    jp = _write_json(tmp_path, "BVe2_official.json", {
        "body": [
            {"from": 1.0, "end": 3.0, "content": "a"},
            {"from": 3.0, "end": 12.7, "content": "b"},
        ],
    })
    transcript, duration = generate_report._build_transcript(
        {"method": "official", "json_path": jp}, "BVe2")

    assert [s.end for s in transcript.segments] == [3.0, 12.7]
    assert duration == 12


def test_json_body_end_from_start_plus_duration(tmp_path):
    jp = _write_json(tmp_path, "BVdur_official.json", {
        "body": [
            {"from": 0, "duration": 2.0, "content": "x"},
            {"from": 10.0, "duration": 5.0, "content": "y"},
        ],
    })
    transcript, duration = generate_report._build_transcript(
        {"method": "official", "json_path": jp}, "BVdur")

    assert [s.end for s in transcript.segments] == [2.0, 15.0]
    assert duration == 15


def test_json_body_missing_end_falls_back_to_start(tmp_path):
    jp = _write_json(tmp_path, "BVnoend_official.json", {
        "body": [
            {"from": 0, "content": "a"},
            {"from": 8.0, "content": "b"},
        ],
    })
    transcript, duration = generate_report._build_transcript(
        {"method": "official", "json_path": jp}, "BVnoend")

    assert [s.end for s in transcript.segments] == [None, None]
    assert duration == 8


# ---------- 2) language 继承 ----------
def test_language_inherited_from_step(tmp_path):
    jp = _write_json(tmp_path, "BVlang_official.json", {
        "language": "ai-zh",
        "body": [{"from": 0, "to": 1, "content": "hi"}],
    })
    # step 同时给 lan，应优先 step
    transcript, _ = generate_report._build_transcript(
        {"method": "official", "json_path": jp, "lan": "zh-Hans"}, "BVlang")

    assert transcript.language == "zh-Hans"


def test_language_inherited_from_json_data_when_step_missing(tmp_path):
    jp = _write_json(tmp_path, "BVlang2_official.json", {
        "lang": "en",
        "body": [{"from": 0, "to": 1, "content": "hi"}],
    })
    transcript, _ = generate_report._build_transcript(
        {"method": "official", "json_path": jp}, "BVlang2")

    assert transcript.language == "en"


# ---------- 3) source 编码 ----------
def test_source_encodes_method_and_paths_and_parts(tmp_path):
    txt = tmp_path / "BVsrc_whisper.txt"
    txt.write_text("[0:00] 开场\n[0:30] 主体\n", encoding="utf-8")
    sub = {
        "method": "mlx-whisper",
        "txt_path": str(txt),
        "parts": 2,
        "total_parts": 3,
        "failed_parts": ["P3: download failed"],
    }
    transcript, _ = generate_report._build_transcript(sub, "BVsrc")

    src = transcript.source
    assert "mlx-whisper" in src
    assert f"txt_path={txt}" in src
    assert "parts=2/3" in src
    assert "failed_parts=P3: download failed" in src


# ---------- 4) json 优先但 source 同记两路径 ----------
def test_json_preferred_but_source_records_both_paths(tmp_path):
    jp = _write_json(tmp_path, "BVboth_official.json", {
        "body": [{"from": 0, "to": 2, "content": "来自json"}],
    })
    txt = tmp_path / "BVboth_official.txt"
    txt.write_text("[0:00] 来自txt\n", encoding="utf-8")
    sub = {"method": "official", "json_path": jp, "txt_path": str(txt)}

    transcript, _ = generate_report._build_transcript(sub, "BVboth")

    # 内容来自 json body
    assert transcript.segments[0].text == "来自json"
    # 但 source 两条路径都记
    assert f"json_path={jp}" in transcript.source
    assert f"txt_path={txt}" in transcript.source


# ---------- build_analysis_input 端到端 ----------
def test_build_analysis_input_uses_end_for_duration(tmp_path):
    jp = _write_json(tmp_path, "BVe2e_official.json", {
        "language": "zh-Hans",
        "body": [
            {"from": 0, "to": 30.0, "content": "前段"},
            {"from": 30.0, "to": 95.0, "content": "后段"},
        ],
    })
    results = {
        "bvid": "BVe2e",
        "subtitle": {"method": "official", "json_path": jp},
    }
    inp = generate_report.build_analysis_input(results, run_fact_check=False)

    assert inp.duration == 95
    assert inp.transcript.language == "zh-Hans"
    assert inp.transcript.segments[1].end == 95.0


def test_build_analysis_input_prefers_explicit_video_duration(tmp_path):
    txt = tmp_path / "BVduration_whisper.txt"
    txt.write_text("## Chunk 1 [00:00]\n正文\n## Chunk 2 [20:00]\n结尾\n", encoding="utf-8")
    results = {
        "bvid": "BVduration",
        "duration": 1287,
        "subtitle": {"method": "h200-asr-chunked", "txt_path": str(txt)},
    }
    inp = generate_report.build_analysis_input(results, run_fact_check=False)
    assert inp.duration == 1287


def test_txt_chunk_headings_provide_timestamps_and_are_not_transcript_segments(tmp_path):
    txt = tmp_path / "BVchunk_h200.txt"
    txt.write_text(
        "## P1 标题元数据\n\n"
        "## Chunk 1 [00:00]\n\n"
        "第一段正文。\n\n"
        "## Chunk 2 [05:00]\n\n"
        "第二段正文。\n",
        encoding="utf-8",
    )

    transcript, duration = generate_report._build_transcript(
        {"method": "h200-asr-chunked", "txt_path": str(txt)}, "BVchunk")

    assert [(segment.start, segment.text) for segment in transcript.segments] == [
        (0.0, "第一段正文。"),
        (300.0, "第二段正文。"),
    ]
    assert duration == 300


def test_txt_only_still_builds_transcript(tmp_path):
    txt = tmp_path / "BVtxt_whisper.txt"
    txt.write_text("[0:00] 仅txt\n[1:00] 第二行\n", encoding="utf-8")
    transcript, duration = generate_report._build_transcript(
        {"method": "whisper", "txt_path": str(txt)}, "BVtxt")

    assert transcript is not None
    assert transcript.language == "unknown"
    assert duration == 60
    assert f"txt_path={txt}" in transcript.source
