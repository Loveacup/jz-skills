#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bilibili_dm_patch.py — 为 yt-dlp 注入 Bilibili dm_img 风控参数的 monkey-patch。

移植自 JefferyHcool/BiliNote (Apache-2.0)
  backend/app/downloaders/bilibili_dm_patch.py
做了本地化适配：零额外依赖、惰性 import、可重复 apply（幂等）。

背景
----
Bilibili 的 playurl/playinfo 接口近期收紧风控，对缺少 dm_img_* 系列
"设备指纹"参数的请求返回 HTTP 412 Precondition Failed。yt-dlp 的
BilibiliBaseIE._download_playinfo 默认不带这些参数，于是音频下载在很多视频上失败。

本 patch 包裹原 _download_playinfo，把下列参数合并进请求 query：
  web_location   : 1550101
  dm_img_list    : "[]"
  dm_img_str     : base64(随机字节)
  dm_cover_img_str: base64(随机字节)
  dm_img_inter   : 固定的交互轨迹 JSON

用法
----
    import bilibili_dm_patch
    bilibili_dm_patch.apply_dm_patch()   # 在 yt-dlp 被 import 后调用即可（幂等）
"""

import base64
import os

# 标记：避免重复包裹（重复 apply 会层层嵌套，幂等保护）
_PATCH_FLAG = "_dm_img_patched"


def _build_dm_params():
    """构造一组 dm_img 风控参数。

    dm_img_str / dm_cover_img_str 用随机字节的 base64，模拟设备指纹；
    其余为 BiliNote 验证过的固定值。
    """
    rnd = base64.b64encode(os.urandom(32)).decode().rstrip("=")
    cover = base64.b64encode(os.urandom(32)).decode().rstrip("=")
    return {
        "web_location": "1550101",
        "dm_img_list": "[]",
        "dm_img_str": rnd,
        "dm_cover_img_str": cover,
        "dm_img_inter": '{"ds":[],"wh":[6093,6631,31],"of":[430,760,380]}',
    }


def apply_dm_patch():
    """把 dm_img 参数注入 yt-dlp 的 BilibiliBaseIE._download_playinfo。

    返回 True 表示已成功打上（或先前已打上）；返回 False 表示当前
    yt-dlp 版本无对应类/方法，静默降级（不抛异常，调用方可忽略）。
    """
    try:
        # 惰性 import：yt-dlp 体积大且非必需依赖，import 失败时直接降级
        from yt_dlp.extractor.bilibili import BilibiliBaseIE
    except Exception:
        return False

    orig = getattr(BilibiliBaseIE, "_download_playinfo", None)
    if orig is None:
        return False

    # 幂等：已打过就不再包裹
    if getattr(orig, _PATCH_FLAG, False):
        return True

    def patched_download_playinfo(self, *args, **kwargs):
        # _download_playinfo 在不同 yt-dlp 版本里 query 的传法不同：
        # 有的接受 query=... 关键字，有的不接受。统一往 kwargs['query'] 合并，
        # 原方法若不识别该参，回退为无 query 调用，保证向后兼容。
        dm = _build_dm_params()
        query = dict(kwargs.get("query") or {})
        query.update(dm)
        kwargs["query"] = query
        try:
            return orig(self, *args, **kwargs)
        except TypeError:
            # 老版本签名不含 query：剔除后重试，至少不比未打 patch 更差
            kwargs.pop("query", None)
            return orig(self, *args, **kwargs)

    setattr(patched_download_playinfo, _PATCH_FLAG, True)
    BilibiliBaseIE._download_playinfo = patched_download_playinfo
    return True


if __name__ == "__main__":
    ok = apply_dm_patch()
    print("dm_img patch applied" if ok else "dm_img patch skipped (yt-dlp unavailable)")
