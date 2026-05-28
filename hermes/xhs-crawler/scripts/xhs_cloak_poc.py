#!/usr/bin/env python3
"""CloakBrowser PoC — 验证 stealth 能力 + 短链跳转。

用法：
    python3 scripts/xhs_cloak_poc.py "<小红书短链>"

⚠️ 注意：
- 这是 PoC，**不带登录态**，未登录账号访问 explore 页会被 302 到 /login，
  body 几乎为空。这是预期行为，证明 cloakbrowser 工作正常，但 stealth
  解决不了"未登录账号无权限"。
- 完整提取需要 launch_persistent_context_async(user_data_dir=...) +
  首次 headed 登录扫码。见 SKILL.md "CloakBrowser 适配"章节。

预期输出：
- 4 项 stealth 探针应当全部正常（webdriver=false, chromeObj=object,
  plugins>=5, UA 不含 HeadlessChrome）
- final URL 会是 xiaohongshu.com/login?redirectPath=... （未登录预期）
"""

import asyncio
import json
import sys

JS_EXTRACTOR = r"""
() => {
    const result = {
        title: document.title.replace(' - 小红书', ''),
        url: location.href,
        author: '',
        content: '',
        tags: [],
        app_restricted: false,
        page_text_length: document.body.innerText.length,
    };
    const bodyText = document.body.innerText;
    if (bodyText.includes('请打开小红书App') ||
        bodyText.includes('扫码查看') ||
        bodyText.includes('App内打开')) {
        result.app_restricted = true;
    }
    const authorSels = ['.author-wrapper .name', '.author-info .nickname',
                        '.user-info .name', '.author-name', '.nickname',
                        '[class*="author"] [class*="name"]'];
    for (const s of authorSels) {
        const el = document.querySelector(s);
        if (el && el.textContent.trim()) { result.author = el.textContent.trim(); break; }
    }
    const contentSels = ['#detail-desc', '.desc', '.note-text',
                         '[class*="content"] [class*="desc"]'];
    for (const s of contentSels) {
        const el = document.querySelector(s);
        if (el && el.innerText.trim()) { result.content = el.innerText.trim(); break; }
    }
    const tagSet = new Set();
    document.querySelectorAll('a[href*="search_result"], .tag, [class*="tag"]')
        .forEach(el => {
            const t = el.textContent.trim();
            if (t.startsWith('#') && t.length < 30) tagSet.add(t);
        });
    result.tags = [...tagSet];
    return result;
}
"""


async def main(url: str):
    import cloakbrowser as cb
    print(f"🚀 CloakBrowser PoC (v{cb.__version__}, Chromium {cb.CHROMIUM_VERSION})")
    print(f"🔗 URL: {url}")

    browser = await cb.launch_async(headless=False, humanize=True)
    print("✓ CloakBrowser launched")
    try:
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = await ctx.new_page()

        print("🌐 goto...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        print(f"🔀 final URL: {page.url}")

        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(1)

        data = await page.evaluate(JS_EXTRACTOR)
        print("\n📊 extracted:")
        print(json.dumps(data, ensure_ascii=False, indent=2))

        probe = await page.evaluate("""
        () => ({
            webdriver: navigator.webdriver,
            userAgent: navigator.userAgent,
            chromeObj: typeof window.chrome,
            plugins: navigator.plugins.length,
            languages: navigator.languages,
        })
        """)
        print("\n🕵️ stealth probe:")
        print(json.dumps(probe, ensure_ascii=False, indent=2))

        await ctx.close()
    finally:
        await browser.close()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://xhslink.com/o/9HYvnxJB3ML"
    asyncio.run(main(url))
