#!/usr/bin/env python3
"""PDF 交付质量门（最小集）。

可独立 CLI 运行，也可被 md2pdf_chrome.py --verify 调用。
设计原则：任何依赖缺失只降级为 skipped，绝不抛错中断主流程。

检查项（P0 最小集，对应实战痛点）：
  - filesize    文件 < 1KB 视为渲染失败          (error)
  - magic       %PDF- 魔数                        (error)
  - pages       页数 >= 1                          (error；缺 pypdf → skipped)
  - mermaid_leak Mermaid 源码残留(图没渲成 SVG)   (error)
  - mermaid_bomb Mermaid 错误炸弹文本印进成品     (error；模糊匹配抗字符重复)
  - diagram_count 源图数↔成功渲染数 metadata 对账 (error；缺 metadata 键则跳过)
  - first_page  首页可提取文本                      (warn)
  - pdf_metadata 源有 frontmatter 但 metadata 空   (warn)

深度项（横向溢出/字号分布/尺寸偏差）依赖重库且阈值脆，归 --verify-deep，默认不跑。
"""
import re
import sys
import json
import unicodedata
from pathlib import Path

# Mermaid 源码特征：渲染失败时源码会以纯文本漏进正文
MERMAID_RE = re.compile(
    r"graph\s+(TD|LR|TB|RL|BT)\b|sequenceDiagram|flowchart\s+(TD|LR|TB|RL|BT)"
    r"|stateDiagram|classDiagram|erDiagram|gantt\b|pie\s+title"
)


def _fuzzy_pattern(s):
    """错误炸弹文本在 PDF 提取时常出现字符重复（如 SSyynnttaaxx），
    对每个字符放宽到 1-2 次重复做模糊匹配。空格放宽为任意空白。"""
    parts = []
    for c in s:
        if c == " ":
            parts.append(r"\s{1,2}")
        else:
            parts.append(re.escape(c) + "{1,2}")
    return "".join(parts)


# M1.4 Mermaid 错误炸弹特征（2026-07-02 事故直接漏检项）：
# 渲染失败时 mermaid 的错误 SVG 含 "Syntax error in text / mermaid version x.y.z"
ERROR_BOMB_RE = re.compile(
    _fuzzy_pattern("Syntax error") + "|" + _fuzzy_pattern("mermaid version"),
    re.IGNORECASE,
)


def _has_frontmatter(md_path):
    try:
        return bool(re.match(r"^---\n", Path(md_path).read_text(encoding="utf-8", errors="ignore")))
    except Exception:
        return False


def verify(pdf, src_md=None):
    """返回 {pdf, findings:[(name,level,msg)], summary:{error,warn,skipped}}。"""
    pdf = Path(pdf)
    f = []
    if not pdf.exists():
        f.append(("exists", "error", f"PDF 不存在: {pdf}"))
        return _result(pdf, f)
    size = pdf.stat().st_size
    if size < 1024:
        f.append(("filesize", "error", f"{size}B 疑似渲染失败"))
    try:
        head = pdf.read_bytes()[:5]
    except Exception as e:
        f.append(("read", "error", f"无法读取: {e}"))
        return _result(pdf, f)
    if head != b"%PDF-":
        f.append(("magic", "error", "非法 PDF 头"))
    try:
        from pypdf import PdfReader
        r = PdfReader(str(pdf))
        pages = r.pages
        if len(pages) == 0:
            f.append(("pages", "error", "0 页"))
        # Mermaid 源码残留（NFKC 归一消除 CJK 兼容映射干扰，不影响 ASCII 特征）
        leak = []
        bombs = []
        for i, p in enumerate(pages):
            txt = unicodedata.normalize("NFKC", p.extract_text() or "")
            if MERMAID_RE.search(txt):
                leak.append(i + 1)
            # M1.4 错误炸弹检测：图渲染失败时的错误 SVG 文本被印进成品
            if ERROR_BOMB_RE.search(txt):
                bombs.append(i + 1)
        if leak:
            f.append(("mermaid_leak", "error", f"Mermaid 源码残留于页 {leak}（图未渲染成 SVG）"))
        if bombs:
            f.append(("mermaid_bomb", "error",
                      f"Mermaid 错误炸弹（Syntax error）印于页 {bombs}——图渲染失败被交付"))
        # 首页文本
        if pages and len((pages[0].extract_text() or "").strip()) == 0:
            f.append(("first_page", "warn", "首页无可提取文本（疑似白屏/纯图）"))
        # metadata
        meta = r.metadata or {}
        if src_md and _has_frontmatter(src_md) and not (meta.get("/Title") or meta.get("/Author")):
            f.append(("pdf_metadata", "warn", "源有 frontmatter 但 PDF metadata 为空"))
        # M1.4 图数对账：渲染端写入的「源图数/成功渲染数」metadata 必须相等
        dt, dr = meta.get("/JZDiagramTotal"), meta.get("/JZDiagramRendered")
        if dt not in (None, "") and dr not in (None, "") and str(dt) != str(dr):
            f.append(("diagram_count", "error",
                      f"Mermaid 图数对账不齐：源 {dt} 个、成功渲染 {dr} 个"))
    except ImportError:
        f.append(("pypdf", "skipped", "pypdf 未安装，页级检查跳过"))
    except Exception as e:
        f.append(("parse", "error", f"PDF 解析失败: {e}"))
    return _result(pdf, f)


def _result(pdf, findings):
    summ = {lvl: sum(1 for x in findings if x[1] == lvl) for lvl in ("error", "warn", "skipped")}
    return {"pdf": str(pdf), "findings": findings, "summary": summ}


def render_report(res, as_json=False):
    if as_json:
        print(json.dumps({
            "pdf": res["pdf"],
            "findings": [{"name": n, "level": lv, "msg": m} for n, lv, m in res["findings"]],
            "summary": res["summary"],
        }, ensure_ascii=False))
        return
    marks = {"error": "❌", "warn": "⚠️ ", "skipped": "⏭ "}
    name = Path(res["pdf"]).name
    if not res["findings"]:
        print(f"✅ {name} 质量门通过（无问题）")
    for n, lv, m in res["findings"]:
        print(f"  {marks.get(lv, '  ')} {n}: {m}")
    s = res["summary"]
    print(f"  === error={s['error']} warn={s['warn']} skipped={s['skipped']} ===")


def main(argv):
    if not argv:
        print("Usage: python verify_pdf.py <pdf> [--src <md>] [--json] [--fail-on warn|error]")
        return 1
    pdf = argv[0]
    src = None
    as_json = False
    fail_on = "error"
    i = 1
    while i < len(argv):
        if argv[i] == "--src" and i + 1 < len(argv):
            src = argv[i + 1]; i += 2
        elif argv[i] == "--json":
            as_json = True; i += 1
        elif argv[i] == "--fail-on" and i + 1 < len(argv):
            fail_on = argv[i + 1]; i += 2
        else:
            i += 1
    res = verify(pdf, src)
    render_report(res, as_json=as_json)
    s = res["summary"]
    if s["error"] > 0:
        return 1
    if fail_on == "warn" and s["warn"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
