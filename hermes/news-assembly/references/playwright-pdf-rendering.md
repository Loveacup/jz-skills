# Playwright PDF Rendering for Bilingual Briefings

Proven technique for generating dual-format PDFs (mobile + A4) from Chinese/English bilingual markdown briefings. Used successfully in morning-news-briefing v5.1.1 pipeline.

## Setup

```bash
pip3 install playwright
# If playwright CLI already exists but Python module doesn't:
# The CLI may be at /opt/homebrew/bin/playwright while Python needs the pip package.
python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

Chromium browser is bundled with the pip package — no separate `playwright install` needed if `sync_playwright().start().chromium.launch()` succeeds.

## Dual-Format Output

### Mobile (430×932px)
- Cream background: `#fffdf8`
- Gold accent: `#b47a32`
- Fonts: Inter + Noto Serif SC via Google Fonts
- Viewport: 430px wide, portrait scroll
- Best for: Telegram/WeChat delivery, phone reading

### Standard (A4)
- Dark gradient cover page: `linear-gradient(135deg, #111827, #123c55)`
- Title font: Georgia / Noto Serif SC
- Content font: 11pt Georgia serif
- Section headers: `#123c55` with `#b47a32` underline
- Best for: desktop reading, printing, archival

## Key Implementation Details

### CSS @import for fonts
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Inter:wght@400;600;700&display=swap');
```
Must use `wait_until="networkidle"` in `page.set_content()` to ensure fonts load before PDF capture.

### Markdown → HTML conversion
- Headers: regex `^# ` → `<h1>`, `^## ` → `<h2>`, `^### ` → `<h3>`
- Bold: `**text**` → `<strong>`
- Horizontal rules: `---` → `<hr>`
- Citation anchors: `[sN]` → `<sup class="cite">[sN]</sup>`
- Tables: pipe-delimited rows → `<table>` with `<th>` for first row
- Paragraphs: non-tag blocks wrapped in `<p>`

### PDF generation call
```python
page.pdf(
    path=output_path,
    width="430px",          # Mobile
    height="932px",         # Mobile
    # format="A4",          # A4
    print_background=True,   # Critical: renders CSS backgrounds
    scale=1.0,
    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
)
```

### Cover page for A4
The cover page uses a full-viewport `<div class="cover">` with dark gradient background. Executive summary bullets are rendered as `<ol><li>...</li></ol>`. A `<div class="page-break">` with `page-break-before: always` separates cover from content.

## Pitfalls

- **Fonts won't render** if `wait_until="networkidle"` is omitted — the PDF will use fallback system fonts.
- **Gradient backgrounds** require `print_background=True` — without it, cover pages render as solid white.
- **Mobile viewport** must match PDF dimensions exactly (430×932) or content gets clipped/scaled.
- **Large markdown** (>50KB) may need pagination — split into multiple `page.pdf()` calls if content overflows.
- **Google Fonts @import** adds ~2-3s latency per page. For production pipelines with many PDFs, consider self-hosting font files.

## Proven CSS Variables

| Element | Mobile | A4 |
|---------|--------|-----|
| Body bg | `#fffdf8` | `#fff` |
| H1 | 22px, centered | 36pt on cover only |
| H2 | 16px, `#b47a32`, bottom border | 16pt, `#123c55`, 2px `#b47a32` border |
| H3 | 14px, `#3d3d3d` | 12pt, `#2d2d2d` |
| Body text | 13px Inter/Noto Serif SC | 11pt Georgia/Noto Serif SC |
| Strong accent | `#b47a32` | `#b47a32` |
| Table header bg | `#f5eedf` | `#f0f4f8` |
| Citation sup | 9px, `#b47a32` | 8pt, `#b47a32` |
