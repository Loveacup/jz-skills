# Mobile PDF visual QA lessons

Use this reference when producing a phone-readable PDF version of a morning-news briefing, especially after a user reports low visual quality.

## What failed in the 2026-05-22 run

A PDF can pass basic file checks and still be visually unacceptable. In this run:

- The first mobile PDF was delivered before visual QA and looked poor.
- Root cause of the structural collapse was invalid HTML: many `.news-card` containers were opened but not closed, causing nested-card rendering and unstable pagination.
- A later structural fix passed tag-balance and text checks, but still had visual defects: oversized blank header area, low-contrast body text, and a market table that overflowed the mobile page width.
- A final visual-fix + audit pass resolved these issues.

## Required mobile PDF acceptance gate

Before delivery, verify all of the following:

1. **Structural HTML sanity**
   - `div` and `span` counts balanced, or parse with a real HTML parser if available.
   - No accidental nested `.news-card` sequence caused by missing closing tags.
   - Avoid external stylesheets; keep critical CSS inline or embedded.

2. **PDF text integrity**
   - PyMuPDF can open the file.
   - Page size is phone-shaped; accepted observed target: about `323–324 × 697–699pt`.
   - Extracted text contains: `分析`, `今日总结`, `来源清单`, `Alex Cai`, `六部监制`.
   - U+FFFD replacement count is `0`.

3. **Visual screenshot QA**
   - Render at least the first page and the first analysis page to PNG.
   - Inspect for: top blank area, text contrast, horizontal overflow, clipped tables, overlap, garbling.
   - The analysis section should begin near the top of its page/section and be visually prominent.

4. **Mobile layout rules**
   - Use single-column cards; do not use wide multi-column tables.
   - Market data should be vertical cards/lists, not a desktop table.
   - Body text should have high contrast. On dark themes, main text should be near white/light gray and secondary text still readable; avoid low-contrast muted gray.
   - Page header should be compact; large decorative hero spacing is a fail for phone PDF.

## Repair pattern

If the user says the PDF quality is bad:

1. Do not argue from file-existence or page-count checks.
2. Create a narrow Kanban repair card for the concrete visual defects.
3. Create a dependent audit card that must check both PyMuPDF signals and rendered PNG screenshots.
4. Require the repair worker to output:
   - revised `.html`
   - revised `.pdf`
   - first-page PNG
   - analysis-page PNG
5. Only deliver after the audit is `done` and the orchestrator spot-checks the artifact paths.

## Delivery caution

A previous version may already have been sent. If a later v2/v3 supersedes it, report clearly which version is final and archive obsolete Kanban repair chains so the board does not keep showing stale blockers.
