# Mobile PDF persistent artifact recovery

Use when a morning-news mobile PDF render task reports success, but the auditor cannot find the PDF/HTML/PNG/validation files.

## Symptom

- Render card summary claims PDF/HTML/PNG were created.
- Auditor blocks with “产物缺失 / scratch workspace 已清除 / PDF/HTML/PNG/validation JSON 不存在”.
- News source repair and source audit may already be valid.

## Recovery

1. Do **not** re-run news search or rewrite the brief.
2. Use the latest audited source Markdown as input.
3. Archive or supersede any final-delivery card that depends on the blocked old PDF audit.
4. Create a narrow chain:
   - `mobile-pdf-render-v2-persist` assigned to `engineer`
   - `mobile-pdf-audit-v2` assigned to `auditor`
   - `mobile-pdf-final-v2` assigned to `reviewer`
5. The render brief must require every artifact to be written under the current Kanban task workspace absolute path:
   - `morning-news-YYYY-MM-DD-mobile-v2.html`
   - `morning-news-YYYY-MM-DD-mobile-v2.pdf`
   - `cover.png`, `analysis.png`, `summary.png`, `sources.png`
   - `render-validation.json`
6. The render worker must read back with `ls -lh` and PyMuPDF before `kanban_complete`; summary must list absolute paths.

## Acceptance gates

- PDF opens; page size about `323 × 675–699pt`.
- U+FFFD count is 0.
- Seven sentinels appear: `执行摘要`, `分析`, `今日总结`, `核心矛盾`, `Alex Cai`, `六部监制`, `来源清单`.
- Cover includes `制作者 Alex Cai`.
- Card sources use `来源：S01 媒体名 · S02 媒体名`.
- Source ledger is S01–SNN numbered lines with media + URL.
- Cover / analysis / summary / sources PNGs exist and are visually checked.

## Pitfall

A successful worker summary is not enough. If artifacts live only in a temporary scratch directory, the next audit cannot verify them and the chain must not deliver the PDF.
