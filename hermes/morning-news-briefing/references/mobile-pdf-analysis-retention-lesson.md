# Mobile PDF analysis retention lesson (2026-05-23)

## Trigger

User asked for a mobile PDF after the text morning-news briefing had already been delivered. The first rendered PDF was visually acceptable and passed a weak audit, but the user noticed: “分析怎么不见了？”

## Root cause

The PDF render task used the delivery Markdown from the 门下交付 card:

- `delivery-morning-news-YYYYMMDD.md` contained the news list and source coverage.
- The analysis had been produced by a separate analysis card artifact (e.g. `morning-analysis-YYYYMMDD.md`).
- The delivery Markdown did not contain the full `### 🔍 分析` and `### 📌 今日总结` sections.

Audit only checked for the substring `分析`, which appeared in headings/metadata, so it missed the absence of the full analysis and summary.

## Durable fix pattern

When generating a mobile PDF after the briefing is complete:

1. Locate both artifacts:
   - final/delivery news Markdown from 门下交付
   - analysis artifact from the analysis card
2. Merge or render them together, preserving:
   - all news items
   - full analysis logic chains
   - full 今日总结 / core contradiction sentence
   - source ledger and signature
3. Do not rely on substring `分析` alone as proof. Verification must check strong sentinel terms from the actual analysis body.

## Required PDF text sentinels

Use PyMuPDF extraction or equivalent and require all of these to appear:

- `分析`
- `今日总结`
- `核心矛盾`
- one distinctive phrase from the summary, e.g. `三条战线` when present
- at least two distinctive analysis topic terms, e.g. `美伊和谈`, `AI芯片`
- `Alex Cai`
- `六部监制`

If any sentinel is absent, the PDF is not deliverable even if page count, dimensions, and visual style pass.

## Repair strategy

Do not rerun the entire news chain. Create a narrow render-repair card that:

- inputs the approved news Markdown plus the analysis artifact
- keeps the accepted mobile newsletter style
- outputs `*-v2-analysis.pdf/html/png`
- runs text-sentinel + visual screenshot checks

Then run a narrow audit card checking analysis retention and style continuity before sending the PDF.