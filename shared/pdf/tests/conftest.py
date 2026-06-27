"""Pytest configuration for the pdf skill tests.

- Makes `scripts/` importable regardless of CWD (import md2pdf_chrome / themes).
- Registers markers: integration (launches Chromium), network (fetches CDN).
- Environment gate: if the *current interpreter* lacks render deps, integration
  tests are skipped with a clear reason instead of failing on import — never
  silently xfail. Run the fast suite with `pytest -m "not integration"`.
"""

import sys
import importlib.util
from pathlib import Path

import pytest

# tests/ lives next to scripts/ under the skill root.
SCRIPTS_DIR = (Path(__file__).resolve().parent.parent / "scripts").resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _missing(mod):
    return importlib.util.find_spec(mod) is None


# 渲染必需依赖（缺则脚本无法生成 PDF）
RENDER_DEPS = ("markdown", "pypdf")
MISSING_RENDER = [m for m in RENDER_DEPS if _missing(m)]


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests that launch Chromium (slower)")
    config.addinivalue_line("markers", "network: marks tests that fetch remote resources (CDN)")


def pytest_collection_modifyitems(config, items):
    """环境门：当前解释器缺渲染依赖时，skip(非 xfail) 所有 integration 用例。"""
    if not MISSING_RENDER:
        return
    reason = (
        f"当前解释器 {sys.executable} 缺 {', '.join(MISSING_RENDER)}；"
        f"跳过渲染相关 integration。请用装齐依赖的 venv: pip install markdown pypdf css_inline"
    )
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
