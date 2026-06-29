"""本地引擎 doctor 集成单测：run_doctor 覆盖 / tier 过滤 / CLI choices。"""
import asyncio
import os

import pytest
from unittest.mock import patch

from wrr.registry import default_registry
from wrr.doctor import run_doctor, summarize_checks


def run(coro):
    return asyncio.run(coro)


# ── run_doctor 覆盖本地引擎 ──────────────────────────────────────────
def test_doctor_includes_local_engines():
    reg = default_registry()
    names = {e.name for e in reg.doctor_targets()}
    assert {"local_supermemory", "local_session",
            "local_qmd", "local_obsidian"} <= names


def test_doctor_single_local_engine():
    reg = default_registry()
    with patch.dict(os.environ, {}, clear=True):
        results = run(run_doctor(reg, engine="local_supermemory"))
    assert len(results) == 1
    assert results[0].engine == "local_supermemory"
    assert results[0].status == "fail"            # 无 Hermes tool → fail


def test_doctor_tier2_filter_includes_qmd_obsidian():
    reg = default_registry()
    results = run(run_doctor(reg, tier=2))
    engines = {r.engine for r in results}
    assert "local_qmd" in engines
    assert "local_obsidian" in engines
    assert "local_supermemory" not in engines     # tier 1 被过滤掉


def test_doctor_tier1_filter_includes_hermes_engines():
    reg = default_registry()
    results = run(run_doctor(reg, tier=1))
    engines = {r.engine for r in results}
    assert "local_supermemory" in engines
    assert "local_session" in engines


def test_doctor_local_qmd_missing_binary_fail():
    reg = default_registry()
    with patch("shutil.which", return_value=None):
        results = run(run_doctor(reg, engine="local_qmd"))
    assert results[0].status == "fail"


def test_doctor_local_obsidian_no_vault_fail():
    reg = default_registry()
    with patch.dict(os.environ, {}, clear=True):
        results = run(run_doctor(reg, engine="local_obsidian"))
    assert results[0].status == "fail"


def test_doctor_summary_counts_local_fails():
    reg = default_registry()
    with patch.dict(os.environ, {}, clear=True):
        with patch("shutil.which", return_value=None):
            results = run(run_doctor(reg, tier=2))
    summary = summarize_checks(results)
    assert summary["fail"] >= 2                    # qmd + obsidian 至少各一 fail


def test_cli_choices_include_local_engines():
    """CLI parser 的 --provider 和 doctor --engine 都应含 4 个本地引擎。"""
    import importlib.util
    here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    spec = importlib.util.spec_from_file_location(
        "wrr_cli", os.path.join(here, "wrr-cli.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    parser = cli.build_parser()

    local = {"local_supermemory", "local_session", "local_qmd", "local_obsidian"}
    found_provider = set()
    found_engine = set()
    for action in parser._subparsers._group_actions[0].choices.values():
        for a in action._actions:
            if a.dest == "provider" and a.choices:
                found_provider |= set(a.choices)
            if a.dest == "engine" and a.choices:
                found_engine |= set(a.choices)
    assert local <= found_provider
    assert local <= found_engine
