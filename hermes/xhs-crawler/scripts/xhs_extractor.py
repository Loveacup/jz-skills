#!/usr/bin/env python3
"""
XHS Extractor - 小红书内容提取器
功能：正文 + 评论 + 标签 + 轮播图截图 + Qwen3-VL OCR
"""

import asyncio
import os
import re
import json
import base64
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import urllib.request


# 加载 .env 文件（如果存在）
def load_env():
    """从 .env 文件加载环境变量"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:  # 环境变量优先级更高
                        os.environ[key] = value


load_env()

# 配置
CHROME_CDP_URL = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:19222")
QWEN_API_URL = os.environ.get(
    "QWEN_API_URL", "http://<internal IP redacted>:9998/v1/chat/completions"
)
OUTPUT_DIR = Path(
    os.environ.get(
        "XHS_OUTPUT_DIR", str(Path.home() / "Documents/Obsidian/AlexCai/00-Inbox")
    )
)
TEMP_DIR = Path(os.environ.get("XHS_TEMP_DIR", "/tmp/xhs_analyzer"))

# JS 提取器
JS_EXTRACTOR = r"""
() => {
    const result = {
        title: document.title.replace(' - 小红书', ''),
        author: '',
        authorId: '',
        content: '',
        tags: [],
        comments: [],
        images: [],
        stats: {}
    };
    
    // 作者
    const authorEl = document.querySelector('.author-wrapper .name, .author-info .nickname, .user-info .name');
    if (authorEl) result.author = authorEl.textContent.trim();
    
    const authorLink = document.querySelector('a[href*="/user/profile/"]');
    if (authorLink) {
        const match = authorLink.href.match(/\/user\/profile\/([^/?]+)/);
        if (match) result.authorId = match[1];
    }
    
    // 正文
    const contentSelectors = ['.note-content .content', '.note-detail .content', '[class*="note"] [class*="content"]', 'article'];
    for (const sel of contentSelectors) {
        const el = document.querySelector(sel);
        if (el && el.textContent.trim().length > 50) {
            result.content = el.textContent.trim();
            break;
        }
    }
    
    if (!result.content || result.content.length < 100) {
        let best = '';
        document.querySelectorAll('div, p').forEach(el => {
            const text = el.textContent.trim();
            if (text.length > best.length && text.length > 200 && text.length < 5000 &&
                /[\u4e00-\u9fa5]/.test(text) && !text.includes('ICP备') && !text.includes('营业执照')) {
                best = text;
            }
        });
        result.content = best;
    }
    
    // 标签
    document.querySelectorAll('a, span').forEach(el => {
        const text = el.textContent.trim();
        if (text.startsWith('#') && text.length > 2 && text.length < 50) {
            result.tags.push(text.slice(1));
        }
    });
    result.tags = [...new Set(result.tags)].slice(0, 15);
    
    // 评论 - 增强版，支持多种选择器
    const seenComments = new Set();
    
    // 多种评论选择器
    const commentSelectors = [
        '.comment-item',
        '.comment-container .item',
        '[class*="comment-item"]',
        '[class*="CommentItem"]',
        '.note-comment',
        '.comment-list .item',
        '.comment-wrapper .item'
    ];
    
    // 提取评论
    for (const selector of commentSelectors) {
        document.querySelectorAll(selector).forEach(item => {
            // 尝试多种方式获取用户名
            let user = '';
            const userSelectors = [
                '.user-name',
                '.nickname', 
                '.author-name',
                '.name',
                '[class*="user"] span',
                'a[href*="/user/"]',
                '.comment-user'
            ];
            
            for (const usel of userSelectors) {
                const uel = item.querySelector(usel);
                if (uel && uel.textContent.trim()) {
                    user = uel.textContent.trim();
                    break;
                }
            }
            
            // 尝试多种方式获取评论内容
            let text = '';
            const textSelectors = [
                '.text',
                '.content',
                '.comment-content',
                '[class*="text"]',
                '[class*="content"]',
                'p',
                'span:last-child'
            ];
            
            for (const tsel of textSelectors) {
                const tel = item.querySelector(tsel);
                if (tel && tel.textContent.trim().length > 2) {
                    text = tel.textContent.trim();
                    break;
                }
            }
            
            // 获取点赞数
            let likes = '';
            const likeSelectors = ['.like-count', '.like', '[class*="like"]', '.thumb'];
            for (const lsel of likeSelectors) {
                const lel = item.querySelector(lsel);
                if (lel) {
                    const match = lel.textContent.match(/(\d+)/);
                    if (match) {
                        likes = match[1];
                        break;
                    }
                }
            }
            
            // 获取时间
            let time = '';
            const timeSelectors = ['.time', '.date', '[class*="time"]'];
            for (const tsel of timeSelectors) {
                const tel = item.querySelector(tsel);
                if (tel && tel.textContent.match(/\d{2}-\d{2}|今天|昨天|\d{4}/)) {
                    time = tel.textContent.trim();
                    break;
                }
            }
            
            // 去重并添加
            const key = user + '|' + text.slice(0, 50);
            if (user && text && !seenComments.has(key) && text.length > 5) {
                seenComments.add(key);
                result.comments.push({user, text, likes, time});
            }
        });
        
        // 如果已提取到评论，跳出
        if (result.comments.length > 0) break;
    }
    
    // 图片
    const seenImgs = new Set();
    document.querySelectorAll('img').forEach(img => {
        let src = img.src || img.getAttribute('data-src');
        if (src && (src.includes('xiaohongshu') || src.includes('xhscdn')) && 
            !seenImgs.has(src) && !src.includes('avatar')) {
            seenImgs.add(src);
            result.images.push(src);
        }
    });
    
    // 统计数据
    const bodyText = document.body.innerText;
    const likeMatch = bodyText.match(/(\d+[\.\d]*)\s*万?\s*赞/);
    const collectMatch = bodyText.match(/(\d+[\.\d]*)\s*万?\s*收藏/);
    const commentMatch = bodyText.match(/共?\s*(\d+[\.\d]*)\s*万?\s*条评论/);
    if (likeMatch) result.stats.likes = likeMatch[1] + (likeMatch[0].includes('万') ? '万' : '');
    if (collectMatch) result.stats.collects = collectMatch[1] + (collectMatch[0].includes('万') ? '万' : '');
    if (commentMatch) result.stats.comments = commentMatch[1] + (commentMatch[0].includes('万') ? '万' : '');
    
    return result;
}
"""


async def ocr_with_qwen(image_path: str) -> str:
    """使用 Qwen3-VL 进行 OCR"""
    try:
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": "Qwen3-VL-32B",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                        },
                        {
                            "type": "text",
                            "text": "请提取这张小红书笔记图片中的所有文字内容。如果是Prompt模板，请保留完整格式。详细输出所有可见文字。",
                        },
                    ],
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
        }

        req = urllib.request.Request(
            QWEN_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[OCR Error: {e}]"


async def extract_full_note(url: str, skip_ocr: bool = False) -> dict:
    """完整提取笔记内容"""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = TEMP_DIR / f"full_{session_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("🚀 小红书提取器")
    print(f"{'=' * 60}")
    print(f"📎 链接: {url}")
    print(f"💾 会话: {session_id}")
    print(f"🔍 OCR: {'跳过' if skip_ocr else '启用'}")

    async with async_playwright() as p:
        # 连接 Chrome CDP
        print(f"\n🔌 连接 Chrome CDP...")
        browser = await p.chromium.connect_over_cdp(CHROME_CDP_URL)
        context = (
            browser.contexts[0] if browser.contexts else await browser.new_context()
        )
        print(f"   ✓ 已连接 (contexts: {len(browser.contexts)})")

        # 打开笔记
        page = await context.new_page()
        print(f"\n🌐 打开笔记...")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(8)
        print(f"   ✓ 页面加载完成")

        # 滚动加载评论
        print(f"\n💬 加载评论区...")
        try:
            # 尝试找到评论区并滚动
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1.5)

            # 尝试点击"查看评论"或类似按钮
            comment_buttons = [
                'button:has-text("查看")',
                'button:has-text("评论")',
                '[class*="comment"] button',
                'a:has-text("共")',
            ]
            for btn_sel in comment_buttons:
                try:
                    btn = page.locator(btn_sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue

            # 继续滚动以加载更多评论
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            print(f"   ✓ 评论加载完成")
        except Exception as e:
            print(f"   ⚠️ 评论加载: {e}")

        # 提取基础数据
        print(f"\n📊 提取基础数据...")
        data = await page.evaluate(JS_EXTRACTOR)
        data["url"] = page.url
        data["session_id"] = session_id
        print(f"   ✓ 正文: {len(data.get('content', ''))} 字")
        print(f"   ✓ 评论: {len(data.get('comments', []))} 条")
        print(f"   ✓ 图片: {len(data.get('images', []))} 张")
        print(f"   ✓ 作者: {data.get('author', 'N/A')}")

        # 检测轮播图数量
        print(f"\n🔍 检测轮播图数量...")
        total_slides = await page.evaluate("""() => {
            // 尝试多种方式检测轮播图数量
            const indicators = document.querySelectorAll('.swiper-pagination-bullet, .indicator, [class*="pagination"]');
            if (indicators.length > 0) return indicators.length;
            
            const slides = document.querySelectorAll('.swiper-slide, .slide, [class*="slide"]');
            if (slides.length > 0) return slides.length;
            
            // 检测图片数量（排除头像）
            const imgs = document.querySelectorAll('img');
            let count = 0;
            imgs.forEach(img => {
                if (img.src && img.src.includes('webpic') && !img.src.includes('avatar')) {
                    count++;
                }
            });
            return count > 0 ? count : 10; // 默认10张
        }""")

        print(f"   ✓ 检测到 {total_slides} 张轮播图")

        # 轮播图截图
        print(f"\n🎠 提取轮播图（{total_slides}张）...")
        screenshots = []
        ocr_results = []

        for i in range(total_slides):
            print(f"   🖼️ 第 {i + 1}/{total_slides} 张")

            screenshot_path = temp_dir / f"slide_{i:02d}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            screenshots.append(str(screenshot_path))
            print(f"      ✓ 截图")

            # OCR 识别（可选）
            if skip_ocr:
                ocr_results.append(
                    {"slide": i + 1, "path": str(screenshot_path), "text": ""}
                )
                print(f"      ⏭️ OCR 跳过")
            else:
                print(f"      🔍 OCR...")
                ocr_text = await ocr_with_qwen(str(screenshot_path))
                ocr_results.append(
                    {"slide": i + 1, "path": str(screenshot_path), "text": ocr_text}
                )
                print(f"      ✓ {len(ocr_text)} 字")

            # 下一张
            if i < total_slides - 1:
                await page.keyboard.press("ArrowRight")
                await asyncio.sleep(1.5)

        data["carousel_screenshots"] = screenshots
        data["carousel_ocr"] = ocr_results

        await browser.close()

        # 生成完整内容
        full_content = data.get("content", "")
        for ocr in ocr_results:
            if ocr.get("text") and not ocr["text"].startswith("[OCR Error"):
                full_content += f"\n\n## 图片 {ocr['slide']} OCR\n{ocr['text']}"
        data["full_content"] = full_content

        # 保存原始数据
        data_file = temp_dir / "data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 原始数据保存: {data_file}")

        return data


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 xhs_extractor.py <小红书链接> [--no-ocr]")
        print("环境变量:")
        print("  CHROME_CDP_URL=ws://127.0.0.1:18792/cdp")
        print("  QWEN_API_URL=http://<internal IP redacted>:9998/v1/chat/completions")
        print("  XHS_OUTPUT_DIR=path/to/output")
        print("  XHS_TEMP_DIR=/tmp/xhs_analyzer")
        sys.exit(1)

    url = sys.argv[1]
    skip_ocr = "--no-ocr" in sys.argv

    data = await extract_full_note(url, skip_ocr=skip_ocr)

    # 打印摘要
    print(f"\n{'=' * 60}")
    print("✅ 提取完成！")
    print(f"{'=' * 60}")
    print(f"作者: {data.get('author')}")
    print(f"正文: {len(data.get('content', ''))} 字")
    print(f"评论: {len(data.get('comments', []))} 条")
    print(f"轮播图OCR: {len(data.get('carousel_ocr', []))} 张")
    print(f"完整内容: {len(data.get('full_content', ''))} 字")

    # 输出JSON到stdout
    print(f"\n📄 JSON 输出:")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
