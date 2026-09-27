#!/usr/bin/env python3
"""命书 HTML → PDF 导出（destiny-matrix v4 · S10 交付）。

用法: python3 export_pdf.py <input.html> [output.pdf]

Playwright Chromium 渲染（禁用 Chrome --virtual-time-budget 路线，
该 flag 已知会令 SVG/JS 渲染挂起，见 MEMORY 2026-02-18 记录）。
依赖: pip install playwright pypdf && python3 -m playwright install chromium
     （pypdf 必需，用于页数与空白页检测）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MIN_PAGES = 20
# 高于此页数大概率是 CSS 分页失控（如每元素一页）
MAX_PAGES = 200
PDF_MARGIN = {"top": "18mm", "bottom": "16mm", "left": "14mm", "right": "14mm"}
RENDER_TIMEOUT_MS = 60000


def extract_title(html_text):
    # 页眉标题优先级：<title> → h1.book-title → 文件名（调用方兜底）
    m = re.search(r"<title>([^<]+)</title>", html_text)
    if m:
        return m.group(1).strip()
    m = re.search(r'class="book-title"[^>]*>([^<]+)<', html_text)
    if m:
        return m.group(1).strip()
    return None


def render_pdf(html_path, pdf_path, title):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle",
                  timeout=RENDER_TIMEOUT_MS)
        # 等 SVG 挂载 + 字体加载完；命书 SVG 为内联静态节点，此处主要防
        # 未来引入 JS 生成图表时抢跑截 PDF。超时不中断（无 SVG 的降级命书也放行）
        try:
            page.wait_for_function(
                "document.querySelectorAll('svg').length > 0"
                " && document.fonts.status === 'loaded'",
                timeout=15000,
            )
        except Exception:
            print("warn: SVG/字体等待超时，继续出 PDF（若命书含图表请人工复核）",
                  file=sys.stderr)
        page.wait_for_timeout(500)

        header = (
            '<div style="width:100%;font-size:8px;color:#8a8a8a;'
            'text-align:center;padding-top:2mm;'
            "font-family:'PingFang SC','Songti SC',sans-serif;\">"
            + title + "</div>"
        )
        footer = (
            '<div style="width:100%;font-size:8px;color:#8a8a8a;'
            'text-align:center;padding-bottom:2mm;">'
            '&mdash; <span class="pageNumber"></span> / '
            '<span class="totalPages"></span> &mdash;</div>'
        )
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=header,
            footer_template=footer,
            margin=PDF_MARGIN,
        )
        browser.close()



def sanity_check(pdf_path):
    """返回 (页数, 问题清单)。问题非空即视为异常。"""
    from pypdf import PdfReader
    problems = []

    reader = PdfReader(str(pdf_path))
    pages = len(reader.pages)

    blank = []
    for i, pg in enumerate(reader.pages):
        text = (pg.extract_text() or "").strip()
        # 纯图表页也会带 SVG 内文字/页眉页脚文本，全空才算空白页
        if not text:
            blank.append(i + 1)

    # 末尾空白页是分页余量常见产物：直接删掉而非报错
    trailing = 0
    while blank and blank[-1] == pages - trailing:
        blank.pop()
        trailing += 1
    if trailing:
        from pypdf import PdfWriter
        writer = PdfWriter()
        for i in range(pages - trailing):
            writer.add_page(reader.pages[i])
        tmp = pdf_path.with_suffix(".tmp.pdf")
        with open(tmp, "wb") as f:
            writer.write(f)
        tmp.replace(pdf_path)
        pages -= trailing
        print("已移除末尾空白页 %d 页" % trailing)

    if blank:
        problems.append("正文中存在空白页: 第 %s 页" % ", ".join(map(str, blank)))
    if pages < MIN_PAGES:
        problems.append("页数 %d < %d，疑似渲染不完整" % (pages, MIN_PAGES))
    if pages > MAX_PAGES:
        problems.append("页数 %d > %d，疑似分页失控" % (pages, MAX_PAGES))
    return pages, problems


def main(argv):
    if len(argv) not in (2, 3):
        print("用法: python3 export_pdf.py <input.html> [output.pdf]", file=sys.stderr)
        return 2
    html_path = Path(argv[1])
    pdf_path = Path(argv[2]) if len(argv) == 3 else html_path.with_suffix(".pdf")
    if html_path.resolve() == pdf_path.resolve():
        print("用法错误: 输出路径不能与输入文件相同", file=sys.stderr)
        return 2
    try:
        from pypdf import PdfReader  # noqa: F401
    except ImportError:
        print("ERROR: pypdf 未安装；请运行 pip install pypdf", file=sys.stderr)
        return 1
    try:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        html_text = html_path.read_text(encoding="utf-8")
        title = extract_title(html_text) or html_path.stem
        render_pdf(html_path, pdf_path, title)
        if not pdf_path.exists() or pdf_path.stat().st_size < 10 * 1024:
            raise RuntimeError("PDF 生成失败或体积异常小")
        pages, problems = sanity_check(pdf_path)
        size_kb = pdf_path.stat().st_size / 1024
        print("PDF: %s" % pdf_path)
        print("页数: %d · 大小: %.0f KB · 页眉标题: %s" % (pages, size_kb, title))
        if problems:
            for prob in problems:
                print("sanity fail: %s" % prob, file=sys.stderr)
            return 1
        print("sanity check 通过")
        return 0
    except Exception as e:
        print("ERROR: %s" % str(e).replace("\\n", " "), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
