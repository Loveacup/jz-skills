"""Fast unit tests for frontmatter → PDF metadata mapping and verify_pdf 质量门。
对应 CQI P1。
"""
from pathlib import Path

import pytest

import md2pdf_chrome as m
import verify_pdf


# --------------------------- frontmatter 解析 --------------------------- #

def test_parse_frontmatter_basic(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("---\ntitle: T\ntags: [x, y]\n---\n# body\n", encoding="utf-8")
    fm = m._parse_frontmatter(md)
    assert fm["title"] == "T"
    assert fm["tags"] == ["x", "y"]


def test_parse_frontmatter_none(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("# no frontmatter\n", encoding="utf-8")
    assert m._parse_frontmatter(md) == {}


def test_to_pdf_date():
    assert m._to_pdf_date("2026-06-14 10:30") == "D:20260614103000"
    assert m._to_pdf_date("2026-06-14") == "D:20260614000000"
    assert m._to_pdf_date(None) is None
    assert m._to_pdf_date("garbage") is None


# --------------------------- metadata 映射 --------------------------- #

def _blank_pdf(path):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        w.write(f)


def test_add_pdf_metadata_maps_fields(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfReader
    pdf = tmp_path / "x.pdf"
    _blank_pdf(pdf)
    md = tmp_path / "x.md"
    md.write_text(
        "---\ntitle: 标题T\nauthor: 作者A\ndescription: 描述D\n"
        "tags: [type/x]\naliases: [别名]\ncreated: 2026-06-14 09:00\n---\n# h\n",
        encoding="utf-8",
    )
    m.add_pdf_metadata(pdf, md)
    meta = PdfReader(str(pdf)).metadata
    assert meta.get("/Title") == "标题T"
    assert meta.get("/Author") == "作者A"
    assert meta.get("/Subject") == "描述D"
    assert "type/x" in (meta.get("/Keywords") or "")
    assert meta.get("/CreationDate") == "D:20260614090000"


def test_add_pdf_metadata_no_author_when_absent(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfReader
    pdf = tmp_path / "x.pdf"
    _blank_pdf(pdf)
    md = tmp_path / "x.md"
    md.write_text("---\ntitle: T\n---\n# h\n", encoding="utf-8")  # 无 author
    m.add_pdf_metadata(pdf, md)
    meta = PdfReader(str(pdf)).metadata
    assert meta.get("/Title") == "T"
    assert not meta.get("/Author")  # 隐私护栏: 不显式声明则不写 author


def test_add_pdf_metadata_no_title_doc_still_writes(tmp_path):
    """边界: 有 frontmatter、无 h1-h3 标题, metadata 仍写入(不被 bookmarks early-return 跳过)。"""
    pytest.importorskip("pypdf")
    from pypdf import PdfReader
    pdf = tmp_path / "x.pdf"
    _blank_pdf(pdf)
    md = tmp_path / "x.md"
    md.write_text("---\ntitle: 无标题正文T\n---\n正文没有任何 markdown 标题。\n", encoding="utf-8")
    m.add_pdf_metadata(pdf, md)
    assert PdfReader(str(pdf)).metadata.get("/Title") == "无标题正文T"


def test_add_pdf_metadata_fallback_title_to_stem(tmp_path):
    """无 title/aliases 时 /Title 用文件名 stem 兜底。"""
    pytest.importorskip("pypdf")
    from pypdf import PdfReader
    pdf = tmp_path / "x.pdf"
    _blank_pdf(pdf)
    md = tmp_path / "我的笔记.md"
    md.write_text("---\ntype: 测试\n---\n正文\n", encoding="utf-8")
    m.add_pdf_metadata(pdf, md)
    assert PdfReader(str(pdf)).metadata.get("/Title") == "我的笔记"


# --------------------------- verify_pdf --------------------------- #

def test_verify_missing_file(tmp_path):
    res = verify_pdf.verify(tmp_path / "nope.pdf")
    assert any(n == "exists" and lv == "error" for n, lv, _ in res["findings"])


def test_verify_too_small(tmp_path):
    p = tmp_path / "tiny.pdf"
    p.write_bytes(b"%PDF-x")
    res = verify_pdf.verify(p)
    assert "filesize" in {n for n, _, _ in res["findings"]}


def test_verify_mermaid_leak_regex():
    assert verify_pdf.MERMAID_RE.search("graph TD\nA-->B")
    assert verify_pdf.MERMAID_RE.search("sequenceDiagram")
    assert verify_pdf.MERMAID_RE.search("flowchart LR")
    # 普通正文里出现 'graph' 一词不应误触发
    assert not verify_pdf.MERMAID_RE.search("这段讲 graph 理论与图论")


def test_verify_no_false_mermaid_on_blank(tmp_path):
    """干净(无 mermaid 源码)的有效 PDF 不应误报 mermaid_leak / pages。"""
    pytest.importorskip("pypdf")
    pdf = tmp_path / "ok.pdf"
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    with open(pdf, "wb") as f:
        w.write(f)
    res = verify_pdf.verify(pdf)
    err = {n for n, lv, _ in res["findings"] if lv == "error"}
    # 核心逻辑不误报(filesize 对极小 blank fixture 另有 test_verify_too_small 覆盖)
    assert "mermaid_leak" not in err
    assert "pages" not in err
    assert "magic" not in err
