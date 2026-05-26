#!/usr/bin/env python3
"""A-share data prefetcher for Hermes + TradingAgents.

This script collects China A-share context before running TradingAgents.
It intentionally avoids trading actions. It writes JSON + Markdown reports under
~/.tradingagents/ashare_context/ so Hermes can summarize the facts or feed them
into a TradingAgents run as external context.

Dependencies:
  uv pip install akshare pandas
Optional fallback:
  uv pip install efinance

Examples:
  python ashare_prefetch.py 600519
  python ashare_prefetch.py 贵州茅台 --days 120 --news-limit 8
  python ashare_prefetch.py 300750 --out-dir ~/.tradingagents/ashare_context
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

# Suppress noisy progress bars from some data libraries during Telegram/gateway runs.
os.environ.setdefault("TQDM_DISABLE", "1")

try:
    import pandas as pd
except Exception as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: pandas. Install with: uv pip install pandas") from exc


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return str(obj)


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _records(df: pd.DataFrame | None, limit: int | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    out = df.copy()
    if limit is not None:
        out = out.head(limit)
    out = out.where(pd.notna(out), None)
    return [{str(k): _clean_value(v) for k, v in row.items()} for row in out.to_dict("records")]


def _is_transient_network_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    needles = [
        "ProxyError",
        "ConnectTimeout",
        "ReadTimeout",
        "ConnectionError",
        "RemoteDisconnected",
        "Max retries exceeded",
        "timed out",
        "NameResolutionError",
    ]
    return any(needle in text for needle in needles)


def _compact_error(exc: Exception, max_len: int = 360) -> str:
    text = f"{type(exc).__name__}: {exc}"
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _run_step(name: str, fn: Callable[[], Any], errors: list[dict[str, str]], delay: float = 0.4) -> Any:
    try:
        result = fn()
        if delay:
            time.sleep(delay)
        return result
    except Exception as exc:
        # Public A-share endpoints are flaky. Network/proxy failures are expected
        # and should not look like fatal analysis errors when cache/fallback data
        # can cover the missing field.
        issue = {
            "step": name,
            "severity": "warning" if _is_transient_network_error(exc) else "error",
            "error": _compact_error(exc),
        }
        errors.append(issue)
        return None


def _normalize_code(query: str) -> str:
    digits = re.sub(r"\D", "", query)
    if len(digits) >= 6:
        return digits[-6:]
    return query.strip()


def _infer_exchange_suffix(code: str) -> str:
    if code.startswith(("6", "9")):
        return f"{code}.SS"
    if code.startswith(("0", "2", "3")):
        return f"{code}.SZ"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    return code


def _market_prefix(code: str) -> str:
    return "sh" if code.startswith(("6", "9")) else "sz" if code.startswith(("0", "2", "3")) else "bj"


def _http_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.sina.com.cn/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def _tencent_quote(code: str) -> dict[str, Any] | None:
    """Realtime fallback independent of Eastmoney: qt.gtimg.cn."""
    symbol = f"{_market_prefix(code)}{code}"
    text = _http_text(f"https://qt.gtimg.cn/q={symbol}")
    if "=\"" not in text:
        return None
    fields = text.split('="', 1)[1].strip().rstrip('";').split("~")
    if len(fields) < 40:
        return None
    # Tencent's quote format is positional. Common fields:
    # 1 name, 2 code, 3 current, 4 preclose, 5 open, 30 timestamp,
    # 31 change, 32 pct, 33 high, 34 low, 36 volume(shares), 37 amount(10k CNY), 38 turnover.
    return {
        "股票名称": fields[1],
        "股票代码": fields[2],
        "日期时间": fields[30],
        "开盘": float(fields[5]) if fields[5] else None,
        "收盘": float(fields[3]) if fields[3] else None,
        "昨收": float(fields[4]) if fields[4] else None,
        "最高": float(fields[33]) if fields[33] else None,
        "最低": float(fields[34]) if fields[34] else None,
        "成交量": int(float(fields[36])) if fields[36] else None,
        "成交额": float(fields[37]) * 10000 if fields[37] else None,
        "涨跌幅": float(fields[32]) if fields[32] else None,
        "涨跌额": float(fields[31]) if fields[31] else None,
        "换手率": float(fields[38]) if fields[38] else None,
    }


def _sina_kline(code: str, count: int) -> pd.DataFrame | None:
    """Historical daily fallback independent of Eastmoney: Sina KLine API."""
    symbol = f"{_market_prefix(code)}{code}"
    url = (
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={max(count, 90)}"
    )
    data = json.loads(_http_text(url))
    if not data:
        return None
    df = pd.DataFrame(data)
    if df.empty:
        return None
    rename = {"day": "日期", "open": "开盘", "high": "最高", "low": "最低", "close": "收盘", "volume": "成交量"}
    df = df.rename(columns=rename)
    for col in ["开盘", "最高", "最低", "收盘", "成交量"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.tail(count)


def _baostock_history(code: str, start: dt.date, end: dt.date) -> pd.DataFrame | None:
    """Historical daily fallback with valuation fields. No API key required."""
    import baostock as bs
    lg = bs.login()
    try:
        if getattr(lg, "error_code", "0") != "0":
            return None
        symbol = f"{_market_prefix(code)}.{code}"
        rs = bs.query_history_k_data_plus(
            symbol,
            "date,code,open,high,low,close,volume,amount,pctChg,turn,peTTM,pbMRQ",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            frequency="d",
            adjustflag="2",
        )
        df = rs.get_data()
    finally:
        try:
            bs.logout()
        except Exception:
            pass
    if df is None or df.empty:
        return None
    df = df.rename(columns={
        "date": "日期", "open": "开盘", "high": "最高", "low": "最低", "close": "收盘",
        "volume": "成交量", "amount": "成交额", "pctChg": "涨跌幅", "turn": "换手率",
    })
    for col in ["开盘", "最高", "最低", "收盘", "成交量", "成交额", "涨跌幅", "换手率", "peTTM", "pbMRQ"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _yfinance_history(code: str, days: int) -> pd.DataFrame | None:
    import yfinance as yf
    ticker = _infer_exchange_suffix(code)
    df = yf.Ticker(ticker).history(period="6mo" if days <= 120 else "1y")
    if df is None or df.empty:
        return None
    df = df.reset_index()
    df["日期"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"Open": "开盘", "High": "最高", "Low": "最低", "Close": "收盘", "Volume": "成交量"})
    return df[[c for c in ["日期", "开盘", "最高", "最低", "收盘", "成交量"] if c in df.columns]].tail(days)


def _import_akshare():
    try:
        import akshare as ak
        return ak
    except Exception as exc:
        raise SystemExit("Missing dependency: akshare. Install with: uv pip install akshare") from exc


def _try_import_efinance():
    try:
        import efinance as ef
        return ef
    except Exception:
        return None


def resolve_symbol(ak: Any, query: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    raw = query.strip()
    code = _normalize_code(raw)
    info = {
        "input": raw,
        "code": code if re.fullmatch(r"\d{6}", code) else None,
        "name": None,
        "yfinance_symbol": None,
        "matched_by": "code" if re.fullmatch(r"\d{6}", code) else None,
    }
    if info["code"]:
        info["yfinance_symbol"] = _infer_exchange_suffix(info["code"])

    stock_list = _run_step("stock_info_a_code_name", lambda: ak.stock_info_a_code_name(), errors)
    if stock_list is None or stock_list.empty:
        return info

    df = stock_list.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename_map = {"证券代码": "code", "A股代码": "code", "代码": "code", "证券简称": "name", "A股简称": "name", "名称": "name"}
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    if "code" not in df.columns and len(df.columns) >= 1:
        df = df.rename(columns={df.columns[0]: "code"})
    if "name" not in df.columns and len(df.columns) >= 2:
        df = df.rename(columns={df.columns[1]: "name"})
    if "code" in df.columns:
        df["code"] = df["code"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(6)
    if "name" in df.columns:
        df["name"] = df["name"].astype(str)

    if info["code"] and {"code", "name"}.issubset(df.columns):
        hit = df[df["code"] == info["code"]]
        if not hit.empty:
            info["name"] = str(hit.iloc[0]["name"])
            return info

    if {"code", "name"}.issubset(df.columns):
        exact = df[df["name"] == raw]
        contains = df[df["name"].str.contains(re.escape(raw), na=False)] if raw else pd.DataFrame()
        hit = exact if not exact.empty else contains
        if not hit.empty:
            row = hit.iloc[0]
            info.update({
                "code": str(row["code"]),
                "name": str(row["name"]),
                "yfinance_symbol": _infer_exchange_suffix(str(row["code"])),
                "matched_by": "name" if not exact.empty else "fuzzy_name",
            })
    return info


def resolve_symbol_from_cache(out_dir: Path, query: str) -> dict[str, Any] | None:
    raw = query.strip()
    normalized = _normalize_code(raw)
    for path in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        symbol = payload.get("symbol") or {}
        code = str(symbol.get("code") or "")
        name = str(symbol.get("name") or "")
        prior_input = str(symbol.get("input") or "")
        if normalized == code or raw in {name, prior_input} or (raw and raw in name):
            if code:
                symbol.setdefault("yfinance_symbol", _infer_exchange_suffix(code))
                symbol["matched_by"] = f"cache_{symbol.get('matched_by') or 'symbol'}"
                return symbol
    return None


def fetch_realtime(ak: Any, ef: Any, code: str, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    def via_ak_em() -> dict[str, Any] | None:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return None
        code_cols = [c for c in df.columns if str(c) in {"代码", "code", "symbol"}]
        col = code_cols[0] if code_cols else df.columns[1]
        hit = df[df[col].astype(str).str.zfill(6) == code]
        if hit.empty:
            return None
        return {"source": "akshare.stock_zh_a_spot_em", "data": _records(hit, 1)[0]}

    result = _run_step("realtime_akshare_em", via_ak_em, errors)
    if result:
        return result

    def via_efinance() -> dict[str, Any] | None:
        if ef is None:
            return None
        quote = ef.stock.get_quote_history(code, klt=101)
        if quote is None or quote.empty:
            return None
        return {"source": "efinance.stock.get_quote_history", "data": _records(quote.tail(1), 1)[0]}

    result = _run_step("realtime_efinance", via_efinance, errors)
    if result:
        return result

    def via_tencent() -> dict[str, Any] | None:
        quote = _tencent_quote(code)
        return {"source": "tencent.qt.gtimg", "data": quote} if quote else None

    return _run_step("realtime_tencent_qt_gtimg", via_tencent, errors)


def fetch_history(ak: Any, ef: Any, code: str, days: int, errors: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str | None]:
    end = dt.date.today()
    start = end - dt.timedelta(days=max(days * 2, days + 30))

    def via_ak() -> pd.DataFrame | None:
        return ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"), adjust="qfq")

    df = _run_step("history_akshare_stock_zh_a_hist", via_ak, errors)
    source = "akshare.stock_zh_a_hist"
    if df is None or df.empty:
        def via_ef() -> pd.DataFrame | None:
            if ef is None:
                return None
            return ef.stock.get_quote_history(code, beg=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d"), klt=101, fqt=1)
        df = _run_step("history_efinance", via_ef, errors)
        source = "efinance.stock.get_quote_history" if df is not None and not df.empty else None
    if df is None or df.empty:
        df = _run_step("history_baostock", lambda: _baostock_history(code, start, end), errors)
        source = "baostock.query_history_k_data_plus" if df is not None and not df.empty else None
    if df is None or df.empty:
        df = _run_step("history_sina_kline", lambda: _sina_kline(code, days), errors)
        source = "sina.CN_MarketData.getKLineData" if df is not None and not df.empty else None
    if df is None or df.empty:
        df = _run_step("history_yfinance", lambda: _yfinance_history(code, days), errors)
        source = "yfinance" if df is not None and not df.empty else None
    if df is None or df.empty:
        return [], source
    return _records(df.tail(days)), source


def calculate_technicals(history: list[dict[str, Any]]) -> dict[str, Any]:
    if not history:
        return {}
    df = pd.DataFrame(history)
    close_col = next((c for c in ["收盘", "close", "最新价", "收盘价"] if c in df.columns), None)
    high_col = next((c for c in ["最高", "high", "最高价"] if c in df.columns), None)
    low_col = next((c for c in ["最低", "low", "最低价"] if c in df.columns), None)
    vol_col = next((c for c in ["成交量", "volume", "成交量(手)"] if c in df.columns), None)
    if not close_col:
        return {}
    close = pd.to_numeric(df[close_col], errors="coerce")
    tech: dict[str, Any] = {
        "latest_close": _clean_value(close.iloc[-1]) if not close.empty else None,
        "return_5d_pct": _clean_value((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close.dropna()) >= 6 else None,
        "return_20d_pct": _clean_value((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close.dropna()) >= 21 else None,
        "ma5": _clean_value(close.rolling(5).mean().iloc[-1]) if len(close.dropna()) >= 5 else None,
        "ma10": _clean_value(close.rolling(10).mean().iloc[-1]) if len(close.dropna()) >= 10 else None,
        "ma20": _clean_value(close.rolling(20).mean().iloc[-1]) if len(close.dropna()) >= 20 else None,
        "ma60": _clean_value(close.rolling(60).mean().iloc[-1]) if len(close.dropna()) >= 60 else None,
    }
    if high_col and low_col:
        high = pd.to_numeric(df[high_col], errors="coerce")
        low = pd.to_numeric(df[low_col], errors="coerce")
        tech["position_60d_pct"] = _clean_value((close.iloc[-1] - low.tail(60).min()) / (high.tail(60).max() - low.tail(60).min()) * 100) if len(close.dropna()) >= 20 and high.tail(60).max() != low.tail(60).min() else None
    if vol_col:
        vol = pd.to_numeric(df[vol_col], errors="coerce")
        tech["volume_ratio_vs_20d"] = _clean_value(vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]) if len(vol.dropna()) >= 20 and vol.rolling(20).mean().iloc[-1] else None
    return tech


def fetch_news(ak: Any, code: str, limit: int, errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    def via_ak() -> pd.DataFrame | None:
        return ak.stock_news_em(symbol=code)
    df = _run_step("news_akshare_stock_news_em", via_ak, errors)
    if df is None or df.empty:
        return []
    return _records(df, limit)


def fetch_financials(ak: Any, code: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    indicator = _run_step("financial_indicator", lambda: ak.stock_financial_analysis_indicator(symbol=code), errors)
    if indicator is not None and not indicator.empty:
        out["financial_analysis_indicator"] = _records(indicator.tail(8))
    # Some AKShare versions removed/renamed stock_a_lg_indicator; call it only when present.
    if hasattr(ak, "stock_a_lg_indicator"):
        lg = _run_step("lg_indicator", lambda: ak.stock_a_lg_indicator(symbol=code), errors)
        if lg is not None and not lg.empty:
            out["lg_indicator"] = _records(lg.tail(8))
    return out


def fetch_moneyflow(ak: Any, code: str, errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    market = "sh" if code.startswith(("6", "9")) else "sz" if code.startswith(("0", "2", "3")) else "bj"
    candidates = [
        ("stock_individual_fund_flow", lambda: ak.stock_individual_fund_flow(stock=code, market=market)),
        ("stock_main_fund_flow", lambda: ak.stock_main_fund_flow(symbol="全部股票")),
    ]
    for name, fn in candidates:
        df = _run_step(f"moneyflow_{name}", fn, errors)
        if df is not None and not df.empty:
            if name == "stock_main_fund_flow":
                code_col = next((c for c in df.columns if "代码" in str(c)), None)
                if code_col:
                    df = df[df[code_col].astype(str).str.zfill(6) == code]
            if not df.empty:
                return _records(df.tail(10))
    return []


def load_latest_cache(out_dir: Path, code: str, exclude: Path | None = None) -> dict[str, Any] | None:
    """Load the best recent prior payload for this code.

    A-share public endpoints are often flaky behind proxies. Cache fallback keeps
    Telegram analysis usable by reusing recent successful price/technical data
    while explicitly flagging that fallback in data_quality. Prefer payloads that
    actually contain price/technical fields over newer error-only payloads.
    """
    scored: list[tuple[int, float, dict[str, Any]]] = []
    for path in out_dir.glob(f"*-{code}.json"):
        if exclude is not None and path == exclude:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        score = 0
        for key, weight in [("realtime", 3), ("technicals", 4), ("history_tail", 2), ("moneyflow", 2), ("financials", 1)]:
            if payload.get(key) not in (None, {}, []):
                score += weight
        scored.append((score, path.stat().st_mtime, payload))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2] if scored[0][0] > 0 else None


def enrich_payload(payload: dict[str, Any], cached: dict[str, Any] | None = None) -> None:
    fallback_fields: list[str] = []
    if cached:
        for key in ["realtime", "history_source", "history_tail", "technicals", "financials", "moneyflow"]:
            current = payload.get(key)
            cached_value = cached.get(key)
            if (current is None or current == {} or current == []) and cached_value not in (None, {}, []):
                payload[key] = cached_value
                fallback_fields.append(key)

    tech = payload.get("technicals") or {}
    hints: list[str] = []
    latest = tech.get("latest_close")
    ma5, ma10, ma20, ma60 = tech.get("ma5"), tech.get("ma10"), tech.get("ma20"), tech.get("ma60")
    pos60 = tech.get("position_60d_pct")
    ret20 = tech.get("return_20d_pct")
    vol_ratio = tech.get("volume_ratio_vs_20d")
    try:
        if latest and ma20 and latest > ma20:
            hints.append("价格位于 MA20 上方，中期趋势偏强")
        if latest and ma5 and latest < ma5:
            hints.append("价格低于 MA5，短线动能有降温迹象")
        if latest and ma10 and latest < ma10:
            hints.append("价格跌破 MA10，短线需关注趋势延续性")
        if latest and ma60 and latest > ma60:
            hints.append("价格仍在 MA60 上方，长期趋势未明显破坏")
        if isinstance(pos60, (int, float)) and pos60 >= 75:
            hints.append("处于近 60 日高位区，追高风险上升")
        if isinstance(ret20, (int, float)) and ret20 >= 30:
            hints.append("近 20 日涨幅较大，存在获利盘兑现压力")
        if isinstance(vol_ratio, (int, float)) and vol_ratio >= 1.2:
            hints.append("成交量高于 20 日均量，资金分歧/关注度提升")
    except Exception:
        pass

    moneyflow = payload.get("moneyflow") or []
    if moneyflow:
        last_flow = moneyflow[-1]
        main = last_flow.get("主力净流入-净额")
        super_large = last_flow.get("超大单净流入-净额")
        if isinstance(main, (int, float)):
            hints.append("最近一日主力净流入为正" if main > 0 else "最近一日主力净流入为负")
        if isinstance(super_large, (int, float)) and super_large < 0:
            hints.append("最近一日超大单净流出，需警惕高位分歧")

    payload["analysis_hints"] = list(dict.fromkeys(hints))
    hard_errors = [item for item in payload.get("errors") or [] if item.get("severity") != "warning"]
    warnings = [item for item in payload.get("errors") or [] if item.get("severity") == "warning"]
    payload["data_quality"] = {
        "fallback_from_cache": bool(fallback_fields),
        "fallback_fields": fallback_fields,
        "errors_count": len(hard_errors),
        "warnings_count": len(warnings),
        "has_realtime": bool(payload.get("realtime")),
        "has_technicals": bool(payload.get("technicals")),
        "has_news": bool(payload.get("news")),
        "has_moneyflow": bool(payload.get("moneyflow")),
    }


def build_markdown(payload: dict[str, Any]) -> str:
    symbol = payload["symbol"]
    md: list[str] = [
        f"# A股上下文预取报告: {symbol.get('name') or ''} {symbol.get('code') or symbol.get('input')}",
        "",
        f"- 生成时间: {payload['generated_at']}",
        f"- 输入: {symbol.get('input')}",
        f"- 代码: {symbol.get('code')}",
        f"- 名称: {symbol.get('name')}",
        f"- Yahoo 兼容代码: {symbol.get('yfinance_symbol')}",
        "",
        "## 数据质量",
        "",
        "```json",
        json.dumps(payload.get('data_quality'), ensure_ascii=False, indent=2, default=_json_default),
        "```",
        "",
        "## 自动分析提示",
        "",
    ]
    for hint in payload.get("analysis_hints", []):
        md.append(f"- {hint}")
    md += [
        "",
        "## 实时行情",
        "",
        f"数据源: {(payload.get('realtime') or {}).get('source')}",
        "",
        "```json",
        json.dumps((payload.get('realtime') or {}).get('data'), ensure_ascii=False, indent=2, default=_json_default),
        "```",
        "",
        "## 技术面摘要",
        "",
        "```json",
        json.dumps(payload.get('technicals'), ensure_ascii=False, indent=2, default=_json_default),
        "```",
        "",
        "## 近期新闻",
        "",
    ]
    for i, item in enumerate(payload.get("news", []), 1):
        title = item.get("新闻标题") or item.get("标题") or item.get("title") or str(item)[:80]
        url = item.get("新闻链接") or item.get("链接") or item.get("url") or ""
        date = item.get("发布时间") or item.get("日期") or item.get("date") or ""
        md.append(f"{i}. {date} {title} {url}")
    md += ["", "## 资金流", "", "```json", json.dumps(payload.get('moneyflow'), ensure_ascii=False, indent=2, default=_json_default), "```", "", "## 基本面片段", "", "```json", json.dumps(payload.get('financials'), ensure_ascii=False, indent=2, default=_json_default), "```"]
    if payload.get("errors"):
        md += ["", "## 采集警告 / 错误 / 降级记录", "", "```json", json.dumps(payload.get('errors'), ensure_ascii=False, indent=2), "```"]
    md += ["", "提醒：本报告仅为数据上下文，不构成投资建议。"]
    return "\n".join(md) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prefetch A-share context for TradingAgents/Hermes analysis.")
    parser.add_argument("query", help="A-share code or name, e.g. 600519 or 贵州茅台")
    parser.add_argument("--days", type=int, default=90, help="Historical trading rows to keep")
    parser.add_argument("--news-limit", type=int, default=8)
    parser.add_argument("--out-dir", default=str(Path.home() / ".tradingagents" / "ashare_context"))
    parser.add_argument("--json-only", action="store_true", help="Print only compact JSON metadata")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ak = _import_akshare()
    ef = _try_import_efinance()
    errors: list[dict[str, str]] = []

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    symbol = resolve_symbol(ak, args.query, errors)
    code = symbol.get("code")
    if not code:
        cached_symbol = resolve_symbol_from_cache(out_dir, args.query)
        if cached_symbol:
            symbol = cached_symbol
            code = symbol.get("code")
            errors.append({
                "step": "resolve_symbol_cache",
                "severity": "warning",
                "error": "Live A-share symbol list unavailable; resolved symbol from local cache.",
            })
    if not code:
        raise SystemExit(f"Could not resolve A-share code from query: {args.query}")

    realtime = fetch_realtime(ak, ef, code, errors)
    history, history_source = fetch_history(ak, ef, code, args.days, errors)
    cached = load_latest_cache(out_dir, code)

    payload = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "symbol": symbol,
        "realtime": realtime,
        "history_source": history_source,
        "history_tail": history[-10:],
        "technicals": calculate_technicals(history),
        "news": fetch_news(ak, code, args.news_limit, errors),
        "financials": fetch_financials(ak, code, errors),
        "moneyflow": fetch_moneyflow(ak, code, errors),
        "errors": errors,
        "disclaimer": "Data context only; not investment advice.",
    }
    enrich_payload(payload, cached)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = out_dir / f"{stamp}-{code}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")

    hard_errors = [item for item in errors if item.get("severity") != "warning"]
    result = {
        "code": code,
        "name": symbol.get("name"),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "errors_count": len(hard_errors),
        "warnings_count": len(errors) - len(hard_errors),
        "data_quality": payload.get("data_quality"),
    }
    if args.json_only:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
