"""M1 质量防线单测（fence-first 保护 / 缩进归一 / 错误炸弹检测 / 图数对账）。

全部纯单元测试，不起浏览器。对应 2026-07-02 `==>` 被高亮正则剥坏事故的回归防线。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from md2pdf_chrome import (  # noqa: E402
    protect_code_spans,
    restore_code_spans,
    preprocess_markdown,
    _normalize_list_indent,
    _parse_mermaid_stat,
    _format_mermaid_errors,
)
import verify_pdf  # noqa: E402


# ---------- M1.1 fence-first ----------

def _roundtrip(md):
    protected, store = protect_code_spans(md)
    return preprocess_markdown(protected), store


def test_mermaid_thick_arrow_survives():
    """事故回归：mermaid 粗箭头 ==> 不得被 ==高亮== 正则剥坏。"""
    md = "```mermaid\nflowchart LR\n    T1 ==> T2 ==> T3\n```\n"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "T1 ==> T2 ==> T3" in restored
    assert "<mark>" not in restored


def test_highlight_outside_fence_still_converts():
    md = "==重点== 正文\n\n```mermaid\nA ==> B\n```\n"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "<mark>重点</mark>" in restored
    assert "A ==> B" in restored


def test_inline_code_protected():
    md = "行内 `x ==y== z` 与 ==真高亮==。"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "`x ==y== z`" in restored
    assert "<mark>真高亮</mark>" in restored


def test_wikilink_inside_bash_fence_survives():
    md = "```bash\nif [[ -f x ]]; then echo ok; fi\n```\n"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "[[ -f x ]]" in restored


def test_tasklist_inside_fence_survives():
    md = "```text\n- [ ] 不是任务清单\n- [x] 也不是\n```\n"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "- [ ] 不是任务清单" in restored
    assert "&#x2610;" not in restored


def test_tilde_fence_protected():
    md = "~~~python\nx = '==a=='\n~~~\n"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "x = '==a=='" in restored


def test_mixed_fences_no_cross_match():
    """``` 围栏不得被 ~~~ 闭合（backreference 配对）。"""
    md = "```js\ncode1\n```\n\n~~~txt\ncode2\n~~~\n"
    protected, store = protect_code_spans(md)
    assert len(store) == 2


def test_frontmatter_like_mermaid_config_survives():
    """mermaid 块内的 ---config--- 不得被 frontmatter 剥离逻辑误伤。"""
    md = "```mermaid\n---\nconfig:\n  theme: base\n---\nflowchart TD\n  A --> B\n```\n"
    out, store = _roundtrip(md)
    restored = restore_code_spans(out, store)
    assert "config:" in restored
    assert "theme: base" in restored


# ---------- M1.5 列表缩进归一 ----------

def test_nested_3space_promoted():
    md = "1. 父项\n   - 子项\n"
    assert "    - 子项" in _normalize_list_indent(md)


def test_orphan_2space_list_not_promoted():
    """文首孤立 2 空格列表不升格（升到 4 空格会变缩进代码块）。"""
    md = "  - 孤立项甲\n  - 孤立项乙\n"
    out = _normalize_list_indent(md)
    assert out.splitlines()[0] == "  - 孤立项甲"


def test_blank_line_keeps_list_context():
    md = "- 父项\n\n  - 松散子项\n"
    assert "    - 松散子项" in _normalize_list_indent(md)


def test_4space_indent_untouched():
    md = "- 父项\n    - 已是4空格\n"
    assert "    - 已是4空格" in _normalize_list_indent(md)


# ---------- M1.2 渲染统计与错误格式化 ----------

def test_parse_mermaid_stat():
    assert _parse_mermaid_stat('xx\nMERMAID_STAT:{"total": 3, "rendered": 3}\n') == {
        "total": 3, "rendered": 3}
    assert _parse_mermaid_stat("no stat here") is None
    assert _parse_mermaid_stat(None) is None


def test_format_mermaid_errors():
    stderr = 'MERMAID_ERRORS:[{"index": 2, "message": "Parse error on line 1", "head": "flowchart LR"}]'
    msg = _format_mermaid_errors(stderr)
    assert "图#2" in msg
    assert "Parse error" in msg
    assert "--allow-diagram-errors" in msg


def test_format_mermaid_errors_missing():
    assert "详情缺失" in _format_mermaid_errors("")


# ---------- M1.4 verify：错误炸弹模糊匹配 ----------

def test_error_bomb_plain():
    assert verify_pdf.ERROR_BOMB_RE.search("Syntax error in text")


def test_error_bomb_doubled_chars():
    """PDF 文本提取的字符重复变体（本次事故实际形态）。"""
    assert verify_pdf.ERROR_BOMB_RE.search("SSyynnttaaxx  eerrrroorr iinn tteexxtt")
    assert verify_pdf.ERROR_BOMB_RE.search("mmeerrmmaaiidd vveerrssiioonn 1111..1166..00")


def test_error_bomb_no_false_positive():
    for benign in (
        "语法检查通过，本报告不含 error 字样的巧合句",
        "水土保持方案编制与监测验收",
        "version 2.0 of the plan",
    ):
        assert not verify_pdf.ERROR_BOMB_RE.search(benign), benign
