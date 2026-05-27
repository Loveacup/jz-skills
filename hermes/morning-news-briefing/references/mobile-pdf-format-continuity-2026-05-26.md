# Mobile PDF format continuity — 2026-05-26 correction

## Trigger

User rejected a technically passing morning-news mobile PDF with: “对比之前的早新闻，格式不对啊”. The PDF had passed page size / sentinel gates, but failed the user’s format-continuity expectation.

## Accepted baseline to compare against

When the user says the current morning-news PDF “format is wrong” or asks to compare with earlier morning-news output, use the recent accepted version characterized as:

- About 16 pages
- Mobile page size around 323×675 pt
- Around 30 news items + 4 analysis items + 83 sources
- Source display, tables, and summary layout were the main accepted-format features

Do not treat a new 12-page / 324×690 pt PDF that passes text gates as automatically acceptable if it diverges from that visual/structural baseline.

## Required recovery sequence

1. **Grill before rework.** Ask which old version to use as baseline and what “format wrong” means. In this session the user chose: “以最近那版 16页、323×675pt、30篇+4分析+83来源 为基准；主要修来源/表格/总结版式”.
2. **Ask content policy if counts differ.** Current content may be 33 news / 91 sources while the baseline was 30 / 83. Do not assume deletion is allowed.
3. **If user chooses review-first, do not jump straight to engineering.** Create a 门下 comparison/recommendation card first, then 尚书 coordination, then 工部 re-render, 御史 audit, 门下 final.
4. **Do not re-search news.** This is a format-continuity repair: reuse current source Markdown/artifacts and old accepted HTML/PDF/CSS as the visual baseline.
5. **Engineering brief focus:** sources, tables, summary layout, CSS/template reuse, page density, and ledger readability — not new editorial content.

## Audit checks beyond ordinary PDF gates

A technically valid PDF still fails if these differ from the accepted baseline:

- Card source line should look like `📡 来源：S01 媒体名 · S02 媒体名`, not bare media names or naked S numbers.
- Source ledger should be continuous S01–SNN with media name + traceable URL/domain, without long URL overflow.
- Markdown pipe tables in the summary must render as real tables or mobile table-cards.
- `今日总结` must be a complete independent card/section, not merely a sentinel hit.
- Page density should resemble the accepted ~16-page version; page count alone is not enough, but large structural shifts need review.

## Reporting discipline

When a user flags format mismatch, acknowledge that “passing dimensions/sentinels ≠ passing format continuity,” then route the comparison/rework chain. Do not defend the current PDF merely because 御史 and 门下 passed technical gates.