# -*- coding: utf-8 -*-
"""P0 回归: 多 P 视频 whisper 降级转录的逐 P 合并。

锁定行为:
  - 逐 P 用各自的 cid 调 download_audio（P1→cid111, P2→cid222），绝不只取 P1
  - 合并产物保留 ## P1 / ## P2 标题，按页顺序拼接
  - 全程 monkeypatch download_audio / transcribe_audio，无真实网络/whisper/ffmpeg
"""

import fetch_subtitle_auto as fsa


def _setup_mocks(monkeypatch, dl_calls):
    """伪造 download_audio（记录 cid + 落假音频文件）与 transcribe_audio（写确定性文字）。"""

    def fake_download_audio(bvid, output_path, cid=None):
        dl_calls.append({"bvid": bvid, "output_path": output_path, "cid": cid})
        with open(output_path, "wb") as f:
            f.write(b"FAKE")
        return True

    def fake_transcribe_audio(audio_path, output_txt_path):
        # 用 cid 推不出页码，这里按调用顺序写入可区分的内容
        idx = len(dl_calls)
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(f"transcript-of-{idx}")
        return "mlx-whisper"

    monkeypatch.setattr(fsa, "download_audio", fake_download_audio)
    monkeypatch.setattr(fsa, "transcribe_audio", fake_transcribe_audio)
    # 兜底：确保任何真实子进程/网络调用都不会发生
    monkeypatch.setattr(
        fsa.subprocess, "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应起真实子进程")),
    )


def test_multi_p_merge_preserves_p_headings_and_per_page_cid(monkeypatch, tmp_path):
    dl_calls = []
    _setup_mocks(monkeypatch, dl_calls)

    pages = [
        {"page": 1, "part": "Intro", "cid": 111},
        {"page": 2, "part": "Main", "cid": 222},
    ]
    out = tmp_path / "merged.txt"

    result = fsa.transcribe_pages_merge(
        "BVmulti", "multi p test", pages, str(tmp_path), output_txt_path=str(out)
    )

    assert result is not None
    assert result["parts"] == 2
    assert result["total_parts"] == 2
    assert result["method"] == "mlx-whisper"

    # 逐 P 各用自己的 cid，顺序正确，绝不只取 P1
    assert [c["cid"] for c in dl_calls] == [111, 222]

    merged = out.read_text(encoding="utf-8")
    assert "## P1 Intro" in merged
    assert "## P2 Main" in merged
    # P1 标题出现在 P2 之前（按页顺序合并）
    assert merged.index("## P1") < merged.index("## P2")


def test_multi_p_skips_failed_page_but_keeps_others(monkeypatch, tmp_path):
    dl_calls = []
    _setup_mocks(monkeypatch, dl_calls)

    # 让 P1 下载失败，P2 成功 —— 合并仍保留 P2 且 result 非 None
    real_dl = fsa.download_audio

    def selective_download(bvid, output_path, cid=None):
        if cid == 111:
            dl_calls.append({"cid": cid})
            return False
        return real_dl(bvid, output_path, cid=cid)

    monkeypatch.setattr(fsa, "download_audio", selective_download)

    pages = [
        {"page": 1, "part": "Intro", "cid": 111},
        {"page": 2, "part": "Main", "cid": 222},
    ]
    out = tmp_path / "merged.txt"
    result = fsa.transcribe_pages_merge(
        "BVmulti", "multi p test", pages, str(tmp_path), output_txt_path=str(out)
    )

    assert result is not None
    assert result["parts"] == 1
    assert result["total_parts"] == 2
    assert any("P1" in fp for fp in result["failed_parts"])
    merged = out.read_text(encoding="utf-8")
    assert "## P2 Main" in merged
    assert "## P1" not in merged


def test_multi_p_all_failed_returns_none_not_exception(monkeypatch, tmp_path):
    dl_calls = []
    _setup_mocks(monkeypatch, dl_calls)
    monkeypatch.setattr(fsa, "download_audio", lambda *a, **k: False)

    pages = [
        {"page": 1, "part": "Intro", "cid": 111},
        {"page": 2, "part": "Main", "cid": 222},
    ]
    result = fsa.transcribe_pages_merge(
        "BVmulti", "multi p test", pages, str(tmp_path),
        output_txt_path=str(tmp_path / "merged.txt"),
    )
    # 全失败仍是结构化的 None（绝不抛异常塌缩流程）
    assert result is None
