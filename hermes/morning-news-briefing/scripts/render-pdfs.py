#!/usr/bin/env python3
"""Render morning-news briefing markdown to dual-format PDF: Mobile (430×932) + A4.

v2.0 — fixed Markdown converter for v4.0 content structure (📰今日要闻 + 🔍分析 + 📌总结).

Usage:
    python3 scripts/render-pdfs.py morning-news-2026-06-03.md

Key design decisions (see references/pdf-rendering-lessons.md):
- System fonts only (no Google Fonts — won't load in headless Chrome)
- State-machine parser (not naive line-by-line — v4.0 emoji sections break simple parsers)
- CJK line-height ≥ 1.75 to prevent overlap
- Playwright domcontentloaded (not networkidle — faster + avoids font-load timeout)
"""

from playwright.sync_api import sync_playwright
import re, os, sys

md_path = sys.argv[1] if len(sys.argv) > 1 else "morning-news-2026-06-03.md"
out_dir = os.path.dirname(os.path.abspath(md_path)) if os.path.dirname(md_path) else "."
date_str = os.path.basename(md_path).replace("morning-news-", "").replace(".md", "")
base = os.path.join(out_dir, f"morning-news-{date_str}")

with open(md_path, "r", encoding="utf-8") as f:
    markdown = f.read()

accent = "#b47a32"
accent_dark = "#8b5e2a"

# ─── CSS (system fonts only, no Google Fonts) ───

MOBILE_CSS = f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  width: 430px; padding: 20px 16px 32px 16px;
  background: #fffdf8; color: #1b1a17;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  font-size: 13.5px; line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}}
h1 {{ font-size: 22px; font-weight: 800; text-align: center; margin: 8px 0 16px 0; color: #1a1a1a; }}
h2 {{ font-size: 17px; font-weight: 700; color: {accent}; margin: 20px 0 8px 0; padding-bottom: 4px; border-bottom: 1.5px solid {accent}; }}
h3 {{ font-size: 15px; font-weight: 700; color: #3d3d3d; margin: 14px 0 6px 0; }}
h4 {{ font-size: 14px; font-weight: 600; color: #555; margin: 10px 0 4px 0; }}
p {{ margin: 5px 0; }}
strong {{ color: #1a1a1a; font-weight: 700; }}
em {{ color: #6a6965; }}
hr {{ border: none; border-top: 1px solid #e8dcc8; margin: 14px 0; }}

.news-item {{ margin: 5px 0 5px 8px; padding-left: 6px; border-left: 2px solid #e8dcc8; font-size: 13px; line-height: 1.7; }}
.news-item strong {{ font-size: 13px; }}

.exec-summary {{
  background: #faf5e8; border-left: 3px solid {accent};
  padding: 10px 12px; margin: 10px 0 16px 0; border-radius: 0 4px 4px 0;
}}
.exec-summary p {{ margin: 3px 0; font-size: 13px; line-height: 1.6; }}
.exec-summary strong {{ color: {accent}; }}

.analysis-block {{
  background: #faf8f2; border: 1px solid #e0d6c2;
  border-radius: 5px; padding: 12px 14px; margin: 12px 0;
}}
.analysis-block h3 {{ font-size: 15px; color: {accent}; margin-bottom: 6px; }}
.analysis-block .label {{ font-weight: 700; color: #1b1a17; font-size: 13px; }}
.analysis-block p {{ font-size: 13px; line-height: 1.7; margin: 3px 0; }}
.analysis-block .why {{ font-size: 12.5px; color: #6a6965; margin-top: 4px; font-style: italic; }}

.today-summary {{
  background: linear-gradient(135deg, {accent} 0%, {accent_dark} 100%);
  color: #fff; padding: 14px 16px; border-radius: 6px; margin: 16px 0;
}}
.today-summary h2 {{ font-size: 13px; color: rgba(255,255,255,0.85); border: none; margin-bottom: 6px; }}
.today-summary p {{ font-size: 14px; font-weight: 600; line-height: 1.7; color: #fff; }}

.source-ledger {{ margin-top: 20px; padding-top: 12px; border-top: 1px solid #e0d6c2; }}
.source-ledger h2 {{ font-size: 13px; color: #8a8a84; border: none; }}
.source-ledger .src-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2px 12px; font-size: 10.5px; color: #8a8a84; }}
.src-grid div {{ line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

ul, ol {{ padding-left: 16px; margin: 4px 0; }}
li {{ font-size: 13px; line-height: 1.7; margin: 2px 0; }}

table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 11px; }}
th {{ background: #f5eedf; padding: 5px 6px; text-align: left; font-weight: 700; border-bottom: 1.5px solid {accent}; }}
td {{ padding: 3px 6px; border-bottom: 1px solid #e8dcc8; }}

.footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #e0d6c2; font-size: 11px; color: #b0b0b0; text-align: center; }}
.cite {{ font-size: 9px; color: {accent}; vertical-align: super; font-weight: 600; }}
"""

A4_CSS = MOBILE_CSS.replace("width: 430px", "max-width: 680px; margin: 0 auto") \
    .replace("font-size: 13.5px", "font-size: 11pt") \
    .replace("font-size: 13px", "font-size: 10pt") \
    .replace("font-size: 22px", "font-size: 28pt") \
    .replace("font-size: 17px", "font-size: 16pt") \
    .replace("font-size: 15px", "font-size: 13pt") \
    .replace("font-size: 14px", "font-size: 12pt") \
    .replace("font-size: 11px", "font-size: 9pt") \
    .replace("font-size: 10.5px", "font-size: 8.5pt") \
    .replace("font-size: 12.5px", "font-size: 9.5pt") \
    .replace("font-size: 9px", "font-size: 7pt") \
    .replace("padding: 20px 16px 32px 16px", "padding: 36px 48px 48px 48px")


# ─── Markdown → HTML Converter ───

def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    i = 0

    def emit(tag, content="", cls=None):
        if cls:
            out.append(f'<{tag} class="{cls}">{content}</{tag}>')
        else:
            out.append(f'<{tag}>{content}</{tag}>')

    def inline(s):
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
        s = re.sub(r'\[s(\d+)\]', rf'<sup class="cite">[s\1]</sup>', s)
        return s

    def flush_buffer(buf, tag="p", cls=None):
        if buf:
            text = " ".join(buf).strip()
            if text:
                emit(tag, inline(text), cls)
            buf.clear()

    p_buf = []
    in_analysis = False
    in_today = False
    in_source = False
    source_items = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_buffer(p_buf)
            i += 1
            continue

        if stripped.startswith("# ") and not stripped.startswith("## "):
            flush_buffer(p_buf)
            emit("h1", inline(stripped[2:]))
            i += 1
            continue

        if stripped.startswith("## ") and not stripped.startswith("### "):
            flush_buffer(p_buf)
            text = stripped[3:]
            if "今日要闻" in text: in_analysis = False
            elif "深度分析" in text: in_analysis, in_today = True, False
            elif "今日总结" in text: in_today, in_analysis = True, False
            elif "来源清单" in text: in_source, in_today = True, False
            emit("h2", inline(text))
            i += 1
            continue

        if stripped.startswith("### "):
            flush_buffer(p_buf)
            emit("h3", inline(stripped[4:]))
            i += 1
            continue

        if stripped.startswith("#### "):
            flush_buffer(p_buf)
            emit("h4", inline(stripped[5:]))
            i += 1
            continue

        if stripped == "---":
            flush_buffer(p_buf)
            emit("hr")
            i += 1
            continue

        if "|" in stripped and stripped.startswith("|"):
            flush_buffer(p_buf)
            rows = []
            while i < len(lines) and "|" in lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
                rows.append(cells); i += 1
            if rows:
                data_rows = [r for r in rows if not all(re.match(r'^-+$', c) for c in r)]
                if data_rows:
                    html = "<table>"
                    for ri, row in enumerate(data_rows):
                        tag = "th" if ri == 0 and len(data_rows) > 1 else "td"
                        html += "<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in row) + "</tr>"
                    html += "</table>"
                    out.append(html)
            continue

        if in_today and stripped[0].isdigit():
            flush_buffer(p_buf)
            out.append('<div class="today-summary">')
            j = i
            while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("#") and not lines[j].strip().startswith("---"):
                ln = lines[j].strip()
                if re.match(r'^\d+\.\s', ln):
                    strong_repl = r"<strong>\1</strong>"
                    num_bold_pat = r"^\d+\.\s*\*\*(.+?)\*\*"
                    out.append(f'<p>{inline(re.sub(num_bold_pat, strong_repl, ln))}</p>')
                else:
                    p_buf.append(ln)
                j += 1
            flush_buffer(p_buf)
            out.append('</div>')
            i, in_today = j, False
            continue

        if in_source and "|" in stripped:
            flush_buffer(p_buf)
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cells) >= 2 and not all(re.match(r'^-+$', c) for c in cells):
                source_items.append((cells[0].strip(), cells[1].strip() if len(cells) > 1 else ""))
            i += 1
            continue

        if in_source and "|" not in stripped:
            flush_buffer(p_buf)
            if source_items:
                out.append('<div class="source-ledger"><h2>📰 来源清单</h2><div class="src-grid">')
                for sid, name in source_items:
                    out.append(f'<div><strong>{inline(sid)}</strong> {inline(name)}</div>')
                out.append('</div></div>')
                source_items = []
            in_source = False

        if stripped.startswith("- ") and not in_analysis and not in_today:
            flush_buffer(p_buf)
            j = i; items = []
            while j < len(lines) and lines[j].strip().startswith("- ") and not lines[j].strip().startswith("---"):
                items.append(inline(lines[j].strip()[2:])); j += 1
            out.append("<ul>" + "".join(f'<li class="news-item">{it}</li>' for it in items) + "</ul>")
            i = j
            continue

        if in_analysis and stripped.startswith("**"):
            flush_buffer(p_buf)
            out.append('<div class="analysis-block">')
            j = i; content_lines = []
            while j < len(lines):
                nl = lines[j].strip()
                if not nl: j += 1; continue
                if nl.startswith("## ") or nl.startswith("### ") or nl == "---": break
                if j > i and nl.startswith("**") and ("：" in nl or ": " in nl): break
                content_lines.append(nl); j += 1
            for cl in content_lines:
                if cl.startswith("### "): out.append(f'<h3>{inline(cl[4:])}</h3>')
                elif cl.startswith("**") and ("：" in cl or ": " in cl):
                    m = re.match(r'\*\*(.+?[:：])\*\*\s*(.*)', cl)
                    if m:
                        label, text = m.group(1), m.group(2)
                        cls = "why" if "为什么重要" in label else ""
                        out.append(f'<p class="label">{inline(label)}</p>')
                        if text: out.append(f'<p class="{"why" if "为什么重要" in label else ""}">{inline(text)}</p>')
                    else: out.append(f'<p>{inline(cl)}</p>')
                elif cl.startswith("- "): out.append(f'<li>{inline(cl[2:])}</li>')
                else: out.append(f'<p>{inline(cl)}</p>')
            out.append('</div>')
            i = j
            continue

        p_buf.append(stripped)
        i += 1

    flush_buffer(p_buf)

    if source_items:
        out.append('<div class="source-ledger"><h2>📰 来源清单</h2><div class="src-grid">')
        for sid, name in source_items:
            out.append(f'<div><strong>{inline(sid)}</strong> {inline(name)}</div>')
        out.append('</div></div>')

    body = "\n".join(out)
    body += f'\n<div class="footer">早新闻简报 · {date_str} · Alex Cai · Hermes Agent v4.0</div>'
    return body


def render_pdf(body_html, output_path, css, width=None, height=None, fmt=None):
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>{body_html}</body>
</html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        if width and height:
            page.set_viewport_size({"width": int(width), "height": int(height)})
        page.set_content(html, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(500)
        kwargs = {"path": output_path, "print_background": True}
        if fmt:
            kwargs["format"] = fmt
            kwargs["margin"] = {"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"}
        else:
            kwargs["width"] = f"{width}px"; kwargs["height"] = f"{height}px"
            kwargs["margin"] = {"top": "0", "right": "0", "bottom": "0", "left": "0"}
        page.pdf(**kwargs)
        browser.close()
    print(f"✅ {output_path} ({os.path.getsize(output_path)/1024:.0f} KB)")


if __name__ == "__main__":
    body_html = md_to_html(markdown)
    render_pdf(body_html, f"{base}-mobile.pdf", MOBILE_CSS, width=430, height=932)
    render_pdf(body_html, f"{base}-a4.pdf", A4_CSS, fmt="A4")
    print("ALL PDFS GENERATED ✓")
