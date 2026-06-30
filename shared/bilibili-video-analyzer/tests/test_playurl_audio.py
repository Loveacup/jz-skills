# -*- coding: utf-8 -*-
"""P0 回归: fetch_subtitle_auto.download_audio() 的 PlayURL 直拉路径。

锁定行为（来自 jz-skills 旧版 audio_to_text.py 的稳定 fallback）:
  - 优先走 B站公开 PlayURL API（x/player/playurl）直拉 DASH audio，绕开 yt-dlp 412
  - 多 P 视频传入的 cid 必须被使用，绝不被 P1 的 cid 覆盖
  - ASR 场景优先最低码率音频，降低下载/转码成本
  - 普通 stream 下载失败时用 HTTP Range 兜底，避免误判 PlayURL 不可用
  - 全程 monkeypatch，无真实网络、无 ffmpeg、无 yt-dlp、无真实下载
"""

import requests

import fetch_subtitle_auto as fsa


class _FakeStreamResp:
    """模拟 requests.get(audio_url, stream=True) 的上下文管理器响应。"""

    def __init__(self, payload=b"FAKE_AUDIO_BYTES", status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=1):
        yield self._payload


class _FakeRangeResp(_FakeStreamResp):
    """模拟支持 Range 的音频 CDN 响应。"""

    def __init__(self, payload=b"RANGE_AUDIO_BYTES"):
        super().__init__(
            payload=payload,
            status_code=206,
            headers={"Content-Range": f"bytes 0-{len(payload)-1}/{len(payload)}"},
        )


class _FakeJsonResp:
    """模拟 playurl 接口的 JSON 响应。"""

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _make_fake_get(calls, p1_cid=111):
    """返回一个伪 requests.get，记录所有调用，永不触网。

    playurl 接口返回带 baseUrl 的 dash audio；音频 URL 返回假字节流。
    若请求里出现 P1 的 cid，说明发生了错误覆盖，测试会因此失败。
    """
    def fake_get(url, params=None, headers=None, stream=False, timeout=None, **kwargs):
        calls.append({"url": url, "params": params or {}, "headers": headers or {}, "stream": stream})
        if "x/player/playurl" in url:
            return _FakeJsonResp({
                "data": {"dash": {"audio": [{"baseUrl": "https://fake-cdn/audio.m4s"}]}}
            })
        # 音频流 URL
        return _FakeStreamResp()

    return fake_get


def test_download_audio_uses_passed_p2_cid(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fsa.requests, "get", _make_fake_get(calls))
    # 若 cid 被错误地用 get_video_info 重新解析，应失败 —— 这里强制其抛错暴露问题
    monkeypatch.setattr(
        fsa, "get_video_info",
        lambda bvid: (_ for _ in ()).throw(AssertionError("不应回退 get_video_info：cid 已显式传入")),
    )

    out = tmp_path / "p2.m4a"
    p2_cid = 222
    ok = fsa.download_audio("BVtest", str(out), cid=p2_cid)
    assert ok is True

    # 找到 playurl 请求
    playurl_calls = [c for c in calls if "x/player/playurl" in c["url"]]
    assert playurl_calls, "应至少发起一次 PlayURL API 请求"
    pu = playurl_calls[0]
    # 使用公开 PlayURL 端点
    assert "x/player/playurl" in pu["url"]
    # 用了传入的 P2 cid，绝不是 P1 cid
    assert pu["params"].get("cid") == p2_cid
    assert pu["params"].get("cid") != 111
    assert pu["params"].get("bvid") == "BVtest"

    # 文件确实由假字节流写出（无真实网络/下载）
    assert out.exists() and out.read_bytes() == b"FAKE_AUDIO_BYTES"


def test_download_audio_does_not_invoke_ytdlp_on_playurl_success(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fsa.requests, "get", _make_fake_get(calls))

    # yt-dlp 回退路径若被触发即失败：PlayURL 成功时不应触碰 subprocess
    def _boom(*a, **k):
        raise AssertionError("PlayURL 成功时不应回退到 yt-dlp / subprocess")

    monkeypatch.setattr(fsa.subprocess, "run", _boom)

    out = tmp_path / "p2.m4a"
    ok = fsa.download_audio("BVtest", str(out), cid=222)
    assert ok is True


def test_download_audio_picks_lowest_bitrate_for_asr(monkeypatch, tmp_path):
    """长音频转 ASR 不需要高码率；优先最低码率可显著降低下载/转码成本。"""
    calls = []

    def fake_get(url, params=None, headers=None, stream=False, timeout=None, **kwargs):
        calls.append({"url": url, "params": params or {}, "headers": headers or {}, "stream": stream})
        if "x/player/playurl" in url:
            return _FakeJsonResp({
                "data": {"dash": {"audio": [
                    {"baseUrl": "https://fake-cdn/audio_192.m4s", "bandwidth": 192000},
                    {"baseUrl": "https://fake-cdn/audio_64.m4s", "bandwidth": 64000},
                    {"baseUrl": "https://fake-cdn/audio_128.m4s", "bandwidth": 128000},
                ]}}
            })
        return _FakeStreamResp(payload=b"LOW_BITRATE_AUDIO")

    monkeypatch.setattr(fsa.requests, "get", fake_get)
    monkeypatch.setattr(
        fsa.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应回退 yt-dlp")),
    )

    out = tmp_path / "audio.m4a"
    assert fsa.download_audio("BVtest", str(out), cid=222) is True
    audio_calls = [c for c in calls if "fake-cdn" in c["url"]]
    assert audio_calls[0]["url"].endswith("audio_64.m4s")
    assert out.read_bytes() == b"LOW_BITRATE_AUDIO"


def test_download_audio_range_fallback_when_stream_download_fails(monkeypatch, tmp_path):
    """普通 stream 下载失败时，用 HTTP Range 兜底；不要误判为 PlayURL 不可用。"""
    calls = []

    def fake_get(url, params=None, headers=None, stream=False, timeout=None, **kwargs):
        calls.append({"url": url, "params": params or {}, "headers": headers or {}, "stream": stream})
        if "x/player/playurl" in url:
            return _FakeJsonResp({
                "data": {"dash": {"audio": [{"baseUrl": "https://fake-cdn/audio.m4s", "bandwidth": 64000}]}}
            })
        if not (headers or {}).get("Range"):
            raise requests.ConnectionError("simulated full stream failure")
        return _FakeRangeResp(payload=b"RANGE_OK")

    monkeypatch.setattr(fsa.requests, "get", fake_get)
    monkeypatch.setattr(
        fsa.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Range 成功时不应回退 yt-dlp")),
    )

    out = tmp_path / "audio.m4a"
    assert fsa.download_audio("BVtest", str(out), cid=222) is True
    range_calls = [c for c in calls if (c["headers"] or {}).get("Range")]
    assert range_calls, "普通下载失败后应发起 Range 请求"
    assert range_calls[0]["headers"]["Range"].startswith("bytes=0-")
    assert out.read_bytes() == b"RANGE_OK"
