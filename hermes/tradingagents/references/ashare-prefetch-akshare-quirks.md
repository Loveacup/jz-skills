# A-share Prefetch / AKShare Quirks

Session-derived notes for maintaining `templates/ashare_prefetch.py`.

## Durable patterns

- Use a dedicated local venv for A-share data dependencies to avoid polluting the Hermes agent venv:
  - `~/.tradingagents/ashare_env/bin/python ~/.hermes/skills/research/tradingagents/templates/ashare_prefetch.py <股票名或代码>`
- For Telegram/gateway runs, prefer `--json-only` or otherwise suppress progress bars/noisy stdout. Set `TQDM_DISABLE=1` before importing libraries that may emit tqdm progress bars.
- AKShare interfaces vary by version. Defensive calls are better than hard assumptions:
  - `stock_a_lg_indicator` may not exist; guard with `hasattr(ak, "stock_a_lg_indicator")` and skip gracefully.
  - `stock_individual_fund_flow(stock=..., market=...)` expects market codes such as `sh`, `sz`, or `bj`, not a display label like `沪深A股`.
  - Choose `sh` for codes starting with `6`/`9`, `sz` for `0`/`2`/`3`, and `bj` as fallback.
- Keep partial-data behavior: if realtime/history/financials fail but news or moneyflow succeeds, still write JSON/Markdown and include `errors[]` in the artifact.

## Example maintenance checks

```bash
~/.tradingagents/ashare_env/bin/python -m py_compile \
  ~/.hermes/skills/research/tradingagents/templates/ashare_prefetch.py

~/.tradingagents/ashare_env/bin/python \
  ~/.hermes/skills/research/tradingagents/templates/ashare_prefetch.py 寒武纪 \
  --days 80 --news-limit 5 --json-only
```

## Interpretation note

A successful prefetch run can still have `errors_count > 0` when some providers are unreachable or a provider schema changed. Treat the artifact as usable if it contains enough grounded data for the requested analysis, and explicitly mention missing sections in the final report.
