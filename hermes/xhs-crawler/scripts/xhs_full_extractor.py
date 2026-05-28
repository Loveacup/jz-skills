#!/usr/bin/env python3
"""
XHS Full Extractor - 小红书完整提取器（含OCR和自动清理）
功能：提取正文、评论、轮播图OCR，生成报告，自动清理临时文件
改进：增强正文和评论提取的完整性
"""

import asyncio
import json
import base64
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import urllib.request

# 配置
QWEN_API_URL = os.environ.get("QWEN_API_URL", "http://<internal IP redacted>:9998/v1/chat/completions")
CHROME_CDP_URL = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:19222")
OUTPUT_DIR = Path.home() / "Documents/Obsidian/AlexCai/00-Inbox"


def ocr_image(img_path: str) -> str:
    """使用本地 Qwen3-VL 进行 OCR"""
    try:
        with open(img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        payload = {
            "model": "Qwen3-VL-32B",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                        {"type": "text", "text": "提取图片中的所有文字内容。只输出文字，不要解释。"}
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        req = urllib.request.Request(
            QWEN_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[OCR Error: {e}]"


async def extract_content_with_retry(page, max_retries=3):
    """提取正文，带重试机制和多选择器备选"""
    for attempt in range(max_retries):
        content = await page.evaluate('''() => {
            let text = '';
            
            // 主要选择器
            const selectors = [
                '.desc',                                          // 最常用
                '.note-content .content',                         // 笔记内容区
                '.note-detail .content',                          // 详情页内容
                '.content-wrapper .desc',                         // 包装器内描述
                '[class*="note"] [class*="content"]',             // 模糊匹配
                'article',                                        // 文章标签
                '.main-content .desc'                             // 主内容区
            ];
            
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.textContent.trim().length > 20) {
                    text = el.textContent.trim();
                    break;
                }
            }
            
            // 如果还没找到，尝试查找包含最多文字的元素
            if (!text || text.length < 50) {
                let bestEl = null;
                let maxLen = 0;
                document.querySelectorAll('div, span, p, article').forEach(el => {
                    const txt = el.textContent.trim();
                    if (txt.length > maxLen && 
                        txt.length > 100 && 
                        txt.length < 5000 &&
                        /[\u4e00-\u9fa5]/.test(txt) &&
                        !txt.includes('ICP备') &&
                        !txt.includes('营业执照') &&
                        !txt.includes('隐私政策')) {
                        maxLen = txt.length;
                        bestEl = el;
                    }
                });
                if (bestEl) text = bestEl.textContent.trim();
            }
            
            return text;
        }''')
        
        if content and len(content) > 50:
            return content
        
        # 如果内容太短，滚动一下再试
        if attempt < max_retries - 1:
            await page.evaluate("window.scrollTo(0, 300)")
            await asyncio.sleep(1)
    
    return content or "[正文提取失败]"


async def load_all_comments(page, max_scrolls=15):
    """加载所有评论，包括点击"查看更多""""
    print(f"\n💬 加载评论（最多滚动 {max_scrolls} 次）...")
    
    previous_comment_count = 0
    no_change_count = 0
    
    for i in range(max_scrolls):
        # 滚动加载
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # 尝试点击"查看更多"或"展开"按钮
        try:
            # 多种可能的按钮文字
            button_selectors = [
                'button:has-text("查看更多")',
                'button:has-text("展开")',
                'div:has-text("查看更多")',
                'span:has-text("查看更多")',
                '[class*="more"]',
                '[class*="expand"]'
            ]
            
            for selector in button_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0 and await button.is_visible():
                        await button.click()
                        await asyncio.sleep(1)
                        print(f"    点击了展开按钮")
                        break
                except:
                    continue
        except:
            pass
        
        # 检查评论数量变化
        current_count = await page.evaluate('''() => {
            return document.querySelectorAll('.comment-item, [class*="comment-item"]').length;
        }''')
        
        if current_count == previous_comment_count:
            no_change_count += 1
            if no_change_count >= 3:  # 连续3次没有变化，认为已加载完成
                print(f"    评论加载完成（连续 {no_change_count} 次无新增）")
                break
        else:
            no_change_count = 0
            previous_comment_count = current_count
            print(f"    滚动 {i+1}: 已加载 {current_count} 条评论")
    
    # 提取评论
    comments = await page.evaluate('''() => {
        const seen = new Set();
        const comments = [];
        
        // 多种评论选择器
        const commentSelectors = [
            '.comment-item',
            '.comment-container .item',
            '[class*="comment-item"]',
            '.note-comment',
            '.comment-list .item',
            '.comment-wrapper .item',
            '[class*="CommentItem"]'
        ];
        
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
                
                // 去重并添加
                const key = (user + text).slice(0, 50);
                if (user && text && !seen.has(key) && text.length > 5) {
                    seen.add(key);
                    comments.push({user, text});
                }
            });
        }
        
        return comments;
    }''')
    
    return comments


async def extract_note(url: str) -> dict:
    """完整提取笔记内容"""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(f"/tmp/xhs_analyzer/xhs_{session_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("🚀 小红书完整提取（增强版）")
    print("="*70)
    print(f"📎 链接: {url}")
    print(f"💾 会话: {session_id}")
    
    async with async_playwright() as p:
        # 连接 Chrome
        print(f"\n🔌 连接 Chrome CDP...")
        browser = await p.chromium.connect_over_cdp(CHROME_CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        
        # 打开笔记
        print(f"🌐 打开笔记...")
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        print(f"📄 标题: {await page.title()}")
        print(f"📄 URL: {page.url}")
        
        # 提取基础数据
        print("\n📊 提取基础数据...")
        base_data = await page.evaluate('''() => {
            const data = { 
                title: document.title.replace(' - 小红书', ''), 
                author: '', 
                content: '',
                tags: [],
                url: window.location.href,
                stats: {}
            };
            
            // 作者
            const authorSelectors = ['.author-name', '.nickname', '.author-wrapper .name'];
            for (const sel of authorSelectors) {
                const el = document.querySelector(sel);
                if (el && el.textContent.trim()) {
                    data.author = el.textContent.trim();
                    break;
                }
            }
            
            // 互动数据
            const bodyText = document.body.innerText;
            const likeMatch = bodyText.match(/([\d.]+)\s*万?\s*赞/);
            const collectMatch = bodyText.match(/([\d.]+)\s*万?\s*收藏/);
            const commentMatch = bodyText.match(/共?\s*([\d.]+)\s*万?\s*条评论/);
            if (likeMatch) data.stats.likes = likeMatch[1] + (likeMatch[0].includes('万') ? '万' : '');
            if (collectMatch) data.stats.collects = collectMatch[1] + (collectMatch[0].includes('万') ? '万' : '');
            if (commentMatch) data.stats.comments = commentMatch[1] + (commentMatch[0].includes('万') ? '万' : '');
            
            return data;
        }''')
        
        # 提取正文（增强版）
        print("\n📝 提取正文...")
        base_data['content'] = await extract_content_with_retry(page)
        
        # 提取标签
        tag_matches = await page.evaluate('''() => {
            const text = document.body.innerText;
            const matches = text.match(/#[\u4e00-\u9fa5\w]+/g);
            return matches ? [...new Set(matches.map(t => t.slice(1)))].slice(0, 15) : [];
        }''')
        base_data['tags'] = tag_matches
        
        print(f"  ✅ 作者: {base_data['author']}")
        print(f"  ✅ 正文: {len(base_data['content'])} 字符")
        print(f"  ✅ 标签: {len(base_data['tags'])} 个")
        print(f"  ✅ 互动: {base_data['stats']}")
        
        # 正文完整性检查
        if len(base_data['content']) < 50:
            print(f"  ⚠️ 警告: 正文较短({len(base_data['content'])}字符)，可能未完整提取")
        
        # 加载评论（增强版）
        comments = await load_all_comments(page)
        print(f"  ✅ 评论: {len(comments)} 条")
        
        # 评论完整性检查
        expected_comments = 0
        if base_data['stats'].get('comments'):
            expected_str = base_data['stats']['comments'].replace('万', '0000')
            try:
                expected_comments = int(float(expected_str))
            except:
                pass
        
        if expected_comments > 0 and len(comments) < expected_comments * 0.5:
            print(f"  ⚠️ 警告: 只提取到 {len(comments)}/{expected_comments} 条评论，可能未完整加载")
        
        # 轮播图 OCR
        print("\n🎠 提取轮播图 OCR...")
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        
        # 检测轮播图数量
        total_slides = await page.evaluate('''() => {
            // 尝试多种方式检测轮播图数量
            const indicators = document.querySelectorAll('.swiper-pagination-bullet, .indicator, [class*="pagination"]');
            if (indicators.length > 0) return indicators.length;
            
            const slides = document.querySelectorAll('.swiper-slide, .slide, [class*="slide"]');
            if (slides.length > 0) return slides.length;
            
            // 检测图片数量
            const imgs = document.querySelectorAll('img');
            let count = 0;
            imgs.forEach(img => {
                if (img.src && img.src.includes('webpic') && !img.src.includes('avatar')) {
                    count++;
                }
            });
            return count > 0 ? count : 12;
        }''')
        
        print(f"  📊 检测到 {total_slides} 张轮播图")
        
        ocr_results = []
        for i in range(total_slides):
            slide_num = i + 1
            print(f"  📸 [{slide_num}/{total_slides}] 截图...", end=" ")
            screenshot_path = temp_dir / f"slide_{i:02d}.png"
            
            await page.screenshot(path=str(screenshot_path), full_page=False)
            print(f"✅", end=" ")
            
            print(f"OCR...", end=" ")
            try:
                text = ocr_image(str(screenshot_path))
                ocr_results.append({"slide": slide_num, "text": text})
                print(f"✅ ({len(text)}字符)")
                
                # 立即删除截图
                os.remove(screenshot_path)
                
            except Exception as e:
                print(f"❌ {e}")
                ocr_results.append({"slide": slide_num, "text": f"[Error: {e}]"})
            
            if i < total_slides - 1:
                await page.keyboard.press("ArrowRight")
                await asyncio.sleep(1.5)
        
        await browser.close()
        
        # 合并OCR文本
        full_ocr_text = "\n\n".join([f"## 图片 {r['slide']}\n{r['text']}" for r in ocr_results])
        
        # 组装完整数据
        full_data = {
            **base_data,
            "comments": comments,
            "carousel_ocr": ocr_results,
            "full_content": base_data['content'] + "\n\n" + full_ocr_text,
            "extracted_at": session_id,
            "completeness_check": {
                "content_length": len(base_data['content']),
                "comments_count": len(comments),
                "expected_comments": expected_comments,
                "ocr_slides": len(ocr_results)
            }
        }
        
        # 保存JSON
        json_path = OUTPUT_DIR / f"xhs_complete_{session_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 JSON保存: {json_path}")
        
        # 保存文本
        text_path = OUTPUT_DIR / f"xhs_complete_{session_id}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(f"标题: {base_data['title']}\n")
            f.write(f"作者: {base_data['author']}\n")
            f.write(f"链接: {base_data['url']}\n")
            f.write(f"互动: {base_data['stats']}\n")
            f.write("="*70 + "\n\n")
            f.write("【正文】\n")
            f.write(base_data['content'] + "\n\n")
            f.write(f"【评论】({len(comments)}条)\n")
            for c in comments:
                f.write(f"- {c['user']}: {c['text'][:200]}\n")
            f.write("\n【轮播图OCR】\n")
            for r in ocr_results:
                f.write(f"\n--- 图{r['slide']} ---\n")
                f.write(r['text'][:800] + "\n")
        print(f"💾 文本保存: {text_path}")
        
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
            print(f"🗑️ 临时目录已删除")
        except Exception as e:
            print(f"⚠️ 清理警告: {e}")
        
        return full_data


def print_checklist():
    """打印检查清单"""
    print("\n" + "="*70)
    print("📋 执行检查清单")
    print("="*70)
    checklist = [
        ("前置检查", [
            "浏览器状态检查: Chrome CDP 端口可连接",
            "登录态验证: Chrome中已登录小红书",
            "环境变量确认: CHROME_CDP_URL配置正确"
        ]),
        ("数据提取", [
            "基础数据提取: 标题、作者、正文内容",
            "正文完整性检查: 正文长度>50字符",
            "标签提取: 所有#标签已提取",
            "互动数据: 点赞、收藏、评论数",
            "评论区加载: 滚动加载直到无新增",
            "评论去重: 检查并去除重复评论",
            "评论完整性检查: 提取数量接近显示数量"
        ]),
        ("轮播图OCR", [
            "轮播图数量确认: 检测笔记总页数",
            "逐张截图: 所有轮播图页面已截图",
            "OCR识别: 每张截图已完成OCR",
            "OCR结果合并: 所有图片文字已合并到报告",
            "截图即时删除: 每完成一张OCR立即删除截图"
        ]),
        ("报告生成", [
            "7章节检查: 0-6章节全部完成",
            "P0约束验证: 元信息、逻辑流、评论分析、核心洞察齐全",
            "数据引用规范: 评论使用原文，禁止概括改写",
            "批判性审视: 包含独特价值和局限盲区分析"
        ]),
        ("临时文件清理", [
            "截图删除: 所有PNG截图文件已删除",
            "临时目录清理: /tmp/xhs_analyzer/下目录已删除",
            "保留文件确认: 仅保留最终报告和数据文件"
        ])
    ]
    
    for title, items in checklist:
        print(f"\n【{title}】")
        for item in items:
            print(f"  ☐ {item}")


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 xhs_full_extractor.py <小红书链接>")
        print("\n示例:")
        print("  python3 xhs_full_extractor.py 'http://xhslink.com/xxxxx'")
        print("\n选项:")
        print("  --checklist  打印完整检查清单")
        sys.exit(1)
    
    if sys.argv[1] == "--checklist":
        print_checklist()
        sys.exit(0)
    
    url = sys.argv[1]
    
    try:
        result = await extract_note(url)
        
        print("\n" + "="*70)
        print("✅ 提取完成！")
        print("="*70)
        print(f"\n📊 统计:")
        print(f"  标题: {result['title']}")
        print(f"  作者: {result['author']}")
        print(f"  正文: {len(result['content'])} 字符")
        print(f"  评论: {len(result['comments'])} 条")
        print(f"  轮播图OCR: {len(result['carousel_ocr'])} 张")
        
        # 完整性总结
        completeness = result.get('completeness_check', {})
        print(f"\n📋 完整性检查:")
        print(f"  正文长度: {completeness.get('content_length', 0)} 字符")
        print(f"  评论提取: {completeness.get('comments_count', 0)}/{completeness.get('expected_comments', '未知')} 条")
        
        if completeness.get('content_length', 0) < 50:
            print(f"  ⚠️ 警告: 正文可能不完整")
        if completeness.get('expected_comments', 0) > 0 and completeness.get('comments_count', 0) < completeness.get('expected_comments', 0) * 0.5:
            print(f"  ⚠️ 警告: 评论可能未完全加载")
        
        print(f"\n💾 文件保存至: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
