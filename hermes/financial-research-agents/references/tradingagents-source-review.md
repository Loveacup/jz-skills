# TradingAgents source review for Hermes skill wrapping

Repository: `TauricResearch/TradingAgents`
License observed during review: Apache-2.0
Framework type: multi-agent LLM stock/market research framework built around LangGraph-style graph orchestration.

## Fit assessment

TradingAgents is a good candidate for a **Hermes operating skill** and a poor candidate for direct source-code migration into a skill.

Use Hermes to install/configure/run/summarize it; do not copy its agent graph, analyst prompts, LLM provider layer, and dataflow code into Hermes.

## Source structure observed

Important files/directories:

- `tradingagents/default_config.py` — default config and environment-variable mapping.
- `tradingagents/graph/trading_graph.py` — main `TradingAgentsGraph` class.
- `tradingagents/graph/setup.py` — graph node setup.
- `tradingagents/agents/analysts/market_analyst.py` — representative analyst agent implementation.
- `tradingagents/agents/utils/agent_utils.py` and `core_stock_tools.py` — tool registration/utilities.
- `tradingagents/dataflows/interface.py` — vendor routing and fallback behavior, including yfinance / Alpha Vantage style sources.
- `tradingagents/llm_clients/factory.py` and provider clients such as `openai_client.py` — multi-provider LLM abstraction.
- `tradingagents/agents/utils/memory.py` — append-style markdown decision memory.
- `cli/main.py` — Typer + questionary + rich interactive CLI. The `analyze` command eventually calls a run path that builds `TradingAgentsGraph(...).propagate(ticker, date)` and writes reports.
- Top-level `main.py` — minimal Python example similar to `ta = TradingAgentsGraph(...); _, decision = ta.propagate("NVDA", "2024-05-10")`.

Approximate size from inspection:

- `tradingagents`: ~60 Python files / ~5.7k lines.
- `cli`: ~7 Python files / ~1.9k lines.
- `tests`: ~16 Python files / ~2.4k lines.

## Useful entrypoint

The stable integration shape is a Python API wrapper:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
# set provider/model/depth/output options here

ta = TradingAgentsGraph(
    selected_analyst_keys=["market", "news", "fundamentals"],
    config=config,
    debug=True,
)
final_state, decision = ta.propagate("NVDA", "2024-05-10")
```

Exact constructor arg names can drift upstream (`selected_analysts` vs `selected_analyst_keys`), so inspect the installed version before finalizing a wrapper.

## Why it fits as a Hermes skill

- Clear programmatic entrypoint: `TradingAgentsGraph(...).propagate(ticker, date)`.
- CLI is mostly a UI shell; the analysis path is callable from Python.
- Config-driven defaults make it possible to inject provider/model/depth settings.
- Multiple LLM providers can reuse user-owned API keys.
- Full reports can be saved to disk while Hermes returns a concise Telegram summary.

## Main integration risks

- **Dependency weight**: LangGraph/LangChain/data-science/trading dependencies should be isolated in the TradingAgents project venv, not Hermes's venv.
- **Runtime length**: full multi-agent debate can take minutes to tens of minutes. Prefer background execution or generous timeout.
- **Token cost**: defaults may use both deep and quick models and multiple debate/risk rounds. Default wrappers should use shallow depth unless user asks otherwise.
- **Data API availability**: yfinance may work as a fallback, while Alpha Vantage or other sources may require keys.
- **Large outputs**: reports can be lengthy; return summary + report path.
- **Financial safety**: always frame as research-only; do not automate trading.

## Recommended Hermes wrapper parameters

Expose:

- `ticker` — required.
- `date` — analysis date or latest supported date.
- `analysts` — subset such as `market`, `news`, `fundamentals`, `social`.
- `research_depth` / debate rounds — default low.
- `llm_provider` and model IDs.
- `output_language` — e.g. Chinese for this user.
- `report_dir` — where to save artifacts.

Return:

- final decision/signal if available.
- concise analyst-section summary.
- major risks and data limitations.
- full report path.
- research-only disclaimer.
