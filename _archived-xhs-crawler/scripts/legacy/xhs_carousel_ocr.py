#!/usr/bin/env python3
"""
XHS Carousel OCR - 小红书轮播图逐张截图OCR
功能：自动滑动轮播图，逐张截图并OCR识别
"""

import asyncio
import os
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
                    if key not in os.environ:
                        os.environ[key] = value


load_env()

CDP_URL = os.environ.get("CHROME_CDP_URL", "ws://127.0.0.1:18792/cdp")
TEMP_DIR = Path(os.environ.get("XHS_TEMP_DIR", "/tmp/xhs_analyzer"))
QWEN_API_URL = os.environ.get(
    "QWEN_API_URL", "http://<internal IP redacted>:9998/v1/chat/completions"
)


async def ocr_with_qwen(image_path: str) -> str:
    """使用本地 Qwen3-VL 进行 OCR"""
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
                            "text": "请提取这张图片中的所有文字内容。如果是Prompt模板，请保留完整格式和占位符。只输出文字内容，不要解释。",
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


async def extract_carousel_images(url: str) -> dict:
    """提取轮播图每张图片"""
    # 检查是否为本地路径
    path = Path(url)
    if path.exists() and path.is_dir():
        # 本地文件夹模式
        return await process_local_images(path)
    
    # URL 模式（原有逻辑）
    return await process_url_images(url)


async def process_local_images(image_dir: Path) -> dict:
    """处理本地文件夹中的图片"""
    session_id = datetime.now().strftime("%H%M%S")
    temp_dir = TEMP_DIR / f"carousel_{session_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 处理本地文件夹: {image_dir}")
    
    # 获取所有图片文件
    image_files = sorted([
        f for f in image_dir.glob("slide_*.png")
    ])
    
    if not image_files:
        # 尝试其他图片格式
        image_files = sorted([
            f for f in image_dir.glob("*")
            if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']
        ])
    
    print(f"🖼️ 找到 {len(image_files)} 张图片")
    
    screenshots = []
    ocr_results = []
    
    for i, img_path in enumerate(image_files, 1):
        print(f"\n📄 处理第 {i}/{len(image_files)} 张: {img_path.name}")
        
        # 复制到临时目录
        temp_path = temp_dir / f"slide_{i:02d}.png"
        import shutil
        shutil.copy(img_path, temp_path)
        screenshots.append(str(temp_path))
        
        # OCR 识别
        print(f"   🔍 OCR 识别中...")
        try:
            text = await ocr_with_qwen(str(temp_path))
            ocr_results.append({
                "slide": i,
                "path": str(temp_path),
                "text": text
            })
            print(f"   ✅ 识别完成 ({len(text)} 字符)")
        except Exception as e:
            print(f"   ❌ OCR 失败: {e}")
            ocr_results.append({
                "slide": i,
                "path": str(temp_path),
                "text": f"[OCR Error: {e}]"
            })
    
    # 保存结果
    result = {
        "url": str(image_dir),
        "session_id": session_id,
        "total_slides": len(screenshots),
        "screenshots": screenshots,
        "ocr_results": ocr_results,
    }
    
    result_file = temp_dir / "result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result


async def process_url_images(url: str) -> dict:
    """通过浏览器处理 URL 中的轮播图（原有逻辑）"""
    session_id = datetime.now().strftime("%H%M%S")
    temp_dir = TEMP_DIR / f"carousel_{session_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

async def process_url_images(url: str) -> dict:
    """通过浏览器处理 URL 中的轮播图（原有逻辑）"""
    session_id = datetime.now().strftime("%H%M%S")
    temp_dir = TEMP_DIR / f"carousel_{session_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = await context.new_page()

        print(f"🌐 加载页面...")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # 找到轮播图容器
        print("🎯 查找轮播图...")

        # 尝试多种选择器找到轮播图
        carousel_selectors = [
            ".swiper",
            ".note-swiper",
            '[class*="swiper"]',
            ".note-content .images",
            ".note-detail .images",
        ]

        carousel_locator = None
        for sel in carousel_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    carousel_locator = loc
                    print(f"   ✓ 找到轮播图: {sel}")
                    break
            except:
                continue

        if not carousel_locator:
            print("   ⚠️ 未找到轮播图，尝试直接找图片...")
            # 尝试找所有图片并滚动
            carousel_locator = page.locator("img").first

        # 获取图片总数
        total_images = 10  # 用户确认有10张
        print(f"   📊 预计图片数: {total_images}")

        # 存储截图和OCR结果
        screenshots = []
        ocr_results = []

        # 尝试找到下一张按钮
        next_button_selectors = [
            ".swiper-button-next",
            ".next-btn",
            '[class*="next"]',
            'button[class*="right"]',
            ".arrow-right",
        ]

        next_button = None
        for sel in next_button_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    next_button = loc
                    print(f"   ✓ 找到下一张按钮: {sel}")
                    break
            except:
                continue

        # 逐张截图
        for i in range(total_images):
            print(f"\n🖼️ 处理第 {i + 1}/{total_images} 张...")

            try:
                # 截图当前轮播图
                screenshot_path = temp_dir / f"slide_{i:02d}.png"

                # 滚动到轮播图区域并截图
                await carousel_locator.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)

                await carousel_locator.screenshot(path=str(screenshot_path))
                screenshots.append(str(screenshot_path))
                print(f"   ✓ 截图已保存: {screenshot_path.name}")

                # OCR识别
                print(f"   🔍 OCR识别...")
                ocr_text = await ocr_with_qwen(str(screenshot_path))
                ocr_results.append(
                    {"slide": i + 1, "path": str(screenshot_path), "text": ocr_text}
                )

                # 显示前100字
                preview = ocr_text[:100].replace("\n", " ")
                print(f"      {preview}...")

                # 点击下一张
                if next_button and i < total_images - 1:
                    try:
                        await next_button.click()
                        await asyncio.sleep(1.5)  # 等待动画完成
                    except Exception as e:
                        print(f"      ⚠️ 点击下一张失败: {e}")
                        # 尝试滑动
                        try:
                            await carousel_locator.evaluate("el => el.scrollBy(300, 0)")
                            await asyncio.sleep(1)
                        except:
                            pass
                else:
                    # 尝试键盘右箭头
                    try:
                        await page.keyboard.press("ArrowRight")
                        await asyncio.sleep(1)
                    except:
                        pass

            except Exception as e:
                print(f"   ❌ 处理失败: {e}")

        await browser.close()

        # 保存结果
        result = {
            "url": url,
            "session_id": session_id,
            "total_slides": len(screenshots),
            "screenshots": screenshots,
            "ocr_results": ocr_results,
        }

        result_file = temp_dir / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result


async def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 xhs_carousel_ocr.py <小红书链接 或 本地图片文件夹>")
        print("示例:")
        print("  python3 xhs_carousel_ocr.py http://xhslink.com/xxxxx")
        print("  python3 xhs_carousel_ocr.py /tmp/xhs_analyzer/full_20260206_165255/")
        sys.exit(1)

    url = sys.argv[1]
    result = await extract_carousel_images(url)

    print("\n" + "=" * 60)
    print("✅ 轮播图 OCR 完成")
    print("=" * 60)
    print(f"共处理: {result['total_slides']} 张")
    if result['screenshots']:
        print(f"结果保存: {os.path.dirname(result['screenshots'][0])}")

    # 打印所有OCR结果
    print("\n📝 OCR 汇总:")
    print("=" * 60)
    for item in result["ocr_results"]:
        print(f"\n--- 第 {item['slide']} 张 ---")
        print(item["text"])


if __name__ == "__main__":
    asyncio.run(main())
