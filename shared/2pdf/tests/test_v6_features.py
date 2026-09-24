"""Behavior coverage for content routing and v6 report rendering options."""

import subprocess
import sys
from pathlib import Path

import md2pdf_chrome as m
from themes.theme_router import route


def test_chinese_report_url_with_cli_word_routes_light_on_a4():
    md = """# A股行业研究\n\n""" + "这份研究分析市场结构、企业收入与投资风险。" * 30 + "参考 https://x.com/cli。"
    assert route(md, page_size="A4", hour=2) not in {
        "gruvbox-dark", "solarized-dark", "dracula", "dark"
    }


def test_mermaid_chart_markup_does_not_trigger_dark_code_routing():
    md = "# 中文研究报告\n\n" + "证据链分析市场变化与监管机制。\n" * 80
    md += "```mermaid\n" + "graph TD\n A-->B\n" * 300 + "```\n"

    assert m.route_theme(md, page_size="A4", hour=2) not in {
        "gruvbox-dark", "solarized-dark", "dracula", "dark"
    }


def test_byline_and_properties_render_from_frontmatter(tmp_path):
    md = tmp_path / "report.md"
    md.write_text(
        "---\ntitle: 行业报告\nauthor: Alex Cai\ncli: [exa, opencli]\n"
        "models: [模型A：研究, 模型B：写作]\ntags: [行业, 研究]\n---\n# 行业报告\n\n正文。\n",
        encoding="utf-8",
    )

    html = m.build_html(md, "行业报告", theme="academic", properties=True, byline=True)

    assert "撰写" in html and "Alex Cai" in html
    assert "协作 CLI" in html and "exa · opencli" in html
    assert "参与模型" in html and "模型A：研究 · 模型B：写作" in html
    assert "tags" in html and "行业 · 研究" in html


def test_emoji_callout_title_does_not_duplicate_builtin_icon():
    rendered = m.convert_callouts("> [!tip] 💡 提醒\n> 内容")
    assert rendered.count("💡") == 1


def test_preview_exports_first_and_chart_pages_at_72dpi(tmp_path, monkeypatch, capsys):
    import pypdf

    class Page:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

        def get(self, _key):
            return {}

    class Reader:
        def __init__(self, _path):
            self.pages = [Page("封面"), Page("普通正文"), Page("图1 市场变化")]

    md = tmp_path / "report.md"
    md.write_text("**📊 图1 市场变化**\n```mermaid\ngraph TD\n A-->B\n```\n", encoding="utf-8")
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"pdf")
    commands = []
    monkeypatch.setattr(pypdf, "PdfReader", Reader)
    monkeypatch.setattr(m.shutil, "which", lambda _name: "/usr/bin/pdftoppm")
    monkeypatch.setattr(m.subprocess, "run", lambda cmd, **_kwargs: commands.append(cmd))

    paths = m.export_preview_pages(pdf, md, tmp_path / "preview")

    assert [Path(path).name for path in paths] == ["page-001.png", "page-003.png"]
    assert all(command[command.index("-r") + 1] == "72" for command in commands)
    assert "page-001.png" in capsys.readouterr().out


def test_help_exits_successfully_and_lists_report_options():
    for flag in ("-h", "--help"):
        result = subprocess.run(
            [sys.executable, m.__file__, flag],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert all(option in result.stdout for option in ("--properties", "--byline", "--preview DIR"))
