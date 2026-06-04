#!/usr/bin/env python3
"""Render a morning-news briefing markdown to dual-format PDF.
Usage: python3 render-dual-pdf.py <path/to/briefing.md>

Outputs:
  <dir>/<name>-mobile.pdf  (430×932px, cream #fffdf8, gold #b47a32)
  <dir>/<name>-a4.pdf      (A4, dark cover #111827→#123c55, Georgia/Noto Serif SC)
"""

from playwright.sync_api import sync_playwright
import re, sys, os

def md_to_html(md: str, is_mobile: bool = True) -> str:
    """Convert news briefing markdown to styled HTML."""
    accent = "#b47a32"
    lines = md.split("\n")
    html_lines = []
    in_table = False
    in_summary_blockquote = False
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_table:
                html_lines.append("</table>")
                in_table = False
            if in_summary_blockquote:
                html_lines.append("</div>")
                in_summary_blockquote = False
            if in_list:
                html_lines.append("</ol>")
                in_list = False
            continue

        if stripped.startswith("> "):
            if not in_summary_blockquote:
                html_lines.append('<div class="exec-summary">')
                in_summary_blockquote = True
            content = stripped[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\[s(\d+)\]', r'<sup class="cite">[s\1]</sup>', content)
            html_lines.append(f'<p class="summary-item">{content}</p>')
            continue

        if in_summary_blockquote:
            html_lines.append("</div>")
            in_summary_blockquote = False
        if in_list and not re.match(r'^\d+\.\s', stripped):
            html_lines.append("</ol>")
            in_list = False

        if stripped.startswith("# "):
            html_lines.append(f'<h1>{stripped[2:]}</h1>')
        elif stripped.startswith("## "):
            html_lines.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith("### "):
            html_lines.append(f'<h3>{stripped[4:]}</h3>')
        elif stripped == "---":
            html_lines.append("<hr>")
        elif "|" in stripped and stripped.startswith("|"):
            if not in_table:
                html_lines.append("<table>")
                in_table = True
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if all(re.match(r'^-+$', c) for c in cells):
                continue
            tag = "th" if not any("</td>" in "".join(html_lines[-5:]) for _ in [1]) else "td"
            html_lines.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif re.match(r'^\d+\.\s+\*\*', stripped):
            if not in_list:
                html_lines.append('<ol class="summary-list">')
                in_list = True
            content = stripped[stripped.index("**") + 2:]
            m = re.match(r'(.+?)\*\*\s*[—–-]\s*(.+)', content + "—")
            bold, rest = (m.group(1), m.group(2)) if m else (content, "")
            rest = re.sub(r'\[s(\d+)\]', r'<sup class="cite">[s\1]</sup>', rest)
            html_lines.append(f'<li><strong>{bold}</strong> {rest}</li>')
        elif stripped.startswith("- **"):
            content = stripped[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\[s(\d+)\]', r'<sup class="cite">[s\1]</sup>', content)
            html_lines.append(f'<li>{content}</li>')
        elif stripped.startswith("- "):
            content = stripped[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\[s(\d+)\]', r'<sup class="cite">[s\1]</sup>', content)
            html_lines.append(f'<li>{content}</li>')
        else:
            content = stripped
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\[s(\d+)\]', r'<sup class="cite">[s\1]</sup>', content)
            html_lines.append(f'<p>{content}</p>')

    for tag, flag in [("</table>", in_table), ("</div>", in_summary_blockquote), ("</ol>", in_list)]:
        if flag:
            html_lines.append(tag)

    body = "\n".join(html_lines)
    return MOBILE_TEMPLATE.format(body=body, accent=accent) if is_mobile else A4_TEMPLATE.format(body=body, accent=accent)


MOBILE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=430">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Inter:wght@400;600;700&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:430px; background:#fffdf8; font-family:'Inter','Noto Serif SC',sans-serif; color:#2d2d2d; padding:24px 20px 40px 20px; font-size:13px; line-height:1.65; }}
h1 {{ font-size:20px; font-weight:700; text-align:center; margin-bottom:20px; color:#1a1a1a; padding-bottom:12px; border-bottom:2px solid {accent}; }}
h2 {{ font-size:16px; font-weight:700; color:{accent}; margin:24px 0 10px 0; padding-bottom:6px; border-bottom:1px solid {accent}; }}
h3 {{ font-size:14px; font-weight:600; color:#3d3d3d; margin:16px 0 6px 0; }}
p {{ margin:6px 0; font-size:13px; }}
strong {{ color:#1a1a1a; font-weight:700; }}
hr {{ border:none; border-top:1px solid #e8dcc8; margin:16px 0; }}
.exec-summary {{ background:#faf5e8; border-left:3px solid {accent}; padding:12px 14px; margin:12px 0 18px 0; border-radius:0 6px 6px 0; }}
.summary-item {{ font-size:13px; line-height:1.6; margin:6px 0; }}
.summary-list {{ padding-left:20px; }}
.summary-list li {{ font-size:13px; line-height:1.6; margin:4px 0; }}
.cite {{ font-size:9px; color:{accent}; vertical-align:super; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0; font-size:11px; }}
th {{ background:#f5eedf; padding:6px 8px; text-align:left; font-weight:700; border-bottom:2px solid {accent}; }}
td {{ padding:4px 8px; border-bottom:1px solid #e8dcc8; }}
</style></head><body>
{body}
</body></html>"""

A4_TEMPLATE = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Inter:wght@400;600;700&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#fff; font-family:Georgia,'Noto Serif SC',serif; color:#1a1a1a; font-size:11pt; line-height:1.7; }}
.content {{ padding:40px 50px; max-width:700px; margin:0 auto; }}
h2 {{ font-size:16pt; font-weight:700; color:#123c55; margin:28px 0 10px 0; padding-bottom:6px; border-bottom:2px solid {accent}; }}
h3 {{ font-size:12pt; font-weight:700; color:#2d2d2d; margin:18px 0 6px 0; }}
p {{ margin:6px 0; font-size:11pt; }}
strong {{ color:#111; font-weight:700; }}
hr {{ border:none; border-top:1px solid #ddd; margin:20px 0; }}
.exec-summary {{ background:#f7f9fb; border-left:4px solid {accent}; padding:14px 18px; margin:14px 0 20px 0; }}
.summary-item {{ font-size:11pt; line-height:1.65; margin:6px 0; }}
.summary-list {{ padding-left:20px; }}
.summary-list li {{ font-size:11pt; line-height:1.65; margin:4px 0; }}
.cite {{ font-size:8pt; color:{accent}; vertical-align:super; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; font-size:9pt; }}
th {{ background:#f0f4f8; padding:6px 10px; text-align:left; font-weight:700; border-bottom:2px solid {accent}; }}
td {{ padding:4px 10px; border-bottom:1px solid #e0e0e0; }}
</style></head><body>
<div class="content">
{body}
</div>
</body></html>"""


def render_pdf(html: str, output_path: str, width: str = None, height: str = None, fmt: str = None):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        if width and height:
            page.set_viewport_size({"width": int(width.replace("px", "")), "height": int(height.replace("px", ""))})
        page.set_content(html, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(1000)

        kwargs = {"path": output_path, "print_background": True}
        if fmt:
            kwargs["format"] = fmt
            kwargs["margin"] = {"top": "0", "right": "0", "bottom": "0", "left": "0"}
        else:
            kwargs["width"] = width
            kwargs["height"] = height
            kwargs["margin"] = {"top": "0", "right": "0", "bottom": "0", "left": "0"}

        page.pdf(**kwargs)
        browser.close()
    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✓ {os.path.basename(output_path)} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 render-dual-pdf.py <path/to/briefing.md>")
        sys.exit(1)

    md_path = sys.argv[1]
    if not os.path.exists(md_path):
        print(f"ERROR: {md_path} not found")
        sys.exit(1)

    out_dir = os.path.dirname(md_path)
    base = os.path.splitext(os.path.basename(md_path))[0]

    with open(md_path, "r", encoding="utf-8") as f:
        markdown = f.read()

    print(f"Rendering {base}...")

    # Mobile
    mobile_html = md_to_html(markdown, is_mobile=True)
    render_pdf(mobile_html, os.path.join(out_dir, f"{base}-mobile.pdf"), width="430px", height="932px")

    # A4
    a4_html = md_to_html(markdown, is_mobile=False)
    render_pdf(a4_html, os.path.join(out_dir, f"{base}-a4.pdf"), fmt="A4")

    print("Done.")
