# Accepted Morning News PDF Layout Variants

Use this reference when the user asks for a designed PDF version of a completed morning-news brief.

These layouts were accepted after iterative feedback on 2026-05-21.

## Shared content contract

Input should be the clean approved brief, e.g. `final-morning-news-YYYYMMDD-clean.md`.

Do not re-search or add facts during rendering. Preserve:

- cover/header
- executive brief
- sectioned news
- market data snapshot
- analysis
- today summary
- compact source ledger
- credit: `制作者 Alex Cai，六部监制`

Before rendering, verify the clean Markdown includes both `## 分析` and `## 今日总结`. If missing, dispatch an analysis/editor worker to add them from approved news only.

## Variant A — Balanced Editorial PDF

Use when the user asks for the normal PDF / đẹp版 / 可转发版 / final PDF.

Accepted target:

- Page size: A4
- Typical length for ~32 news items: 8–10 pages
- Style: financial morning brief / editorial report
- Density: “适当详细但不空”
- News text: preserve reasonably complete clean Markdown paragraphs; do not collapse into headline-only cards
- Cover: compact header, may share first page with executive summary / first news section
- Pagination: natural flow; avoid forcing every section onto its own page
- Sources: compact `S01` ledger; story cards must show both source IDs and media names, e.g. `来源：S01 BBC · S02 Reuters`, not bare `S01 · S02`

Core CSS posture:

```css
@page { size: A4; margin: 14mm 14mm 15mm; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
  font-size: 12.5px;
  line-height: 1.72;
  background: #fffdf8;
  color: #171717;
}
.cover { min-height: 98mm; margin: -14mm -14mm 6mm; padding: 18mm 18mm 10mm; }
.story { margin: 0 0 4.8mm; padding-bottom: 3.8mm; border-bottom: 1px solid #ded6c8; }
.market-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; }
.analysis, .summary { border: 1.5px solid #d7b06d; background: linear-gradient(180deg,#fff9ed,#fffdf8); }
.source-list { columns: 2 82mm; column-gap: 7mm; }
```

Acceptance checks:

- extracted text contains `Alex Cai`, `六部监制`, `分析`, `今日总结`, `来源清单`
- replacement characters `�` count is 0
- page count is not extreme versus content length (for the 2026-05-21 clean brief, accepted: 8 pages)
- render page 1 and the analysis page to images and inspect for large blank areas, overlap, or broken glyphs

## Variant B — Mobile Editorial PDF

Use when the user asks for “手机 PDF 版”, “手机阅读版”, or PDF primarily read inside Telegram/mobile.

Accepted target:

- Page size: custom narrow mobile page: `430px × 900–932px` CSS page
- Actual PDF page size from Chromium: about `323.04pt × 675–699pt`
- Typical length for ~32 news items: about 17–23 pages, depending on density (compact v3 after whitespace feedback: 17 pages)
- Style: single-column mobile morning brief / newsletter article flow
- Typography: larger than A4 version; comfortable line-height but not wasteful
- News: card-style single-column story blocks, but long cards should be allowed to split across pages
- Sources: compact source ID footer inside each card, but include media names beside IDs, e.g. `来源：S01 BBC · S02 Reuters`; full ledger remains at end
- Cover: compact newsletter header preferred; avoid a full-page cover when the user complains about blank space

Core CSS posture:

```css
@page { size: 430px 900px; margin: 10px 16px 16px; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
  font-size: 15.2px;
  line-height: 1.64;
  background: #fffdf8;
  color: #1b1a17;
  overflow-wrap: break-word;
}
.cover { margin: -10px -16px 8px; padding: 28px 22px 20px; }
.story { break-inside: auto; page-break-inside: auto; margin: 0 0 9px; padding: 8px 9px 7px; border: 1px solid #e4dac9; border-radius: 12px; background: #fffefa; }
.story h3 { font-size: 17px; line-height: 1.36; break-after: auto; }
.market-grid { display: grid; grid-template-columns: 1fr; gap: 6px; }
.analysis-card { break-inside: auto; page-break-inside: auto; border: 1px solid #eadcc6; border-radius: 12px; padding: 8px 8px 7px; }
.source-list { display: grid; grid-template-columns: 1fr; gap: 2px; }
```

If the user says the mobile PDF has too much blank space, first remove/relax pagination blockers: avoid blanket `break-inside: avoid` on `.story`, `.analysis-card`, `.important`, `.section-head`, and avoid `break-after: avoid` on headings. Let long cards split across pages, then verify text continuation across the page break.

Acceptance checks:

- verify page dimensions are narrow/mobile-like, e.g. first page rect around `323 × 699 pt`
- extracted text contains `Alex Cai`, `六部监制`, `分析`, `今日总结`, `来源清单`
- replacement characters `�` count is 0
- render page 1 and the analysis page to images; page 1 should look like a mobile cover, analysis page should be readable in one column

## Rendering pattern

Use Playwright/Chromium:

```js
await page.emulateMedia({ media: 'print' });
await page.pdf({ path: pdfPath, printBackground: true, preferCSSPageSize: true, tagged: true });
```

Use PyMuPDF for verification:

```python
import fitz
pdf = fitz.open(pdf_path)
text = "\n".join(page.get_text() for page in pdf)
assert "分析" in text and "今日总结" in text
assert text.count("\ufffd") == 0
print(pdf.page_count, pdf[0].rect)
```
