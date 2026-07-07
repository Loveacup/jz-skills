---
name: 2pdf
description: Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. Also converts Markdown / Obsidian notes into beautiful CJK-safe styled PDF (and PNG/HTML/WeChat) with themes, Mermaid, and bookmarks. When Claude needs to fill a PDF form, process/generate/analyze PDFs at scale, or turn Markdown/Obsidian notes into PDF. Triggers: md to pdf, markdown to pdf, 转 PDF, Obsidian 导出 PDF, 笔记转 PDF, export note to PDF.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Skill

> **Source repo**: https://github.com/Loveacup/jz-skills (path `shared/2pdf`) — to update this skill: `git pull` then re-run `python3 scripts/md2pdf_chrome.py --setup` (idempotent).

## Overview

This skill covers PDF processing operations: extract text/tables, merge/split, create new PDFs, fill forms, and convert Markdown to styled PDF with CJK support.

- **Markdown to PDF** (primary workflow): `scripts/md2pdf_chrome.py` — see below
- **PDF operations** (merge, split, extract, create): see `references/pdf-operations.md`
- **Fill PDF forms**: read `references/forms.md` and follow its instructions
- **Advanced** (pypdfium2, pdf-lib, troubleshooting): see `references/advanced.md`
- **Markdown to PDF internals** (pagination, font sizing, Mermaid, callouts): see `references/md2pdf-details.md`

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
**Prerequisites — one command**: `python3 scripts/md2pdf_chrome.py --setup` (first run may take minutes: creates the persistent venv `~/.venvs/pdf-skill`, installs `markdown`/`pypdf`/`css_inline`, installs Playwright Chromium if missing, vendors pinned mermaid/highlight.js locally, then runs a smoke render + verify — green means the whole chain works on THIS machine, mac or Windows). Node.js must be present (`brew install node` / `winget install OpenJS.NodeJS`); `pandoc` is optional (lifeboat only).

> ✅ **Self-healing**: even without `--setup`, any render command run from a dependency-less `python3` auto-switches to (or auto-creates) the persistent venv and re-executes itself — no manual env work. Disable with `--no-bootstrap`. Setup is idempotent; re-run it after upgrades.

### Usage

```bash
python scripts/md2pdf_chrome.py <md_file> [pdf_file] [header_text] \
  [--format pdf|png|html|wechat] [--browser playwright|chrome|auto] \
  [--theme NAME] [--page-size A4|430x932] \
  [--verify] [--allow-diagram-errors] [--no-metadata] [--fallback pandoc] \
  [--sm PATTERN] [--xs PATTERN] [--sm-after PATTERN] [--xs-after PATTERN]

# One-time environment bootstrap (idempotent; also: --preflight --fix)
python3 scripts/md2pdf_chrome.py --setup

# Preflight: check current interpreter + deps + browsers BEFORE rendering
python scripts/md2pdf_chrome.py --preflight            # human-readable
python scripts/md2pdf_chrome.py --preflight --json     # machine-readable (CI/quality gate)

# Examples
python scripts/md2pdf_chrome.py report.md
python scripts/md2pdf_chrome.py report.md ~/output/report.pdf "My Report Title"
python scripts/md2pdf_chrome.py note.md out.pdf --browser auto --verify   # resilient render + quality gate
python scripts/md2pdf_chrome.py report.md output.pdf --theme academic --sm "开发路线图" --xs-after "变更历史"
```

### Output formats & resilience

| Flag | Effect |
|------|--------|
| `--format pdf\|png\|html\|wechat` | Output format. `pdf` (default), `png` (full-page screenshot), `html` (standalone), `wechat` (CSS inlined for WeChat paste) |
| `--browser playwright\|chrome\|auto` | Rendering engine. `playwright` (default, bundled Chromium); `chrome` (system Chrome via `executablePath`); `auto` tries bundled → system Chrome → (pdf only) pandoc, surviving runtime launch failures. Prints actual `engine` + `executable` to stderr |
| `--page-size A4\|WxH` | `A4` (default) or a custom mobile size like `430x932`. Validated up front |
| `--setup` | One-time idempotent bootstrap: persistent venv + deps + Playwright Chromium + pinned vendor assets (mermaid/hljs, `vendor.lock.json`) + smoke render acceptance. Alias: `--preflight --fix` |
| `--preflight [--json]` | Health-check current interpreter, deps, browsers, pandoc, vendored assets, persistent venv — no rendering. Exit 0 ok / 1 fatal / 2 missing doc |
| `--verify` | After rendering PDF, run delivery quality gate (`verify_pdf.py`): Mermaid-source leak, **Mermaid error-bomb text (fuzzy match)**, **diagram count reconciliation** (`/JZDiagramTotal` vs `/JZDiagramRendered` metadata), file size/magic, page count, metadata |
| `--allow-diagram-errors` | Explicitly allow a PDF to be produced even when some Mermaid diagrams failed (default: **fail-fast, exit 3, no output file**) |
| `--no-bootstrap` | Disable the automatic venv self-healing re-exec |
| `--fallback pandoc` | Force the pandoc lifeboat (pandoc → HTML+CSS → system Chrome print-to-pdf). Style NOT faithful, no Mermaid, A4 only. Also auto-triggered by `--browser auto` when no Chromium can launch |
| `--no-metadata` | Skip writing source frontmatter into PDF metadata (including diagram-count keys) |

**Themes** auto-discover from `scripts/themes/*.css` (currently 18: academic, blue, dark, dracula, editorial, gruvbox-dark, gruvbox-light, kami, minimalist, newsletter, nord, sepia, social-card, solarized-dark, solarized-light, swiss, warm-academic, wechat-article). Use `--theme auto` to let the content-aware router pick a palette based on keywords, code density, and frontmatter.

**Source frontmatter → PDF metadata**: `title` / `author` / `description` / `tags` / `aliases` / `created` / `modified` map to `/Title /Author /Subject /Keywords /CreationDate /ModDate`. `/Author` is written only when frontmatter explicitly declares `author` (privacy guard); `--no-metadata` disables the whole step.

**Three-tier fallback** (rendering resilience — the 6-13 incident hardening):
1. **Primary** — Playwright bundled Chromium (`--browser playwright`, default).
2. **System Chrome** — `--browser chrome`, or `auto` when bundled Chromium fails to launch.
3. **Pandoc lifeboat** — `--fallback pandoc`, or `auto` when no Chromium launches (pdf only). Style not faithful; emergency use.

**Quality-first fail-fast** (the 7-02 `==>` incident hardening — four defense layers):
1. **Fence-first preprocessing** — code fences & inline code are extracted to placeholders BEFORE `==highlight==`/wikilink/tasklist conversions, so Mermaid thick arrows (`A ==> B`) and code containing `[[ ]]`/`- [ ]` are never mangled.
2. **Render-time fail-fast** — every Mermaid block is `mermaid.parse()`-prechecked then rendered individually in the page; any failure aborts with exit 3, block number, error message and source head — **no PDF is produced**. Engine downgrade and the pandoc lifeboat are NOT triggered by diagram content errors.
3. **Parse precheck reporting** — errors are reported in seconds (before full page render), so the agent can fix the md immediately.
4. **Independent verify gate** — `--verify` re-checks the delivered PDF in a separate process: error-bomb fuzzy text scan + diagram count reconciliation via PDF metadata.

**Cross-platform (mac + Windows)**: CJK font stacks include PingFang/YaHei (+ Consolas/Cascadia for code); system-Chrome discovery covers `/Applications`, `%ProgramFiles%`, Linux paths; Playwright cache detection covers `Library/Caches`, `.cache`, `%LOCALAPPDATA%`; no `/tmp` hardcoding (uses the platform temp dir); vendored assets live next to `scripts/`. Deploy/sync shell scripts remain mac-side; on Windows just `git pull` + `--setup`.

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
| `--theme NAME` | Set visual theme: `blue` (default), `dark`, `academic`, `auto` — auto-discovered from `scripts/themes/*.css`. `auto` uses the content-aware router. |
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
4. **Mermaid**: Convert mermaid code blocks → `<div class="mermaid">`, load pinned Mermaid JS vendored next to the script (`scripts/mermaid.min.js` + `vendor.lock.json`, downloaded by `--setup`), auto-scale SVG
5. **Syntax Highlighting**: highlight.js CDN with theme-aware styling (atom-one-dark / atom-one-light)
6. **Content Adaptation JS**: Adaptive table font sizing (5+ cols → 10px, 7+ → 9px), section density analysis (auto-shrink dense sections)
7. **Render**: Playwright Chromium headless — `waitForFunction` waits for Mermaid SVG rendering, `networkidle` ensures all resources loaded, then `page.pdf()` with A4 format + page numbers + native bookmarks & accessibility tags (`outline: true, tagged: true`)
8. **Post-process**: Remove blank pages + write metadata via pypdf `clone_from` (preserves native outline/tags); pypdf bookmark builder kept only as fallback for PDFs without a native outline (e.g. pandoc lifeboat)

For pagination rules, font sizing tables, Mermaid details, callout types, and CSS customization, see `references/md2pdf-details.md`.

### Pitfalls

**Mermaid failures never reach the PDF (by design).** If a render exits with code 3 and a `图#N` error listing, the md has a genuine Mermaid syntax error — fix the listed block and re-run. Historical note: thick arrows `==>` used to be destroyed by the highlight preprocessor (2026-07-02 incident); fence-first protection fixed this permanently, so `==>` is safe to use now.

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
| **Markdown to PDF** | `scripts/md2pdf_chrome.py` | Playwright Chromium, CJK-safe |
| Merge/Split/Rotate PDFs | pypdf | `references/pdf-operations.md` |
| Extract text | pdfplumber | `references/pdf-operations.md` |
| Extract tables | pdfplumber | `references/pdf-operations.md` |
| Create PDFs | reportlab | `references/pdf-operations.md` |
| CLI merge/split | qpdf / pdftk | `references/pdf-operations.md` |
| OCR scanned PDFs | pytesseract | `references/pdf-operations.md` |
| Fill PDF forms | pypdf / pdf-lib | `references/forms.md` |
| pypdfium2, pdf-lib | advanced libs | `references/advanced.md` |
| Page headers/footers | `scripts/md2pdf_chrome.py` | Playwright, auto page numbering |
