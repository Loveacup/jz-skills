#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bili_env.py — 跨环境运行底座，被所有 fetch_* / 转录脚本共享。

解决两类真实事故:

A. 依赖路径在 Hermes profile HOME 下失效
   Hermes 以 profile 隔离方式运行，会把 $HOME 改写成
   `~/.hermes/profiles/<name>/home`，于是 os.path.expanduser('~') 不再指向
   真实属主家目录，`~/Library/Python/3.9/.../site-packages` 里的 requests /
   mlx_whisper 全部找不到（ModuleNotFoundError）。
   → 用 pwd.getpwuid(os.getuid()).pw_dir 取**真实属主**家目录，绕开 $HOME。

B. yt-dlp 下载 Bilibili 音频缺 UA/Referer → HTTP 412 Precondition Failed
   Bilibili 对无 UA/Referer 的网页请求返回 412。
   → 统一在这里构造带 header 的下载命令。
"""

import os
import pwd
import sys

# 浏览器 UA：Bilibili 反爬要求。API 与 yt-dlp 共用同一串，便于一处维护。
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
BILI_REFERER = "https://www.bilibili.com"


def real_home():
    """真实属主家目录，独立于 $HOME。

    Hermes profile 会改写 $HOME，os.path.expanduser('~') 不可信；
    pwd.getpwuid 直接读 passwd，永远指向真实属主。
    """
    return pwd.getpwuid(os.getuid()).pw_dir


def user_site_packages():
    """当前解释器对应的用户级 site-packages 绝对路径（基于真实家目录）。

    形如 ~/Library/Python/3.9/lib/python/site-packages。版本号取运行解释器
    的 major.minor（这些脚本固定用 /usr/bin/python3，即 3.9），未来换解释器
    也能自洽。
    """
    ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    return os.path.join(
        real_home(), "Library", "Python", ver, "lib", "python", "site-packages"
    )


def ensure_user_site():
    """把用户级 site-packages **追加**到 sys.path 末尾，返回该路径。

    必须 append（不能 insert(0)）：3.9 user-site 里可能有为 3.9 编译的扩展，
    insert(0) 会让它们遮蔽当前解释器的 stdlib。
    幂等：重复调用不会重复添加。
    """
    site = user_site_packages()
    if site not in sys.path:
        sys.path.append(site)
    return site


def build_ytdlp_audio_cmd(bvid, output_path, extra=None):
    """构造 yt-dlp 下载 Bilibili 音频的命令 list。

    关键：显式带 --user-agent + --referer，否则 Bilibili 返回 412。
    """
    cmd = [
        "yt-dlp",
        "--user-agent", BROWSER_UA,
        "--referer", BILI_REFERER,
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "-o", output_path,
        "--no-playlist",
        "--progress",
        f"https://www.bilibili.com/video/{bvid}/",
    ]
    if extra:
        cmd[1:1] = list(extra)
    return cmd
