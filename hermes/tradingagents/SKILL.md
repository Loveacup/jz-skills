---
name: tradingagents
description: "Use when the user wants AI-assisted stock analysis, TradingAgents setup, or to run TauricResearch/TradingAgents locally. Guides installation, API keys, non-interactive runs, report summarization, and risk disclaimers."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, finance, stocks, research, langgraph, multi-agent]
    homepage: https://github.com/TauricResearch/TradingAgents
    related_skills: [financial-research-agents, web-research-router, polymarket]
---

# TradingAgents

## Overview

TradingAgents is TauricResearch's multi-agent stock-analysis framework. It uses LangGraph/LangChain to coordinate analysts, researchers, a trader, and risk-management agents around a ticker/date, then produces a trading decision and supporting rationale.

This skill teaches Hermes how to use TradingAgents as an **external local tool**. Do not copy the upstream TradingAgents source or prompts into Hermes. Install or update the upstream package, run it through its CLI or Python API, then summarize the generated output for the user.

Important: TradingAgents output is research assistance, not investment advice. Never execute trades, place orders, rebalance portfolios, or present results as guaranteed alpha.

### 🚨 Red Flags: DO NOT CUT CORNERS

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll skip the install check, it's probably already there" | Missing dependencies cause silent failures. Always verify repo + API key before running. |
| "Let me run the full multi-round analysis for this single ticker" | Multi-round burns tokens. Use cost-controlled config unless the user explicitly requests deep analysis. |
| "The raw output is fine, I'll send it as-is" | Raw TradingAgents output is verbose JSON/logs. Convert to structured report with risk disclaimers. |
| "I can infer the ticker from context" | Ambiguous symbols (e.g., 茅台 vs 600519.SH) cause wrong analysis. Confirm with user before running. |
| "This looks like a strong buy signal" | You are NOT an investment advisor. Always add disclaimers about data latency, hallucination risk, and non-advice. |

## When to Use

Use this skill when the user asks to:

- Analyze a stock/ticker with TradingAgents.
- Set up or troubleshoot `TauricResearch/TradingAgents`.
- Compare multi-agent financial analysis results across tickers or dates.
- Generate a Chinese or English research summary from a TradingAgents run.
- Save a local Markdown report of a TradingAgents decision.

Do **not** use this skill for:

- Real-time trading execution or broker account actions.
- Financial advice that requires a licensed professional.
- Simple current price lookup; use a direct market-data source instead.
- Crypto/prediction-market research unless the user explicitly wants to adapt TradingAgents beyond its stock-analysis assumptions.

## Mental Model

Treat TradingAgents as a heavyweight research pipeline:

1. Data tools collect stock, market, news, social, and fundamentals information.
2. Analyst agents form domain-specific views.
3. Bull/bear researchers debate.
4. A trader agent synthesizes a decision.
5. Risk managers discuss the trade.
6. Final output is written to memory/log/results paths depending on config.

A single run can trigger many LLM calls and external data requests. Always choose a lightweight configuration first unless the user asks for deep analysis.

## Install / Update

Preferred local install path:

```bash
mkdir -p ~/projects
cd ~/projects
if [ ! -d TradingAgents ]; then
  git clone https://github.com/TauricResearch/TradingAgents.git
fi
cd TradingAgents
git pull --ff-only
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -e .
```

If `uv` is unavailable:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Verify import:

```bash
cd ~/projects/TradingAgents
source .venv/bin/activate
python - <<'PY'
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
print('TradingAgents import OK')
print('default provider:', DEFAULT_CONFIG.get('llm_provider'))
PY
```

## API Keys and Secrets

Put API keys in environment variables, not in the skill and not in committed files. If running from Hermes, prefer `~/.hermes/.env` plus normal shell export/loading patterns.

Common LLM keys supported by upstream TradingAgents include:

```bash
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
XAI_API_KEY
DEEPSEEK_API_KEY
DASHSCOPE_API_KEY
DASHSCOPE_CN_API_KEY
ZHIPU_API_KEY
ZHIPU_CN_API_KEY
MINIMAX_API_KEY
MINIMAX_CN_API_KEY
OPENROUTER_API_KEY
```

Market-data/news keys may include:

```bash
ALPHA_VANTAGE_API_KEY
FINNHUB_API_KEY
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
```

Not every run requires every key. Start with the key for the selected LLM provider and the default free data path. Add Alpha Vantage or other vendor keys only when the data route requires them.

Before running, check only for the keys needed by the selected provider:

```bash
printenv OPENROUTER_API_KEY >/dev/null && echo 'OpenRouter key present'
printenv OPENAI_API_KEY >/dev/null && echo 'OpenAI key present'
printenv ANTHROPIC_API_KEY >/dev/null && echo 'Anthropic key present'
```

## Non-Interactive Run Pattern

The upstream CLI can be interactive. For Telegram/gateway use, prefer a non-interactive Python wrapper that accepts ticker/date/provider/model values and prints a compact result.

Minimal wrapper:

```python
from pathlib import Path
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

TICKER = "NVDA"
DATE = "2026-01-15"

config = DEFAULT_CONFIG.copy()
config.update({
    "llm_provider": "openrouter",
    "deep_think_llm": "anthropic/claude-sonnet-4",
    "quick_think_llm": "openai/gpt-4o-mini",
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "output_language": "Chinese",
    "results_dir": str(Path.home() / ".tradingagents" / "results"),
    "data_cache_dir": str(Path.home() / ".tradingagents" / "cache"),
})

selected_analysts = ["market", "news", "fundamentals"]
ta = TradingAgentsGraph(selected_analysts, config=config, debug=True)
state, decision = ta.propagate(TICKER, DATE)

print("=== DECISION ===")
print(decision)
```

Run it from the TradingAgents repo venv:

```bash
cd ~/projects/TradingAgents
source .venv/bin/activate
python /path/to/run_tradingagents_once.py
```

## Recommended Defaults

For first runs or Telegram requests, use a cost-controlled setup:

- Analysts: `market`, `news`, `fundamentals`
- Debate rounds: `1`
- Risk discussion rounds: `1`
- Output language: match the user's language; Chinese for Chinese requests.
- Provider: reuse the user's already-configured low-cost provider when possible.
- Ticker/date: ask only if missing; otherwise infer obvious ticker symbols from the user request.

Avoid defaulting to the deepest settings. Deep debate can be slow and expensive.

## A-Share / China Market Support

Upstream TradingAgents is primarily wired for Yahoo Finance (`yfinance`) and Alpha Vantage data vendors. The inspected data routing layer exposes only `yfinance` and `alpha_vantage` vendors; it does not include native `akshare`, `tushare`, Eastmoney, Sina, or Wind-style A-share data adapters.

Practical implication:

- A-share tickers may work partially if Yahoo Finance supports the symbol format, e.g. `600519.SS` for Shanghai or `000001.SZ` for Shenzhen.
- Price/OHLCV data is the most likely to work through yfinance.
- Fundamentals, China-language news, insider transactions, and market-specific context are likely incomplete or unreliable.
- For serious A-share research, augment TradingAgents with a separate Chinese market data layer such as AKShare/Tushare, then feed the fetched facts into the final Hermes summary or a custom wrapper.

When the user asks for A-share analysis, state this limitation clearly and prefer a hybrid workflow: fetch A-share data separately, run TradingAgents only where its tools can resolve the ticker, then combine outputs with Chinese-market-specific sources.

Useful open-source references for improving A-share support:

- `hsliuping/TradingAgents-CN`: closest architectural reference because it is a Chinese/A-share enhanced fork of TradingAgents. Study its `tradingagents/dataflows/providers/china/{akshare.py,tushare.py,baostock.py}` provider layer and data-source initialization scripts.
- `oujingzhou/openfr`: lightweight AKShare-based financial research agent. Good reference for minimal A-share tools, retries, TTL stock-list caching, multi-source fallback between Eastmoney/Sina/THS, and concise CLI design.
- `zwldarren/ashare-analyzer`: A-share multi-agent analyzer with a unified `DataManager`, provider fallback order (`efinance`, `akshare`, `tushare`, `baostock`, `yfinance`), rate limiters, chip distribution, and notification-oriented daily analysis.
- `ialak/daily_stock_analysis`: broader daily watchlist pipeline for A/H/US stocks with AkShare/Tushare/Pytdx/Baostock/YFinance, fundamentals aggregation, chip structure, market review, strategy Q&A, and multi-channel push.

Recommended enhancement order for Hermes/TradingAgents A-share use: first add a standalone A-share data prefetch wrapper using AKShare/eFinance, then add a TradingAgents-compatible provider adapter, and only then consider replacing or forking TradingAgents internals.

### A-Share Optimized Hermes Workflow

For A-share requests, prefer the bundled prefetch template before running TradingAgents:

```bash
# Copy the template somewhere executable, or run it directly from the skill directory.
python ~/.hermes/skills/research/tradingagents/templates/ashare_prefetch.py 600519 --days 90 --news-limit 8
python ~/.hermes/skills/research/tradingagents/templates/ashare_prefetch.py 贵州茅台 --days 120
```

If Chinese-name resolution fails, treat it as a possible user typo or informal name rather than a data failure. Search/resolve the intended A-share code, clearly state the assumption, and ask or rerun if there are plausible alternatives. Example: user says “东方精密”; the closest A-share match may be `东方精工 002611.SZ`, while `东山精密 002384.SZ` is a different plausible target. Label the assumed ticker in the report.

Dependencies:

```bash
uv pip install akshare pandas
uv pip install efinance  # optional Eastmoney-based fallback
uv pip install baostock yfinance  # optional non-Eastmoney historical fallbacks
```

Current tested fallback behavior on this macOS Hermes install: Eastmoney `clist` and `push2his` endpoints may disconnect consistently, while Tencent quote (`qt.gtimg.cn`) and BaoStock history work for `688256`. The prefetch template now falls back in this order: realtime `akshare.stock_zh_a_spot_em` → `efinance.stock.get_quote_history` → Tencent quote; history `akshare.stock_zh_a_hist` → efinance → BaoStock pre-adjusted history → Sina KLine → yfinance. Prefer BaoStock before Sina because Sina/Tencent unadjusted history can distort technical indicators around ex-right/dividend events.

The prefetcher writes both JSON and Markdown under:

```text
~/.tradingagents/ashare_context/
```

For maintenance quirks around AKShare version differences, noisy progress bars, and money-flow market parameters, see `references/ashare-prefetch-akshare-quirks.md`.

For user requests like “寒武纪详细报告” or “我要详细报告”, follow the saved-report workflow and concise-chat style in `references/a-share-detailed-report-format.md`: generate the depth in a Markdown report, then lead the Telegram reply with a short conclusion, 3–6 key judgments, and the report path.

It collects, when available:

- A-share code/name resolution from AKShare.
- Yahoo-compatible suffix hint such as `600519.SS` or `300750.SZ`.
- Real-time quote with AKShare/eFinance fallback.
- Recent historical OHLCV.
- Derived technical summary: latest close, 5/20-day return, MA5/10/20/60, 60-day price position, volume ratio.
- Eastmoney news via AKShare.
- Financial indicator snippets.
- Fund-flow snippets.
- Recent money-flow snippets, using exchange-aware `sh`/`sz` market parameters.
- Automatic analysis hints for trend, high-position risk, volume expansion, and large-order divergence.
- Data-quality metadata, including hard error count, transient network warning count, and whether stale-but-recent cached fields were reused.
- Cached symbol resolution when the live A-share name/code list is temporarily unavailable.
- Collection warnings/errors and fallback notes.

### A-share symbol/name ambiguity pitfalls

- If the user gives a fuzzy or slightly wrong Chinese name and `ashare_prefetch.py` cannot resolve it (e.g. user says `东方精密`, but the intended A-share may be `东方精工 002611` or `东山精密 002384`), do **not** silently pick a stock. Search/resolve the likely code, state the ambiguity clearly, and, if proceeding with the closest match, label it at the top of the report and offer to rerun for the alternate ticker.
- Prefer code-based reruns after disambiguation: once a likely code is found, run `ashare_prefetch.py <code> --days ...` instead of retrying the fuzzy name.
- Be careful with news fetched by numeric code only: A-share code strings can appear as ETF share-class codes or unrelated identifiers. Filter/weight news by whether the title/content mentions the company name; call out irrelevant-code matches rather than treating them as company news.

Use the generated Markdown/JSON as grounded context for Hermes summaries. If running TradingAgents afterward, still keep the A-share context in the final report because upstream TradingAgents may miss China-specific data. Public A-share endpoints are flaky behind some proxies; if a live endpoint fails, the prefetcher may reuse the newest prior JSON for missing fields and mark this in `data_quality.fallback_from_cache`. Transient proxy/time-out failures are classified as `severity: warning`, so `errors_count` only reflects non-network hard failures.

## CLI Usage

If the user is at a terminal and wants the interactive UI, run:

```bash
cd ~/projects/TradingAgents
source .venv/bin/activate
tradingagents analyze
```

For automated Hermes runs, avoid interactive prompts. If the upstream CLI supports flags in the installed version, inspect them first:

```bash
tradingagents analyze --help
```

If flags are insufficient, use the Python API wrapper instead.

## Report Handling

After a run, save a stable report under a timestamped path, for example:

```text
~/.tradingagents/reports/YYYYMMDD-HHMMSS-TICKER.md
```

The report should include:

- Ticker and analysis date.
- TradingAgents repo/version or git commit if available.
- Provider/model configuration.
- Selected analysts.
- Final decision exactly as returned by TradingAgents.
- Hermes summary and risk notes.
- Data/source limitations.

When replying to the user, send a compact summary first and include the local report path.

## Summary Template

Use this structure for final user-facing summaries:

```markdown
## TradingAgents 分析摘要

- 标的: TICKER
- 分析日期: YYYY-MM-DD
- 配置: provider / deep model / quick model
- 分析师: market, news, fundamentals
- 最终倾向: BUY / HOLD / SELL / unclear

## 核心理由
- ...
- ...
- ...

## 主要风险
- ...
- ...

## 数据限制
- ...

完整报告: /path/to/report.md

提醒：这不是投资建议，不能直接作为实盘交易依据。
```

## Troubleshooting

### Import fails

Make sure the command is running inside the repo venv and package is installed editable:

```bash
cd ~/projects/TradingAgents
source .venv/bin/activate
uv pip install -e .
python -c "import tradingagents; print(tradingagents.__file__)"
```

### Missing API key

Read the traceback to identify the provider. Add the matching environment variable. Do not paste secrets into chat if avoidable; ask the user to edit `~/.hermes/.env` or their shell profile.

### Data vendor errors

If yfinance returns empty data or rate-limits, retry later or configure an alternate vendor such as Alpha Vantage if supported by the current upstream version. Document the limitation in the final report.

### Run takes too long

Reduce:

- Analyst count.
- `max_debate_rounds`.
- `max_risk_discuss_rounds`.
- News article limit.
- Deep model size.

For long runs, use a background process with completion notification rather than blocking the main session.

### Interactive CLI hangs in Telegram

Stop the process and switch to the Python API wrapper. Interactive CLIs are poor fits for gateway sessions.

### Output is too verbose

Do not paste the entire trace into Telegram. Save the full output to a report file and summarize the decision, rationale, risk, and limitations.

## Safety Rules

- Never place orders or execute trades.
- Never claim the output is investment advice.
- Always mention data latency and LLM hallucination risk.
- Prefer `HOLD/unclear` wording if the decision is ambiguous.
- Preserve the raw final decision in the report before summarizing.
- Do not hide model/provider costs; warn before deep multi-round runs.

## Verification Checklist

- [ ] TradingAgents repo/package exists and imports successfully.
- [ ] Required provider API key is present.
- [ ] Ticker and date are explicit or reasonably inferred.
- [ ] Cost-controlled config is used unless the user requested deep analysis.
- [ ] Run completed without unhandled traceback.
- [ ] Full output/report is saved locally.
- [ ] User-facing summary includes decision, rationale, risks, data limitations, and non-investment-advice disclaimer.

---

## Deployment & Sync

After ANY update to this SKILL.md:
1. Sync to ALL Hermes profiles (dynamic discovery):
   ```bash
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/research/tradingagents
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/tradingagents-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/research/tradingagents "$dst"
   done
   ```
2. `qmd update`
