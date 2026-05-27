# Mobile PDF PendingConfirm Recovery

Context: morning-news mobile PDF rendering may finish successfully, write the PDF/HTML and validation summary, then self-block with `PendingConfirm: 等待 reviewer 确认 complete` instead of calling `kanban_complete`.

## Correct recovery

1. Do **not** rerender or rebuild the PDF just because the Kanban card is blocked.
2. Inspect the blocked card comments/summary for artifact paths and validation data.
3. Independently verify the artifact before delivery:
   - PDF exists and non-empty
   - PyMuPDF page count and first page rect match the mobile target (`~323 × 697/699 pt`)
   - extracted text contains `分析`, `今日总结`, `来源清单`, `Alex Cai`, `六部监制`
   - replacement character `�` count is 0
   - render page 1 and an analysis page to images; visually check no large blank areas, overlap, or broken glyphs
4. If verification passes, the Regent/orchestrator may complete the PDF card with a concise evidence summary.
5. If verification fails, create a narrow repair card; do not restart the whole news chain.

## Why

`PendingConfirm` here is a workflow-gate artifact, not necessarily a content failure. Treat it like “artifact produced, needs external acceptance check,” not like a failed renderer.
