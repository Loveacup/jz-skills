"""Native outline/tagged (Chromium page.pdf outline:true, tagged:true) 测试。

对应 CQI v2 §6.8 方向 1：原生书签替代自制 pypdf 书签。
覆盖：
- add_pdf_bookmarks 检测到原生 outline 即跳过（兜底不重复写）
- add_pdf_bookmarks 无原生 outline 时仍工作（pandoc 救生艇路径）
- add_pdf_metadata 用 clone_from 保留既有 outline
- integration：全链渲染后 outline + StructTreeRoot + metadata 三者共存
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import md2pdf_chrome as m

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample.md"


def _pdf_with_outline(path, title="既有书签"):
    """构造带 1 条 outline 的最小 PDF。"""
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.add_outline_item(title, 0)
    with open(path, "wb") as f:
        w.write(f)


def _outline_titles(path):
    from pypdf import PdfReader
    titles = []

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                titles.append(it.title)

    walk(PdfReader(str(path)).outline)
    return titles


# --------------------------- fast --------------------------- #

def test_bookmarks_skip_when_native_outline_present(tmp_path):
    pytest.importorskip("pypdf")
    pdf = tmp_path / "x.pdf"
    _pdf_with_outline(pdf)
    md = tmp_path / "x.md"
    md.write_text("# 标题甲\n\n## 标题乙\n", encoding="utf-8")
    m.add_pdf_bookmarks(pdf, md)
    # 原生书签保持原样，未被 md 标题重建覆盖
    assert _outline_titles(pdf) == ["既有书签"]


def test_bookmarks_still_added_without_native_outline(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    pdf = tmp_path / "x.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(pdf, "wb") as f:
        w.write(f)
    md = tmp_path / "x.md"
    md.write_text("# 标题甲\n\n## 标题乙\n", encoding="utf-8")
    m.add_pdf_bookmarks(pdf, md)
    assert _outline_titles(pdf) == ["标题甲", "标题乙"]


def test_metadata_preserves_existing_outline(tmp_path):
    pytest.importorskip("pypdf")
    from pypdf import PdfReader
    pdf = tmp_path / "x.pdf"
    _pdf_with_outline(pdf, title="保留我")
    md = tmp_path / "x.md"
    md.write_text("---\ntitle: 元数据标题\n---\n# b\n", encoding="utf-8")
    m.add_pdf_metadata(pdf, md)
    assert _outline_titles(pdf) == ["保留我"]
    assert PdfReader(str(pdf)).metadata.get("/Title") == "元数据标题"


# --------------------------- integration --------------------------- #

@pytest.mark.integration
def test_fullchain_native_outline_tagged_metadata():
    """全链（渲染→remove_blank_pages→bookmarks→metadata）后三者共存。"""
    from pypdf import PdfReader
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        md_path = out_dir / "sample.md"
        md_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "scripts/md2pdf_chrome.py", str(md_path)],
            cwd=str(REPO_ROOT), timeout=120, capture_output=True, text=True,
        )
        pdf = out_dir / "sample.pdf"
        assert pdf.exists(), f"pdf not created. stderr:\n{proc.stderr}"

        reader = PdfReader(str(pdf))
        root = reader.trailer["/Root"]
        # 原生书签存活（且是 Chromium 直出，不是 pypdf 重建）
        assert reader.outline, "native outline missing after full chain"
        assert "native outline present" in proc.stdout
        # tagged 结构存活
        assert "/StructTreeRoot" in root, "StructTreeRoot stripped by post-processing"
        # metadata 步骤未被跳过
        assert reader.metadata is not None and reader.metadata.get("/Title")
