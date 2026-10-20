# -*- coding: utf-8 -*-
"""Regression: dm_img parameters are injected into in-process yt-dlp requests."""

import sys
import types

import bilibili_dm_patch


REQUIRED_DM_KEYS = {
    "web_location",
    "dm_img_list",
    "dm_img_str",
    "dm_cover_img_str",
    "dm_img_inter",
}


def test_build_dm_params_has_required_keys():
    dm = bilibili_dm_patch._build_dm_params()
    assert REQUIRED_DM_KEYS.issubset(dm)
    assert isinstance(dm["dm_img_str"], str) and dm["dm_img_str"]
    assert isinstance(dm["dm_cover_img_str"], str) and dm["dm_cover_img_str"]
    assert dm["dm_img_list"] == "[]"


def _install_fake_ytdlp(monkeypatch, recorder):
    fake_yt_dlp = types.ModuleType("yt_dlp")
    fake_extractor = types.ModuleType("yt_dlp.extractor")
    fake_bili = types.ModuleType("yt_dlp.extractor.bilibili")

    class BilibiliBaseIE:
        def _download_playinfo(self, *args, **kwargs):
            recorder["queries"].append(dict(kwargs.get("query") or {}))
            recorder["orig_calls"] += 1
            return {"ok": True}

    fake_bili.BilibiliBaseIE = BilibiliBaseIE
    fake_extractor.bilibili = fake_bili
    fake_yt_dlp.extractor = fake_extractor
    monkeypatch.setitem(sys.modules, "yt_dlp", fake_yt_dlp)
    monkeypatch.setitem(sys.modules, "yt_dlp.extractor", fake_extractor)
    monkeypatch.setitem(sys.modules, "yt_dlp.extractor.bilibili", fake_bili)
    return BilibiliBaseIE


def test_patch_preserves_caller_query_and_is_idempotent(monkeypatch):
    recorder = {"queries": [], "orig_calls": 0}
    base_ie = _install_fake_ytdlp(monkeypatch, recorder)

    assert bilibili_dm_patch.apply_dm_patch() is True
    first = base_ie._download_playinfo
    assert bilibili_dm_patch.apply_dm_patch() is True
    assert base_ie._download_playinfo is first

    caller_query = {"bvid": "BVxxx", "cid": "123", "qn": "64"}
    base_ie()._download_playinfo(query=dict(caller_query))
    assert recorder["orig_calls"] == 1
    assert recorder["queries"][0].items() >= caller_query.items()
    assert REQUIRED_DM_KEYS.issubset(recorder["queries"][0])


def test_patch_degrades_gracefully_without_ytdlp(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    monkeypatch.setitem(sys.modules, "yt_dlp.extractor", None)
    monkeypatch.setitem(sys.modules, "yt_dlp.extractor.bilibili", None)
    assert bilibili_dm_patch.apply_dm_patch() is False
