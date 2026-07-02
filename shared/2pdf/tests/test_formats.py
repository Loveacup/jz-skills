"""RED-phase tests for the `--format png|html|wechat` feature.

These exercise the interface contract that will be added to
`scripts/md2pdf_chrome.py` (parse_cli_args, output_path_for, inline_css,
md_to_output, VALID_FORMATS) and the new themes. They are expected to FAIL or
ERROR until the implementation exists.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import md2pdf_chrome

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample.md"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------- #
# Unit (fast, no Chromium)
# --------------------------------------------------------------------------- #

def test_valid_formats_constant():
    for fmt in ("pdf", "png", "html", "wechat"):
        assert fmt in md2pdf_chrome.VALID_FORMATS


def test_parse_format_png():
    parsed = md2pdf_chrome.parse_cli_args(["in.md", "--format", "png"])
    assert parsed["format"] == "png"


def test_parse_format_html():
    parsed = md2pdf_chrome.parse_cli_args(["in.md", "--format", "html"])
    assert parsed["format"] == "html"


def test_parse_format_wechat():
    parsed = md2pdf_chrome.parse_cli_args(["in.md", "--format", "wechat"])
    assert parsed["format"] == "wechat"


def test_parse_format_default_pdf():
    parsed = md2pdf_chrome.parse_cli_args(["in.md"])
    assert parsed["format"] == "pdf"


def test_parse_preserves_theme_and_pagesize():
    parsed = md2pdf_chrome.parse_cli_args(
        ["in.md", "--format", "png", "--theme", "kami", "--page-size", "800x418"]
    )
    assert parsed["theme"] == "kami"
    assert parsed["page_size"] == "800x418"
    assert parsed["positional"] == ["in.md"]


def test_output_path_for_each_format():
    md = Path("/tmp/doc.md")
    assert str(md2pdf_chrome.output_path_for(md, "png")).endswith("doc.png")
    assert str(md2pdf_chrome.output_path_for(md, "html")).endswith("doc.html")
    assert str(md2pdf_chrome.output_path_for(md, "wechat")).endswith(
        "doc.wechat.html"
    )
    assert str(md2pdf_chrome.output_path_for(md, "pdf")).endswith("doc.pdf")


def test_output_path_for_explicit():
    result = md2pdf_chrome.output_path_for(
        Path("/tmp/doc.md"), "png", "/tmp/out.png"
    )
    assert result == Path("/tmp/out.png")


def test_inline_css_inlines_styles():
    html = (
        "<html><head><style>p{color:red}</style></head>"
        "<body><p>hi</p></body></html>"
    )
    result = md2pdf_chrome.inline_css(html)
    assert "style=" in result
    assert "color" in result
    # The <p> should carry the inlined style.
    assert "<p" in result


# --------------------------------------------------------------------------- #
# Theme (fast)
# --------------------------------------------------------------------------- #

NEW_THEMES = ("kami", "editorial", "swiss", "social-card", "wechat-article")


def test_new_themes_listed():
    from themes import list_themes

    listed = list_themes()
    for name in NEW_THEMES:
        assert name in listed


def test_new_themes_loadable():
    from themes import load_theme

    for name in NEW_THEMES:
        theme = load_theme(name)
        assert theme.css, f"theme {name} has empty css"
        assert theme.name, f"theme {name} has empty name"


# --------------------------------------------------------------------------- #
# Integration (Chromium, slower)
# --------------------------------------------------------------------------- #

def _run_cli(out_dir, fmt=None):
    """Copy the fixture into an isolated dir and run the CLI there."""
    md_path = out_dir / "sample.md"
    md_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    cmd = [sys.executable, "scripts/md2pdf_chrome.py", str(md_path)]
    if fmt is not None:
        cmd += ["--format", fmt]
    proc = subprocess.run(
        cmd, cwd=str(REPO_ROOT), timeout=120,
        capture_output=True, text=True,
    )
    return md_path, proc


@pytest.mark.integration
def test_render_png_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        md_path, proc = _run_cli(out_dir, "png")
        png = out_dir / "sample.png"
        assert png.exists(), f"png not created. stderr:\n{proc.stderr}"
        data = png.read_bytes()
        assert len(data) > 0
        assert data[:8] == PNG_MAGIC


@pytest.mark.integration
def test_render_html_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        md_path, proc = _run_cli(out_dir, "html")
        html_path = out_dir / "sample.html"
        assert html_path.exists(), f"html not created. stderr:\n{proc.stderr}"
        text = html_path.read_text(encoding="utf-8")
        assert text.strip()
        assert "<html" in text
        assert "</html>" in text


@pytest.mark.integration
def test_render_wechat_inlines_css():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        md_path, proc = _run_cli(out_dir, "wechat")
        wechat_path = out_dir / "sample.wechat.html"
        assert wechat_path.exists(), (
            f"wechat html not created. stderr:\n{proc.stderr}"
        )
        text = wechat_path.read_text(encoding="utf-8")
        assert text.strip()
        assert "style=" in text


@pytest.mark.integration
def test_render_pdf_regression():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        md_path, proc = _run_cli(out_dir, fmt=None)
        pdf = out_dir / "sample.pdf"
        assert pdf.exists(), f"pdf not created. stderr:\n{proc.stderr}"
        data = pdf.read_bytes()
        assert len(data) > 1024
        assert data[:4] == b"%PDF"
