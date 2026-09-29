#!/usr/bin/env python3
"""Guard scoped edits to semantic destiny-matrix HTML."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PureWindowsPath
from decimal import Decimal, InvalidOperation
from book_html import BookHTML, Node, is_hidden, normalize_text, limitation_text_size, MIN_LIMITATION_HAN

# Voice/condition markers whose loss can raise a sentence's certainty (review hint for S9, not an issue).
CERTAINTY_MARKERS = (("在…的读法里", r"在[^，。；！？]{1,16}的读法里"), ("传统上", r"传统上"), ("常见的讲法", r"常见的讲法"),
                     ("如果", r"如果"), ("可能", r"可能"), ("倾向", r"倾向"), ("多半", r"多半"), ("例如", r"例如"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def html_fragment(node: Node) -> str:
    return node.serialize()


def bindings(node: Node) -> list[tuple]:
    return sorted(((n.tag, n.attr("data-value-ref"), n.attr("data-value"), n.attr("data-unit"),
                    n.attr("data-precision"), n.attr("data-claim-ids"), n.attr("data-quote-id"), normalize_text(n.text()))
                  for n in node.descendants() if any(n.has_attr(k) for k in
                  ("data-value-ref", "data-claim-ids", "data-quote-id"))), key=repr)


def prose_bindings(node: Node) -> tuple:
    """Bindings prose edits must keep: value/quote nodes verbatim, and the section's claim-ID set.

    Paragraph text carrying data-claim-ids may be reworded or merged (S8.5 reader-editor);
    the claims it cites may not be added or dropped."""
    fixed = sorted(((n.tag, n.attr("data-value-ref"), n.attr("data-value"), n.attr("data-unit"),
                     n.attr("data-precision"), n.attr("data-claim-ids"), n.attr("data-quote-id"), normalize_text(n.text()))
                    for n in node.descendants() if n.has_attr("data-value-ref") or n.has_attr("data-quote-id")), key=repr)
    claims = sorted({c for n in node.descendants() if not is_hidden(n)
                     for c in (n.attr("data-claim-ids") or "").split()})
    return fixed, claims


def limitation_marks(node: Node) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in node.descendants():
        if n.has_attr("data-limitation-id") and not is_hidden(n) and not any(is_hidden(a) for a in n.ancestors()):
            for lid in (n.attr("data-limitation-id") or "").split():
                counts[lid] = counts.get(lid, 0) + 1
    return counts


def certainty_counts(node: Node) -> dict[str, int]:
    text = normalize_text(node.text())
    return {label: len(re.findall(pattern, text)) for label, pattern in CERTAINTY_MARKERS}


def certainty_review(before: BookHTML, after: BookHTML, sections: set[str]) -> list[dict]:
    rows = []
    bmap, amap = before.section_map(), after.section_map()
    for sid in sorted(sections & set(bmap) & set(amap)):
        old, new = certainty_counts(bmap[sid]), certainty_counts(amap[sid])
        if sum(new.values()) < sum(old.values()) or any(new[k] < old[k] for k in old):
            rows.append({"section": sid, "before": old, "after": new,
                         "before_total": sum(old.values()), "after_total": sum(new.values())})
    return rows


def clean_fragment(node: Node, *, omit_figures: bool = False) -> str:
    clone = clean_fragment_node(node, omit_figures=omit_figures)
    return clone.serialize() if clone else ""


def clean_fragment_node(node: Node, *, omit_figures: bool = False) -> Node | None:
    if node.tag == "#comment" or is_hidden(node):
        return None
    if omit_figures and node.tag == "figure" and node.has_class("chart-container"):
        return None
    clone = Node(node.tag, dict(node.attrs), line=node.line, column=node.column)
    for child in node.children:
        if isinstance(child, Node):
            cleaned = clean_fragment_node(child, omit_figures=omit_figures)
            if cleaned is not None:
                clone.children.append(cleaned)
        else:
            clone.children.append(child)
    return clone


def _nonfigure_tree(node: Node):
    if node.tag == "figure" and node.has_class("chart-container"):
        return None
    if node.tag == "#text":
        return node.semantic_tree()
    attrs = {k: v for k, v in sorted(node.attrs.items())
             if k not in {"class", "style", "width", "height"}}
    children = []
    for child in node.children:
        item = _nonfigure_tree(child) if isinstance(child, Node) else ["#text", normalize_text(child)]
        if item is not None:
            children.append(item)
    return [node.tag, attrs, children]


def _citation_tree(node: Node):
    citation_classes = {"citation", "footnote-ref", "reference-index"}
    classes = set((node.attr("class") or "").split())
    if node.tag == "cite" or ((node.tag in ("sup", "a")) and classes & citation_classes):
        return None
    if node.tag == "#text":
        return node.semantic_tree()
    attrs = {k: v for k, v in sorted(node.attrs.items())
             if k not in {"style", "data-quote-id", "data-source-id", "data-citation-id", "data-reference-id"}}
    children = []
    for child in node.children:
        item = _citation_tree(child) if isinstance(child, Node) else ["#text", normalize_text(child)]
        if item is not None:
            children.append(item)
    return [node.tag, attrs, children]


def _pointer(document, pointer: str):
    current = document
    if pointer and (not pointer.startswith("/") or re.search(r"~(?![01])", pointer)):
        raise ValueError("JSON pointer 必须符合 RFC 6901")
    for token in pointer[1:].split("/") if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not re.fullmatch(r"0|[1-9]\d*", token):
                raise ValueError("数组 pointer 索引无效")
            current = current[int(token)]
        else:
            current = current[token]
    return current


def _value_ref_issues(book: BookHTML, evidence: dict, evidence_path: str) -> list[str]:
    artifacts, errors = {}, []
    root = Path(evidence_path).resolve().parent
    referenced = {(node.attr("data-value-ref") or "").split("#", 1)[0] for node in book.values}
    for row in evidence.get("artifacts", []):
        if row.get("artifact_id") not in referenced:
            continue
        try:
            rel = Path(row["path"])
            if rel.is_absolute() or PureWindowsPath(row["path"]).is_absolute():
                raise ValueError("artifact path 不得为绝对路径")
            path = (root / rel).resolve()
            if root not in path.parents:
                raise ValueError("artifact path 越界")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != row.get("sha256") or row.get("status", "current") != "current":
                raise ValueError("artifact 哈希不匹配或已失效")
            artifacts[row["artifact_id"]] = json.loads(raw)
        except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
    for node in book.values:
        try:
            artifact, pointer = (node.attr("data-value-ref") or "").split("#", 1)
            value = _pointer(artifacts[artifact], pointer)
            if value is None or Decimal(str(value)) != Decimal(str(node.attr("data-value"))):
                errors.append(f"{node.attr('data-value-ref')} 的新数值没有匹配 evidence 原值")
        except (KeyError, ValueError, IndexError, TypeError, InvalidOperation) as exc:
            errors.append(f"无效 data-value-ref: {exc}")
    return errors


def _contract_tree(node: Node):
    if node.tag == "#text":
        return ["#text", normalize_text(node.text(include_hidden=True))]
    if node.tag == "#comment":
        return ["#comment", node.text(include_hidden=True)]
    attrs = {k: v for k, v in sorted(node.attrs.items()) if k not in {"class", "style", "width", "height"}}
    children = [_contract_tree(child) if isinstance(child, Node) else ["#text", normalize_text(child)]
                for child in node.children]
    return [node.tag, attrs, children]


def changed(a: BookHTML, b: BookHTML) -> tuple[set[str], set[str]]:
    def fingerprints(book):
        sections = {str(n.attr("data-section-id") or n.attr("id")): digest(json.dumps(_contract_tree(n), ensure_ascii=False, sort_keys=True))
                    for n in book.sections if n.attr("data-section-id") or n.attr("id")}
        figures = {str(n.attr("data-chart-id")): digest(json.dumps(_contract_tree(n), ensure_ascii=False, sort_keys=True))
                   for n in book.figures if n.attr("data-chart-id")}
        return sections, figures
    af, bf = fingerprints(a), fingerprints(b)
    sections = {k for k in set(af[0]) | set(bf[0]) if af[0].get(k) != bf[0].get(k)}
    figures = {k for k in set(af[1]) | set(bf[1]) if af[1].get(k) != bf[1].get(k)}
    return sections, figures


def _data(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _invalid_claims(evidence: dict) -> set[str]:
    return {claim for correction in evidence.get("corrections", [])
            for claim in correction.get("invalidated_claim_ids", [])}


def _revision(path: str, evidence: dict) -> tuple[set[str], set[str], list[str]]:
    data = _data(path)
    if not isinstance(data, (dict, list)):
        raise ValueError("revision 文件必须是对象或指令数组")
    rows = data if isinstance(data, list) else data.get("revision_instructions", data.get("instructions", []))
    if not isinstance(rows, list) or not rows:
        raise ValueError("revision instructions 必须为非空数组")
    sections, claims, targets = set(), set(), []
    required = {"check_id", "fix_type", "owner", "claim_ids", "section_ids", "problem", "acceptance"}
    for row in rows:
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("revision instruction 字段不完整")
        if not isinstance(row["fix_type"], str) or row["fix_type"] not in {"calculation", "source", "analysis", "prose", "layout"}:
            raise ValueError("revision fix_type 无效")
        if not isinstance(row["claim_ids"], list) or not isinstance(row["section_ids"], list):
            raise ValueError("claim_ids 与 section_ids 必须为数组")
        if any(not isinstance(x, str) or not x for x in row["claim_ids"] + row["section_ids"]):
            raise ValueError("claim_ids/section_ids 只能包含非空字符串")
        if not isinstance(row["check_id"], str) or not isinstance(row["owner"], str):
            raise ValueError("check_id/owner 必须为字符串")
        if row.get("figure_ids", []) and (not isinstance(row["figure_ids"], list) or
                                           any(not isinstance(x, str) or not x for x in row["figure_ids"])):
            raise ValueError("figure_ids 必须为非空字符串数组")
        sections.update(row["section_ids"])
        claims.update(row["claim_ids"])
        targets.append(row["check_id"])
    return sections, claims, targets
def _raw_text(node: Node) -> str:
    if node.tag == "#text":
        return node.children[0] if node.children else ""
    return "".join(_raw_text(child) if isinstance(child, Node) else child for child in node.children)


def _hidden_signature(book: BookHTML):
    hidden_selectors = set()
    for style in (n for n in book.nodes if n.tag == "style"):
        css = _raw_text(style)
        if re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", css, re.I):
            for selector in re.findall(r"([^{}]+)\{[^{}]*(?:display\s*:\s*none|visibility\s*:\s*hidden)", css, re.I):
                hidden_selectors.update(re.findall(r"[.#]([\w-]+)", selector))
    rows = ((node.tag, node.attr("id"), node.attr("class"), normalize_text(node.text(include_hidden=True)))
            for node in book.nodes if is_hidden(node) or node.attr("id") in hidden_selectors or
            bool(set((node.attr("class") or "").split()) & hidden_selectors))
    return sorted(rows, key=repr)


def _protected_numbers(node: Node):
    text = normalize_text(node.text(include_hidden=True))
    return sorted(re.findall(r"(?<![\w])[-+]?\d+(?:[.,]\d+)*(?:%|°)?", text))


def _guard(before: BookHTML, after: BookHTML, scope: str, targets: set[str],
           revision: str | None, evidence_path: str | None, plan_path: str | None = None) -> list[dict]:
    issues = []
    bsections, bfigures = before.section_map(), before.figure_map()
    asections, afigures = after.section_map(), after.figure_map()
    changed_sections, changed_figures = changed(before, after)
    def fail(code, message):
        issues.append({"path": "html", "code": code, "message": message})
    if set(bsections) != set(asections) or set(bfigures) != set(afigures):
        fail("semantic_ids_changed", "section/figure 身份集合不得变化")
        return issues
    if scope == "layout":
        if changed_sections or changed_figures:
            fail("layout_semantics_changed", "layout scope 不允许改变任何 section/figure 语义")
        if _hidden_signature(before) != _hidden_signature(after):
            fail("layout_visibility_changed", "layout scope 不得隐藏正文、披露或图表信息")
    elif scope == "citations":
        prose_changed = any(_citation_tree(bsections[sid]) != _citation_tree(asections[sid])
                            for sid in bsections)
        if prose_changed or changed_figures:
            fail("citation_scope_exceeded", "citations scope 不允许改动正文文字或图表")
    elif scope == "charts":
        if changed_figures - targets:
            fail("unauthorized_figure", f"未授权图表发生变化: {sorted(changed_figures-targets)}")
        allowed_sections = {before.containing_section(bfigures[f]).attr("data-section-id")
                            for f in targets if f in bfigures and before.containing_section(bfigures[f])}
        if changed_sections - allowed_sections:
            fail("unauthorized_section", "授权图表之外的 section 发生变化")
        for fid in changed_figures & targets:
            if bindings(bfigures[fid]) != bindings(afigures[fid]):
                fail("chart_binding_changed", f"图表 {fid} 的数据/证据绑定发生变化")
            old_parent = before.containing_section(bfigures[fid])
            new_parent = after.containing_section(afigures[fid])
            if old_parent is None or new_parent is None or _nonfigure_tree(old_parent) != _nonfigure_tree(new_parent):
                fail("chart_scope_prose_changed", f"图表 {fid} 之外的 section 内容发生变化")
    elif scope == "prose":
        if changed_sections - targets:
            fail("unauthorized_section", f"未授权 section 发生变化: {sorted(changed_sections-targets)}")
        if changed_figures:
            fail("prose_figure_changed", "prose scope 不允许修改图表")
        if _hidden_signature(before) != _hidden_signature(after):
            fail("prose_visibility_changed", "prose scope 不得隐藏或新增隐藏内容")
        planned = {}
        if plan_path:
            planned = {s.get("section_id"): s.get("limitation_ids", []) for s in _data(plan_path).get("sections", [])
                       if isinstance(s, dict)}
        for sid in changed_sections & targets:
            if prose_bindings(bsections[sid]) != prose_bindings(asections[sid]):
                fail("prose_binding_changed", f"section {sid} 的数值、引文或 claim 集合发生变化")
            # Set comparison: a repeated number may be dropped with its duplicate clause, never added or altered.
            if set(_protected_numbers(bsections[sid])) != set(_protected_numbers(asections[sid])):
                fail("prose_numbers_changed", f"section {sid} 中的数字不能通过 prose scope 修改")
            old_marks, new_marks = limitation_marks(bsections[sid]), limitation_marks(asections[sid])
            if set(old_marks) != set(new_marks):
                fail("prose_limitation_changed", f"section {sid} 的读者层限制被删除或新增: "
                     f"删除 {sorted(set(old_marks)-set(new_marks))}，新增 {sorted(set(new_marks)-set(old_marks))}")
            for n in asections[sid].descendants():
                if (n.has_attr("data-limitation-id") and not is_hidden(n)
                        and not any(is_hidden(a) for a in n.ancestors())
                        and limitation_text_size(n) < MIN_LIMITATION_HAN):
                    fail("prose_limitation_emptied", f"section {sid} 的限制 {n.attr('data-limitation-id')} 被删到只剩编号或不足 {MIN_LIMITATION_HAN} 个汉字")
            for lid in planned.get(sid, []):
                if new_marks.get(lid, 0) != 1:
                    fail("prose_limitation_count", f"计划限制 {lid} 在 section {sid} 中须恰好出现一次，当前 {new_marks.get(lid, 0)} 次")
    elif scope == "content":
        if not revision or not evidence_path:
            fail("revision_required", "content scope 必须提供 --revision 与 --evidence")
            return issues
        try:
            evidence = _data(evidence_path)
            revision_sections, revision_claims, _ = _revision(revision, evidence)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            fail("invalid_revision", str(exc))
            return issues
        if not targets or not targets.issubset(revision_sections):
            fail("revision_target_mismatch", "目标 section 必须包含在已接受的 revision 指令中")
        if changed_sections - targets:
            fail("unauthorized_section", f"未授权 section 发生变化: {sorted(changed_sections-targets)}")
        if any((before.containing_section(bfigures[fid]) is None or
                before.containing_section(bfigures[fid]).attr("data-section-id") not in targets)
               for fid in changed_figures):
            fail("unauthorized_figure", "content scope 中发生变化的图表必须属于授权 section")
        invalid = _invalid_claims(evidence)
        visible_claims = set(after.visible_claim_ids())
        if invalid & visible_claims:
            fail("invalidated_claim_retained", f"修订后仍引用失效 claim: {sorted(invalid & visible_claims)}")
        active = {c.get("claim_id") for c in evidence.get("claims", []) if c.get("status") == "active"}
        if visible_claims - active:
            fail("inactive_claim_reference", f"修订后引用非 active claim: {sorted(visible_claims-active)}")
        old_claims = set(before.visible_claim_ids())
        new_claims = visible_claims - old_claims
        if new_claims - revision_claims:
            fail("claim_not_in_revision", f"新增 claim 未列入修订指令: {sorted(new_claims-revision_claims)}")
        for message in _value_ref_issues(after, evidence, evidence_path):
            fail("invalid_value_ref", message)
    return issues


def _prepare(before: BookHTML, revision: str, evidence_path: str, output: Path):
    evidence = _data(evidence_path)
    targets, _, checks = _revision(revision, evidence)
    revision_doc = _data(revision)
    revision_rows = revision_doc if isinstance(revision_doc, list) else revision_doc.get("revision_instructions", revision_doc.get("instructions", []))
    figure_targets = {fid for row in revision_rows for fid in row.get("figure_ids", [])}
    sections, figures = before.section_map(), before.figure_map()
    unknown_sections = targets - set(sections)
    unknown_figures = figure_targets - set(figures)
    if unknown_sections or unknown_figures:
        raise ValueError(f"未知 section/figure ID: sections={sorted(unknown_sections)}, figures={sorted(unknown_figures)}")
    invalid = _invalid_claims(evidence)
    active = {c.get("claim_id") for c in evidence.get("claims", []) if c.get("status") == "active"}
    output.mkdir(parents=True, exist_ok=False)
    (output / "sections").mkdir()
    (output / "figures").mkdir()
    retained_sections = []
    for sid, node in sections.items():
        if sid not in targets:
            fragment = clean_fragment(node, omit_figures=True)
            (output / "sections" / f"{sid}.html").write_text(fragment, encoding="utf-8")
            retained_sections.append(sid)
    retained_figures = []
    for fid, node in figures.items():
        claims = {claim for child in node.descendants() for claim in (child.attr("data-claim-ids") or "").split()}
        if claims & invalid or claims - active:
            continue
        fragment = clean_fragment(node)
        if _value_ref_issues(BookHTML(fragment), evidence, evidence_path):
            continue
        (output / "figures" / f"{fid}.html").write_text(fragment, encoding="utf-8")
        retained_figures.append({"chart_id": fid, "sha256": digest(fragment)})
    css = "\n".join(n.text(include_hidden=True) for n in before.nodes if n.tag == "style")
    css = re.sub(r"/\*[\s\S]*?\*/", "", css)
    (output / "styles.css").write_text(css, encoding="utf-8")
    manifest = {"rejected_sections": sorted(targets), "retained_sections": sorted(retained_sections),
                "retained_figures": retained_figures, "revision_checks": checks,
                "styles_sha256": digest(css)}
    (output / "repair_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scope guard for semantic HTML revisions")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after")
    parser.add_argument("--scope", choices=("prose", "layout", "citations", "charts", "content"))
    parser.add_argument("--targets")
    parser.add_argument("--revision")
    parser.add_argument("--evidence")
    parser.add_argument("--plan")
    parser.add_argument("--prepare-revision", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        before = BookHTML.from_file(args.before)
        if args.prepare_revision:
            if not args.revision or not args.evidence or not args.output:
                raise ValueError("--prepare-revision 需要 --revision --evidence --output")
            _prepare(before, args.revision, args.evidence, Path(args.output))
            result, code = {"ok": True, "prepared": args.output}, 0
        else:
            if not args.after or not args.scope or not args.targets:
                raise ValueError("常规模式需要 --after、--scope 与 --targets")
            after = BookHTML.from_file(args.after)
            targets = {x.strip() for x in args.targets.split(",") if x.strip()}
            sections, figures = before.section_map(), before.figure_map()
            if args.scope == "charts" and targets - set(figures):
                raise ValueError(f"未知 figure ID: {sorted(targets-set(figures))}")
            if args.scope in ("prose", "content", "citations") and targets - set(sections):
                raise ValueError(f"未知 section ID: {sorted(targets-set(sections))}")
            if args.scope == "content" and (not args.revision or not args.evidence):
                raise ValueError("content scope 需要 --revision 与 --evidence")
            if args.scope == "layout" and targets - (set(sections) | set(figures)):
                raise ValueError(f"未知 layout target ID: {sorted(targets-(set(sections)|set(figures)))}")
            issues = _guard(before, after, args.scope, targets, args.revision, args.evidence, args.plan)
            result, code = {"ok": not issues, "issues": issues}, (0 if not issues else 1)
            if args.scope == "prose":
                changed_sections, _ = changed(before, after)
                result["certainty_review"] = certainty_review(before, after, changed_sections & targets)
    except FileExistsError as exc:
        result, code = {"ok": False, "issues": [{"path": "output", "code": "output_exists", "message": str(exc)}]}, 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result, code = {"ok": False, "issues": [{"path": "input", "code": "input_error", "message": str(exc)}]}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
