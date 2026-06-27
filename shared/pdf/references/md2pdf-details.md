# Markdown to PDF — Detailed Reference

Detailed documentation for `scripts/md2pdf_chrome.py` internals: pagination rules, font sizing, Mermaid diagrams, Obsidian callouts, and CSS customization.

## Smart Pagination v2

The script uses a **two-stage pre-measurement** pagination strategy. Instead of relying solely on CSS hints, JS measures every block element's actual rendered position and height at DOMContentLoaded, then makes position-aware decisions:

### Stage 1: CSS Baseline Rules

| Rule | Method | Effect |
|------|--------|--------|
| Headings never orphaned | `h1-h6 { page-break-after: avoid }` | Heading always has content below it on the same page |
| Lists follow headings | `ul, ol { page-break-before: avoid }` | Lists don't jump to next page away from their heading |
| No widow/orphan lines | `p { orphans: 3; widows: 3 }` | At least 3 lines at top/bottom of page |
| HR stays with content | `hr { page-break-after: avoid }` | Separator stays with following content |
| Mermaid diagrams intact | `.mermaid { page-break-inside: avoid }` | Diagrams stay on one page |

### Stage 2: JS Pre-Measurement Engine

JS collects `offsetTop` + `getBoundingClientRect().height` for all block elements (`h1-h6, p, table, ul, ol, pre, .callout, details.callout, .mermaid, blockquote, .doc-section > *, .doc-subsection > *`), simulates A4 page boundaries (970px), then applies 4 rules:

| Rule | Condition | Action |
|------|-----------|--------|
| **Full-page element** | Element height > 92% page | `break-inside: auto` — must allow internal break |
| **Heading orphan** | Heading in bottom 15% of page | `break-before: page` — push to next page |
| **Cross-boundary** | Element overflows to next page | Position-aware: <25% overflow → allow break; >75% overflow + fits one page → push; 25-75% overflow + tall → allow break; short → push |
| **Gap prevention** | Avoid-break element starts past 55% and would leave >40% blank | `break-inside: auto` — relax to prevent large gap |

### Stage 3: Heading-Content Pair Protection

After individual decisions, a second pass ensures headings and their first content block stay on the same page. If a heading lands on page N but its content starts on page N+1, the heading is pushed to N+1.

### Two-Level Section Wrapping

Content is wrapped at two levels for fine-grained control:
- **h2 → `<section class="doc-section">`** — primary sections
- **h3 → `<div class="doc-subsection">`** — subsections within each h2 section

## Content-Adaptive Font Sizing

Font sizing is handled at two levels:

**Script defaults (automatic via CSS):**

| Content Type | Base Size | Notes |
|-------------|-----------|-------|
| Body text | 13px | Base size |
| Blockquotes | 12.5px | Nested → 12px |
| Callout body | 12.5px | Callout lists → 12px |
| Tables | 11.5px | JS: 5+ columns → 10px, 7+ columns → 9px |
| Nested lists | 12.5px | 2nd level → 12px |
| Code blocks | 10.5px | Fixed |

**Claude Code relay classes (inserted per section via CLI flags):**

| Class | Font Size | Use Case |
|-------|-----------|----------|
| `.text-sm` | 12px | Dense H4 subsections, detailed specs |
| `.text-xs` | 11px | Reference tables, appendix content |

## Code Syntax Highlighting

Fenced code blocks are syntax-highlighted via **highlight.js** (CDN):
- **Default theme**: `atom-one-dark` (matches dark code block background)
- **Academic theme**: `atom-one-light` (matches light code block background)
- CSS overrides ensure highlight.js doesn't conflict with the dark `pre` background
- Supports all highlight.js languages automatically

## PDF Bookmarks

After Chrome generates the PDF, **pypdf** post-processes it to add a navigable outline:
- Extracts h1-h3 headings from the Markdown source
- Maps each heading to its PDF page via text search
- Creates a hierarchical bookmark tree (h1 > h2 > h3)
- Enables sidebar navigation in PDF viewers

## Local Image Embedding

Local images in Markdown (`![alt](./img.png)`) are converted to base64 data URIs before rendering:
- Ensures images display correctly regardless of working directory
- Skips remote URLs (`http://`, `https://`) and existing data URIs
- Gracefully handles missing files (preserves original path)
- MIME types detected automatically via `mimetypes.guess_type()`

## Custom Themes

Themes are auto-discovered from `scripts/themes/*.css`. Each CSS file has a TOML-style metadata header:

```css
/*
[theme]
name = dark
description = Charcoal background, VS Code-inspired
hljs_theme = atom-one-dark
*/
body { color: #d4d4d4; background: #1e1e1e; }
```

To add a new theme: create `scripts/themes/<name>.css` with metadata + CSS overrides, then use `--theme <name>`.

Built-in themes:

| Theme | Description | Code Theme |
|-------|-------------|------------|
| `blue` (default) | Professional blue (`#1a3c5e`), gradient tables, sans-serif | atom-one-dark |
| `dark` | Charcoal background, blue accents, VS Code-inspired | atom-one-dark |
| `academic` | Serif fonts (Palatino), minimal styling, traditional | atom-one-light |

Themes auto-discover from `scripts/themes/*.css`; the full current set (11) also includes
`warm-academic`, `editorial`, `kami`, `minimalist`, `newsletter`, `swiss`, `social-card`, `wechat-article`.
Run `--theme <unknown>` to print the live list (each CSS file carries a `[theme]` metadata header with its `hljs_theme`).

## Footnote Support

Standard Markdown footnotes via the `footnotes` extension:
- Inline references: `[^1]` renders as superscript blue link
- Definitions: `[^1]: text` renders in a compact reference section at document end
- Styled at 10px with clear visual separation

## Mermaid Diagram Support

Mermaid diagrams in fenced code blocks are automatically rendered:

- **Rendering**: Mermaid JS v11 (local file or CDN), `startOnLoad: false` + explicit `mermaid.run()` for reliable timing
- **Offline support**: Place `mermaid.min.js` in `scripts/` directory for air-gapped environments
- **Auto-scaling**: After rendering, JS measures each SVG and proportionally scales to fit page (max 580px wide, 650px tall)
- **Natural sizing**: `useMaxWidth: false` — diagrams render at natural size, then scale down (not stretch up)
- **ViewBox preservation**: Ensures crisp rendering at any scale via SVG viewBox
- **Chrome timing**: `--virtual-time-budget=20000` gives Chrome enough virtual time for CDN load + render + post-processing

## Obsidian Callout Support

All 26 Obsidian callout types are supported with color-coded styling:

| Category | Types | Color |
|----------|-------|-------|
| Informational | `note`, `info`, `todo` | Blue |
| Summary | `abstract`, `summary`, `tldr` | Teal |
| Positive | `tip`, `hint`, `important`, `success`, `check`, `done` | Green |
| Question | `question`, `help`, `faq` | Yellow |
| Warning | `warning`, `caution`, `attention` | Orange |
| Negative | `failure`, `fail`, `missing`, `danger`, `error`, `bug` | Red |
| Reference | `example`, `quote`, `cite` | Purple |

Foldable callouts (`> [!type]-` and `> [!type]+`) render as `<details open>` — always expanded in PDF since collapsed content would be invisible in print.

## CSS Customization

Styling features in the script:
- Professional blue theme (`#1a3c5e` headings, gradient table headers) with dark and academic alternatives
- `-apple-system` + `PingFang SC` font stack for CJK (Palatino for academic theme)
- Callout boxes with color-coded borders and backgrounds (26+ types)
- Code blocks with dark theme (`#2c3e50`) + highlight.js syntax highlighting
- Responsive tables with striped rows and adaptive font sizing
- A4 page size with 20mm/18mm margins
- Task list checkboxes (&#x2610; / &#x2611;)
- `<mark>` highlight with yellow background
- Mermaid diagrams with auto-scaling and page-break control
- Footnote section with compact 10px styling
- PDF bookmarks for sidebar navigation

## CJK Font Rendering

| Method | CJK Support | Notes |
|--------|-------------|-------|
| Playwright bundled Chromium | Perfect | **Default** (`--browser playwright`); uses system fonts natively |
| System Chrome | Perfect | `--browser chrome`, or `auto` fallback when bundled Chromium can't launch |
| WeasyPrint | Broken on macOS | Font embedding bug — text extraction OK but visual garbled |
| pandoc + LaTeX | OK if fonts configured | Requires CJK LaTeX packages |

**WeasyPrint CJK 已知问题**: macOS 上 PingFang SC 等系统字体存于 AssetV2 哈希路径，WeasyPrint/Pango 无法正确嵌入，导致 PDF 中文显示乱码（但 pypdf 提取文本正常）。**务必使用 Chromium 系方案（Playwright bundled 默认，或 `--browser chrome` 用系统 Chrome），不要用 WeasyPrint。**

## Page Headers/Footers

To add page headers/footers with page numbers, use `scripts/md2pdf_browser.py` (Playwright version) which supports `displayHeaderFooter`.
