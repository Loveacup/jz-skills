"""Fast unit tests for --browser/--preflight/--fallback parsing, page-size 校验,
_launch_plan 全分支, 以及 --preflight --json 契约(子进程)。对应 CQI P0。
"""
import json
import sys
import importlib.util
import subprocess
from pathlib import Path

import pytest

import md2pdf_chrome as m

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "md2pdf_chrome.py"


# --------------------------- CLI 解析 --------------------------- #

def test_parse_browser_default():
    assert m.parse_cli_args(["in.md"])["browser"] == "playwright"


def test_parse_browser_values():
    for b in ("playwright", "chrome", "auto"):
        assert m.parse_cli_args(["in.md", "--browser", b])["browser"] == b


def test_parse_browser_invalid_raises():
    with pytest.raises(ValueError):
        m.parse_cli_args(["in.md", "--browser", "firefox"])


def test_parse_preflight_flag():
    assert m.parse_cli_args(["--preflight"])["preflight"] is True


def test_parse_fallback_pandoc():
    assert m.parse_cli_args(["in.md", "--fallback", "pandoc"])["fallback"] == "pandoc"


def test_parse_fallback_invalid_raises():
    with pytest.raises(ValueError):
        m.parse_cli_args(["in.md", "--fallback", "latex"])


def test_parse_no_metadata():
    assert m.parse_cli_args(["in.md", "--no-metadata"])["write_metadata"] is False
    assert m.parse_cli_args(["in.md"])["write_metadata"] is True


def test_parse_verify_flag():
    assert m.parse_cli_args(["in.md", "--verify"])["verify"] is True


def test_parse_pagesize_invalid_raises():
    # 回归: 非法 page-size 应像 --theme/--format 一样早失败
    with pytest.raises(ValueError):
        m.parse_cli_args(["in.md", "--page-size", "huge"])


def test_parse_pagesize_valid():
    assert m.parse_cli_args(["in.md", "--page-size", "430x932"])["page_size"] == "430x932"
    assert m.parse_cli_args(["in.md", "--page-size", "A4"])["page_size"] == "A4"


# --------------------------- _launch_plan --------------------------- #

def test_launch_plan_playwright_forces_bundled():
    assert m._launch_plan("playwright") == [("chromium.launch()", "playwright-chromium", "bundled")]


def test_launch_plan_invalid():
    with pytest.raises(ValueError):
        m._launch_plan("firefox")


def test_launch_plan_chrome_requires_chrome(monkeypatch):
    monkeypatch.setattr(m, "_find_system_chrome", lambda: None)
    with pytest.raises(RuntimeError):
        m._launch_plan("chrome")


def test_launch_plan_chrome_uses_executable(monkeypatch):
    monkeypatch.setattr(m, "_find_system_chrome", lambda: "/fake/chrome")
    plan = m._launch_plan("chrome")
    assert plan[0][1] == "system-chrome"
    assert "/fake/chrome" in plan[0][0]


def test_launch_plan_auto_order(monkeypatch):
    monkeypatch.setattr(m, "_bundled_launchable", lambda: True)
    monkeypatch.setattr(m, "_find_system_chrome", lambda: "/fake/chrome")
    assert [p[1] for p in m._launch_plan("auto")] == ["playwright-chromium", "system-chrome"]


def test_launch_plan_auto_no_bundled_falls_to_chrome(monkeypatch):
    monkeypatch.setattr(m, "_bundled_launchable", lambda: False)
    monkeypatch.setattr(m, "_find_system_chrome", lambda: "/fake/chrome")
    assert [p[1] for p in m._launch_plan("auto")] == ["system-chrome"]


def test_launch_plan_auto_nothing_raises_needpandoc(monkeypatch):
    monkeypatch.setattr(m, "_bundled_launchable", lambda: False)
    monkeypatch.setattr(m, "_find_system_chrome", lambda: None)
    with pytest.raises(m._NeedPandoc):
        m._launch_plan("auto")


# --------------------------- preflight JSON 契约 --------------------------- #

def test_preflight_json_schema_and_exit_matches_interpreter():
    """blocker#1 双向: 当前解释器有 markdown → ok/exit0; 缺 → fail/exit1。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--preflight", "--json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT / "scripts"), timeout=60,
    )
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    assert set(data) >= {"checks", "overall"}
    assert data["overall"] in ("ok", "degraded", "fail")
    md_check = next(c for c in data["checks"] if c["name"] == "interpreter:markdown")
    has_md = importlib.util.find_spec("markdown") is not None
    if has_md:
        assert md_check["status"] == "ok"
        assert proc.returncode == 0
    else:
        assert md_check["status"] == "fail"
        assert proc.returncode == 1
