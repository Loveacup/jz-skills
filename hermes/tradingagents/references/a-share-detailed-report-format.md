# A-share detailed report format and workflow

Use this reference when the user asks for a “详细报告” on an A-share stock such as 寒武纪 (`688256`). The goal is a grounded research report, not a wall of raw data.

## Recommended workflow

1. Resolve the stock by code or exact Chinese name. If the name is ambiguous, state the assumption and prefer a code-based rerun.
2. Run the A-share prefetcher from the stable local venv when available:

```bash
~/.tradingagents/ashare_env/bin/python ~/.hermes/skills/research/tradingagents/templates/ashare_prefetch.py <股票名或代码> --days 120 --news-limit 8
```

3. Read the generated Markdown/JSON from `~/.tradingagents/ashare_context/` and use it as the factual base.
4. If time/cost permits, augment with TradingAgents or web/news checks, but do not let upstream US-market assumptions override the A-share context.
5. Save the full report under `~/.tradingagents/reports/YYYYMMDD-HHMM-TICKER-name-detailed.md`.
6. In chat, lead with a short conclusion and 3–6 key judgments, then give the report path. Avoid pasting excessive raw tables into Telegram.

## Report structure

- **结论先行**: bullish/neutral/bearish/unclear, suitable holding horizon, and biggest uncertainty.
- **标的识别与数据质量**: code, name, exchange, data timestamp, stale-cache/fallback notes.
- **行情与技术面**: latest close, 5/20/60-day context, moving averages, price-position percentile, volume ratio, drawdown/extension risk.
- **资金面**: recent main/large-order flow, divergence between price and flow, whether flow confirms the trend.
- **基本面/产业逻辑**: business position, growth drivers, valuation pressure, policy/supply-chain sensitivity.
- **新闻与催化**: only include company-relevant news; filter same-code or keyword false positives.
- **核心风险**: valuation, liquidity/lock-up, earnings delivery, policy/export restrictions, market beta.
- **情景推演**: bull/base/bear cases with observable triggers.
- **操作观察点**: levels or conditions to watch, framed as research signals rather than trading instructions.
- **免责声明**: not investment advice; public endpoints may be delayed or incomplete.

## User-facing style

For this user, detailed does not mean verbose in chat. Prefer:

- first sentence: “结论：…”
- 3–6 bullet judgments
- path to the full Markdown report
- no repeated caveats; one clear risk/disclaimer is enough

Keep the full depth in the saved report, not in the Telegram message.
