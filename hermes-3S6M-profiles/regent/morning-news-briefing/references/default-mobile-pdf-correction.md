# 默认手机版 PDF 交付纠偏

## Trigger

当用户只说“早新闻”时，默认交付物是**手机版 PDF**，不是文字版。除非用户明确说“直接文字 / 不要 PDF / 发正文”，不得先建文字交付链。

## Correct workflow

1. 正常检索：中文/中国、美国/国际、市场/AI 三路来源采集。
2. Fan-in：合并、去重、分析、今日总结，形成完整 source Markdown。
3. Mobile source merge：确认 source Markdown 同时含执行摘要、新闻正文、分析、今日总结、来源清单、署名。
4. Render：生成 `.html`、`.pdf`、首页 PNG、分析页 PNG、总结页 PNG、来源页 PNG。
5. Audit：PyMuPDF 文本 + HTML + PNG 视觉终审；通过后才交付。
6. Delivery：主频道只发 `MEDIA:<pdf_path>` 与一句验收证据。

## If the wrong text chain was already created

- 不要重跑全量新闻检索。
- 归档/废止文字交付卡，保留已通过的 fan-in source artifact。
- 若源稿被御史指出 URL/年份/重复来源问题，先建精准 source repair → source reaudit。
- 再建 render → PDF audit → final delivery 链。

## Minimum acceptance evidence

- PDF 手机尺寸约 `323 × 675–699pt`。
- U+FFFD = 0。
- 七哨兵全命中：执行摘要、分析、今日总结、核心矛盾、Alex Cai、六部监制、来源清单。
- 首页含“制作者 Alex Cai”。
- 来源格式为 `来源：S01 媒体名 · S02 媒体名`；末尾来源清单 S01–SNN 逐行。
- 首页/分析/总结/来源 PNG 视觉抽检通过。
