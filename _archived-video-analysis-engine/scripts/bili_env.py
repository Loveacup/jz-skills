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
import time

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


# ============ Cookie Netscape 持久化 ============
# 首次用 Chrome 浏览器 cookie 提取后落盘为 Netscape 格式，后续 yt-dlp 调用
# 复用 --cookiefile，避免每次重新读 Chrome（慢、且会触发钥匙串授权弹窗）。
COOKIE_MAX_AGE_DAYS = 7  # 超过此天数视为过期，自动刷新


def cookie_file_path():
    """Cookie 文件绝对路径：<skill 根>/.cookies/bilibili.txt。

    基于脚本自身位置推导（scripts/ 的上一级即 skill 根），不依赖 $HOME，
    与 real_home() 改写无关，跨 Hermes profile 稳定。
    """
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(scripts_dir)
    return os.path.join(skill_root, ".cookies", "bilibili.txt")


def cookie_is_fresh(path=None, max_age_days=COOKIE_MAX_AGE_DAYS):
    """Cookie 文件是否存在且未过期（mtime 在 max_age_days 内、且非空）。"""
    path = path or cookie_file_path()
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False
        age = time.time() - os.path.getmtime(path)
        return age <= max_age_days * 86400
    except OSError:
        return False


# cookie 提取预热用的稳定公开视频（仅触发 yt-dlp 走一遍以 dump cookie jar）
_COOKIE_WARMUP_URL = "https://www.bilibili.com/video/BV1GJ411x7h7/"

# 进程内负缓存：本进程已尝试提取且失败，则不再重复跑 60s 预热（避免叠加超时）
_COOKIE_EXTRACT_FAILED = False


def ensure_cookie_file(browser="chrome", force=False):
    """确保 Netscape 格式 cookie 文件可用，返回路径或 None。

    - 文件仍新鲜且非强制刷新：直接复用，不碰浏览器。
    - 否则用 yt-dlp **CLI** 从浏览器提取并落盘（同时传 --cookies-from-browser
      与 --cookies FILE，yt-dlp 会把读到的 cookie jar 以 Netscape 格式 dump 到
      FILE 供后续复用）。

    用 CLI 而非 in-process yt_dlp.cookies：本仓脚本固定跑 /usr/bin/python3(3.9)，
    该解释器并无 yt_dlp 模块（yt-dlp 是 homebrew CLI）；走 CLI 才能跨解释器生效。

    全程 best-effort：任何失败都返回 None，调用方据此降级为无 cookie 流程，
    保证浏览器/yt-dlp 缺失时不回归（不抛异常）。
    """
    import subprocess  # 局部 import，避免顶层污染

    global _COOKIE_EXTRACT_FAILED
    path = cookie_file_path()

    if not force and cookie_is_fresh(path):
        return path

    # 本进程已失败过且非强制：直接降级，不再叠加 60s 预热
    if _COOKIE_EXTRACT_FAILED and not force:
        return None

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cmd = [
            "yt-dlp",
            "--cookies-from-browser", browser,
            "--cookies", path,        # 同时给出 → yt-dlp 退出时把 cookie jar dump 到此
            "--skip-download", "--simulate",
            "--quiet", "--no-warnings",
            _COOKIE_WARMUP_URL,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if cookie_is_fresh(path):
            try:
                os.chmod(path, 0o600)  # 含登录态，仅属主可读写
            except OSError:
                pass
            return path
        _COOKIE_EXTRACT_FAILED = True
        return None
    except Exception:
        # 浏览器未安装 / yt-dlp 缺失 / 钥匙串解锁失败等，一律静默降级
        _COOKIE_EXTRACT_FAILED = True
        return None


def build_ytdlp_audio_cmd(bvid, output_path, extra=None, use_cookie=True,
                          apply_patch=True):
    """构造 yt-dlp 下载 Bilibili 音频的命令 list。

    关键：显式带 --user-agent + --referer，否则 Bilibili 返回 412。

    use_cookie=True 时尝试复用/创建 Netscape cookie 文件（best-effort，
    失败则自动退回无 cookie 流程，向后兼容）。
    apply_patch=True 时尝试给 in-process yt-dlp 打 dm_img patch；注意本函数
    产出的是 **CLI 子进程** 命令，子进程不受本进程 monkey-patch 影响——此处
    调用仅为对「同进程内直接用 yt-dlp API」的调用方生效，对 CLI 子进程的 412
    防护依赖的是 UA/Referer + cookie，而非本 patch。保留调用以满足统一入口约定，
    且幂等无副作用。
    """
    if apply_patch:
        try:
            from bilibili_dm_patch import apply_dm_patch
            apply_dm_patch()
        except Exception:
            pass

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

    # cookie：优先用已落盘的 Netscape 文件；缺失则尝试提取一份供本次及后续复用
    if use_cookie:
        cookie_path = ensure_cookie_file()
        if cookie_path:
            # 插在 URL 之前、yt-dlp 之后；路径不打印到 trace/Markdown（敏感）
            cmd[1:1] = ["--cookies", cookie_path]

    if extra:
        cmd[1:1] = list(extra)
    return cmd
