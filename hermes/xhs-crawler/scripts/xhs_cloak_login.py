#!/usr/bin/env python3
"""
XHS CloakBrowser Login — 一次性扫码登录脚本

使用：
    python3 scripts/xhs_cloak_login.py

会拉起 headed CloakBrowser 窗口，自动跳转到登录页。
扫码完成后脚本检测到 cookie 即自动关闭并持久化到
~/.cloakbrowser/xhs_profile/（约 17MB，包含 12+ 小红书 cookie）。

cookie 有效期约 1 年。过期后重跑本脚本即可。
"""

import asyncio
import os
import sys
from pathlib import Path

PROFILE_DIR = Path(
    os.environ.get(
        "CLOAKBROWSER_PROFILE_DIR",
        str(Path.home() / ".cloakbrowser" / "xhs_profile"),
    )
)


async def main():
    import cloakbrowser as cb

    print(f"🚀 CloakBrowser Login (v{cb.__version__})")
    print(f"📁 Profile 目录: {PROFILE_DIR}")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    ctx = await cb.launch_persistent_context_async(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        humanize=True,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN",
    )
    try:
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("🌐 打开小红书首页，请扫码登录...")
        await page.goto("https://www.xiaohongshu.com/explore", timeout=30000)

        # 等扫码 — 检测 web_session cookie 出现即视为登录成功
        print("⏳ 等待登录（检测到 web_session cookie 即结束，最长 5 分钟）...")
        for i in range(60):  # 60 * 5s = 5 分钟
            await asyncio.sleep(5)
            cookies = await ctx.cookies("https://www.xiaohongshu.com")
            xhs_cookies = [c for c in cookies if "xiaohongshu" in c.get("domain", "")]
            has_session = any(c["name"] == "web_session" for c in xhs_cookies)
            if has_session:
                print(f"✅ 登录成功！检测到 {len(xhs_cookies)} 个 xiaohongshu cookie")
                for c in xhs_cookies:
                    if c["name"] in ("web_session", "a1", "webId"):
                        print(f"  - {c['name']}: ...{c['value'][-12:]}")
                break
            print(f"  ({i + 1}/60) 仍未检测到 web_session cookie...")
        else:
            print("❌ 5 分钟内未完成登录，请重试")
            sys.exit(1)

        # 再等一会儿让 storage 全量写盘
        await asyncio.sleep(3)
        print(f"💾 Profile 已持久化到: {PROFILE_DIR}")
    finally:
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
