#!/usr/bin/env python3
"""Convert Obsidian Markdown to PDF using Chrome headless."""

import sys
import re
import os
import glob
import shutil
import tempfile
import base64
import json
import importlib.util
import mimetypes
import subprocess
from pathlib import Path

try:
    import markdown
except ImportError:  # 允许在缺依赖的解释器上仍能跑 --preflight 给出友好提示
    markdown = None

from themes import load_theme, list_themes

# 支持的输出格式
VALID_FORMATS = ("pdf", "png", "html", "wechat")

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


# M1.1 fence-first：文本级转换（==高亮==/wikilink/任务清单/图片内嵌）会污染代码
# 内容——mermaid 粗箭头 `T1 ==> T2` 曾被高亮正则剥成 `T1 > T2`（2026-07-02 事故）。
# 因此先把 fenced code block 与行内代码抽成占位符，全部转换完成后再回填。
_FENCE_RE = re.compile(r"^(?P<f>`{3,}|~{3,})[^\n]*\n(?:.*?\n)?(?P=f)[ \t]*$", re.M | re.S)
_INLINE_CODE_RE = re.compile(r"(?<!`)(`+)([^`\n]+?)\1(?!`)")


def protect_code_spans(md_text):
    """抽取代码围栏与行内代码为占位符，返回 (text, store)。"""
    store = []

    def _stash(m):
        store.append(m.group(0))
        return f"\x02JZCODE{len(store) - 1}\x03"

    md_text = _FENCE_RE.sub(_stash, md_text)
    md_text = _INLINE_CODE_RE.sub(_stash, md_text)
    return md_text, store


def restore_code_spans(md_text, store):
    for i, block in enumerate(store):
        md_text = md_text.replace(f"\x02JZCODE{i}\x03", block)
    return md_text


# ===== M2 环境自愈：持久 venv + vendor 资源 pin（跨平台，/tmp 不可依赖） =====
SCRIPTS_DIR = Path(__file__).resolve().parent
VENV_DIR = Path.home() / ".venvs" / "pdf-skill"   # 四端 CLI 软链共享同一 canonical，读同一路径
MERMAID_PIN = "11.16.0"   # pin 精确版本：消除 CDN @11 浮动与 /tmp 缓存漂移（2026-07-02 定案）
HLJS_PIN = "11.9.0"
MERMAID_LOCAL = SCRIPTS_DIR / "mermaid.min.js"
HLJS_LOCAL = SCRIPTS_DIR / "highlight.min.js"
HLJS_STYLES_DIR = SCRIPTS_DIR / "hljs-styles"
VENDOR_LOCK = SCRIPTS_DIR / "vendor.lock.json"
MERMAID_CDN = f"https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_PIN}/dist/mermaid.min.js"
HLJS_CDN = f"https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@{HLJS_PIN}/build/highlight.min.js"


def _venv_python():
    """持久 venv 的解释器路径（win 为 Scripts\\python.exe）。"""
    sub = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    return VENV_DIR / sub


def get_mermaid_src():
    """Return mermaid script src — local pinned copy if available, else pinned CDN."""
    if MERMAID_LOCAL.exists():
        return f"file://{MERMAID_LOCAL}"
    return MERMAID_CDN


def _hljs_js_src():
    """highlight.js 脚本地址：本地 pin 副本优先（--setup 下载），否则 pinned CDN。"""
    if HLJS_LOCAL.exists():
        return f"file://{HLJS_LOCAL}"
    return HLJS_CDN


def _hljs_css_src(theme):
    """hljs 样式表地址：本地副本优先，否则 pinned CDN。"""
    from themes import load_theme as _lt
    name = _lt(theme).hljs_theme
    local = HLJS_STYLES_DIR / f"{name}.min.css"
    if local.exists():
        return f"file://{local}"
    return f"https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@{HLJS_PIN}/build/styles/{name}.min.css"


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
    """文本级转换。调用方须已用 protect_code_spans 保护代码内容（M1.1）。"""
    md_text = re.sub(r"^---\n.*?\n---\n", "", md_text, flags=re.DOTALL)
    md_text = convert_callouts(md_text)
    md_text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", md_text)
    md_text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", md_text)
    md_text = re.sub(r"==(.*?)==", r"<mark>\1</mark>", md_text)
    # Convert task list checkboxes
    md_text = re.sub(r"^(\s*)- \[x\] ", r"\1- &#x2611; ", md_text, flags=re.MULTILINE)
    md_text = re.sub(r"^(\s*)- \[ \] ", r"\1- &#x2610; ", md_text, flags=re.MULTILINE)
    # M1.5 嵌套列表缩进归一：python-markdown 需 4 空格才识别嵌套，
    # Obsidian 常见 2-3 空格缩进会被压扁成一行。
    md_text = _normalize_list_indent(md_text)
    return md_text


def _normalize_list_indent(md_text):
    """把「真嵌套」的 2-3 空格列表缩进提升为 4 空格（上下文感知）。

    仅当前一非空行处于列表上下文时才升格——文首/段后的孤立 2-3 空格列表项
    保持原样（升到 4 空格会被 markdown 误判为缩进代码块）。空行不打断列表上下文。
    """
    out = []
    in_list = False
    for ln in md_text.split("\n"):
        m = re.match(r"^( {2,3})([-*+] |\d+[.)] )", ln)
        if m and in_list:
            ln = "    " + ln[len(m.group(1)):]
        if re.match(r"^\s*([-*+] |\d+[.)] )", ln):
            in_list = True
        elif ln.strip():
            in_list = False
        out.append(ln)
    return "\n".join(out)


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


def _page_margin(page_size):
    """Return CSS @page margin. Tighter margins for mobile (430px page)."""
    if page_size == "A4":
        return "20mm 18mm 20mm 18mm"
    return "12mm 10mm 12mm 10mm"


def build_html(md_path, header_text, directives=None, theme="blue", page_size="A4"):
    md_path = Path(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Print outline for Claude Code relay
    outline = extract_outline(md_text)
    if outline:
        print(f"📋 Outline:\n{outline}")

    md_text = apply_directives(md_text, directives or [])
    # M1.1 fence-first：保护代码围栏/行内代码 → 文本转换 → 回填
    md_text, _code_store = protect_code_spans(md_text)
    md_text = preprocess_markdown(md_text)
    # Embed local images as base64 data URIs
    md_text = embed_local_images(md_text, md_path.parent)
    md_text = restore_code_spans(md_text, _code_store)
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
      fontFamily: '-apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif'
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

  // M1.2/M1.3 逐块 parse 预检 + render + 错误收集。渲染状态挂 window.__mermaidStatus，
  // Python 侧据此 fail-fast（有错默认不产出 PDF），而非把错误炸弹印进成品。
  window.__mermaidStatus = { total: 0, rendered: 0, errors: [], finished: false };
  window.addEventListener('load', async function() {
    var st = window.__mermaidStatus;
    var blocks = Array.from(document.querySelectorAll('.mermaid'));
    st.total = blocks.length;
    for (var i = 0; i < blocks.length; i++) {
      var el = blocks[i];
      var src = el.textContent;
      try {
        await mermaid.parse(src);  // M1.3 渲染前 parse 预检，定位到块号
        var out = await mermaid.render('jzmm' + i, src);
        el.innerHTML = out.svg;
        st.rendered++;
      } catch (e) {
        st.errors.push({
          index: i + 1,
          message: String((e && e.message) || e).slice(0, 400),
          head: src.trim().split('\\n').slice(0, 2).join(' | ').slice(0, 120)
        });
        el.setAttribute('data-mermaid-failed', '1');
      }
    }

    // Auto-scale: measure each SVG and proportionally fit to page
    var maxW = 580;  // ~A4 content width at 96dpi minus margins
    var maxH = 650;  // ~65% of A4 page height, leave room for text
    var pageBreakH = 750;

    blocks.forEach(function(el) {
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
    st.finished = true;
  });
</script>""".replace("__MERMAID_SRC__", mermaid_src)

    # Convert page_size to CSS @page size value
    if page_size == "A4":
        size_val = "A4"
    else:
        # e.g. "430x932" → "430px 932px"
        w, h = page_size.split("x")
        size_val = f"{w}px {h}px"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{header_text}</title>
<style>
  * {{ box-sizing: border-box; break-inside: auto; }}

  @page {{
    size: {size_val};
    margin: {_page_margin(page_size)};
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
    font-family: "SF Mono", "Fira Code", "Menlo", "Cascadia Code", "Consolas", monospace;
    background: #f0f3f5;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 11px;
    color: #c0392b;
  }}
  /* M1.5 行内代码禁断行：`T1 --> T2` 曾被从箭头中间折断（pre 内不受影响） */
  :not(pre) > code {{ white-space: nowrap; }}
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
<link rel="stylesheet" href="{_hljs_css_src(theme)}">
<script src="{_hljs_js_src()}"></script>
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
    """Replace CDN mermaid script with local pinned copy for file:// access.

    本地副本存 scripts/ 旁（持久、跨平台），不再用 /tmp（重启即失、Windows 无此路径）。
    """
    if not MERMAID_LOCAL.exists():
        try:
            import urllib.request
            print(f"  📥 Downloading mermaid.min.js {MERMAID_PIN} ...")
            urllib.request.urlretrieve(MERMAID_CDN, str(MERMAID_LOCAL))
            _record_vendor("mermaid", MERMAID_PIN, MERMAID_LOCAL)
        except Exception:
            return html  # keep CDN version

    html = re.sub(
        r'<script src="https://cdn\.jsdelivr\.net/npm/mermaid[^"]*"',
        f'<script src="file://{MERMAID_LOCAL}"',
        html,
    )
    return html


def _record_vendor(name, version, path):
    """vendor.lock.json 记录 pin 版本与 sha256（升级须显式重跑 --setup）。"""
    import hashlib
    try:
        lock = json.loads(VENDOR_LOCK.read_text()) if VENDOR_LOCK.exists() else {}
        lock[name] = {
            "version": version,
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "file": Path(path).name,
        }
        VENDOR_LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False))
    except Exception:
        pass


# ===== 浏览器选择 / 健康检查 helper（803/1094 共用，杜绝再改源码切浏览器） =====


class MermaidRenderError(RuntimeError):
    """M1.2 Mermaid 图渲染失败＝内容错误：不降级引擎、不转 pandoc、不产出成品，
    直接终止并报块号+错误信息（质量为先：宁可不出，不出错的）。"""


class _NeedPandoc(Exception):
    """信号：playwright 与系统 chrome 均不可用，PDF 场景应转 pandoc 救生艇。"""


def _node_env():
    """803/1094 重复的 NODE_PATH 拼装，去重。"""
    env = dict(os.environ)
    extra = ":".join(
        str(p) for p in [Path.home() / "node_modules", Path("/usr/local/lib/node_modules")]
        if p.exists()
    )
    if extra:
        env["NODE_PATH"] = extra
    return env


def _find_system_chrome():
    """跨平台探测系统 Chrome/Chromium 可执行文件，找不到返回 None（M2.4 X2）。"""
    candidates = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Linux
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    ]
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            if base:
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    for c in candidates:
        if c and os.path.exists(c):
            return c
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    return None


def _bundled_launchable():
    """比 require 更接近能否 launch：能拿到存在的 executablePath 才算 OK。"""
    cache_globs = [
        str(Path.home() / "Library/Caches/ms-playwright/chromium-*"),   # macOS
        str(Path.home() / ".cache/ms-playwright/chromium-*"),           # Linux
    ]
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):     # Windows (M2.4 X3)
        cache_globs.append(os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright", "chromium-*"))
    if not any(glob.glob(g) for g in cache_globs):
        return False
    try:
        r = subprocess.run(
            ["node", "-e",
             "const p=require('playwright').chromium.executablePath();"
             "require('fs').accessSync(p);process.stdout.write(p)"],
            capture_output=True, text=True, env=_node_env(), timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def _launch_plan(browser):
    """返回按序尝试的 [(launch_expr, engine, exe)]。launch_expr 是注入 node 的 chromium.launch(...) 表达式。

    - playwright：强制 bundled（不前置探测，运行失败由调用方决定）
    - chrome：    系统 chrome，缺失即 raise
    - auto：      bundled(可探测) → 系统 chrome(存在)，逐个运行尝试；都没有抛 _NeedPandoc
    """
    bundled = ("chromium.launch()", "playwright-chromium", "bundled")
    if browser == "playwright":
        return [bundled]
    if browser == "chrome":
        exe = _find_system_chrome()
        if not exe:
            raise RuntimeError("--browser chrome 但未找到系统 Chrome；先跑 --preflight 检查")
        return [(f"chromium.launch({{ executablePath: {json.dumps(exe)} }})", "system-chrome", exe)]
    if browser == "auto":
        plan = []
        if _bundled_launchable():
            plan.append(bundled)
        exe = _find_system_chrome()
        if exe:
            plan.append((f"chromium.launch({{ executablePath: {json.dumps(exe)} }})", "system-chrome", exe))
        if not plan:
            raise _NeedPandoc("bundled chromium 与系统 chrome 均不可用")
        return plan
    raise ValueError(f"Unknown browser '{browser}'")


def _mermaid_wait_and_check_js(wait_timeout, allow_diagram_errors):
    """生成等待 Mermaid 渲染完成 + fail-fast 检查的 JS 片段（pdf/png/html 路径共用）。

    __mermaidStatus.finished 由页面内渲染循环置位；有错误且未显式放行时
    以 exit code 3 终止（内容错误信号，Python 侧不降级引擎、不转 pandoc）。
    """
    allow = "true" if allow_diagram_errors else "false"
    return f"""
  await page.waitForFunction(() => {{
    const st = window.__mermaidStatus;
    return document.querySelectorAll('.mermaid').length === 0 || (st && st.finished);
  }}, {{ timeout: {wait_timeout} }}).catch(() => console.error('Mermaid wait timeout, proceeding'));
  const mmSt = await page.evaluate(() => window.__mermaidStatus || null);
  if (mmSt) console.log('MERMAID_STAT:' + JSON.stringify({{ total: mmSt.total, rendered: mmSt.rendered }}));
  if (mmSt && mmSt.errors.length > 0) {{
    console.error('MERMAID_ERRORS:' + JSON.stringify(mmSt.errors));
    if (!{allow}) {{ await browser.close(); process.exit(3); }}
  }}
  await page.waitForTimeout(2000);"""


def _parse_mermaid_stat(stdout):
    """从渲染脚本 stdout 提取 MERMAID_STAT，无则返回 None。"""
    m = re.search(r"MERMAID_STAT:(\{.*?\})", stdout or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def _format_mermaid_errors(stderr):
    m = re.search(r"MERMAID_ERRORS:(\[.*\])", stderr or "")
    if not m:
        return "Mermaid 渲染失败（详情缺失）"
    try:
        errs = json.loads(m.group(1))
    except Exception:
        return f"Mermaid 渲染失败: {m.group(1)[:400]}"
    lines = [f"Mermaid {len(errs)} 个图渲染失败（已按质量门终止，未产出成品）："]
    for e in errs:
        lines.append(f"  图#{e.get('index')}: {e.get('message')}")
        if e.get("head"):
            lines.append(f"    源块首行: {e['head']}")
    lines.append("  修正 md 中对应 mermaid 块后重试；或用 --allow-diagram-errors 显式降级放行。")
    return "\n".join(lines)


def _render_playwright(html_path, pdf_path, page_size="A4", browser="playwright",
                       allow_diagram_errors=False):
    """Render PDF via Playwright/Chrome. browser ∈ {playwright,chrome,auto}。

    auto 逐个尝试 plan 中的引擎：即使前置探测通过、运行时崩溃（如 6-13 的 launch 崩）
    也会继续降级系统 chrome；全部失败抛 _NeedPandoc，交上层转 pandoc。
    Mermaid 内容错误（exit 3）例外：抛 MermaidRenderError，绝不降级/兜底。
    返回 mermaid 渲染统计 dict 或 None（供图数对账写入 metadata）。
    """
    has_mermaid = 'class="mermaid"' in html_path.read_text(encoding="utf-8")
    wait_timeout = 60000 if has_mermaid else 10000

    # Convert page_size to Playwright format. Playwright's page.pdf() accepts
    # 'format: "A4"' (predefined) or 'width: "...px", height: "...px"' (custom).
    if page_size == "A4":
        pw_format = "format: 'A4'"
    else:
        w, h = page_size.split("x")
        pw_format = f"width: '{w}px', height: '{h}px'"

    pdf_margin = "top: '8mm', bottom: '8mm', left: '8mm', right: '8mm'" if page_size != "A4" else "top: '15mm', bottom: '15mm', left: '15mm', right: '15mm'"

    plan = _launch_plan(browser)
    last_err = ""
    for idx, (launch_expr, engine, exe) in enumerate(plan):
        print(f"  \U0001F5A5  engine={engine} executable={exe}", file=sys.stderr)
        script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await {launch_expr};
  const page = await browser.newPage();
  await page.goto('file://{html_path}', {{ waitUntil: 'networkidle', timeout: 120000 }});
{_mermaid_wait_and_check_js(wait_timeout, allow_diagram_errors)}
  await page.pdf({{
    path: '{pdf_path}',
    {pw_format},
    printBackground: true,
    margin: {{ {pdf_margin} }},
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: '<div style="font-size:9px;color:#888;width:100%;text-align:center;padding-bottom:2mm;">\\u2014 <span class="pageNumber"></span> / <span class="totalPages"></span> \\u2014</div>',
    outline: true,
    tagged: true,
  }});
  await browser.close();
  console.log('OK');
}})();
"""
        script_path = Path(tempfile.gettempdir()) / "pw_render.js"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True, text=True, timeout=180, env=_node_env(),
        )
        # M1.2 exit 3 = Mermaid 内容错误：立即终止，不降级引擎、不转 pandoc
        if result.returncode == 3:
            raise MermaidRenderError(_format_mermaid_errors(result.stderr))
        if pdf_path.exists() and pdf_path.stat().st_size >= 1024:
            return _parse_mermaid_stat(result.stdout)
        last_err = result.stderr
        if idx < len(plan) - 1:
            print(f"  ⚠️  {engine} 渲染失败，降级下一引擎", file=sys.stderr)

    print(f"  Playwright/Chrome stderr: {last_err}", file=sys.stderr)
    if browser == "auto":
        raise _NeedPandoc("playwright 与系统 chrome 渲染均失败")
    raise RuntimeError("Playwright PDF generation failed")


def md_to_pdf(md_path, pdf_path=None, header_text=None, directives=None,
              theme="blue", page_size="A4", browser="playwright",
              fallback=None, write_metadata=True, allow_diagram_errors=False):
    md_path = Path(md_path)
    pdf_path = Path(pdf_path) if pdf_path else md_path.with_suffix(".pdf")
    header_text = header_text or md_path.stem

    html = build_html(md_path, header_text, directives, theme=theme, page_size=page_size)

    # Localize Mermaid JS for file:// rendering
    if 'class="mermaid"' in html:
        html = _localize_mermaid_src(html)

    html_path = Path(tempfile.gettempdir()) / f"{md_path.stem}.html"
    html_path.write_text(html, encoding="utf-8")

    diagram_stat = None
    if fallback == "pandoc":
        _render_pandoc_fallback(md_path, pdf_path, theme=theme, page_size=page_size)
    else:
        try:
            diagram_stat = _render_playwright(
                html_path, pdf_path, page_size=page_size, browser=browser,
                allow_diagram_errors=allow_diagram_errors)
        except _NeedPandoc as e:
            print(f"  ⚠️  {e} → 转 pandoc 救生艇", file=sys.stderr)
            _render_pandoc_fallback(md_path, pdf_path, theme=theme, page_size=page_size)

    # Remove blank/near-empty pages
    removed = remove_blank_pages(pdf_path)
    if removed:
        print(f"  🧹 Removed {removed} blank page(s)")

    # Add PDF bookmarks from heading hierarchy
    add_pdf_bookmarks(pdf_path, md_path)

    # 源笔记 frontmatter → PDF metadata（独立一步，无标题文档也写）
    # M1.4 附带写入 mermaid 图数统计，供 verify_pdf 做「源图数↔成功渲染数」对账
    if write_metadata:
        extra = None
        if diagram_stat:
            extra = {
                "/JZDiagramTotal": str(diagram_stat.get("total", "")),
                "/JZDiagramRendered": str(diagram_stat.get("rendered", "")),
            }
        add_pdf_metadata(pdf_path, md_path, extra=extra)

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

    # Identify pages to drop
    drop = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        is_last = i == total - 1
        # Remove if: completely empty, OR last page with < 50 chars
        if len(text) == 0 or (is_last and len(text) < 50):
            drop.append(i)

    if not drop:
        return 0

    # clone_from 保留原生 outline/StructTreeRoot（tagged PDF），逐页 remove_page；
    # 空白页无标题，不会有书签目标悬空
    writer = PdfWriter(clone_from=str(pdf_path))
    for i in reversed(drop):
        writer.remove_page(i)

    tmp_path = pdf_path.with_suffix(".tmp.pdf")
    with open(tmp_path, "wb") as f:
        writer.write(f)
    tmp_path.replace(pdf_path)
    return len(drop)


def add_pdf_bookmarks(pdf_path, md_path):
    """Add PDF outline bookmarks based on Markdown heading hierarchy using pypdf.

    Chromium 原生 `outline: true` 已在渲染时直出书签（含正确目标页）；
    检测到原生 outline 即跳过，避免 pypdf 重写剥掉 tagged 结构。
    本函数保留为 pandoc 救生艇等无原生书签产物的兜底。
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return  # silently skip if pypdf not available

    try:
        if PdfReader(str(pdf_path)).outline:
            print("  \U0001F516 native outline present (Chromium), skip pypdf bookmarks")
            return
    except Exception:
        pass

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


# ===== Frontmatter → PDF metadata =====


def _parse_frontmatter(md_path):
    """读原始 md（preprocess strip 之前）提取 YAML frontmatter dict；无则 {}。"""
    try:
        text = Path(md_path).read_text(encoding="utf-8")
    except Exception:
        return {}
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not m:
        return {}
    try:
        import yaml
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _to_pdf_date(val):
    """'YYYY-MM-DD[ HH:MM]' → PDF 'D:YYYYMMDDHHmmSS'；失败返回 None。"""
    if not val:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?", str(val))
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2), m.group(3)
    hh, mm = m.group(4) or "00", m.group(5) or "00"
    return f"D:{y}{mo}{d}{hh}{mm}00"


def add_pdf_metadata(pdf_path, md_path, extra=None):
    """源笔记 frontmatter → PDF metadata。独立一步，无标题文档也写。

    /Author 仅在 frontmatter 显式声明时写（避免把 vault 私有信息/邮箱泄露到外发 PDF）。
    extra: 附加自定义键（如 /JZDiagramTotal 图数对账）。pypdf 缺失则静默跳过。
    """
    try:
        from pypdf import PdfWriter
    except ImportError:
        return
    fm = _parse_frontmatter(md_path)
    pdf_path = Path(pdf_path)
    al = fm.get("aliases") or []
    al = [al] if isinstance(al, str) else list(al)
    tags = fm.get("tags") or []
    tags = [tags] if isinstance(tags, str) else list(tags)
    meta = {
        "/Title": str(fm.get("title") or (al[0] if al else Path(md_path).stem)),
        "/Subject": str(fm.get("description") or fm.get("type") or ""),
        "/Keywords": "; ".join(str(x) for x in (tags + al)),
    }
    if fm.get("author"):
        meta["/Author"] = str(fm["author"])
    cd = _to_pdf_date(fm.get("created"))
    md_mod = _to_pdf_date(fm.get("modified"))
    if cd:
        meta["/CreationDate"] = cd
    if md_mod:
        meta["/ModDate"] = md_mod
    if extra:
        meta.update(extra)
    meta = {k: v for k, v in meta.items() if v}
    if not meta:
        return
    try:
        # clone_from（而非 reader+append）保留原生 outline 与 tagged 结构
        writer = PdfWriter(clone_from=str(pdf_path))
        writer.add_metadata(meta)
        tmp = pdf_path.with_suffix(".meta.pdf")
        with open(tmp, "wb") as f:
            writer.write(f)
        tmp.replace(pdf_path)
        print(f"  \U0001F3F7  PDF metadata: {', '.join(k[1:] for k in meta)}")
    except Exception as e:
        print(f"  ⚠️  metadata 写入跳过: {e}", file=sys.stderr)


# ===== pandoc 救生艇（第三路 fallback） =====


def _render_pandoc_fallback(md_path, pdf_path, theme="blue", page_size="A4"):
    """pandoc → standalone HTML（注入主题 CSS）→ 系统 chrome --print-to-pdf。

    丢弃自研管线（callout/section/自适应字号/Mermaid），仅 A4，绝不静默（调用处已告警）。
    """
    md_path = Path(md_path)
    pdf_path = Path(pdf_path)
    chrome = _find_system_chrome()
    pandoc = shutil.which("pandoc")
    print("  ⚠️  pandoc 救生艇：样式不保真，Mermaid 不渲染", file=sys.stderr)
    if not chrome:
        raise RuntimeError("pandoc fallback 需系统 Chrome 做 print-to-pdf（未找到）")
    if not pandoc:
        raise RuntimeError("pandoc fallback 需 pandoc（brew install pandoc）")
    if page_size != "A4":
        print("  ⚠️  救生艇仅 A4，忽略自定义 page-size", file=sys.stderr)
    tmp = Path(tempfile.mkdtemp(prefix="md2pdf_fb_"))
    try:
        css = tmp / "theme.css"
        try:
            css.write_text(load_theme(theme).css, encoding="utf-8")
        except Exception:
            css.write_text("", encoding="utf-8")
        html = tmp / (md_path.stem + ".html")
        subprocess.run(
            [pandoc, str(md_path), "-f", "gfm+footnotes", "-t", "html5",
             "--standalone", "--embed-resources", "--highlight-style=tango",
             "--css", str(css), "-o", str(html)],
            check=True, timeout=120,
        )
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--user-data-dir={tmp}/profile", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_path}", f"file://{html}"],
            check=True, timeout=180, capture_output=True,
        )
        if not pdf_path.exists() or pdf_path.stat().st_size < 1024:
            raise RuntimeError("pandoc fallback 产物为空")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===== preflight 健康检查 =====


# ===== M2 环境自愈：引导 / 自动 re-exec / --setup =====


def _pandoc_install_hint():
    """按平台给 pandoc 安装提示（M2.4 X6）。"""
    if sys.platform == "win32":
        return "winget install pandoc"
    if sys.platform == "darwin":
        return "brew install pandoc"
    return "apt install pandoc"


def _bootstrap_venv():
    """建持久 venv 并装依赖（幂等）。成功返回 venv python 路径，失败返回 None。"""
    vp = _venv_python()
    if not vp.exists():
        print(f"  🔧 创建持久 venv: {VENV_DIR}（首次较慢，一次性）", file=sys.stderr)
        try:
            import venv as _venvmod
            VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
            _venvmod.EnvBuilder(with_pip=True).create(str(VENV_DIR))
        except Exception as e:
            print(f"  ❌ venv 创建失败: {e}", file=sys.stderr)
            return None
    r = subprocess.run([str(vp), "-m", "pip", "install", "-q", "markdown", "pypdf"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ 依赖安装失败: {r.stderr[-400:]}", file=sys.stderr)
        return None
    # css_inline 仅 --format wechat 需要，装失败不阻塞
    subprocess.run([str(vp), "-m", "pip", "install", "-q", "css_inline"],
                   capture_output=True, text=True)
    return vp


def _reexec_into_venv(no_bootstrap=False):
    """当前解释器缺依赖时切到持久 venv 重跑自身；venv 不存在则自动引导。

    Windows 上 os.execv 行为怪异（M2.4 X5），统一用 subprocess + sys.exit。
    JZ2PDF_REEXEC 环境变量防循环。返回即代表无法自愈（调用方走原错误路径）。
    """
    if os.environ.get("JZ2PDF_REEXEC") == "1":
        return
    vp = _venv_python()
    if not vp.exists():
        if no_bootstrap:
            return
        vp = _bootstrap_venv()
        if not vp:
            return
    env = dict(os.environ)
    env["JZ2PDF_REEXEC"] = "1"
    print(f"  ♻️  当前解释器缺依赖 → 切换持久 venv 重跑: {vp}", file=sys.stderr)
    r = subprocess.run([str(vp), str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
    sys.exit(r.returncode)


def _ensure_vendor(force=False):
    """下载/校验 pinned 前端资源到 scripts/ 旁（mermaid + highlight.js + hljs 主题 CSS）。"""
    import urllib.request
    ok = True
    jobs = [(MERMAID_LOCAL, MERMAID_CDN, "mermaid", MERMAID_PIN),
            (HLJS_LOCAL, HLJS_CDN, "highlight.js", HLJS_PIN)]
    try:
        from themes import list_themes as _lts, load_theme as _lt
        HLJS_STYLES_DIR.mkdir(exist_ok=True)
        for t in _lts():
            name = _lt(t).hljs_theme
            jobs.append((
                HLJS_STYLES_DIR / f"{name}.min.css",
                f"https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@{HLJS_PIN}/build/styles/{name}.min.css",
                f"hljs-style:{name}", HLJS_PIN))
    except Exception:
        pass
    for path, url, name, ver in jobs:
        if path.exists() and not force:
            continue
        try:
            print(f"  📥 {name} {ver} → {path.name}")
            urllib.request.urlretrieve(url, str(path))
            _record_vendor(name, ver, path)
        except Exception as e:
            print(f"  ⚠️  {name} 下载失败（渲染时回退 CDN）: {e}", file=sys.stderr)
            ok = False
    return ok


_SMOKE_MD = """---
title: 2pdf setup smoke
---
# Setup 冒烟验收：中文排版与图表

中文断行与**加粗**、==高亮==、`行内 --> 代码` 混排；数字 827.1 亿元。

| 列一 | 列二 |
|---|---|
| 水土保持 | 防洪评价 |

```mermaid
flowchart LR
    A["中文节点"] ==> B{"判断?"}
    B -->|是| C["通过"]
```

```python
def ok() -> str:
    return "高亮"  # 中文注释
```
"""


def run_setup():
    """--setup 一键引导（幂等）：venv+依赖 → 浏览器 → vendor pin → smoke 渲染验收。

    原则：质量为先、首次可以慢——smoke 全绿才算 setup 成功（跨平台保证书）。
    """
    print("== 2pdf --setup ==")
    failures = []

    # 1) venv + python 依赖
    vp = _bootstrap_venv()
    print(f"  {'✅' if vp else '❌'} venv+deps: {VENV_DIR}")
    if not vp:
        failures.append("venv")

    # 2) node / playwright chromium
    if not (shutil.which("node") and shutil.which("npx")):
        hint = "winget install OpenJS.NodeJS" if sys.platform == "win32" else "brew install node"
        print(f"  ❌ node 缺失：{hint}")
        failures.append("node")
    elif not _bundled_launchable():
        print("  📥 安装 playwright chromium（首次较慢，数百 MB）...")
        r = subprocess.run(["npx", "-y", "playwright", "install", "chromium"],
                           env=_node_env(), text=True)
        if _bundled_launchable():
            print("  ✅ playwright chromium 就绪")
        elif _find_system_chrome():
            print("  ⚠️  bundled chromium 未装成，系统 Chrome 可作降级引擎")
        else:
            print("  ❌ 无可用浏览器引擎")
            failures.append("browser")
    else:
        print("  ✅ playwright chromium 已就绪")

    # 3) vendor 资源 pin
    if _ensure_vendor():
        print(f"  ✅ vendor: mermaid {MERMAID_PIN} + hljs {HLJS_PIN}（{VENDOR_LOCK.name}）")
    else:
        print("  ⚠️  部分 vendor 资源未本地化（渲染时回退 CDN）")

    # 4) pandoc（救生艇，warn 级）
    if shutil.which("pandoc"):
        print("  ✅ pandoc 就绪")
    else:
        print(f"  ⚠️  pandoc 缺失（救生艇不可用）：{_pandoc_install_hint()}")

    # 5) smoke 渲染验收（用 venv python 子进程跑完整链路 + verify）
    if vp and "browser" not in failures:
        smoke_dir = Path(tempfile.mkdtemp(prefix="jz2pdf_smoke_"))
        smoke_md = smoke_dir / "smoke.md"
        smoke_pdf = smoke_dir / "smoke.pdf"
        smoke_md.write_text(_SMOKE_MD, encoding="utf-8")
        env = dict(os.environ)
        env["JZ2PDF_REEXEC"] = "1"
        r = subprocess.run(
            [str(vp), str(Path(__file__).resolve()), str(smoke_md), str(smoke_pdf),
             "--browser", "auto", "--verify"],
            capture_output=True, text=True, env=env, timeout=300)
        smoke_ok = (r.returncode == 0 and smoke_pdf.exists()
                    and "error=0" in (r.stdout or ""))
        print(f"  {'✅' if smoke_ok else '❌'} smoke 渲染验收（mermaid+CJK+高亮+verify）")
        if not smoke_ok:
            failures.append("smoke")
            print((r.stdout or "")[-600:])
            print((r.stderr or "")[-600:], file=sys.stderr)
        shutil.rmtree(smoke_dir, ignore_errors=True)
    else:
        failures.append("smoke-skipped")
        print("  ⏭  smoke 跳过（前置步骤未就绪）")

    print(f"  === setup: {'OK，环境已就绪' if not failures else 'FAIL: ' + ','.join(failures)} ===")
    return 0 if not failures else 1


def run_preflight(md_path=None, want_format="pdf", as_json=False):
    """渲染前依赖/环境健康检查。退出码：0 可用(或仅 WARN)，1 致命 FAIL，2 指定 md 不存在。"""
    checks = []

    def chk(name, status, hint=""):
        checks.append({"name": name, "status": status, "hint": hint})

    def okfail(cond):
        return "ok" if cond else "fail"

    def okwarn(cond):
        return "ok" if cond else "warn"

    # interpreter（blocker#1）：当前解释器能否 import markdown——缺则脚本根本起不来
    chk("interpreter:markdown", okfail(importlib.util.find_spec("markdown") is not None),
        f"当前解释器 {sys.executable} 缺 markdown；pip install markdown 或换装齐依赖的 venv")
    chk("pypdf", okwarn(importlib.util.find_spec("pypdf") is not None),
        "pip install pypdf（缺则跳过去空白页/书签/metadata）")
    chk("css_inline", okwarn(importlib.util.find_spec("css_inline") is not None),
        "pip install css_inline（--format wechat 需要）")
    chk("playwright:bundled", okwarn(_bundled_launchable()),
        "npx playwright install chromium（缺则 auto 降级系统 chrome）")
    chk("system-chrome", okwarn(_find_system_chrome() is not None),
        "安装 Google Chrome（--browser chrome / auto 第二路 / pandoc 救生艇需要）")
    chk("pandoc", okwarn(shutil.which("pandoc") is not None),
        f"{_pandoc_install_hint()}（pandoc 救生艇需要）")
    chk("mermaid-vendor", okwarn(MERMAID_LOCAL.exists()),
        f"mermaid {MERMAID_PIN} 本地副本缺失（--setup 下载；否则渲染时联网取 pinned CDN）")
    chk("hljs-vendor", okwarn(HLJS_LOCAL.exists()),
        "highlight.js 本地副本缺失（--setup 下载；否则渲染时走 CDN，离线降级）")
    chk("venv:persistent", okwarn(_venv_python().exists()),
        f"持久 venv 未建（{VENV_DIR}）；跑 --setup 一键引导，或渲染命令将自动引导")

    code = 0
    if md_path is not None:
        p = Path(md_path)
        if not p.exists():
            chk("doc:exists", "fail", f"源文档不存在: {md_path}")
            code = 2
        else:
            text = p.read_text(encoding="utf-8", errors="ignore")
            chk("doc:lines", "info", f"{len(text.splitlines())} 行")
            chk("doc:mermaid", "info", "含 Mermaid" if "```mermaid" in text else "无 Mermaid")
            chk("doc:frontmatter", "info",
                "有 frontmatter" if re.match(r"^---\n", text) else "无 frontmatter（PDF metadata 用文件名兜底）")

    fatal = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    if as_json:
        overall = "fail" if fatal else ("degraded" if has_warn else "ok")
        print(json.dumps({"checks": checks, "overall": overall}, ensure_ascii=False))
    else:
        marks = {"ok": "✅", "warn": "⚠️ ", "fail": "❌", "info": "ℹ️ "}
        for c in checks:
            tail = f"  {c['hint']}" if c["status"] != "ok" else ""
            print(f"  {marks.get(c['status'], '  ')} {c['name']:22}{tail}")
        print(f"  === overall: {'FAIL' if fatal else ('DEGRADED' if has_warn else 'OK')} ===")
    if code == 2:
        return 2
    return 1 if fatal else 0


def parse_cli_args(argv):
    """解析命令行参数（argv 不含程序名），返回 dict。

    复用已有的 --sm/--xs/--sm-after/--xs-after、--theme、--page-size 解析逻辑，
    并新增 --format。无效 format 抛 ValueError（便于单元测试），由 __main__ 捕获退出。
    """
    directives = []
    positional = []
    theme = "blue"
    page_size = "A4"
    fmt = "pdf"
    browser = "playwright"
    preflight = False
    fallback = None
    write_metadata = True
    as_json = False
    verify = False
    allow_diagram_errors = False
    setup = False
    no_bootstrap = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--sm", "--xs", "--sm-after", "--xs-after") and i + 1 < len(argv):
            css = "text-sm" if "sm" in arg else "text-xs"
            mode = "after" if arg.endswith("-after") else "heading"
            directives.append((argv[i + 1], css, mode))
            i += 2
        elif arg == "--theme" and i + 1 < len(argv):
            theme = argv[i + 1]
            if theme not in list_themes():
                print(f"Unknown theme '{theme}'. Available: {', '.join(list_themes())}")
                sys.exit(1)
            i += 2
        elif arg == "--page-size" and i + 1 < len(argv):
            page_size = argv[i + 1]
            if page_size != "A4" and not re.match(r"^\d+x\d+$", page_size):
                raise ValueError(
                    f"Unknown page-size '{page_size}'. Use 'A4' or 'WxH' (e.g. 430x932)"
                )
            i += 2
        elif arg == "--format" and i + 1 < len(argv):
            fmt = argv[i + 1]
            if fmt not in VALID_FORMATS:
                raise ValueError(
                    f"Unknown format '{fmt}'. Available: {', '.join(VALID_FORMATS)}"
                )
            i += 2
        elif arg == "--browser" and i + 1 < len(argv):
            browser = argv[i + 1]
            if browser not in ("playwright", "chrome", "auto"):
                raise ValueError(
                    f"Unknown browser '{browser}'. Use playwright|chrome|auto"
                )
            i += 2
        elif arg == "--fallback" and i + 1 < len(argv):
            fallback = argv[i + 1]
            if fallback not in ("pandoc",):
                raise ValueError(f"Unknown fallback '{fallback}'. Only 'pandoc' supported")
            i += 2
        elif arg == "--preflight":
            preflight = True
            i += 1
        elif arg == "--no-metadata":
            write_metadata = False
            i += 1
        elif arg == "--json":
            as_json = True
            i += 1
        elif arg == "--verify":
            verify = True
            i += 1
        elif arg == "--allow-diagram-errors":
            allow_diagram_errors = True
            i += 1
        elif arg == "--setup" or (arg == "--fix" and preflight):
            setup = True
            i += 1
        elif arg == "--no-bootstrap":
            no_bootstrap = True
            i += 1
        else:
            positional.append(arg)
            i += 1

    return {
        "positional": positional,
        "theme": theme,
        "page_size": page_size,
        "format": fmt,
        "directives": directives,
        "browser": browser,
        "preflight": preflight,
        "fallback": fallback,
        "write_metadata": write_metadata,
        "as_json": as_json,
        "verify": verify,
        "allow_diagram_errors": allow_diagram_errors,
        "setup": setup,
        "no_bootstrap": no_bootstrap,
    }


def output_path_for(md_path, fmt, out_path=None):
    """根据格式推导输出路径。指定 out_path 时直接使用。"""
    if out_path:
        return Path(out_path)
    md_path = Path(md_path)
    ext = {
        "pdf": ".pdf",
        "png": ".png",
        "html": ".html",
        "wechat": ".wechat.html",
    }[fmt]
    return md_path.with_name(md_path.stem + ext)


def inline_css(html):
    """将 <style> 中的 CSS 内联到元素 style 属性，便于微信粘贴。"""
    import css_inline  # 延迟导入，缺失时不影响模块导入

    return css_inline.inline(html)


def _render_playwright_output(html_path, out_path, fmt, page_size="A4", browser="playwright",
                              allow_diagram_errors=False):
    """渲染 png/html/wechat（非 pdf）。逐引擎尝试；非 pdf 无 pandoc 兜底。"""
    html_path = Path(html_path)
    out_path = Path(out_path)
    has_mermaid = 'class="mermaid"' in html_path.read_text(encoding="utf-8")
    wait_timeout = 60000 if has_mermaid else 10000

    # png 视口宽度：自定义 page_size 'WxH' 取 W，A4 取合理默认值
    if page_size == "A4":
        view_w = 794
    else:
        view_w = int(page_size.split("x")[0])

    # 等待 Mermaid 渲染完成 + M1.2 fail-fast（与 pdf 路径共用同一片段）
    common_wait = _mermaid_wait_and_check_js(wait_timeout, allow_diagram_errors)

    if fmt == "png":
        action = f"""
  await page.setViewportSize({{ width: {view_w}, height: 1000 }});
  await page.screenshot({{ path: '{out_path}', fullPage: true, type: 'png' }});"""
    else:
        # html / wechat：取完整渲染后的 DOM，写到 stdout（base64）由 Python 落盘
        action = """
  const content = await page.content();
  process.stdout.write('__HTML_START__' + Buffer.from(content).toString('base64') + '__HTML_END__');"""

    try:
        plan = _launch_plan(browser)
    except _NeedPandoc:
        raise RuntimeError(f"{fmt} 渲染需 playwright 或系统 chrome，均不可用；先跑 --preflight")

    last_err = ""
    for idx, (launch_expr, engine, exe) in enumerate(plan):
        print(f"  \U0001F5A5  engine={engine} executable={exe}", file=sys.stderr)
        script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await {launch_expr};
  const page = await browser.newPage();
  await page.goto('file://{html_path}', {{ waitUntil: 'networkidle', timeout: 120000 }});
{common_wait}
{action}
  await browser.close();
}})();
"""
        script_path = Path(tempfile.gettempdir()) / "pw_render_output.js"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True, text=True, timeout=180, env=_node_env(),
        )

        # M1.2 exit 3 = Mermaid 内容错误：立即终止，不降级引擎
        if result.returncode == 3:
            raise MermaidRenderError(_format_mermaid_errors(result.stderr))

        if fmt in ("html", "wechat"):
            out = result.stdout
            if "__HTML_START__" in out and "__HTML_END__" in out:
                b64 = out.split("__HTML_START__", 1)[1].split("__HTML_END__", 1)[0]
                content = base64.b64decode(b64).decode("utf-8")
                if fmt == "wechat":
                    content = inline_css(content)
                out_path.write_text(content, encoding="utf-8")

        if out_path.exists() and out_path.stat().st_size > 0:
            return
        last_err = result.stderr
        if idx < len(plan) - 1:
            print(f"  ⚠️  {engine} 渲染失败，降级下一引擎", file=sys.stderr)

    raise RuntimeError(f"Playwright {fmt} generation failed: {last_err}")


def md_to_output(md_path, out_path=None, fmt="pdf", header_text=None,
                 directives=None, theme="blue", page_size="A4",
                 browser="playwright", fallback=None, write_metadata=True,
                 allow_diagram_errors=False):
    """按格式分发。pdf 走原有 md_to_pdf 路径，其余渲染 png/html/wechat。"""
    md_path = Path(md_path)
    if fmt == "pdf":
        md_to_pdf(md_path, out_path, header_text, directives,
                  theme=theme, page_size=page_size, browser=browser,
                  fallback=fallback, write_metadata=write_metadata,
                  allow_diagram_errors=allow_diagram_errors)
        return

    header_text = header_text or md_path.stem
    html = build_html(md_path, header_text, directives, theme=theme, page_size=page_size)

    # 本地化 Mermaid JS 以支持 file:// 渲染
    if 'class="mermaid"' in html:
        html = _localize_mermaid_src(html)

    html_path = Path(tempfile.gettempdir()) / f"{md_path.stem}.html"
    html_path.write_text(html, encoding="utf-8")

    out = output_path_for(md_path, fmt, out_path)
    _render_playwright_output(html_path, out, fmt, page_size=page_size, browser=browser,
                              allow_diagram_errors=allow_diagram_errors)

    size_kb = out.stat().st_size / 1024
    print(f"✅ {out.name} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    try:
        args = parse_cli_args(sys.argv[1:])
    except ValueError as e:
        print(e)
        sys.exit(1)

    positional = args["positional"]

    # --setup：一键引导（venv+浏览器+vendor+smoke），幂等；--preflight --fix 同义
    if args["setup"]:
        sys.exit(run_setup())

    # --preflight：依赖/环境自检，可独立运行或对指定 md 体检；本身不依赖 markdown
    if args["preflight"]:
        sys.exit(run_preflight(
            md_path=positional[0] if positional else None,
            want_format=args["format"],
            as_json=args["as_json"],
        ))

    if not positional:
        print(
            "Usage: python md2pdf_chrome.py <md_file> [out_file] [header_text] "
            "[--format pdf|png|html|wechat] [--browser playwright|chrome|auto] "
            "[--fallback pandoc] [--setup] [--preflight [--json] [--fix]] "
            "[--verify] [--allow-diagram-errors] [--no-bootstrap] [--no-metadata] "
            "[--theme NAME (auto-discovered from scripts/themes/*.css)] "
            "[--page-size A4|430x932] [--sm PATTERN] [--xs PATTERN] "
            "[--sm-after PATTERN] [--xs-after PATTERN]"
        )
        sys.exit(1)

    if markdown is None:
        # M2.1 环境自愈：缺依赖 → 自动切换/引导持久 venv 重跑（成功则 sys.exit 不返回）
        _reexec_into_venv(no_bootstrap=args["no_bootstrap"])
        print(
            "❌ 当前解释器缺 markdown 包且自动引导失败。请跑 `--setup` 一键引导，"
            "或 pip install markdown pypdf；可先 `--preflight` 自查。",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        md_to_output(
            positional[0],
            positional[1] if len(positional) > 1 else None,
            fmt=args["format"],
            header_text=positional[2] if len(positional) > 2 else None,
            directives=args["directives"] or None,
            theme=args["theme"],
            page_size=args["page_size"],
            browser=args["browser"],
            fallback=args["fallback"],
            write_metadata=args["write_metadata"],
            allow_diagram_errors=args["allow_diagram_errors"],
        )
    except MermaidRenderError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(3)

    if args["verify"] and args["format"] == "pdf":
        try:
            from verify_pdf import verify as _verify_pdf, render_report as _render_vr
            out_resolved = output_path_for(
                positional[0], args["format"],
                positional[1] if len(positional) > 1 else None,
            )
            _render_vr(_verify_pdf(out_resolved, positional[0]))
        except Exception as e:
            print(f"  ⚠️  verify 跳过: {e}", file=sys.stderr)
