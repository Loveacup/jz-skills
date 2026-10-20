# -*- coding: utf-8 -*-
"""P0 回归: bilibili_dm_patch.py 的 dm_img 风控参数注入。

锁定行为:
  - dm 参数包含 yt-dlp playinfo 请求所需的全部反风控键
  - apply_dm_patch() 幂等（重复调用不会层层包裹）
  - dm 参数在请求执行前合并进 query（保留调用方原 query）
  - 全程无网络、不起 yt-dlp CLI

注意: 本仓库 patch 包裹的是 yt-dlp BilibiliBaseIE._download_playinfo（in-process
yt-dlp 签名/请求路径），而非 _sign_wbi。dm_img patch 仅保护进程内 yt-dlp，
不保护 CLI yt-dlp —— 这正是它存在的意义。
"""

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
    assert REQUIRED_DM_KEYS.issubset(dm.keys())
    # 设备指纹字段非空且为字符串（base64 随机字节）
    assert isinstance(dm["dm_img_str"], str) and dm["dm_img_str"]
    assert isinstance(dm["dm_cover_img_str"], str) and dm["dm_cover_img_str"]
    assert dm["dm_img_list"] == "[]"


def _install_fake_ytdlp(monkeypatch, recorder):
    """在内存里伪造 yt_dlp.extractor.bilibili.BilibiliBaseIE，避免依赖真实 yt-dlp。

    recorder['queries'] 记录每次 _download_playinfo 收到的 query，
    用于断言 dm 参数确实在请求前到达。
    """
    fake_yt_dlp = types.ModuleType("yt_dlp")
    fake_extractor = types.ModuleType("yt_dlp.extractor")
    fake_bili = types.ModuleType("yt_dlp.extractor.bilibili")

    class BilibiliBaseIE:
        def _download_playinfo(self, *args, **kwargs):
            # 原方法：把收到的 query 记录下来（模拟“请求执行”）
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


def test_dm_params_reach_download_playinfo_with_caller_query_preserved(monkeypatch):
    recorder = {"queries": [], "orig_calls": 0}
    BilibiliBaseIE = _install_fake_ytdlp(monkeypatch, recorder)

    assert bilibili_dm_patch.apply_dm_patch() is True

    # 调用方原 query —— patch 必须保留它，并叠加 dm 参数
    caller_query = {"bvid": "BVxxx", "cid": "123", "qn": "64"}
    ie = BilibiliBaseIE()
    ie._download_playinfo(query=dict(caller_query))

    assert len(recorder["queries"]) == 1
    seen = recorder["queries"][0]
    # 调用方 query 原样保留
    for k, v in caller_query.items():
        assert seen[k] == v
    # dm 参数在请求前已合并
    assert REQUIRED_DM_KEYS.issubset(seen.keys())


def test_apply_dm_patch_is_idempotent(monkeypatch):
    recorder = {"queries": [], "orig_calls": 0}
    BilibiliBaseIE = _install_fake_ytdlp(monkeypatch, recorder)

    assert bilibili_dm_patch.apply_dm_patch() is True
    first = BilibiliBaseIE._download_playinfo
    # 重复 apply 不应层层包裹
    assert bilibili_dm_patch.apply_dm_patch() is True
    second = BilibiliBaseIE._download_playinfo
    assert first is second

    # 调一次 → 原方法只被调用一次（没有嵌套重复执行）
    ie = BilibiliBaseIE()
    ie._download_playinfo(query={"bvid": "BVxxx"})
    assert recorder["orig_calls"] == 1


def test_apply_dm_patch_graceful_when_ytdlp_absent(monkeypatch):
    # 模拟 yt-dlp 不可用：import 失败时静默降级返回 False，绝不抛
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    monkeypatch.setitem(sys.modules, "yt_dlp.extractor", None)
    monkeypatch.setitem(sys.modules, "yt_dlp.extractor.bilibili", None)
    assert bilibili_dm_patch.apply_dm_patch() is False
