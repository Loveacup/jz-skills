# Morning News PDF Report Lessons

Use this reference when converting a morning-news briefing into a designed PDF.

## Accepted layout variants

See `references/pdf-layout-accepted-variants.md` for the two stored, user-accepted PDF layouts:

- **Balanced Editorial PDF** — A4, normal forwarding/reading version, usually 8–10 pages for ~32 items.
- **Mobile Editorial PDF** — narrow 430×932 CSS page, single-column mobile reading version, usually ~20–25 pages for ~32 items.

## Durable lessons from PDF iterations

0. **Default to the balanced version**
   - The accepted default after iteration is neither the whitespace-heavy 14-page version nor the over-compressed 6-page version.
   - Aim for a balanced 8–10 page report when the clean brief has ~32 news items plus analysis and sources.
   - Keep each news item reasonably complete from the clean Markdown; do not collapse it into headline-only cards just to reduce page count.
   - The user prefers: “适当详细但不空”.

1. **Do not confuse detail with raw appendices**
   - A detailed report should expand the clean, approved brief and preserve source traceability.
   - Do not paste three worker raw artifacts as full appendices unless the user explicitly asks for raw materials.
   - Default PDF structure: cover/header → executive brief → sectioned news → market data → analysis → today summary → compact source ledger.

2. **Analysis is a required deliverable, not decoration**
   - Before rendering, verify the clean Markdown contains both `## 分析` and `## 今日总结`.
   - If missing, dispatch a reasoning/editor agent to add analysis from the approved news only; do not let the prince write it directly.
   - In the PDF, make analysis visually prominent with a dedicated section/card treatment, but avoid forcing it to start on a mostly empty page.

3. **Avoid whitespace-heavy forced pagination**
   - Do not make every major section its own page by default.
   - Avoid blanket `break-before: page`, `page-break-before: always`, fixed `height: 267mm`, or full-page chapter cards except when the user asks for a deck-like report.
   - Prefer natural flow pagination with `break-inside: avoid` only for individual cards/items.
   - Cover can be compact and share the first page with executive summary or first news section when the user wants less empty space.

4. **PDF acceptance checks**
   - Compare page count against the previous version when revising for whitespace or density.
   - For “too empty” feedback: remove unnecessary forced breaks and allow sections to flow naturally.
   - For “too brief” feedback: increase body font/line-height modestly and preserve full clean Markdown news paragraphs rather than compressing copy.
   - Verify extracted text contains `分析`, `今日总结`, the one-line summary, and any requested credit such as `Alex Cai` / `六部监制`.
   - Check replacement characters (`�`) are zero.
   - Render page 1 and the analysis page to images; inspect for large blank areas, overlaps, and broken glyphs.

## Useful implementation pattern

- Generate a clean Markdown first: `final-morning-news-YYYYMMDD-clean.md`.
- Generate self-contained HTML from the clean Markdown.
- Use Playwright/Chromium PDF export with print backgrounds.
   - Keep sources compact via a source ledger (`S01`, `S02`, …) instead of repeating long URL lists inside every news card.
   - In each news card's source line, show both the source ID and media name, e.g. `来源：S01 BBC · S02 Reuters · S05 新华网`; do not show bare IDs only.
