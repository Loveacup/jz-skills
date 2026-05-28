---
name: pdf
description: Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, filling forms, and converting Markdown to styled PDF (A4 + mobile 430×932px) with CJK support. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Skill

## Overview

This skill covers PDF processing operations: extract text/tables, merge/split, create new PDFs, fill forms, and convert Markdown to styled PDF with CJK support. Also supports mobile PDF (430×932px) for newsletter-style briefings.

- **Markdown to PDF** (primary workflow): `scripts/md2pdf_chrome.py` — see below
- **PDF operations** (merge, split, extract, create): see `references/pdf-operations.md`
- **Fill PDF forms**: read `references/forms.md` and follow its instructions
- **Advanced** (pypdfium2, pdf-lib, troubleshooting): see `references/advanced.md`
- **Markdown to PDF internals** (pagination, font sizing, Mermaid, callouts, themes): see `references/md2pdf-details.md`
- **Mobile PDF layout** (430×932px newsletter): see `references/mobile-layout.md`

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Markdown to Beautiful PDF (CJK-safe)

Convert Obsidian Flavored Markdown to styled PDF with perfect Chinese/Japanese/Korean rendering.

**Script**: `scripts/md2pdf_chrome.py`
**Prerequisites**: Python 3 + `markdown` + `pypdf` (`pip install markdown pypdf`) + Node.js + Playwright (`npm install playwright && npx playwright install chromium`)

### Usage

```bash
python scripts/md2pdf_chrome.py <md_file> [pdf_file] [header_text] [--theme blue|dark|academic] [--sm PATTERN] [--xs PATTERN] [--sm-after PATTERN] [--xs-after PATTERN]

# Examples
python scripts/md2pdf_chrome.py report.md
python scripts/md2pdf_chrome.py report.md ~/output/report.pdf "My Report Title"
python scripts/md2pdf_chrome.py report.md output.pdf --sm "Phase 2" --sm "Phase 3"
python scripts/md2pdf_chrome.py report.md output.pdf --theme academic --sm "开发路线图" --xs-after "变更历史"
python scripts/md2pdf_chrome.py morning-news.md --page-size 430x932 --theme newsletter
```

### Claude Code Relay Workflow

The script and Claude Code work as a team. The script handles rendering mechanics, Claude Code handles content intelligence.

```
Step 1: Script runs → outputs Outline + PDF (with defaults)
Step 2: Claude Code reads Outline + document head (first ~5 lines) and tail (last ~20 lines) → decides layout
Step 3 (if needed): Claude Code re-runs with flags → script wraps matching content and renders
```

**CLI directives** (script automatically wraps matching content, no file editing needed):

| Flag | Effect |
|------|--------|
| `--theme NAME` | Set visual theme: `blue` (default), `dark`, `academic` — auto-discovered from `scripts/themes/*.css` |
| `--sm "heading text"` | Wrap children of matching heading in `text-sm` (12px) |
| `--xs "heading text"` | Wrap children of matching heading in `text-xs` (11px) |
| `--sm-after "text"` | Wrap from matching line to end of document in `text-sm` (12px) |
| `--xs-after "text"` | Wrap from matching line to end of document in `text-xs` (11px) |

`--sm`/`--xs`: case-insensitive substring match against **heading text**, wraps child sections.
`--sm-after`/`--xs-after`: case-insensitive substring match against **any line**, wraps from that line to EOF. Use for non-heading content like metadata/changelog at document end.

**Manual markers** can also be inserted into Markdown (raw HTML, preserved by `md_in_html` extension):

| Marker | Effect |
|--------|--------|
| `<div style="page-break-before:always"></div>` | Force page break |
| `<div class="text-sm" markdown="1">...</div>` | Shrink to 12px |
| `<div class="text-xs" markdown="1">...</div>` | Shrink to 11px |

**Decision heuristics** for Claude Code (not hardcoded in script):
- **Outline**: 5+ child headings with avg <500c → `--sm` to shrink the section
- **Head/Tail**: metadata (版本/日期/作者) or changelog (变更历史) → `--xs-after`
- Section <300c → don't break before it, let it flow with neighbors
- Section >2000c → consider breaking before it
- Short Phase (e.g. Phase 1: 226c) → no break before it

Most documents need zero intervention (one run). Only complex documents with mixed section sizes or metadata/changelog need a second pass with flags.

### Pipeline

```
Obsidian MD → preprocess → Python markdown (md_in_html) → section wrap → styled HTML + JS → Playwright Chromium → PDF
```

1. **Preprocess**: Strip YAML frontmatter, convert all 26 Obsidian callout types (including foldable), remove wikilinks, convert highlights (`==text==` → `<mark>`), convert task lists, embed local images as base64
2. **Convert**: Python `markdown` library with extensions: `tables`, `fenced_code`, `toc`, `sane_lists`, `md_in_html`, `footnotes`
3. **Section Wrap**: Post-process HTML — wrap `<h2>` into `<section class="doc-section">`, wrap `<h3>` into `<div class="doc-subsection">`
4. **Mermaid**: Convert mermaid code blocks → `<div class="mermaid">`, load Mermaid JS (auto-downloads to `/tmp/mermaid.min.js` on first use), auto-scale SVG
5. **Syntax Highlighting**: highlight.js CDN with theme-aware styling (atom-one-dark / atom-one-light)
6. **Content Adaptation JS**: Adaptive table font sizing (5+ cols → 10px, 7+ → 9px), section density analysis (auto-shrink dense sections)
7. **Render**: Playwright Chromium headless — `waitForFunction` waits for Mermaid SVG rendering, `networkidle` ensures all resources loaded, then `page.pdf()` with A4 format + page numbers
8. **Post-process**: Remove blank pages + add PDF bookmarks (h1-h3 outline) via pypdf

For pagination rules, font sizing tables, Mermaid details, callout types, and CSS customization, see `references/md2pdf-details.md`.

### Pitfalls

**Playwright PDFs are heavy.** A 7-page CJK document can produce a ~1.9MB PDF because Chromium embeds all fonts and full CSS. This routinely times out when delivering via messaging platforms (Telegram MEDIA delivery, etc.).

**Compression is ineffective.** Ghostscript (`-dPDFSETTINGS=/screen`) only shaves ~20% off font-heavy Playwright PDFs. `weasyprint` requires system libs (`libgobject-2.0-0`, pango) often missing. `fpdf2` chokes on `.ttc` system fonts. Splitting pages helps only marginally.

**Delivery fallback strategy (proven):**
1. Generate the styled PDF with `md2pdf_chrome.py` — save to local disk
2. Send the **markdown source** as a text message to the user (it's ~12KB)
3. Tell the user the PDF path on local disk for direct opening
4. If local delivery is not an option, consider `md2pdf_browser.py` which uses the same Playwright pipeline but may handle differently

**Prefer this pattern when the user asks "make a PDF and send it":**
- Generate PDF → note size → if >500KB, preemptively send markdown + local path
- Don't waste turns on compression — it won't reduce enough for Playwright PDFs

## Quick Reference

| Task | Tool | Details |
|------|------|---------|
| **Markdown to PDF** | `scripts/md2pdf_chrome.py` | Playwright, CJK-safe, 7 themes |
| **Markdown→Mobile PDF** | `scripts/md2pdf_chrome.py --page-size 430x932 --theme newsletter` | 430×932px newsletter |
| Merge/Split/Rotate PDFs | pypdf | `references/pdf-operations.md` |
| Extract text | pdfplumber | `references/pdf-operations.md` |
| Extract tables | pdfplumber | `references/pdf-operations.md` |
| Create PDFs | reportlab | `references/pdf-operations.md` |
| CLI merge/split | qpdf / pdftk | `references/pdf-operations.md` |
| OCR scanned PDFs | pytesseract | `references/pdf-operations.md` |
| Fill PDF forms | pypdf / pdf-lib | `references/forms.md` |
| pypdfium2, pdf-lib | advanced libs | `references/advanced.md` |
| Page headers/footers | `scripts/md2pdf_chrome.py` | Playwright, auto page numbering |
