#!/usr/bin/env python3
"""Convert Obsidian Markdown to PDF using Chrome headless."""

import sys
import re
import subprocess
import base64
import json
import mimetypes
import markdown
from pathlib import Path
from themes import load_theme, list_themes

# All Obsidian callout types
CALLOUT_STYLES = {
    "note": {"emoji": "&#x1F4DD;", "color": "#2c3e50", "bg": "#eaecee"},
    "abstract": {"emoji": "&#x1F4CB;", "color": "#117a65", "bg": "#d1f2eb"},
    "summary": {"emoji": "&#x1F4CB;", "color": "#117a65", "bg": "#d1f2eb"},
    "tldr": {"emoji": "&#x1F4CB;", "color": "#117a65", "bg": "#d1f2eb"},
    "info": {"emoji": "&#x2139;&#xFE0F;", "color": "#2471a3", "bg": "#d6eaf8"},
    "todo": {"emoji": "&#x2611;&#xFE0F;", "color": "#2471a3", "bg": "#d6eaf8"},
    "tip": {"emoji": "&#x1F4A1;", "color": "#1e8449", "bg": "#d5f5e3"},
    "hint": {"emoji": "&#x1F4A1;", "color": "#1e8449", "bg": "#d5f5e3"},
    "important": {"emoji": "&#x1F525;", "color": "#1a5276", "bg": "#d4e6f1"},
    "success": {"emoji": "&#x2705;", "color": "#1e8449", "bg": "#d5f5e3"},
    "check": {"emoji": "&#x2705;", "color": "#1e8449", "bg": "#d5f5e3"},
    "done": {"emoji": "&#x2705;", "color": "#1e8449", "bg": "#d5f5e3"},
    "question": {"emoji": "&#x2753;", "color": "#b7950b", "bg": "#fef9e7"},
    "help": {"emoji": "&#x2753;", "color": "#b7950b", "bg": "#fef9e7"},
    "faq": {"emoji": "&#x2753;", "color": "#b7950b", "bg": "#fef9e7"},
    "warning": {"emoji": "&#x26A0;&#xFE0F;", "color": "#b45309", "bg": "#fef3c7"},
    "caution": {"emoji": "&#x26A0;&#xFE0F;", "color": "#b45309", "bg": "#fef3c7"},
    "attention": {"emoji": "&#x26A0;&#xFE0F;", "color": "#b45309", "bg": "#fef3c7"},
    "failure": {"emoji": "&#x274C;", "color": "#922b21", "bg": "#fadbd8"},
    "fail": {"emoji": "&#x274C;", "color": "#922b21", "bg": "#fadbd8"},
    "missing": {"emoji": "&#x274C;", "color": "#922b21", "bg": "#fadbd8"},
    "danger": {"emoji": "&#x26A1;", "color": "#b91c1c", "bg": "#fee2e2"},
    "error": {"emoji": "&#x26A1;", "color": "#b91c1c", "bg": "#fee2e2"},
    "bug": {"emoji": "&#x1F41B;", "color": "#922b21", "bg": "#fadbd8"},
    "example": {"emoji": "&#x1F4D6;", "color": "#6c3483", "bg": "#f4ecf7"},
    "quote": {"emoji": "&#x1F4AC;", "color": "#6c3483", "bg": "#f4ecf7"},
    "cite": {"emoji": "&#x1F4AC;", "color": "#6c3483", "bg": "#f4ecf7"},
    # Custom callout types
    "decision": {"emoji": "&#x2705;", "color": "#1e8449", "bg": "#d5f5e3"},
    "insight": {"emoji": "&#x1F4A1;", "color": "#9c27b0", "bg": "#f3e5f5"},
    "meta": {"emoji": "&#x2139;&#xFE0F;", "color": "#607d8b", "bg": "#eceff1"},
    "multi-column": {"emoji": "", "color": "#666", "bg": "transparent"},
}

# Friendly display names
CALLOUT_NAMES = {
    "note": "笔记",
    "abstract": "摘要",
    "summary": "摘要",
    "tldr": "TL;DR",
    "info": "信息",
    "todo": "待办",
    "tip": "提示",
    "hint": "提示",
    "important": "重要",
    "success": "完成",
    "check": "完成",
    "done": "完成",
    "question": "问题",
    "help": "帮助",
    "faq": "FAQ",
    "warning": "警告",
    "caution": "注意",
    "attention": "注意",
    "failure": "失败",
    "fail": "失败",
    "missing": "缺失",
    "danger": "危险",
    "error": "错误",
    "bug": "Bug",
    "example": "示例",
    "quote": "引用",
    "cite": "引用",
    "decision": "决策",
    "insight": "洞察",
    "meta": "元信息",
    "multi-column": "多列",
}


def embed_local_images(md_text, md_dir):
    """Convert local image paths to base64 data URIs for reliable Chrome rendering."""

    def _replace_img(m):
        alt = m.group(1)
        src = m.group(2)
        # Skip URLs and data URIs
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        img_path = (md_dir / src).resolve()
        if not img_path.exists():
            return m.group(0)
        mime = mimetypes.guess_type(str(img_path))[0] or "image/png"
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        return f"![{alt}](data:{mime};base64,{b64})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _replace_img, md_text)


MERMAID_LOCAL = Path(__file__).parent / "mermaid.min.js"



def get_mermaid_src():
    """Return mermaid script src — local file if available, else CDN."""
    if MERMAID_LOCAL.exists():
        return f"file://{MERMAID_LOCAL}"
    return "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"


def wrap_sections(html):
    """Wrap content between h2/h3 tags into <section> elements for page-break control.

    Two-level wrapping:
      - h2 → <section class="doc-section"> (primary sections)
      - h3 inside h2 sections → <div class="doc-subsection"> (finer-grained control)
    """
    # --- Level 1: wrap h2 sections ---
    parts = re.split(r"(<h2[^>]*>.*?</h2>)", html)
    if len(parts) <= 1:
        return html

    result = []
    result.append(parts[0])

    i = 1
    while i < len(parts):
        if re.match(r"<h2", parts[i]):
            heading = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ""
            # Level 2: wrap h3 subsections within this h2 section
            content = _wrap_subsections(content)
            result.append(f'<section class="doc-section">{heading}{content}</section>')
            i += 2
        else:
            result.append(parts[i])
            i += 1
    return "".join(result)


def _wrap_subsections(html):
    """Wrap content between h3 tags into <div class="doc-subsection"> for fine-grained break control."""
    parts = re.split(r"(<h3[^>]*>.*?</h3>)", html)
    if len(parts) <= 1:
        return html

    result = []
    result.append(parts[0])

    i = 1
    while i < len(parts):
        if re.match(r"<h3", parts[i]):
            heading = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ""
            result.append(f'<div class="doc-subsection">{heading}{content}</div>')
            i += 2
        else:
            result.append(parts[i])
            i += 1
    return "".join(result)


def preprocess_markdown(md_text):
    md_text = re.sub(r"^---\n.*?\n---\n", "", md_text, flags=re.DOTALL)
    md_text = convert_callouts(md_text)
    md_text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", md_text)
    md_text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", md_text)
    md_text = re.sub(r"==(.*?)==", r"<mark>\1</mark>", md_text)
    # Convert task list checkboxes
    md_text = re.sub(r"^(\s*)- \[x\] ", r"\1- &#x2611; ", md_text, flags=re.MULTILINE)
    md_text = re.sub(r"^(\s*)- \[ \] ", r"\1- &#x2610; ", md_text, flags=re.MULTILINE)
    return md_text


def convert_callouts(md_text):
    # Match all callout types including foldable syntax (- or +)
    callout_types = "|".join(CALLOUT_STYLES.keys())
    pattern = re.compile(rf"^>\s*\[!({callout_types})\]([+-])?\s*(.*)", re.IGNORECASE)

    lines = md_text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = pattern.match(line)
        if m:
            ct = m.group(1).lower()
            fold = m.group(2)  # '-' or '+' or None
            custom_title = m.group(3).strip()
            # For multi-column without custom title: no title
            # For others: use custom title or default name
            if ct == "multi-column" and not custom_title:
                title = ""
            else:
                title = custom_title or CALLOUT_NAMES.get(ct, ct.capitalize())
            s = CALLOUT_STYLES.get(ct, CALLOUT_STYLES["note"])

            content = []
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                content.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            content_md = "\n".join(content)
            # Recursively process nested callouts in content
            content_md = convert_callouts(content_md)
            content_html = markdown.markdown(
                content_md,
                extensions=["tables", "fenced_code", "sane_lists", "md_in_html"],
            )

            # For foldable callouts collapsed by default, use <details>
            if fold == "-":
                result.append("")
                result.append(
                    f'<details open class="callout" style="background:{s["bg"]};border-left:4px solid {s["color"]};padding:4px 12px;margin:10px 0;border-radius:6px;">'
                )
                result.append(
                    f'<summary style="color:{s["color"]};font-weight:700;padding:8px 0;cursor:pointer;list-style:none;">{s["emoji"]} {title}</summary>'
                )
                result.append(f'<div style="padding:4px 0 8px 0;">{content_html}</div>')
                result.append("</details>")
                result.append("")
            else:
                result.append("")
                # Special handling for multi-column without title: container without title bar
                if ct == "multi-column" and not title:
                    result.append(
                        f'<div class="callout callout-multi-column" style="background:#f8f9fa;border:1px dashed #ccc;padding:8px 12px;margin:10px 0;border-radius:6px;">'
                    )
                    result.append(content_html)
                    result.append("</div>")
                else:
                    result.append(
                        f'<div class="callout" style="background:{s["bg"]};border-left:4px solid {s["color"]};padding:8px 12px;margin:10px 0;border-radius:6px;">'
                    )
                    result.append(
                        f'<p class="callout-title" style="color:{s["color"]};font-weight:700;margin:0 0 6px 0;">{s["emoji"]} {title}</p>'
                    )
                    result.append(content_html)
                    result.append("</div>")
                result.append("")
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def extract_outline(md_text):
    """Extract heading structure with content sizes for Claude Code relay."""
    lines = md_text.split("\n")
    headings = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+)", line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))
    if not headings:
        return ""
    outline = []
    for j, (line_no, level, title) in enumerate(headings):
        next_line = headings[j + 1][0] if j + 1 < len(headings) else len(lines)
        chars = sum(len(l) for l in lines[line_no + 1 : next_line] if l.strip())
        indent = "  " * (level - 1)
        outline.append(f"{indent}{'#' * level} {title} ({chars}c)")
    return "\n".join(outline)


def apply_directives(md_text, directives):
    """Apply text-sm/text-xs wrappers based on directives.

    directives: list of (pattern, css_class, mode) tuples.
      mode='heading': wrap children of matching heading section
      mode='after': wrap from matching line to end of document
    """
    if not directives:
        return md_text

    lines = md_text.split("\n")
    headings = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+)", line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2).strip()))

    insertions = []  # (start_line, end_line, css_class)

    for pattern, css_class, mode in directives:
        if mode == "heading":
            for j, (line_no, level, title) in enumerate(headings):
                if pattern.lower() in title.lower():
                    start_line = None
                    for k in range(j + 1, len(headings)):
                        if headings[k][1] > level:
                            start_line = headings[k][0]
                            break
                        if headings[k][1] <= level:
                            break
                    if start_line is None:
                        continue
                    end_line = len(lines)
                    for k in range(j + 1, len(headings)):
                        if headings[k][1] <= level:
                            end_line = headings[k][0]
                            break
                    insertions.append((start_line, end_line, css_class))
                    break
        elif mode == "after":
            for i, line in enumerate(lines):
                if pattern.lower() in line.lower():
                    insertions.append((i, len(lines), css_class))
                    break

    insertions.sort(key=lambda x: x[0], reverse=True)

    for start_line, end_line, css_class in insertions:
        lines.insert(end_line, f"\n</div>\n")
        lines.insert(start_line, f'\n<div class="{css_class}" markdown="1">\n')

    return "\n".join(lines)


def build_html(md_path, header_text, directives=None, theme="blue"):
    md_path = Path(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Print outline for Claude Code relay
    outline = extract_outline(md_text)
    if outline:
        print(f"📋 Outline:\n{outline}")

    md_text = apply_directives(md_text, directives or [])
    md_text = preprocess_markdown(md_text)
    # Embed local images as base64 data URIs
    md_text = embed_local_images(md_text, md_path.parent)
    body = markdown.markdown(
        md_text,
        extensions=[
            "tables", "fenced_code", "toc", "sane_lists", "md_in_html",
            "footnotes",
        ],
    )

    # Convert mermaid code blocks to <div class="mermaid">
    body = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        lambda m: f'<div class="mermaid">{m.group(1)}</div>',
        body,
        flags=re.DOTALL,
    )
    has_mermaid = 'class="mermaid"' in body

    # Wrap h2 sections for smart page breaking
    body = wrap_sections(body)

    # Mermaid JS (only if needed)
    mermaid_script = ""
    if has_mermaid:
        mermaid_src = get_mermaid_src()
        mermaid_script = """
<script src="__MERMAID_SRC__"></script>
<script>
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    themeVariables: {
      fontSize: '12px',
      fontFamily: '-apple-system, "PingFang SC", sans-serif'
    },
    flowchart: {
      htmlLabels: true,
      curve: 'basis',
      nodeSpacing: 25,
      rankSpacing: 35,
      padding: 10,
      useMaxWidth: false
    },
    sequence: {
      mirrorActors: false,
      useMaxWidth: false,
      width: 150,
      height: 40,
      boxMargin: 8,
      noteMargin: 8,
      messageMargin: 30
    },
    stateDiagram: {
      useMaxWidth: false
    }
  });

  window.addEventListener('load', function() {
    mermaid.run().then(function() {
      // Auto-scale: measure each SVG and proportionally fit to page
      var maxW = 580;  // ~A4 content width at 96dpi minus margins
      var maxH = 650;  // ~65% of A4 page height, leave room for text
      var pageBreakH = 750;

      document.querySelectorAll('.mermaid').forEach(function(el) {
        var svg = el.querySelector('svg');
        if (!svg) return;

        // Read rendered size from viewBox or attributes
        var vb = svg.viewBox && svg.viewBox.baseVal;
        var w = (vb && vb.width > 0) ? vb.width
              : parseFloat(svg.getAttribute('width'))
              || svg.getBoundingClientRect().width || 500;
        var h = (vb && vb.height > 0) ? vb.height
              : parseFloat(svg.getAttribute('height'))
              || svg.getBoundingClientRect().height || 300;

        if (w <= 0 || h <= 0) return;

        // Proportional scale to fit within bounds
        var scale = 1;
        if (w > maxW) scale = Math.min(scale, maxW / w);
        if (h > maxH) scale = Math.min(scale, maxH / h);

        var newW = Math.round(w * scale);
        var newH = Math.round(h * scale);

        // Ensure viewBox is set for crisp scaling
        if (!vb || vb.width <= 0) {
          svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
        }
        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.setAttribute('width', newW);
        svg.setAttribute('height', newH);
        svg.style.maxWidth = '100%';

        // Mark very tall diagrams to allow page breaking
        if (newH > pageBreakH) {
          el.classList.add('mermaid-large');
        }
      });
    }).catch(function(e) { console.error('Mermaid:', e); });
  });
</script>""".replace("__MERMAID_SRC__", mermaid_src)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{header_text}</title>
<style>
  * {{ box-sizing: border-box; break-inside: auto; }}

  @page {{
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                 "Hiragino Sans GB", "Noto Sans SC", "Microsoft YaHei",
                 "Source Han Sans CN", "Apple Color Emoji", "Segoe UI Emoji",
                 "Noto Color Emoji", sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: #2c3e50;
    margin: 0;
    padding: 0;
  }}

  /* ===== Headings ===== */
  h1 {{
    font-size: 26px;
    color: #1a3c5e;
    border-bottom: 3px solid #1a3c5e;
    padding-bottom: 10px;
    margin: 0 0 16px 0;
    font-weight: 700;
    letter-spacing: 0.5px;
  }}
  h2 {{
    font-size: 20px;
    color: #1a3c5e;
    border-bottom: 2px solid #b0cfe0;
    padding-bottom: 4px;
    margin: 22px 0 10px 0;
    font-weight: 600;
  }}
  h3 {{
    font-size: 16px;
    color: #24618a;
    margin: 16px 0 8px 0;
    font-weight: 600;
  }}
  h4 {{
    font-size: 14px;
    color: #2980b9;
    margin: 12px 0 6px 0;
    font-weight: 600;
  }}
  /* Heading pagination hints: suggest keeping headings with following content.
     Unlike page-break-before:always, break-after:avoid is advisory —
     Chrome will try to honor it but can ignore when space is tight. */
  h2, h3, h4 {{ break-after: avoid; }}

  /* ===== Text ===== */
  p {{
    margin: 6px 0;
    text-align: justify;
    orphans: 2;
    widows: 2;
  }}
  strong {{ color: #1a3c5e; }}
  em {{ color: #555; }}
  mark {{ background: #fff3b0; padding: 1px 4px; border-radius: 3px; font-weight: 500; }}
  a {{ color: #2874a6; text-decoration: none; }}

  hr {{
    border: none;
    border-top: 2px solid #dce1e4;
    margin: 16px 0;
  }}

  /* ===== Blockquotes ===== */
  blockquote {{
    border-left: 3px solid #7f8c8d;
    padding: 8px 14px;
    margin: 10px 0;
    background: #f8f9fa;
    color: #555;
    font-style: italic;
    font-size: 12.5px;
    border-radius: 0 5px 5px 0;
  }}
  blockquote p {{ margin: 4px 0; }}
  blockquote blockquote {{ border-left-color: #bdc3c7; font-size: 12px; }}

  /* ===== Tables ===== */
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 11.5px;
    line-height: 1.6;
    page-break-inside: auto;
  }}
  th {{
    background: linear-gradient(180deg, #1a3c5e 0%, #24506e 100%);
    color: white;
    font-weight: 600;
    padding: 8px 10px;
    text-align: left;
    border: 1px solid #1a3c5e;
    font-size: 11px;
  }}
  td {{
    padding: 6px 10px;
    border: 1px solid #d5dbdb;
    vertical-align: top;
  }}
  tr:nth-child(even) td {{ background: #f2f4f6; }}
  tr {{ page-break-inside: avoid; }}

  /* ===== Lists ===== */
  ul, ol {{ margin: 8px 0; padding-left: 22px; }}
  li {{ margin: 2px 0; }}
  /* Nested lists: progressively smaller */
  li ul, li ol {{ font-size: 12.5px; margin: 2px 0; }}
  li li ul, li li ol {{ font-size: 12px; }}

  /* ===== Code ===== */
  code {{
    font-family: "SF Mono", "Fira Code", "Menlo", monospace;
    background: #f0f3f5;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 11px;
    color: #c0392b;
  }}
  pre {{
    background: #2c3e50;
    color: #ecf0f1;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 10.5px;
    line-height: 1.5;
    margin: 8px 0;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  pre code {{
    background: transparent;
    color: #ecf0f1;
    padding: 0;
  }}

  /* ===== Sections (h2-level grouping) ===== */
  .doc-section {{
    page-break-inside: auto;
    break-inside: auto;
  }}
  /* ===== Subsections (h3-level grouping) ===== */
  .doc-subsection {{
    page-break-inside: auto;
    break-inside: auto;
  }}

  /* ===== Document metadata (auto-detected) ===== */
  .doc-meta {{
    font-size: 11px;
    color: #7f8c8d;
    margin: -8px 0 20px 0;
    padding: 6px 0;
    border-bottom: 1px solid #eee;
    line-height: 1.5;
  }}

  /* ===== Changelog (auto-detected) ===== */
  .changelog-header {{ font-size: 11px; color: #7f8c8d; }}
  .changelog {{ font-size: 10px; color: #666; line-height: 1.5; }}
  .changelog li {{ font-size: 10px; margin: 2px 0; }}

  /* ===== Claude Code relay classes ===== */
  .text-sm {{ font-size: 12px !important; line-height: 1.7; }}
  .text-sm p, .text-sm li {{ font-size: 12px; }}
  .text-sm table {{ font-size: 10.5px; }}
  .text-xs {{ font-size: 11px !important; line-height: 1.6; }}
  .text-xs p, .text-xs li {{ font-size: 11px; }}
  .text-xs table {{ font-size: 10px; }}

  /* ===== Callouts ===== */
  .callout {{ font-size: 12.5px; }}
  .callout p {{ margin: 4px 0; }}
  .callout table {{ font-size: 10.5px; }}
  .callout li {{ font-size: 12px; }}

  /* ===== Details (foldable callouts) ===== */
  details.callout {{ font-size: 12.5px; }}
  details.callout summary {{ font-size: 13px; }}
  details.callout[open] summary {{ margin-bottom: 4px; }}
  details.callout p {{ margin: 4px 0; }}
  details.callout table {{ font-size: 10.5px; }}
  details.callout li {{ font-size: 12px; }}

  /* ===== Mermaid diagrams ===== */
  .mermaid {{
    text-align: center;
    margin: 10px auto;
    background: #fafbfc;
    padding: 12px;
    border-radius: 6px;
    border: 1px solid #e1e4e8;
  }}
  .mermaid svg {{
    display: block;
    margin: 0 auto;
  }}
  /* Large diagrams: allow page break if JS marks them */
  .mermaid.mermaid-large {{
    page-break-inside: auto;
    break-inside: auto;
  }}

  /* ===== Footnotes (markdown footnotes extension) ===== */
  .footnote {{
    font-size: 10px;
    color: #666;
    line-height: 1.5;
  }}
  .footnote hr {{
    border-top: 1px solid #ccc;
    margin: 24px 0 8px 0;
  }}
  .footnote ol {{
    padding-left: 18px;
    margin: 4px 0;
  }}
  .footnote li {{
    font-size: 10px;
    margin: 2px 0;
  }}
  sup {{ font-size: 0.75em; }}
  a.footnote-ref {{ color: #2874a6; text-decoration: none; font-weight: 600; }}

  /* ===== Syntax highlighting (highlight.js override) ===== */
  pre code.hljs {{
    background: transparent !important;
    color: #ecf0f1 !important;
    padding: 0 !important;
    font-size: inherit;
  }}

  /* ===== Theme overrides ===== */
  {load_theme(theme).css}
</style>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11/build/styles/{load_theme(theme).hljs_theme}.min.css">
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11/build/highlight.min.js"></script>
<script>hljs.highlightAll();</script>
{mermaid_script}
</head>
<body>
{body}
<script>
  // Content-adaptive sizing: tables + section density analysis
  document.addEventListener('DOMContentLoaded', function() {{
    // 1. Adaptive table font sizing
    document.querySelectorAll('table').forEach(function(table) {{
      var row = table.querySelector('tr');
      if (!row) return;
      var cols = row.querySelectorAll('th, td').length;
      if (cols >= 7) {{
        table.style.fontSize = '9px';
        table.style.lineHeight = '1.4';
      }} else if (cols >= 5) {{
        table.style.fontSize = '10px';
        table.style.lineHeight = '1.5';
      }}
    }});

    // 2. Section density analysis — auto-shrink dense sections
    // Dense = 5+ sub-headings with avg content < 500 chars per subsection
    document.querySelectorAll('.doc-section').forEach(function(section) {{
      // Skip sections already styled by CLI directives
      if (section.classList.contains('text-sm') || section.classList.contains('text-xs')) return;
      if (section.closest('.text-sm') || section.closest('.text-xs')) return;

      var subsections = section.querySelectorAll('.doc-subsection');
      if (subsections.length < 5) return;

      var totalChars = 0;
      subsections.forEach(function(sub) {{
        var h3 = sub.querySelector('h3, h4');
        var headingLen = h3 ? h3.textContent.length : 0;
        totalChars += sub.textContent.length - headingLen;
      }});

      var avgChars = totalChars / subsections.length;
      if (avgChars < 500) {{
        section.classList.add('text-sm');
      }}
    }});
  }});
</script>
</body>
</html>"""


def _localize_mermaid_src(html):
    """Replace CDN mermaid script with local copy for file:// access."""
    local_mermaid = Path("/tmp/mermaid.min.js")
    if not local_mermaid.exists():
        try:
            import urllib.request
            url = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
            print(f"  📥 Downloading mermaid.min.js ...")
            urllib.request.urlretrieve(url, str(local_mermaid))
        except Exception:
            return html  # keep CDN version

    html = re.sub(
        r'<script src="https://cdn\.jsdelivr\.net/npm/mermaid[^"]*"',
        f'<script src="file://{local_mermaid}"',
        html,
    )
    return html


def _render_playwright(html_path, pdf_path):
    """Render PDF using Playwright. Reliable for all documents including large Mermaid."""
    has_mermaid = 'class="mermaid"' in html_path.read_text(encoding="utf-8")
    wait_timeout = 60000 if has_mermaid else 10000

    script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://{html_path}', {{ waitUntil: 'networkidle', timeout: 120000 }});
  // Wait for Mermaid SVG rendering
  await page.waitForFunction(() => {{
    const m = document.querySelectorAll('.mermaid');
    return m.length === 0 || Array.from(m).every(el => el.querySelector('svg') !== null);
  }}, {{ timeout: {wait_timeout} }}).catch(() => console.error('Mermaid wait timeout, proceeding'));
  await page.waitForTimeout(2000);
  await page.pdf({{
    path: '{pdf_path}',
    format: 'A4',
    printBackground: true,
    margin: {{ top: '15mm', bottom: '15mm', left: '15mm', right: '15mm' }},
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: '<div style="font-size:9px;color:#888;width:100%;text-align:center;padding-bottom:2mm;">\\u2014 <span class="pageNumber"></span> / <span class="totalPages"></span> \\u2014</div>',
  }});
  await browser.close();
  console.log('OK');
}})();
"""
    script_path = Path("/tmp") / "pw_render.js"
    script_path.write_text(script, encoding="utf-8")

    import os
    env = dict(os.environ)
    node_paths = [Path.home() / "node_modules", Path("/usr/local/lib/node_modules")]
    extra = ":".join(str(p) for p in node_paths if p.exists())
    if extra:
        env["NODE_PATH"] = extra

    result = subprocess.run(
        ["node", str(script_path)],
        capture_output=True, text=True, timeout=180, env=env,
    )

    if not pdf_path.exists() or pdf_path.stat().st_size < 1024:
        print(f"  Playwright stderr: {result.stderr}", file=sys.stderr)
        raise RuntimeError("Playwright PDF generation failed")


def md_to_pdf(md_path, pdf_path=None, header_text=None, directives=None, theme="blue"):
    md_path = Path(md_path)
    pdf_path = Path(pdf_path) if pdf_path else md_path.with_suffix(".pdf")
    header_text = header_text or md_path.stem

    html = build_html(md_path, header_text, directives, theme=theme)

    # Localize Mermaid JS for file:// rendering
    if 'class="mermaid"' in html:
        html = _localize_mermaid_src(html)

    html_path = Path("/tmp") / f"{md_path.stem}.html"
    html_path.write_text(html, encoding="utf-8")

    _render_playwright(html_path, pdf_path)

    # Remove blank/near-empty pages
    removed = remove_blank_pages(pdf_path)
    if removed:
        print(f"  🧹 Removed {removed} blank page(s)")

    # Add PDF bookmarks from heading hierarchy
    add_pdf_bookmarks(pdf_path, md_path)

    size_kb = pdf_path.stat().st_size / 1024
    print(f"\u2705 {pdf_path.name} ({size_kb:.0f} KB)")


def remove_blank_pages(pdf_path):
    """Remove blank and near-empty pages from the PDF.

    Removes pages that are completely empty or have < 50 chars of text
    (trailing artifact pages). Returns the number of pages removed.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return 0

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    if total <= 1:
        return 0

    # Identify pages to keep
    keep = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        is_last = i == total - 1
        # Remove if: completely empty, OR last page with < 50 chars
        if len(text) == 0 or (is_last and len(text) < 50):
            continue
        keep.append(i)

    removed = total - len(keep)
    if removed == 0:
        return 0

    writer = PdfWriter()
    for i in keep:
        writer.add_page(reader.pages[i])

    tmp_path = pdf_path.with_suffix(".tmp.pdf")
    with open(tmp_path, "wb") as f:
        writer.write(f)
    tmp_path.replace(pdf_path)
    return removed


def add_pdf_bookmarks(pdf_path, md_path):
    """Add PDF outline bookmarks based on Markdown heading hierarchy using pypdf."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return  # silently skip if pypdf not available

    # Extract headings from markdown
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    headings = []
    for line in md_text.split("\n"):
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # Clean markdown formatting from title
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)
            title = re.sub(r"\*(.+?)\*", r"\1", title)
            title = re.sub(r"`(.+?)`", r"\1", title)
            headings.append((level, title))

    if not headings:
        return

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    # Build page text index for heading-to-page mapping
    page_texts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        # Normalize whitespace for matching
        page_texts.append(re.sub(r"\s+", " ", text))

    def find_page(title):
        """Find which page a heading appears on by text search."""
        # Normalize the search title
        search = re.sub(r"\s+", " ", title).strip()
        for i, text in enumerate(page_texts):
            if search in text:
                return i
        # Fuzzy: try first 20 chars
        short = search[:20]
        if len(short) > 5:
            for i, text in enumerate(page_texts):
                if short in text:
                    return i
        return 0  # fallback to first page

    # Add bookmarks with hierarchy
    # Track parent bookmarks for nesting
    parent_stack = []  # [(level, bookmark_ref)]

    for level, title in headings:
        page_num = find_page(title)

        # Find the right parent for this heading level
        while parent_stack and parent_stack[-1][0] >= level:
            parent_stack.pop()

        parent = parent_stack[-1][1] if parent_stack else None
        bookmark = writer.add_outline_item(title, page_num, parent=parent)
        parent_stack.append((level, bookmark))

    # Write back
    tmp_path = pdf_path.with_suffix(".tmp.pdf")
    with open(tmp_path, "wb") as f:
        writer.write(f)

    # Atomic replace
    tmp_path.replace(pdf_path)
    print(f"  \U0001F516 {len(headings)} bookmarks added")


if __name__ == "__main__":
    # Parse directives from args
    directives = []
    positional = []
    theme = "blue"
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--sm", "--xs", "--sm-after", "--xs-after") and i + 1 < len(
            sys.argv
        ):
            css = "text-sm" if "sm" in arg else "text-xs"
            mode = "after" if arg.endswith("-after") else "heading"
            directives.append((sys.argv[i + 1], css, mode))
            i += 2
        elif arg == "--theme" and i + 1 < len(sys.argv):
            theme = sys.argv[i + 1]
            if theme not in list_themes():
                print(f"Unknown theme '{theme}'. Available: {', '.join(list_themes())}")
                sys.exit(1)
            i += 2
        else:
            positional.append(sys.argv[i])
            i += 1

    if not positional:
        print(
            "Usage: python md2pdf_chrome.py <md_file> [pdf_file] [header_text] [--theme blue|dark|academic] [--sm PATTERN] [--xs PATTERN] [--sm-after PATTERN] [--xs-after PATTERN]"
        )
        sys.exit(1)
    md_to_pdf(
        positional[0],
        positional[1] if len(positional) > 1 else None,
        positional[2] if len(positional) > 2 else None,
        directives or None,
        theme=theme,
    )
