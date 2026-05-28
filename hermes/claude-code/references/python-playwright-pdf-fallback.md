# Python Playwright PDF 渲染回退方案

## 适用场景

当 CC print mode 或 tmux 模式在渲染 PDF 时卡住（>5 分钟无输出），直接用 Python + Playwright 渲染更可靠。

## 已知触发条件

- 输入 markdown > ~15KB 且内容结构复杂（多级标题、blockquote、列表、表格）
- CC print mode 可能在 Playwright 调用阶段静默运行 >8 分钟无进度信号
- 复现：morning-news-2026-05-28.md（~19KB, 37 sources）→ CC 运行 8+ 分钟无输出

## 回退方案

```python
import markdown, re, os
from playwright.sync_api import sync_playwright

# 1. 读取 markdown
with open("input.md", "r", encoding="utf-8") as f:
    md = f.read()

# 2. 转换为 HTML
html_body = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])

# 3. 提取模板 CSS（从 morning-news-briefing 的 mobile-template.html）
template_path = "~/.hermes/profiles/regent/skills/productivity/morning-news-briefing/assets/mobile-template.html"
with open(template_path, "r", encoding="utf-8") as f:
    template = f.read()
style_match = re.search(r"<style[^>]*>(.*?)</style>", template, re.DOTALL)
css = style_match.group(1) if style_match else "<fallback CSS here>"

# 4. 组装完整 HTML
full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=430, initial-scale=1.0">
<style>{css}</style></head>
<body>{html_body}</body></html>"""

# 5. 渲染 PDF
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 430, "height": 932})
    page.goto(f"file://{html_path}")
    page.wait_for_load_state("networkidle")
    page.pdf(path=pdf_path, width="430px", height="932px", print_background=True)
    browser.close()
```

## 成功案例

- morning-news-2026-05-28: 19KB markdown → 19KB HTML → 943KB PDF / 7 pages，耗时 <5 秒

## 依赖

```bash
pip install markdown playwright
python3 -m playwright install chromium
```
