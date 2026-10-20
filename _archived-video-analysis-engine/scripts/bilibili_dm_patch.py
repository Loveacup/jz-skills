#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject dm_img anti-risk-control parameters into in-process yt-dlp Bilibili requests.

The patch is dependency-free, lazily imports yt-dlp, and is idempotent. It only
protects callers using the yt-dlp Python API; CLI yt-dlp remains protected by
UA/Referer/cookie handling in ``bili_env``.
"""

import base64
import os


_PATCH_FLAG = "_dm_img_patched"


def _build_dm_params():
    """Return the dm_img parameters required by Bilibili playinfo requests."""
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
    """Patch ``BilibiliBaseIE._download_playinfo`` and return whether it applied.

    Returns ``False`` when the installed yt-dlp version does not expose the
    expected implementation, allowing callers to degrade without an exception.
    """
    try:
        from yt_dlp.extractor.bilibili import BilibiliBaseIE
    except Exception:
        return False

    orig = getattr(BilibiliBaseIE, "_download_playinfo", None)
    if orig is None:
        return False
    if getattr(orig, _PATCH_FLAG, False):
        return True

    def patched_download_playinfo(self, *args, **kwargs):
        query = dict(kwargs.get("query") or {})
        query.update(_build_dm_params())
        kwargs["query"] = query
        try:
            return orig(self, *args, **kwargs)
        except TypeError:
            # Older yt-dlp signatures may not accept query; preserve their
            # original behavior rather than making the fallback path worse.
            kwargs.pop("query", None)
            return orig(self, *args, **kwargs)

    setattr(patched_download_playinfo, _PATCH_FLAG, True)
    BilibiliBaseIE._download_playinfo = patched_download_playinfo
    return True


if __name__ == "__main__":
    print("dm_img patch applied" if apply_dm_patch() else "dm_img patch skipped (yt-dlp unavailable)")
