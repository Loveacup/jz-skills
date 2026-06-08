#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bili_env.py — bili_env.py 的 stdlib-only 回归测试（无需 pytest）。

运行: python3 tests/test_bili_env.py   （在 skill 根目录）

覆盖两类真实事故的回归:
  A. 依赖路径在 Hermes profile HOME 下失效
     —— 用户站点目录必须基于 pwd.getpwuid(真实属主家目录) 解析，
        而不是 $HOME / os.path.expanduser('~')（后者在 Hermes 下会被
        改写成 profile home，导致 ~/Library/Python 下的 requests 找不到）。
  B. yt-dlp 下载音频缺 UA/Referer 触发 Bilibili HTTP 412
     —— 下载命令必须带 User-Agent 和 Referer header。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import bili_env  # noqa: E402


def main():
    failures = []

    # ---- A. 用户站点目录解析独立于 $HOME ----
    import pwd
    real_home = pwd.getpwuid(os.getuid()).pw_dir

    # A1: 正常情况下返回真实属主家目录下的 site-packages
    site = bili_env.user_site_packages()
    if not site.startswith(real_home):
        failures.append(f"[A1] user_site_packages 未基于真实家目录: {site} (real_home={real_home})")
    if "Library/Python" not in site or "site-packages" not in site:
        failures.append(f"[A1] user_site_packages 路径形态不对: {site}")

    # A2: 即使 $HOME 被改写（模拟 Hermes profile home），仍解析到真实家目录
    saved_home = os.environ.get("HOME")
    try:
        os.environ["HOME"] = "/tmp/fake-hermes-profile-home"
        site_override = bili_env.user_site_packages()
    finally:
        if saved_home is not None:
            os.environ["HOME"] = saved_home
        else:
            os.environ.pop("HOME", None)
    if site_override.startswith("/tmp/fake-hermes-profile-home"):
        failures.append(f"[A2] $HOME 改写后 user_site_packages 被污染: {site_override}")
    if site_override != site:
        failures.append(f"[A2] $HOME 改写后结果不稳定: {site_override} != {site}")

    # A3: ensure_user_site() 把该目录追加（而非 insert 到 0）到 sys.path
    saved_path = list(sys.path)
    try:
        added = bili_env.ensure_user_site()
        if added not in sys.path:
            failures.append(f"[A3] ensure_user_site 未把目录加入 sys.path: {added}")
        # 必须 append 到末尾，不能 insert(0) —— 否则 3.9 编译的扩展会遮蔽 stdlib
        if sys.path[0] == added:
            failures.append("[A3] ensure_user_site 误用 insert(0)，应 append 到末尾")
    finally:
        sys.path[:] = saved_path

    # ---- B. yt-dlp 音频下载命令带 UA + Referer ----
    cmd = bili_env.build_ytdlp_audio_cmd("BV1ouEp6gETM", "/tmp/out.m4a")
    if not isinstance(cmd, list) or cmd[0] != "yt-dlp":
        failures.append(f"[B1] build_ytdlp_audio_cmd 应返回以 'yt-dlp' 开头的 list: {cmd}")
    joined = " ".join(cmd)
    # 必须显式携带 User-Agent
    if "--user-agent" not in cmd:
        failures.append(f"[B1] yt-dlp 命令缺少 --user-agent: {cmd}")
    if "Mozilla" not in joined:
        failures.append(f"[B1] yt-dlp UA 不含浏览器特征 (Mozilla): {cmd}")
    # 必须显式携带 Referer（Bilibili 反爬关键，缺则 412）
    if "--referer" not in cmd:
        failures.append(f"[B2] yt-dlp 命令缺少 --referer: {cmd}")
    if "bilibili.com" not in joined:
        failures.append(f"[B2] yt-dlp Referer 未指向 bilibili.com: {cmd}")
    # BV 号与输出路径正确透传
    if "BV1ouEp6gETM" not in joined or "/tmp/out.m4a" not in cmd:
        failures.append(f"[B3] yt-dlp 命令未正确透传 BV 号/输出路径: {cmd}")

    if failures:
        print("❌ 测试失败:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("✅ test_bili_env: 全部通过 (A1/A2/A3 + B1/B2/B3)")


if __name__ == "__main__":
    main()
