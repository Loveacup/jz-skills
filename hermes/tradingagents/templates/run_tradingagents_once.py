#!/usr/bin/env python3
"""Non-interactive TradingAgents runner template.

Usage from a TradingAgents checkout/venv:
  python run_tradingagents_once.py --ticker NVDA --date 2026-01-15 \
    --provider openrouter \
    --deep-model anthropic/claude-sonnet-4 \
    --quick-model openai/gpt-4o-mini \
    --language Chinese

This template intentionally never places trades. It only runs analysis and
writes a Markdown report under ~/.tradingagents/reports/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TradingAgents once without interactive prompts.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. NVDA")
    parser.add_argument("--date", required=True, help="Analysis date YYYY-MM-DD")
    parser.add_argument("--provider", default="openrouter", help="TradingAgents llm_provider")
    parser.add_argument("--deep-model", default="anthropic/claude-sonnet-4")
    parser.add_argument("--quick-model", default="openai/gpt-4o-mini")
    parser.add_argument("--analysts", default="market,news,fundamentals", help="Comma-separated analyst keys")
    parser.add_argument("--debate-rounds", type=int, default=1)
    parser.add_argument("--risk-rounds", type=int, default=1)
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--report-dir", default=str(Path.home() / ".tradingagents" / "reports"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ticker = args.ticker.upper().strip()
    analysts = [x.strip() for x in args.analysts.split(",") if x.strip()]

    config = DEFAULT_CONFIG.copy()
    config.update(
        {
            "llm_provider": args.provider,
            "deep_think_llm": args.deep_model,
            "quick_think_llm": args.quick_model,
            "max_debate_rounds": args.debate_rounds,
            "max_risk_discuss_rounds": args.risk_rounds,
            "output_language": args.language,
            "results_dir": str(Path.home() / ".tradingagents" / "results"),
            "data_cache_dir": str(Path.home() / ".tradingagents" / "cache"),
        }
    )

    ta = TradingAgentsGraph(analysts, config=config, debug=True)
    state, decision = ta.propagate(ticker, args.date)

    report_dir = Path(args.report_dir).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = report_dir / f"{stamp}-{ticker}.md"

    metadata = {
        "ticker": ticker,
        "date": args.date,
        "provider": args.provider,
        "deep_model": args.deep_model,
        "quick_model": args.quick_model,
        "analysts": analysts,
        "debate_rounds": args.debate_rounds,
        "risk_rounds": args.risk_rounds,
        "language": args.language,
    }

    report = "\n".join(
        [
            f"# TradingAgents Report: {ticker}",
            "",
            "## Metadata",
            "",
            "```json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Final Decision",
            "",
            str(decision),
            "",
            "## Safety Note",
            "",
            "This is AI-assisted research output, not investment advice. Do not use it as the sole basis for trading decisions.",
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8")

    print(json.dumps({"report_path": str(report_path), "metadata": metadata, "decision": str(decision)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
