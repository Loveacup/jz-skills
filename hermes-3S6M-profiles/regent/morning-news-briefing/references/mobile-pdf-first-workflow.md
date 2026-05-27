# Mobile PDF-first morning news workflow

Use when the user asks directly for “早新闻手机 PDF 版 / 手机 PDF 版 / mobile PDF” instead of first requesting a text briefing.

## Durable pattern

This is **not** a shortcut rendering task. It is the normal morning-news chain with PDF as the final delivery artifact:

1. Parallel source collection
   - Chinese / China-related lane: `hanlinyuan`
   - US + international lane: `hanlinyuan`
   - market + technology lane: `jiangzuojian`
2. Fan-in editor: merge only parent artifacts, no new search.
3. Analysis + summary: produce full `分析` and `今日总结` from the approved news only.
4. Reviewer merge: combine news Markdown + analysis artifact into one mobile-source Markdown.
5. Engineer render: generate HTML, PDF, and screenshots for cover / analysis / summary pages.
6. Auditor final check: verify PDF text, dimensions, sentinels, screenshots, and style continuity.
7. Regent delivery: send the audited PDF with `MEDIA:<absolute_path>`.

## Key acceptance gates

**Must also pass the "手机版 PDF 版式八诫" checklist:** see `references/mobile-pdf-layout-eight-commandments.md` for the full 8-item gate with self-test script.

## Key acceptance gates (core)

- PDF is mobile-like: first page rect roughly `323 × 675–699pt`.
- Extracted text has zero U+FFFD replacement characters.
- Strong sentinels all appear: `执行摘要`, `分析`, `今日总结`, `核心矛盾`, `Alex Cai`, `六部监制`, `来源清单`.
- Visual screenshots include cover, analysis page, and summary page.
- Style remains the accepted light newsletter/editorial style (`#fffdf8` background, single-column cards), not a fresh dark/terminal redesign.
- The source Markdown used for rendering must already include the merged analysis artifact; do not render from delivery-news-only Markdown.

## Operational note

If the request is PDF-first, do not spend the final response on a long text news summary. The user asked for a file. Deliver the PDF and give only a short evidence line: page count, mobile dimensions, no乱码, and content gates passed.
