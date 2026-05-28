#!/usr/bin/env python3
"""
XHS CloakBrowser Extractor - 用 CloakBrowser 持久化 profile 完整提取小红书
功能：正文、作者、标签、互动数据、评论、轮播图截图 + DeepSeek-OCR-2 OCR
特点：
  - 无需手动启动 Chrome with CDP，cloakbrowser 自己拉独立 Chromium
  - 反检测能力（webdriver=false, plugins>=5, Chrome UA）
  - 持久化登录态在 ~/.cloakbrowser/xhs_profile/
  - OCR 走 vveai.com DeepSeek-OCR-2（云端，无需本地 Qwen）
"""

import asyncio
import base64
import json
import os
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# 让 print 实时刷新（背景进程下默认会被 buffer）
import functools

print = functools.partial(print, flush=True)  # noqa: A001


# ---------------- env loading ----------------
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v)


load_env()

OCR_API_URL = os.environ.get(
    "OCR_API_URL", "https://api.vveai.com/v1/chat/completions"
)
OCR_API_KEY = os.environ.get("OCR_API_KEY", "")
OCR_MODEL = os.environ.get("OCR_MODEL", "DeepSeek-OCR-2")
PROFILE_DIR = Path(
    os.environ.get(
        "CLOAKBROWSER_PROFILE_DIR",
        str(Path.home() / ".cloakbrowser" / "xhs_profile"),
    )
)
OUTPUT_DIR = Path.home() / "Documents/Obsidian/AlexCai/00-Inbox"


# ---------------- OCR ----------------
def _dedupe_repeats(text: str) -> str:
    """DeepSeek-OCR 偶尔陷入重复循环或输出 grounding 标签，清理一下。"""
    if not text:
        return text
    import re

    # 0) 去掉 grounding 标签 <|ref|>...<|/ref|><|det|>...</|det|>
    text = re.sub(r"<\|ref\|>", "", text)
    text = re.sub(r"<\|/ref\|>", "", text)
    text = re.sub(r"<\|det\|>\[\[[^\]]*\]\]<\|/det\|>", "", text)
    text = re.sub(r"<\|[^|]*\|>", "", text)

    # 1) 切句号/句尾，统计重复句子
    parts = re.split(r"(?<=[。！？\.\!\?\n])", text)
    seen = {}
    out = []
    for p in parts:
        s = p.strip()
        if not s:
            out.append(p)
            continue
        seen[s] = seen.get(s, 0) + 1
        if seen[s] > 3:
            continue
        out.append(p)
    cleaned = "".join(out)
    # 2) 把同一短语连续重复 >=6 次的折叠为 [×N]
    cleaned = re.sub(
        r"((?:[\u4e00-\u9fa5\w]{1,15}?))(?:\1){5,}",
        lambda m: f"{m.group(1)}[×重复]",
        cleaned,
    )
    return cleaned.strip()


def ocr_image(img_path: str, prompt: str = None) -> str:
    """调用 DeepSeek-OCR-2（OpenAI 兼容格式）提取图片文字。"""
    if not OCR_API_KEY:
        return "[OCR Error: OCR_API_KEY 未配置]"
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": OCR_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt or "<image>\nOCR this image",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 4000,
        }

        req = urllib.request.Request(
            OCR_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OCR_API_KEY}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data["choices"][0]["message"]["content"].strip()
            return _dedupe_repeats(raw)
    except Exception as e:
        return f"[OCR Error: {e}]"


# ---------------- 正文提取（沿用 xhs_full_extractor 经验） ----------------
EXTRACT_BASE_JS = r"""
() => {
    const data = {
        title: document.title.replace(' - 小红书', ''),
        author: '',
        content: '',
        tags: [],
        url: location.href,
        stats: {},
        app_restricted: false,
    };

    const bodyText = document.body.innerText;
    if (bodyText.includes('请打开小红书App') ||
        bodyText.includes('扫码查看') ||
        bodyText.includes('App内打开')) {
        data.app_restricted = true;
    }

    // 作者
    for (const sel of ['.author-wrapper .name', '.author-info .nickname',
                       '.user-info .name', '.author-name', '.nickname',
                       '[class*="author"] [class*="name"]']) {
        const el = document.querySelector(sel);
        if (el && el.textContent.trim()) { data.author = el.textContent.trim(); break; }
    }

    // 互动数据
    const likeMatch = bodyText.match(/([\d.]+)\s*万?\s*赞/);
    const collectMatch = bodyText.match(/([\d.]+)\s*万?\s*收藏/);
    const commentMatch = bodyText.match(/共?\s*([\d.]+)\s*万?\s*条评论/);
    if (likeMatch) data.stats.likes = likeMatch[0].replace(/赞|\s/g, '');
    if (collectMatch) data.stats.collects = collectMatch[0].replace(/收藏|\s/g, '');
    if (commentMatch) data.stats.comments = commentMatch[0].replace(/条评论|共|\s/g, '');

    return data;
}
"""

EXTRACT_CONTENT_JS = r"""
() => {
    // 1) 精确选择器：#detail-desc 是小红书笔记正文容器
    const desc = document.querySelector('#detail-desc');
    if (desc && desc.innerText.trim().length > 20) {
        return desc.innerText.trim();
    }

    // 2) 找其它候选，但排除登录蒙层文字
    const reject = ['刷到更懂你的优质内容', '搜索最新种草', '查看收藏、点赞', '与他人更好地互动'];
    const isJunk = t => !t || t.length < 30 || reject.some(r => t.includes(r));

    let text = '';
    const selectors = ['.note-content .content', '.note-detail .content',
                       '.content-wrapper .desc', 'article',
                       '.main-content .desc',
                       '[class*="note"] [class*="content"]'];
    for (const sel of selectors) {
        for (const el of document.querySelectorAll(sel)) {
            const t = el.innerText.trim();
            if (!isJunk(t)) { text = t; break; }
        }
        if (text) break;
    }

    if (!text || text.length < 50) {
        let best = null, maxLen = 0;
        document.querySelectorAll('div, p, article').forEach(el => {
            const t = el.textContent.trim();
            if (t.length > maxLen && t.length > 100 && t.length < 5000 &&
                /[\u4e00-\u9fa5]/.test(t) && !isJunk(t) &&
                !t.includes('ICP备') && !t.includes('营业执照') &&
                !t.includes('隐私政策') && !t.includes('行吟信息')) {
                maxLen = t.length;
                best = el;
            }
        });
        if (best) text = best.textContent.trim();
    }
    return text;
}
"""

EXTRACT_TAGS_JS = r"""
() => {
    const text = document.body.innerText;
    const matches = text.match(/#[\u4e00-\u9fa5\w]+/g);
    return matches ? [...new Set(matches.map(t => t.slice(1)))].slice(0, 15) : [];
}
"""

EXTRACT_COMMENTS_JS = r"""
() => {
    const out = [];
    const seenEls = new Set();
    const itemSels = ['.comment-item', '.parent-comment', '.sub-comment',
                      '.comment-container .item', '[class*="comment-item"]',
                      '.note-comment', '.comment-list .item',
                      '[class*="CommentItem"]'];
    for (const sel of itemSels) {
        document.querySelectorAll(sel).forEach(item => {
            if (seenEls.has(item)) return;
            seenEls.add(item);
            let user = '';
            for (const us of ['.user-name', '.nickname', '.author-name',
                              '.name', '[class*="user"] span',
                              'a[href*="/user/"]', '.comment-user']) {
                const ue = item.querySelector(us);
                if (ue && ue.textContent.trim()) { user = ue.textContent.trim(); break; }
            }
            let text = '';
            for (const ts of ['.text', '.content', '.comment-content',
                              '[class*="text"]', '[class*="content"]',
                              'p', 'span:last-child']) {
                const te = item.querySelector(ts);
                if (te && te.textContent.trim().length > 2) {
                    text = te.textContent.trim();
                    break;
                }
            }
            // 判断是否是楼主回复
            const isAuthor = !!item.querySelector('[class*="author-tag"], .tag-item');
            if (user && text && text.length > 1) {
                out.push({ user, text, is_author_reply: isAuthor });
            }
        });
    }
    return out;
}
"""


async def load_all_comments(page, note_id: str = "", xsec_token: str = "") -> list:
    """
    评论加载（DOM 模式）：
    - 滚动 `.note-scroller` 评论容器到底部，触发小红书内置的分页 API（带 x-s/x-t 签名）
    - 主动点击 `.show-more` 按钮展开子评论
    - 用 EXTRACT_COMMENTS_JS 从 DOM 提取最终列表

    ⚠ 不要直接 fetch /comment/page API：缺 x-s 签名头会返回
       "当前账号存在异常，请切换账号后重试"（即使 cookie 完整）。
       Vue 组件内置的 axios interceptor 才会自动签名，所以走 DOM 渲染。

    ⚠ 必须登录态：未登录时小红书只放 10 条预览，剩余需要登录 cookie。
       登录态过期后跑 scripts/xhs_cloak_login.py 扫码刷新。

    ⚠ 不要用 headless=True 跑 cloakbrowser 提取评论 — 实测 headless 模式
       即使带完整登录 cookie，页面仍渲染"登录查看全部评论内容"占位符，
       只显示 10 条。**必须 headless=False（headed 模式）**才能拿到完整评论。
    """
    note_scroller_sel = '.note-scroller'

    # ----- 阶段 1：滚动加载所有主评论 -----
    print(f"\n💬 加载评论（DOM 模式）...")
    prev = 0
    no_change = 0
    for i in range(40):
        await page.evaluate(
            f"() => {{ const el = document.querySelector('{note_scroller_sel}'); "
            f"if (el) el.scrollTop = el.scrollHeight; }}"
        )
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        cur = await page.evaluate(
            "() => document.querySelectorAll('.parent-comment').length"
        )
        if cur == prev:
            no_change += 1
            if no_change >= 4:
                print(f"    主评论加载完成（{cur} 条）")
                break
        else:
            print(f"    滚动 {i + 1}: 主评论 {cur} 条 (+{cur - prev})")
            no_change = 0
            prev = cur

    # ----- 阶段 2：展开所有 .show-more 子评论按钮 -----
    print(f"    展开子评论...")
    for round_i in range(8):
        # 先把所有 .show-more 滚到视口内（小红书 Vue 组件需要按钮在视口才会触发事件）
        try:
            btns = page.locator('.show-more')
            n_btns = await btns.count()
            if n_btns == 0:
                break
            clicked = 0
            # 倒序点击（从底部往上滚），避免上面的展开把下面的按钮顶飞
            for idx in range(n_btns):
                try:
                    # 每次重新定位（DOM 会变）
                    cur_btns = page.locator('.show-more')
                    cnt_now = await cur_btns.count()
                    if cnt_now == 0:
                        break
                    b = cur_btns.first
                    await b.scroll_into_view_if_needed(timeout=2000)
                    await asyncio.sleep(0.3)
                    bbox = await b.bounding_box()
                    if bbox and 0 < bbox['y'] < 900:
                        await page.mouse.click(
                            bbox['x'] + bbox['width'] / 2,
                            bbox['y'] + bbox['height'] / 2,
                        )
                        clicked += 1
                        await asyncio.sleep(0.8)
                except Exception:
                    continue
            sub_cnt = await page.evaluate(
                "() => document.querySelectorAll('.comment-item-sub').length"
            )
            remaining = await page.locator('.show-more').count()
            print(f"    展开轮 {round_i + 1}: 点击 {clicked}, 子评论 {sub_cnt}, 剩余 {remaining}")
            if remaining == 0 or clicked == 0:
                break
            # 滚到底加载更多
            await page.evaluate(
                f"() => {{ const el = document.querySelector('{note_scroller_sel}'); "
                f"if (el) el.scrollTop = el.scrollHeight; }}"
            )
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"    展开异常: {e}")
            break

    return await page.evaluate(EXTRACT_COMMENTS_JS)


def _normalize_comment(c: dict, is_sub: bool) -> dict:
    """统一评论结构（保留：用于将来 API 模式回归）"""
    user = c.get("user_info", {}) or {}
    show_tags = c.get("show_tags") or []
    is_author = "is_author" in show_tags
    target = c.get("target_comment") or {}
    target_user = (target.get("user_info") or {}).get("nickname", "") if target else ""
    text = c.get("content", "") or ""
    if target_user:
        text = f"回复 @{target_user}: {text}"
    return {
        "user": user.get("nickname", ""),
        "text": text,
        "likes": c.get("like_count", "0"),
        "create_time": c.get("create_time"),
        "ip_location": c.get("ip_location", ""),
        "is_author_reply": is_author,
        "is_sub": is_sub,
        "id": c.get("id", ""),
    }


# ---------------- 轮播图 ----------------
async def collect_slide_image_urls(page) -> list:
    """从 .note-slider-img 中提取唯一图片 URL 列表（去重并保留顺序）。"""
    return await page.evaluate(
        """
        () => {
            const seen = new Set();
            const urls = [];
            document.querySelectorAll('.note-slider-img img, .xhs-slider-container img').forEach(img => {
                if (!img.src || img.src.includes('avatar')) return;
                if (!img.src.includes('webpic') && !img.src.includes('xhscdn')) return;
                // 去掉 query string 后做去重 key
                const key = img.src.split('!')[0];
                if (!seen.has(key)) { seen.add(key); urls.push(img.src); }
            });
            return urls;
        }
        """
    )


def download_image(url: str, dest: Path, timeout: int = 30) -> bool:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.xiaohongshu.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            dest.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"      ⚠️ 下载失败: {e}")
        return False


async def capture_carousel(page, temp_dir: Path) -> list:
    print("\n🎠 提取轮播图 OCR（直连 CDN 下载 + OCR）...")
    # 给 lazy-load 图片一些时间出现 — 滚一下并触发右箭头
    for _ in range(3):
        try:
            await page.keyboard.press("ArrowRight")
        except Exception:
            pass
        await asyncio.sleep(0.6)
    await asyncio.sleep(1)

    urls = await collect_slide_image_urls(page)
    if not urls:
        print("    未找到轮播图 URL，跳过")
        return []

    print(f"    📊 共 {len(urls)} 张唯一图片")
    results = []
    for i, url in enumerate(urls, 1):
        path = temp_dir / f"slide_{i:02d}.png"
        if not download_image(url, path):
            results.append({"slide": i, "text": "[下载失败]", "url": url})
            continue
        try:
            text = ocr_image(str(path))
            results.append({"slide": i, "text": text, "url": url})
            print(f"    📸 [{i}/{len(urls)}] OCR ✓ ({len(text)} 字符)")
            try:
                path.unlink()
            except Exception:
                pass
        except Exception as e:
            print(f"    ❌ slide {i} OCR 失败: {e}")
            results.append({"slide": i, "text": f"[Error: {e}]", "url": url})
    return results


# ---------------- 主流程 ----------------
async def extract(url: str) -> dict:
    import cloakbrowser as cb

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(f"/tmp/xhs_analyzer/cloak_{session_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"🚀 CloakBrowser XHS Extractor (cb {cb.__version__}, Chromium {cb.CHROMIUM_VERSION})")
    print("=" * 70)
    print(f"📎 URL: {url}")
    print(f"📁 Profile: {PROFILE_DIR}")
    print(f"💾 会话: {session_id}")

    if not PROFILE_DIR.exists():
        print(
            f"\n❌ Profile 目录不存在: {PROFILE_DIR}\n"
            f"   请先运行登录脚本：python3 scripts/xhs_cloak_login.py"
        )
        sys.exit(1)

    print("🔧 启动 CloakBrowser persistent context...")
    ctx = await cb.launch_persistent_context_async(
        user_data_dir=str(PROFILE_DIR),
        headless=False,  # ⚠ 必须 headed：headless 模式即使有登录 cookie 也只渲染 10 条评论
        humanize=True,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN",
    )
    print("✓ context 启动完成")

    try:
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("\n🌐 加载页面...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)
        # 等 networkidle，最多再等 5s
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        final_url = page.url
        print(f"🔀 final URL: {final_url}")

        # 从 URL 解析 note_id 和 xsec_token（用于评论 API）
        import re as _re
        from urllib.parse import urlparse, parse_qs
        note_id_match = _re.search(r"/explore/([a-f0-9]+)", final_url)
        note_id = note_id_match.group(1) if note_id_match else ""
        qs = parse_qs(urlparse(final_url).query)
        xsec_token = qs.get("xsec_token", [""])[0]

        # 滚一下，触发懒加载
        for _ in range(2):
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        # 基础数据
        base = await page.evaluate(EXTRACT_BASE_JS)
        if base.get("app_restricted"):
            print("⚠️ 页面要求 App 内打开。可能登录态过期，请重新跑 login 脚本。")

        # 正文
        base["content"] = await page.evaluate(EXTRACT_CONTENT_JS)
        # 标签
        base["tags"] = await page.evaluate(EXTRACT_TAGS_JS)

        print(f"\n📄 标题: {base['title']}")
        print(f"👤 作者: {base['author']}")
        print(f"📝 正文: {len(base['content'])} 字符")
        print(f"🏷️ 标签: {len(base['tags'])} 个 -> {base['tags'][:8]}")
        print(f"📊 互动: {base['stats']}")

        # 评论
        comments = await load_all_comments(page, note_id=note_id, xsec_token=xsec_token)
        print(f"💬 评论提取: {len(comments)} 条")

        # 轮播图
        ocr_results = await capture_carousel(page, temp_dir)

        # 期望评论数
        expected = 0
        if base["stats"].get("comments"):
            try:
                s = base["stats"]["comments"].replace("万", "0000")
                expected = int(float(s))
            except Exception:
                pass

        full_ocr_text = "\n\n".join(
            [f"## 图片 {r['slide']}\n{r['text']}" for r in ocr_results]
        )

        full = {
            **base,
            "comments": comments,
            "carousel_ocr": ocr_results,
            "full_content": base["content"] + ("\n\n" + full_ocr_text if full_ocr_text else ""),
            "extracted_at": session_id,
            "completeness_check": {
                "content_length": len(base["content"]),
                "comments_count": len(comments),
                "expected_comments": expected,
                "ocr_slides": len(ocr_results),
            },
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / f"xhs_cloak_{session_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(full, f, ensure_ascii=False, indent=2)
        print(f"\n💾 JSON: {json_path}")

        text_path = OUTPUT_DIR / f"xhs_cloak_{session_id}.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(f"标题: {base['title']}\n")
            f.write(f"作者: {base['author']}\n")
            f.write(f"链接: {base['url']}\n")
            f.write(f"互动: {base['stats']}\n")
            f.write(f"标签: {' '.join('#' + t for t in base['tags'])}\n")
            f.write("=" * 70 + "\n\n")
            f.write("【正文】\n")
            f.write(base["content"] + "\n\n")
            f.write(f"【评论】({len(comments)} 条)\n")
            for c in comments:
                f.write(f"- {c['user']}: {c['text'][:200]}\n")
            f.write("\n【轮播图 OCR】\n")
            for r in ocr_results:
                f.write(f"\n--- 图 {r['slide']} ---\n")
                f.write((r["text"][:1500]) + "\n")
        print(f"💾 TEXT: {text_path}")

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        return full
    finally:
        await ctx.close()


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 xhs_cloak_extractor.py <小红书链接>")
        sys.exit(1)
    url = sys.argv[1]
    try:
        result = await extract(url)
        print("\n" + "=" * 70)
        print("✅ 提取完成")
        print("=" * 70)
        c = result.get("completeness_check", {})
        print(f"  正文: {c.get('content_length')} 字符")
        print(
            f"  评论: {c.get('comments_count')}/"
            f"{c.get('expected_comments') or '未知'} 条"
        )
        print(f"  OCR:  {c.get('ocr_slides')} 张")
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
