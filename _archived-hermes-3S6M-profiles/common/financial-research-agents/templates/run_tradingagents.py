#!/usr/bin/env python3
"""Non-interactive TradingAgents wrapper template.

Copy this into an isolated TradingAgents checkout and adapt to the installed
version's exact constructor/config keys. Keep API keys in environment variables.
"""

import argparse
import json
from pathlib import Path
from datetime import date as date_cls

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def build_config(args):
    config = DEFAULT_CONFIG.copy()

    # Keep these keys version-tolerant: upstream config names can drift.
    if args.llm_provider:
        config["llm_provider"] = args.llm_provider
    if args.deep_model:
        config["deep_think_llm"] = args.deep_model
    if args.quick_model:
        config["quick_think_llm"] = args.quick_model

    # Cost-control defaults for messaging-platform runs.
    for key in ("max_debate_rounds", "max_risk_discuss_rounds", "max_recur_limit"):
        if key in config:
            config[key] = args.depth

    if args.output_language:
        config["output_language"] = args.output_language

    report_dir = Path(args.report_dir).expanduser().resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    for key in ("results_dir", "reports_dir", "output_dir"):
        if key in config:
            config[key] = str(report_dir)

    return config


def main():
    parser = argparse.ArgumentParser(description="Run TradingAgents non-interactively")
    parser.add_argument("ticker", help="Ticker symbol, e.g. NVDA")
    parser.add_argument("--date", default=date_cls.today().isoformat(), help="Analysis date YYYY-MM-DD")
    parser.add_argument("--analysts", default="market,news,fundamentals", help="Comma-separated analyst keys")
    parser.add_argument("--depth", type=int, default=1, help="Debate/risk depth; keep low by default")
    parser.add_argument("--llm-provider", default=None, help="TradingAgents provider name")
    parser.add_argument("--deep-model", default=None, help="Deep/research model ID")
    parser.add_argument("--quick-model", default=None, help="Quick/cheap model ID")
    parser.add_argument("--output-language", default="Chinese", help="Report language if supported")
    parser.add_argument("--report-dir", default="~/TradingAgents/reports", help="Where to save reports/artifacts")
    args = parser.parse_args()

    config = build_config(args)
    analysts = [x.strip() for x in args.analysts.split(",") if x.strip()]

    # Upstream versions may call this argument selected_analysts or selected_analyst_keys.
    try:
        graph = TradingAgentsGraph(selected_analyst_keys=analysts, config=config, debug=True)
    except TypeError:
        graph = TradingAgentsGraph(selected_analysts=analysts, config=config, debug=True)

    final_state, decision = graph.propagate(args.ticker.upper(), args.date)

    print(json.dumps({
        "ticker": args.ticker.upper(),
        "date": args.date,
        "analysts": analysts,
        "decision": decision,
        "report_dir": str(Path(args.report_dir).expanduser().resolve()),
        "disclaimer": "Research only; not investment advice.",
    }, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
