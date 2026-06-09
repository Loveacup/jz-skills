#!/usr/bin/env python3
"""
XHS Extractor v2 - 小红书内容提取器（修复版）
修复问题：
1. 图片数量读取不完整 - 增强轮播图检测 + 预加载
2. App 限制检测 - 提前识别并提示用户
3. 添加降级处理 - 部分失败时返回已有数据
4. 增强错误处理和重试机制
"""

import asyncio
import os
import re
import json
import base64
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import urllib.request

# 加载 .env 文件
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_env()

CHROME_CDP_URL = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:19222")
QWEN_API_URL = os.environ.get("QWEN_API_URL", "http://<internal IP redacted>:9998/v1/chat/completions")
OUTPUT_DIR = Path(os.environ.get("XHS_OUTPUT_DIR", str(Path.home() / "Documents/Obsidian/AlexCai/00-Inbox")))
TEMP_DIR = Path(os.environ.get("XHS_TEMP_DIR", "/tmp/xhs_analyzer"))

# 增强版 JS 提取器
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
        stats: {},
        app_restricted: false
    };
    
    // 检测 App 限制
    const bodyText = document.body.innerText;
    if (bodyText.includes('请打开小红书App') || 
        bodyText.includes('扫码查看') ||
        bodyText.includes('App内打开') ||
        document.querySelector('.qrcode, [class*="qrcode"], [class*="qr-code"]')) {
        result.app_restricted = true;
    }
    
    // 作者
    const authorSelectors = [
        '.author-wrapper .name',
        '.author-info .nickname', 
        '.user-info .name',
        '.author-name',
        '.nickname',
        '[class*="author"] [class*="name"]'
    ];
    for (const sel of authorSelectors) {
        const el = document.querySelector(sel);
        if (el && el.textContent.trim()) {
            result.author = el.textContent.trim();
            break;
        }
    }
    
    const authorLink = document.querySelector('a[href*="/user/profile/"]');
    if (authorLink) {
        const match = authorLink.href.match(/\/user\/profile\/([^/?]+)/);
        if (match) result.authorId = match[1];
    }
    
    // 正文 - 增强版多选择器
    const contentSelectors = [
        '.desc',
        '.note-content .content',
        '.note-detail .content',
        '.content-wrapper .desc',
        '[class*="note"] [class*="content"]',
        'article',
        '.main-content .desc',
        '[class*="detail"] [class*="content"]'
    ];
    for (const sel of contentSelectors) {
        const el = document.querySelector(sel);
        if (el && el.textContent.trim().length > 50) {
            result.content = el.textContent.trim();
            break;
        }
    }
    
    // 兜底：查找最长文本块
    if (!result.content || result.content.length < 100) {
        let best = '';
        document.querySelectorAll('div, p, span, article').forEach(el => {
            const text = el.textContent.trim();
            if (text.length > best.length && text.length > 200 && text.length < 8000 &&
                /[\u4e00-\u9fa5]/.test(text) && 
                !text.includes('ICP备') && 
                !text.includes('营业执照') &&
                !text.includes('隐私政策') &&
                !text.includes('用户协议')) {
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
    
    // 评论 - 增强版
    const seenComments = new Set();
    const commentSelectors = [
        '.comment-item',
        '.comment-container .item',
        '[class*="comment-item"]',
        '[class*="CommentItem"]',
        '.note-comment',
        '.comment-list .item',
        '.comment-wrapper .item',
        '[class*="comment"] > div'
    ];
    
    for (const selector of commentSelectors) {
        document.querySelectorAll(selector).forEach(item => {
            let user = '';
            const userSelectors = [
                '.user-name', '.nickname', '.author-name', '.name',
                '[class*="user"] span', 'a[href*="/user/"]', '.comment-user'
            ];
            for (const usel of userSelectors) {
                const uel = item.querySelector(usel);
                if (uel && uel.textContent.trim()) {
                    user = uel.textContent.trim();
                    break;
                }
            }
            
            let text = '';
            const textSelectors = [
                '.text', '.content', '.comment-content',
                '[class*="text"]', '[class*="content"]', 'p', 'span:last-child'
            ];
            for (const tsel of textSelectors) {
                const tel = item.querySelector(tsel);
                if (tel && tel.textContent.trim().length > 2) {
                    text = tel.textContent.trim();
                    break;
                }
            }
            
            let likes = '';
            const likeSelectors = ['.like-count', '.like', '[class*="like"]', '.thumb'];
            for (const lsel of likeSelectors) {
                const lel = item.querySelector(lsel);
                if (lel) {
                    const match = lel.textContent.match(/(\d+)/);
                    if (match) { likes = match[1]; break; }
                }
            }
            
            let time = '';
            const timeSelectors = ['.time', '.date', '[class*="time"]'];
            for (const tsel of timeSelectors) {
                const tel = item.querySelector(tsel);
                if (tel && tel.textContent.match(/\d{2}-\d{2}|今天|昨天|\d{4}/)) {
                    time = tel.textContent.trim();
                    break;
                }
            }
            
            const key = user + '|' + text.slice(0, 50);
            if (user && text && !seenComments.has(key) && text.length > 5) {
                seenComments.add(key);
                result.comments.push({user, text, likes, time});
            }
        });
        if (result.comments.length > 0) break;
    }
    
    // 图片 - 增强版，包含 data-src
    const seenImgs = new Set();
    document.querySelectorAll('img').forEach(img => {
        let src = img.src || img.getAttribute('data-src') || img.dataset.src;
        if (src && (src.includes('xiaohongshu') || src.includes('xhscdn')) && 
            !seenImgs.has(src) && !src.includes('avatar') && !src.includes('icon')) {
            seenImgs.add(src);
            result.images.push(src);
        }
    });
    
    // 统计数据
    const likeMatch = bodyText.match(/([\d.]+)\s*万?\s*赞/);
    const collectMatch = bodyText.match(/([\d.]+)\s*万?\s*收藏/);
    const commentMatch = bodyText.match(/共?\s*([\d.]+)\s*万?\s*条评论/);
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


async def detect_carousel_slides(page) -> int:
    """增强版轮播图数量检测"""
    # 方法1：检测指示器
    indicators = await page.evaluate("""() => {
        const els = document.querySelectorAll('.swiper-pagination-bullet, .indicator, [class*="pagination"], [class*="dot"]');
        return els.length;
    }""")
    if indicators > 1:
        return indicators
    
    # 方法2：检测 slide 元素
    slides = await page.evaluate("""() => {
        const els = document.querySelectorAll('.swiper-slide, .slide, [class*="slide"]');
        return els.length;
    }""")
    if slides > 1:
        return slides
    
    # 方法3：预加载后检测图片
    await page.evaluate("""() => {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (img.dataset.src) img.src = img.dataset.src;
            if (img.getAttribute('data-src')) img.src = img.getAttribute('data-src');
        });
    }""")
    await asyncio.sleep(2)
    
    img_count = await page.evaluate("""() => {
        const imgs = document.querySelectorAll('img');
        let count = 0;
        imgs.forEach(img => {
            if (img.src && (img.src.includes('webpic') || img.src.includes('xhscdn')) 
                && !img.src.includes('avatar') && !img.src.includes('icon')) {
                count++;
            }
        });
        return count;
    }""")
    if img_count > 0:
        return img_count
    
    # 方法4：检测页码指示器文本（如 "1/14"）
    page_indicator = await page.evaluate("""() => {
        const text = document.body.innerText;
        const match = text.match(/(\d+)\s*\/\s*(\d+)/);
        return match ? parseInt(match[2]) : 0;
    }""")
    if page_indicator > 1:
        return page_indicator
    
    return 10  # 默认


async def extract_full_note(url: str, skip_ocr: bool = False) -> dict:
    """完整提取笔记内容（修复版）"""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = TEMP_DIR / f"full_{session_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    errors = []
    warnings = []

    print(f"\n{'=' * 60}")
    print("🚀 小红书提取器 v2（修复版）")
    print(f"{'=' * 60}")
    print(f"📎 链接: {url}")
    print(f"💾 会话: {session_id}")
    print(f"🔍 OCR: {'跳过' if skip_ocr else '启用'}")

    try:
        async with async_playwright() as p:
            # 连接 Chrome CDP
            print(f"\n🔌 连接 Chrome CDP...")
            try:
                browser = await p.chromium.connect_over_cdp(CHROME_CDP_URL)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                print(f"   ✓ 已连接")
            except Exception as e:
                errors.append(f"CDP连接失败: {e}")
                print(f"   ❌ CDP连接失败: {e}")
                return {
                    "error": "CDP连接失败",
                    "details": str(e),
                    "url": url,
                    "session_id": session_id
                }

            # 打开笔记
            print(f"\n🌐 打开笔记...")
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(8)
                print(f"   ✓ 页面加载完成")
            except PlaywrightTimeout:
                errors.append("页面加载超时")
                print(f"   ⚠️ 页面加载超时，尝试继续...")
            except Exception as e:
                errors.append(f"页面加载错误: {e}")
                print(f"   ⚠️ 页面加载错误: {e}")

            # 提取基础数据
            print(f"\n📊 提取基础数据...")
            data = await page.evaluate(JS_EXTRACTOR)
            data["url"] = page.url
            data["session_id"] = session_id
            data["errors"] = errors
            data["warnings"] = warnings
            
            # 检测 App 限制
            if data.get("app_restricted"):
                warnings.append("该笔记被限制在App内查看，网页端无法获取完整内容")
                print(f"   ⚠️ 检测到App限制！网页端无法获取完整内容")
                print(f"   💡 建议：请在小红书App中打开此链接，然后手动复制内容")
                
                # 即使有限制，也返回已获取的数据
                await browser.close()
                return data
            
            print(f"   ✓ 正文: {len(data.get('content', ''))} 字")
            print(f"   ✓ 评论: {len(data.get('comments', []))} 条")
            print(f"   ✓ 图片: {len(data.get('images', []))} 张")
            print(f"   ✓ 作者: {data.get('author', 'N/A')}")
            
            # 正文完整性检查
            if len(data.get("content", "")) < 50:
                warnings.append(f"正文较短({len(data.get('content', ''))}字符)，可能未完整提取")
                print(f"   ⚠️ 警告: 正文较短")

            # 滚动加载评论
            print(f"\n💬 加载评论区...")
            try:
                for _ in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)
                
                # 尝试点击展开按钮
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
                
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)
                
                print(f"   ✓ 评论加载完成")
            except Exception as e:
                warnings.append(f"评论加载异常: {e}")
                print(f"   ⚠️ 评论加载: {e}")

            # 重新提取（评论加载后）
            data = await page.evaluate(JS_EXTRACTOR)
            data["url"] = page.url
            data["session_id"] = session_id
            data["errors"] = errors
            data["warnings"] = warnings
            
            print(f"   ✓ 更新后评论: {len(data.get('comments', []))} 条")

            # 检测轮播图数量（增强版）
            print(f"\n🔍 检测轮播图数量...")
            total_slides = await detect_carousel_slides(page)
            print(f"   ✓ 检测到 {total_slides} 张轮播图")

            # 轮播图截图
            print(f"\n🎠 提取轮播图（{total_slides}张）...")
            screenshots = []
            ocr_results = []

            for i in range(total_slides):
                print(f"   🖼️ 第 {i + 1}/{total_slides} 张")

                screenshot_path = temp_dir / f"slide_{i:02d}.png"
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    screenshots.append(str(screenshot_path))
                    print(f"      ✓ 截图")
                except Exception as e:
                    warnings.append(f"截图失败(第{i+1}张): {e}")
                    print(f"      ❌ 截图失败: {e}")
                    continue

                # OCR 识别
                if skip_ocr:
                    ocr_results.append({"slide": i + 1, "path": str(screenshot_path), "text": ""})
                    print(f"      ⏭️ OCR 跳过")
                else:
                    print(f"      🔍 OCR...")
                    try:
                        ocr_text = await ocr_with_qwen(str(screenshot_path))
                        ocr_results.append({"slide": i + 1, "path": str(screenshot_path), "text": ocr_text})
                        print(f"      ✓ {len(ocr_text)} 字")
                    except Exception as e:
                        warnings.append(f"OCR失败(第{i+1}张): {e}")
                        ocr_results.append({"slide": i + 1, "path": str(screenshot_path), "text": f"[OCR Error: {e}]"})
                        print(f"      ❌ OCR失败: {e}")

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
            
    except Exception as e:
        errors.append(f"提取过程异常: {e}")
        return {
            "error": "提取失败",
            "details": str(e),
            "url": url,
            "session_id": session_id,
            "errors": errors,
            "warnings": warnings
        }


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 xhs_extractor_v2.py <小红书链接> [--no-ocr]")
        print("\n修复内容:")
        print("  ✓ 增强轮播图检测（指示器/slide/图片/页码）")
        print("  ✓ 预加载所有图片避免懒加载问题")
        print("  ✓ App限制检测和提示")
        print("  ✓ 降级处理：部分失败返回已有数据")
        print("  ✓ 增强错误处理和日志")
        sys.exit(1)

    url = sys.argv[1]
    skip_ocr = "--no-ocr" in sys.argv

    data = await extract_full_note(url, skip_ocr=skip_ocr)

    # 打印摘要
    print(f"\n{'=' * 60}")
    if data.get("error") and not data.get("content"):
        print("❌ 提取失败")
    elif data.get("warnings"):
        print("⚠️ 提取完成（有警告）")
    else:
        print("✅ 提取完成！")
    print(f"{'=' * 60}")
    print(f"作者: {data.get('author', 'N/A')}")
    print(f"正文: {len(data.get('content', ''))} 字")
    print(f"评论: {len(data.get('comments', []))} 条")
    print(f"轮播图OCR: {len(data.get('carousel_ocr', []))} 张")
    print(f"完整内容: {len(data.get('full_content', ''))} 字")
    
    if data.get("warnings"):
        print(f"\n⚠️ 警告:")
        for w in data["warnings"]:
            print(f"  - {w}")
    
    if data.get("errors"):
        print(f"\n❌ 错误:")
        for e in data["errors"]:
            print(f"  - {e}")

    # 输出JSON到stdout
    print(f"\n📄 JSON 输出:")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
