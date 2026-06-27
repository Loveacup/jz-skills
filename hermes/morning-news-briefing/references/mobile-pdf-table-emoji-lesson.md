# Mobile PDF table + emoji lesson (2026-05-24)

## Trigger

During a mobile morning-news PDF iteration, the user noticed that a table in the `今日总结` section did not render as a table. The user also clarified that emoji may be added appropriately.

## Durable lessons

1. **Summary tables must render as tables, not Markdown pipe text.**
   - If the source Markdown contains a pipe table in `今日总结` / summary, the mobile HTML/PDF must convert it to an actual `<table>` or to a mobile-friendly table-card pattern.
   - Never leave raw `| col | col |` lines visible in the PDF.
   - Preserve the row/column relationship: headers, labels, and cells must remain visually connected.

2. **Mobile tables may become vertical cards.**
   - Narrow mobile pages often cannot fit a normal wide table.
   - It is acceptable—and usually preferable—to render each row as a bordered card with field labels, provided all table content remains intact.
   - Use visible separators, labels, and consistent spacing so the reader can tell it came from a table.

3. **Do not compress content to fix layout.**
   - Layout repair may reduce whitespace, padding, heading gaps, card margins, source-ledger spacing, or use smarter page breaks.
   - It must not delete rows, collapse paragraphs into headline-only text, abbreviate analysis, or remove source/summary content.
   - If correct table rendering adds pages, prefer content completeness over page-count targets.

4. **Emoji are allowed, but structural and restrained.**
   - Appropriate uses: section titles, small labels, row headers in summary/data cards, navigation chips.
   - Avoid decorative overload, visual noise, or using emoji as a substitute for factual text.
   - Verify emoji do not render as tofu/garbled glyphs, shift layout, or create alignment problems.

## Verification checklist

- Render `summary.png` / summary-page screenshot and visually inspect it.
- Confirm the PDF/HTML does not expose raw Markdown table pipes in the summary area.
- Confirm table headers and all rows/cells from the source are present.
- Confirm no horizontal overflow on mobile width.
- Confirm full-content sentinels still pass: 执行摘要, 分析, 今日总结, 核心矛盾, 来源清单, Alex Cai, 六部监制.
- Confirm U+FFFD count is 0 and emoji glyphs display correctly.
