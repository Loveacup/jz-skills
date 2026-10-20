#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_verify_report_sparse.py — pytest tests for sparse mode in verify_report.py

Run:
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3.12 -m pytest -q \
      -p no:cacheprovider tests/test_verify_report_sparse.py
"""

import json
import os
import subprocess
import sys

import pytest

from verify_report import build_gates, evaluate

# ─── 路径常量 ────────────────────────────────────────────────────────────────

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "scripts", "verify_report.py")

# ─── Minimal sparse-passing Markdown ────────────────────────────────────────
#
# §3 insight: 1 × 💡 heading, body ≥ 20 CJK chars
# §4 module : 1 × 模块 1: heading, body ≥ 20 CJK chars
# §5        : 1 blockquote group
# §7        : 1 独特价值 bullet / 1 局限与偏见 bullet / 1 可行动项 bullet
# §1 lines  : 3 lines → ≤ 100 ✓

SPARSE_PASS_MD = """\
## 0. 元数据

短视频基本信息，92秒单段转录。

## 1. 逻辑链

主要内容直接来自转录文本。

## 2. 视频概述

视频简要描述。

## 3. 核心洞察

### 💡 洞察一：内容直接反映用户体验

这个内容用了超过二十个汉字进行描述让它能够超过最低门槛要求符合稀疏模式的洞察标准。

## 4. 内容深度拆解

### 模块 1: 主要功能模块

这个模块同样使用了超过二十个汉字进行描述让它能够超过最低词数门槛要求符合稀疏模式。

## 5. 高光时刻

> "这是一个高光引用段落，展示了视频核心内容。"

## 6. 知识图谱

基础知识节点

## 7. 批判与行动

### 独特价值

- 独特视角展示

### 局限与偏见

- 证据来源单一

### 可行动项

- 立即尝试该方法

## 8. 附录

相关资源链接
"""


# ─── Test 1: sparse passes ───────────────────────────────────────────────────

def test_sparse_pass_minimal_md():
    """A concise §0–§8 MD with 1 insight ≥20w, 1 module ≥20w, 1 quote, §7 1/1/1 passes sparse."""
    results, overall = evaluate(SPARSE_PASS_MD, 'sparse')
    failed = [g for g, r in results.items() if not r['pass']]
    assert overall, f"Expected sparse PASS but gates failed: {failed}\n{results}"


# ─── Test 2: same MD fails full and condensed ────────────────────────────────

def test_full_rejects_sparse_minimal_md():
    """The same minimal MD fails full (1 insight < 3 required)."""
    _results, overall = evaluate(SPARSE_PASS_MD, 'full')
    assert not overall, "Expected full FAIL for sparse-minimal MD"


def test_condensed_rejects_sparse_minimal_md():
    """The same minimal MD fails condensed (1 insight < 2 required)."""
    _results, overall = evaluate(SPARSE_PASS_MD, 'condensed')
    assert not overall, "Expected condensed FAIL for sparse-minimal MD"


# ─── Test 3: sparse fails on gate violations ────────────────────────────────

def _make_md(**replacements):
    md = SPARSE_PASS_MD
    for old, new in replacements.items():
        md = md.replace(old, new)
    return md


def test_sparse_fails_g3_insight_under_20_words():
    """G3 fails when §3 insight body has fewer than 20 words."""
    md = _make_md(**{
        "这个内容用了超过二十个汉字进行描述让它能够超过最低门槛要求符合稀疏模式的洞察标准。": "简短内容"
    })
    results, overall = evaluate(md, 'sparse')
    assert not overall, "Expected sparse FAIL when §3 insight body < 20 words"
    assert not results['G3']['pass'], f"Expected G3 FAIL, got: {results['G3']}"


def test_sparse_fails_g4_module_under_20_words():
    """G4 fails when §4 module body has fewer than 20 words."""
    md = _make_md(**{
        "这个模块同样使用了超过二十个汉字进行描述让它能够超过最低词数门槛要求符合稀疏模式。": "模块简述"
    })
    results, overall = evaluate(md, 'sparse')
    assert not overall, "Expected sparse FAIL when §4 module body < 20 words"
    assert not results['G4']['pass'], f"Expected G4 FAIL, got: {results['G4']}"


def test_sparse_fails_g5_absent():
    """G5 fails when §5 has no blockquote groups."""
    md = _make_md(**{
        '> "这是一个高光引用段落，展示了视频核心内容。"': "暂无高光引用内容"
    })
    results, overall = evaluate(md, 'sparse')
    assert not overall, "Expected sparse FAIL when §5 has no blockquotes"
    assert not results['G5']['pass'], f"Expected G5 FAIL, got: {results['G5']}"


def test_sparse_fails_g7_no_valid_bullets():
    """G7 fails when 独特价值 subsection has no bullet items."""
    md = _make_md(**{"- 独特视角展示": "独特价值暂无条目"})
    results, overall = evaluate(md, 'sparse')
    assert not overall, "Expected sparse FAIL when 独特价值 has 0 bullets"
    assert not results['G7']['pass'], f"Expected G7 FAIL, got: {results['G7']}"


def test_sparse_fails_g7_no_blind_bullets():
    """G7 fails when 局限与偏见 subsection has no bullet items."""
    md = _make_md(**{"- 证据来源单一": "局限暂无条目"})
    results, overall = evaluate(md, 'sparse')
    assert not overall, "Expected sparse FAIL when 局限与偏见 has 0 bullets"
    assert not results['G7']['pass'], f"Expected G7 FAIL, got: {results['G7']}"


def test_sparse_fails_g7_no_action_bullets():
    """G7 fails when 可行动项 subsection has no action items."""
    md = _make_md(**{"- 立即尝试该方法": "行动项暂无条目"})
    results, overall = evaluate(md, 'sparse')
    assert not overall, "Expected sparse FAIL when 可行动项 has 0 bullets"
    assert not results['G7']['pass'], f"Expected G7 FAIL, got: {results['G7']}"


# ─── Test 4: CLI --mode sparse --json ────────────────────────────────────────

def test_cli_sparse_json_pass(tmp_path):
    """CLI --mode sparse --json exits 0 and returns overall_pass=True for passing MD."""
    report = tmp_path / "sparse_report.md"
    report.write_text(SPARSE_PASS_MD, encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, SCRIPT, str(report), '--mode', 'sparse', '--json'],
        capture_output=True, text=True,
    )
    out = proc.stdout + proc.stderr

    assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}\n{out}"

    s = out.find("RESULT_JSON_START")
    e = out.find("RESULT_JSON_END")
    assert s != -1 and e != -1, f"Missing RESULT_JSON markers\n{out}"
    data = json.loads(out[s + len("RESULT_JSON_START"):e].strip())
    assert data['overall_pass'] is True, f"Expected overall_pass=True\n{data}"


def test_cli_sparse_json_fail(tmp_path):
    """CLI --mode sparse --json exits 1 and returns overall_pass=False for failing MD."""
    # Use MD with short insight body
    md = _make_md(**{
        "这个内容用了超过二十个汉字进行描述让它能够超过最低门槛要求符合稀疏模式的洞察标准。": "简短"
    })
    report = tmp_path / "sparse_fail.md"
    report.write_text(md, encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, SCRIPT, str(report), '--mode', 'sparse', '--json'],
        capture_output=True, text=True,
    )
    out = proc.stdout + proc.stderr

    assert proc.returncode == 1, f"Expected exit 1, got {proc.returncode}\n{out}"

    s = out.find("RESULT_JSON_START")
    e = out.find("RESULT_JSON_END")
    assert s != -1 and e != -1, f"Missing RESULT_JSON markers\n{out}"
    data = json.loads(out[s + len("RESULT_JSON_START"):e].strip())
    assert data['overall_pass'] is False, f"Expected overall_pass=False\n{data}"


def test_cli_depth_alias_sparse(tmp_path):
    """--depth sparse is accepted as alias for --mode sparse."""
    report = tmp_path / "sparse_report.md"
    report.write_text(SPARSE_PASS_MD, encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, SCRIPT, str(report), '--depth', 'sparse'],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"Expected exit 0 with --depth sparse\n{proc.stdout}{proc.stderr}"


# ─── Test 5: full and condensed gate dicts are byte-for-byte unchanged ───────

def test_full_gate_dict_unchanged():
    """build_gates('full') returns exactly the previously established values."""
    expected = {
        'min_insights': 3, 'insight_words': 200,
        'min_modules': 3, 'module_words': 500,
        'min_highlights': 5,
        'valid': 3, 'blind': 2, 'action': 3,
        'g1_max_lines': 100,
    }
    assert build_gates('full') == expected, (
        f"full gate dict changed!\ngot: {build_gates('full')}\nexpected: {expected}"
    )


def test_condensed_gate_dict_unchanged():
    """build_gates('condensed') returns exactly the previously established values."""
    expected = {
        'min_insights': 2, 'insight_words': 150,
        'min_modules': 2, 'module_words': None,
        'min_highlights': 2,
        'valid': 3, 'blind': 2, 'action': 3,
        'g1_max_lines': 100,
    }
    assert build_gates('condensed') == expected, (
        f"condensed gate dict changed!\ngot: {build_gates('condensed')}\nexpected: {expected}"
    )
