#!/usr/bin/env python3
"""Validate destiny-matrix HTML against its chart plan and case evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PureWindowsPath
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from book_html import BookHTML, Node, normalize_text, is_hidden, limitation_text_size, MIN_LIMITATION_HAN

HARD_FORBIDDEN = ("命中注定", "这辈子注定", "天注定", "克夫", "克妻", "改命", "真命天子",
                  "真爱", "不可改变", "无法逆转", "克应", "命定")
SENTENCE_DELIMITERS = "。！？；\n"
# Style-spec §2.7: pipeline vocabulary that must not reach reader-facing prose (appendix excluded).
# Hits are review_required hints only, never issues.
PROCESS_TERMS = ("本次", "工具虚岁", "工具", "字段", "口径", "未核", "绑定", "浮点", "引擎回退", "MOSEPH",
                 "artifact", "JSON Pointer", "claim", "judge", "chief", "parallel", "tension",
                 "not_comparable", "跨会话记忆", "外部提交", "未采用", "不裁定", "审稿", "星历文件")
PROCESS_PATTERNS = (("S0–S10", r"(?<![A-Za-z0-9])S(?:10|[0-9])(?:\.5)?(?![A-Za-z0-9])"),
                    ("sect1/2", r"sect[12]"),
                    ("ISO 时间戳", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"))
# Style-spec §2.4 / D3: a paragraph should open with a judgement about the reader, not a denial or a method note.
OPENING_NEGATIONS = ("不是", "并不", "并非", "不代表", "不等于", "不意味着", "不能说明", "不能", "不证明",
                     "这不是", "这并不", "这不", "这里不", "本书不", "这些不是", "它不是")
OPENING_METHODS = ("这张盘该怎么读", "该怎么读", "读法上", "按照", "按本书", "本节", "这一节", "本章", "以下",
                   "下面先", "先说明", "需要说明", "说明一下", "严格来说", "在解读之前", "方法上")
OPENING_LIMITATION_ADVISORY = 5


class InputFailure(Exception):
    pass


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputFailure(f"无法读取{label}: {exc}") from exc


def _resolve_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise KeyError("JSON pointer 必须符合 RFC 6901")
    current = document
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not re.fullmatch(r"0|[1-9]\d*", part):
                raise KeyError(f"数组 pointer 索引无效: {part}")
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(f"无法读取 pointer 段 {part}")
    return current


def _artifact_documents(evidence: dict, base_dir: Path, issues: list[dict]) -> dict[str, Any]:
    result = {}
    artifacts = evidence.get("artifacts", [])
    if not isinstance(artifacts, list):
        issues.append({"path": "evidence.artifacts", "code": "invalid_artifacts", "message": "artifacts 必须为数组"})
        return result
    seen = set()
    root = base_dir.resolve()
    for index, artifact in enumerate(artifacts):
        path = f"evidence.artifacts[{index}]"
        if not isinstance(artifact, dict):
            issues.append({"path": path, "code": "invalid_artifact", "message": "artifact 必须为对象"})
            continue
        artifact_id, rel = artifact.get("artifact_id"), artifact.get("path")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in seen:
            issues.append({"path": path + ".artifact_id", "code": "duplicate_or_missing_id", "message": "artifact_id 缺失或重复"})
            continue
        seen.add(artifact_id)
        if not isinstance(rel, str) or not rel:
            issues.append({"path": path + ".path", "code": "missing_path", "message": "artifact path 缺失"})
            continue
        if Path(rel).is_absolute() or PureWindowsPath(rel).is_absolute():
            issues.append({"path": path + ".path", "code": "absolute_artifact_path", "message": "artifact path 必须是 evidence 工作区内的相对路径"})
            continue
        candidate = (root / rel).resolve()
        if candidate != root and root not in candidate.parents:
            issues.append({"path": path + ".path", "code": "path_escape", "message": "artifact path 必须位于 evidence 工作区内"})
            continue
        if artifact.get("status", "current") != "current":
            # Historical entries stay in the ledger; only current references are loadable.
            continue
        try:
            raw = candidate.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            expected = artifact.get("sha256")
            if not isinstance(expected, str) or digest != expected:
                issues.append({"path": path + ".sha256", "code": "artifact_hash_mismatch", "message": "artifact 必须声明且匹配 SHA-256"})
                continue
        except (OSError, UnicodeError) as exc:
            issues.append({"path": path + ".path", "code": "artifact_unreadable", "message": str(exc)})
            continue
        try:
            result[artifact_id] = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            # Evidence may register HTML/PDF deliverables; only data refs require JSON.
            continue
    return result


def _parse_data_ref(value: str) -> tuple[str, str]:
    if "#" not in value:
        raise ValueError("data ref 必须为 artifact_id#<json_pointer>")
    artifact_id, pointer = value.split("#", 1)
    if not artifact_id:
        raise ValueError("artifact_id 为空")
    return artifact_id, pointer
def _data_ref_covers(container_ref: str, leaf_ref: str) -> bool:
    try:
        container_artifact, container_pointer = _parse_data_ref(container_ref)
        leaf_artifact, leaf_pointer = _parse_data_ref(leaf_ref)
    except (TypeError, ValueError):
        return False
    if container_artifact != leaf_artifact:
        return False
    def parts(pointer):
        return [segment.replace("~1", "/").replace("~0", "~")
                for segment in pointer[1:].split("/")] if pointer else []
    container_parts, leaf_parts = parts(container_pointer), parts(leaf_pointer)
    return len(container_parts) <= len(leaf_parts) and leaf_parts[:len(container_parts)] == container_parts


def _display_number(value: Any, precision: int) -> str:
    number = Decimal(str(value))
    quantum = Decimal(1).scaleb(-precision)
    number = number.quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{number:.{precision}f}"


def _finite_tokens(value: str) -> bool:
    for match in re.finditer(r"(?<![A-Za-z])[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|(?i:NaN|Infinity)", value):
        try:
            if not math.isfinite(float(match.group(0))):
                return False
        except ValueError:
            return False
    return True
def _raw_text(node: Node) -> str:
    if node.tag == "#text":
        return node.children[0] if node.children else ""
    return "".join(_raw_text(child) if isinstance(child, Node) else child for child in node.children)


def _svg_issues(svg: Node, index: int) -> list[dict]:
    base = f"html.svg[{index}]"
    issues = []
    try:
        parsed = ET.fromstring(svg.serialize())
    except ET.ParseError as exc:
        return [{"path": base, "code": "invalid_svg_xml", "message": str(exc)}]
    ids: dict[str, int] = {}
    references: list[tuple[str, str]] = []
    drawable = 0
    for node in parsed.iter():
        attrs = node.attrib
        for key, value in attrs.items():
            if not _finite_tokens(value):
                issues.append({"path": base, "code": "non_finite_svg_value", "message": f"{key} 含非有限数值"})
            if key == "id":
                ids[value] = ids.get(value, 0) + 1
            if key in ("href", "{http://www.w3.org/1999/xlink}href") and value.startswith("#"):
                references.append((key, value[1:]))
            references.extend((key, ref) for ref in re.findall(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)", value, re.I))
        tag = node.tag.rsplit("}", 1)[-1].lower()
        try:
            if tag == "circle":
                valid = float(attrs.get("r", "0")) > 0
            elif tag == "ellipse":
                valid = float(attrs.get("rx", "0")) > 0 and float(attrs.get("ry", "0")) > 0
            elif tag == "rect":
                valid = float(attrs.get("width", "0")) > 0 and float(attrs.get("height", "0")) > 0
            elif tag == "line":
                valid = (attrs.get("x1"), attrs.get("y1")) != (attrs.get("x2"), attrs.get("y2"))
            elif tag in ("polygon", "polyline"):
                points = re.findall(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", attrs.get("points", ""))
                required = 3 if tag == "polygon" else 2
                valid = len(points) >= required * 2
                if tag == "polygon" and valid:
                    coords = [(float(points[i]), float(points[i + 1])) for i in range(0, len(points) - 1, 2)]
                    valid = len(set(coords)) >= 3
            elif tag == "path":
                valid = bool(re.search(r"[MmLlHhVvCcSsQqTtAaZz].*[0-9]", attrs.get("d", "")))
            elif tag == "text":
                valid = bool("".join(node.itertext()).strip())
            else:
                valid = False
            if valid:
                drawable += 1
            elif tag in ("circle", "ellipse", "rect", "line", "polygon", "polyline", "path"):
                issues.append({"path": base, "code": "degenerate_svg_geometry", "message": f"{tag} 几何缺失或退化"})
        except (ValueError, OverflowError):
            issues.append({"path": base, "code": "degenerate_svg_geometry", "message": f"{tag} 几何数值非法"})
    for element_id, count in ids.items():
        if count > 1:
            issues.append({"path": base, "code": "duplicate_svg_id", "message": f"SVG id 重复: {element_id}"})
    for attr, ref in references:
        if ref not in ids:
            issues.append({"path": base, "code": "missing_svg_reference", "message": f"{attr} 引用不存在的 id: {ref}"})
    if drawable == 0:
        issues.append({"path": base, "code": "empty_svg", "message": "SVG 没有可见绘图元素"})
    return issues


def _issues_for_html(book: BookHTML, plan: Any, evidence: Any, artifacts: dict,
                     sources: Any, base_dir: Path) -> list[dict]:
    issues: list[dict] = []
    def add(path: str, code: str, message: str):
        issues.append({"path": path, "code": code, "message": message})

    if not isinstance(plan, dict) or not isinstance(plan.get("sections"), list) or not isinstance(plan.get("chart_table"), list):
        add("plan", "invalid_plan", "chart_plan 必须包含 sections 与 chart_table 数组")
        return issues
    if not isinstance(evidence, dict):
        add("evidence", "invalid_evidence", "case_evidence 必须为对象")
        return issues
    kinds = {"disclosure", "body", "appendix"}
    semantic_sections = book.sections
    book_mains = [n for n in book.nodes if n.tag == "main" and n.attr("id") == "book"]
    if len(book_mains) != 1:
        add("html.main", "book_main_count", "必须恰有一个 <main id=\"book\">")
    elif any(not any(a is book_mains[0] for a in section.ancestors()) for section in semantic_sections):
        add("html.sections", "section_outside_book", "所有语义 section 必须位于 <main id=\"book\">")
    for index, section in enumerate(n for n in book.nodes if n.tag == "section"):
        if section.attr("data-content-kind") not in kinds:
            add(f"html.sections[{index}]", "invalid_content_kind", "所有 section 均须归类为 disclosure/body/appendix")
    disclosure_ids = set()
    for index, aside in enumerate(n for n in book.nodes if n.tag == "aside"):
        disclosure_id = aside.attr("data-disclosure-id")
        if not disclosure_id or disclosure_id in disclosure_ids:
            add(f"html.asides[{index}]", "duplicate_or_missing_disclosure_id", "每个 aside 必须有唯一 data-disclosure-id")
        if disclosure_id:
            disclosure_ids.add(disclosure_id)
    for index, section in enumerate(semantic_sections):
        kind = section.attr("data-content-kind")
        if kind not in kinds:
            add(f"html.sections[{index}].data-content-kind", "invalid_content_kind", "content-kind 只能是 disclosure/body/appendix")
    for kind in sorted(kinds):
        count = sum(s.attr("data-content-kind") == kind for s in semantic_sections)
        if count != 1 and kind in ("disclosure", "appendix"):
            add(f"html.sections[{kind}]", "section_kind_count", f"{kind} section 必须恰有一个，当前 {count}")
    if not any(s.attr("data-content-kind") == "body" for s in semantic_sections):
        add("html.sections.body", "missing_body_sections", "至少需要一个正文 body section")
    body_sections = [s for s in semantic_sections if s.attr("data-content-kind") == "body"]
    html_ids = [s.attr("data-section-id") for s in body_sections]
    if any(not value for value in html_ids) or len(set(html_ids)) != len(html_ids):
        add("html.sections.body", "duplicate_or_missing_section_id", "body section 必须有唯一 data-section-id")
    if any(s.attr("id") != "ch-" + str(s.attr("data-section-id")) for s in body_sections):
        add("html.sections.body", "invalid_section_anchor", "正文 section id 必须为 ch-<section_id>")
    planned_sections = plan.get("sections", [])
    plan_ids = [s.get("section_id") for s in planned_sections if isinstance(s, dict)]
    valid_plan_ids = [x for x in plan_ids if isinstance(x, str) and x]
    if len(plan_ids) != len(planned_sections) or len(valid_plan_ids) != len(plan_ids):
        add("plan.sections", "invalid_sections", "每个计划 section 必须包含非空字符串 section_id")
    if len(valid_plan_ids) != len(set(valid_plan_ids)):
        add("plan.sections", "duplicate_section_id", "plan.sections 中 section_id 重复")
    if html_ids != valid_plan_ids:
        add("html.sections.body", "section_plan_mismatch", f"HTML 与 plan.sections 顺序/ID 不一致；HTML={html_ids}，plan={valid_plan_ids}")
    for module in (n for n in book.nodes if n.attr("data-module") == "synastry"):
        owner = next((a for a in module.ancestors() if a.attr("data-content-kind") == "body"), None)
        if (module.tag != "div" or module.attr("id") != "module-synastry" or
                owner is None or owner.attr("data-section-id") != "relationships"):
            add(f"html:module-synastry", "invalid_synastry_location", "合盘模块必须是 relationships 内的 div#module-synastry")

    appendix_sections = [s for s in semantic_sections if s.attr("data-content-kind") == "appendix"]
    appendix_ids = set()
    known_anchors = {n.attr("id") for n in book.nodes if n.attr("id")}
    for index, details in enumerate(book.details):
        appendix = next((a for a in details.ancestors() if a.attr("data-content-kind") == "appendix"), None)
        appendix_id = details.attr("data-appendix-id")
        if appendix is None:
            add(f"html.details[{index}]", "details_outside_appendix", "details 只能位于 appendix section")
        if not appendix_id or appendix_id in appendix_ids:
            add(f"html.details[{index}].data-appendix-id", "duplicate_or_missing_appendix_id", "每个 details 必须有唯一 data-appendix-id")
        if appendix_id:
            appendix_ids.add(appendix_id)
            if details.attr("id") != appendix_id:
                add(f"html.details[{index}]", "appendix_anchor_mismatch", "details 的 id 必须与 data-appendix-id 一致")
            has_entry = any(n.tag == "a" and n.attr("href") == "#" + appendix_id
                            for section in body_sections for n in section.descendants())
            if not has_entry:
                add(f"html.details[{index}]", "appendix_entry_link_missing", f"正文缺少指向 #{appendix_id} 的入口链接")
            back = next((n for n in details.descendants() if n.tag == "a" and n.attr("href", "").startswith("#ch-")), None)
            if back is None or back.attr("href", "")[1:] not in known_anchors:
                add(f"html.details[{index}]", "appendix_return_link_missing", "附录必须有返回有效正文锚点的链接")
    css_text = "\n".join(_raw_text(n) for n in book.nodes if n.tag == "style")
    hidden_classes, hidden_ids, hidden_tags = set(), set(), set()
    for selectors, rules in re.findall(r"([^{}]+)\{([^{}]*)\}", css_text):
        if not re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", rules, re.I):
            continue
        for selector in selectors.split(","):
            hidden_classes.update(re.findall(r"\.([\w-]+)", selector))
            hidden_ids.update(re.findall(r"#([\w-]+)", selector))
            simple = selector.strip().lower()
            if re.fullmatch(r"[a-z][\w-]*", simple):
                hidden_tags.add(simple)
    for node in book.nodes:
        decorative_svg = (node.tag == "svg" and (node.attr("aria-hidden") or "").lower() == "true"
                          and not normalize_text(_raw_text(node)))
        style = (node.attr("style") or "").lower().replace(" ", "")
        markup_hidden = ("hidden" in node.attrs or bool(re.search(
            r"(?:^|;)display:none(?:;|$)|(?:^|;)visibility:hidden(?:;|$)", style))
            or "hidden" in (node.attr("class") or "").split())
        concealed = (markup_hidden or
                     ((node.attr("aria-hidden") or "").lower() == "true" and not decorative_svg) or
                     node.attr("id") in hidden_ids or node.tag in hidden_tags or
                     bool(set((node.attr("class") or "").split()) & hidden_classes))
        if concealed:
            add(f"html:{node.line}:{node.column}", "hidden_dom", "存在隐藏 DOM")
    for comment in book.comments:
        add(f"html:{comment['line']}:{comment['column']}", "html_comment", "成品不得包含 HTML 注释或审稿批注")

    _limitation_issues(book, planned_sections, evidence, add)

    rows = plan.get("chart_table", [])
    plan_chart_ids = [r.get("chart_id") for r in rows if isinstance(r, dict)]
    valid_plan_chart_ids = [x for x in plan_chart_ids if isinstance(x, str) and x]
    if len(plan_chart_ids) != len(rows) or len(valid_plan_chart_ids) != len(plan_chart_ids):
        add("plan.chart_table", "invalid_chart_row", "每个图表行必须有非空字符串 chart_id")
    if len(valid_plan_chart_ids) != len(set(valid_plan_chart_ids)):
        add("plan.chart_table", "duplicate_chart_id", "chart_table 中 chart_id 重复")
    figures = book.figures
    for index, node in enumerate(n for n in book.nodes if n.tag == "figure" and n.has_attr("data-chart-id")):
        if not node.has_class("chart-container"):
            add(f"html.figures[{index}]", "invalid_chart_figure", "带 data-chart-id 的 figure 必须有 chart-container class")
    html_chart_ids = [f.attr("data-chart-id") for f in figures]
    if any(not chart_id for chart_id in html_chart_ids) or len(html_chart_ids) != len(set(html_chart_ids)):
        add("html.figures", "duplicate_or_missing_chart_id", "图表 figure 必须有唯一 data-chart-id")
    if set(html_chart_ids) != set(valid_plan_chart_ids):
        add("html.figures", "chart_plan_mismatch", f"HTML 与 chart_table 不一致；缺少 {sorted(set(valid_plan_chart_ids)-set(html_chart_ids))}，多出 {sorted(set(html_chart_ids)-set(valid_plan_chart_ids))}")
    plan_by_id = {row.get("chart_id"): row for row in rows
                  if isinstance(row, dict) and isinstance(row.get("chart_id"), str) and row.get("chart_id")}
    figure_by_id = {f.attr("data-chart-id"): f for f in figures if f.attr("data-chart-id")}
    active_claims = {c.get("claim_id") for c in evidence.get("claims", [])
                     if isinstance(c, dict) and isinstance(c.get("claim_id"), str) and c.get("status") == "active"}
    section_ids = set(html_ids)
    for chart_id, row in plan_by_id.items():
        section_id = row.get("section_id")
        if not isinstance(section_id, str) or section_id not in section_ids:
            add(f"plan.chart_table[{chart_id}].section_id", "unknown_chart_section", "图表必须归属一个正文 section")
        if not isinstance(section_id, str) or not re.fullmatch(r"chart-" + re.escape(section_id) + r"-\d{2}", chart_id):
            add(f"plan.chart_table[{chart_id}].chart_id", "invalid_chart_id", "chart_id 必须为 chart-<section_id>-NN")
        if row.get("missing_policy") != "omit_with_disclosure":
            add(f"plan.chart_table[{chart_id}].missing_policy", "invalid_missing_policy", "missing_policy 必须为 omit_with_disclosure")
        figure = figure_by_id.get(chart_id)
        if figure and figure.attr("data-section-id") not in (None, section_id):
            add(f"html.figures[{chart_id}]", "chart_section_mismatch", "figure section 与 chart_table 不一致")
        row_claims = row.get("claim_ids", [])
        if not isinstance(row_claims, list):
            add(f"plan.chart_table[{chart_id}].claim_ids", "invalid_claim_ids", "图表 claim_ids 必须是数组")
        else:
            for claim_id in row_claims:
                if claim_id not in active_claims:
                    add(f"plan.chart_table[{chart_id}].claim_ids", "inactive_claim", f"图表计划引用非 active claim: {claim_id}")
    for index, node in enumerate(book.claim_nodes):
        for claim_id in (node.attr("data-claim-ids") or "").split():
            if claim_id not in active_claims:
                add(f"html.claims[{index}]", "inactive_claim", f"data-claim-ids 引用非 active claim: {claim_id}")
    for index, node in enumerate(n for n in book.nodes if n.tag in ("q", "blockquote") and not n.has_attr("data-quote-id")):
        add(f"html.quotes[{index}]", "missing_quote_id", "每个 q/blockquote 必须提供 data-quote-id")

    source_rows = sources.get("sources", []) if isinstance(sources, dict) else []
    quotes = {}
    source_by_id = {s.get("source_id"): s for s in source_rows if isinstance(s, dict)}
    common_reading_ids = {s.get("source_id") for s in evidence.get("sources", [])
                          if isinstance(s, dict) and s.get("kind") == "common_reading"}
    for source in source_rows:
        if not isinstance(source, dict):
            continue
        for quote in source.get("quotes", []) if isinstance(source.get("quotes", []), list) else []:
            if isinstance(quote, dict) and quote.get("quote_id"):
                quotes[quote["quote_id"]] = (source, quote)
    for index, quote_node in enumerate(book.quotes):
        quote_id = quote_node.attr("data-quote-id")
        pair = quotes.get(quote_id)
        if pair is None:
            add(f"html.quotes[{index}]", "unknown_quote", f"quote_id 不存在于 sources.json: {quote_id}")
            continue
        source, quote = pair
        if source.get("kind") == "common_reading" or source.get("source_id") in common_reading_ids:
            add(f"html.quotes[{index}]", "common_reading_quoted", f"{quote_id} 属于通行读法来源，只能不加引号地转述")
            continue
        if source.get("verification_status") != "verified":
            add(f"html.quotes[{index}]", "unverified_quote", f"{quote_id} 所属来源不是 verified")
            continue
        actual = normalize_text(quote_node.text())
        candidates = [normalize_text(quote.get("original") or "")]
        if quote.get("translation_kind") in ("published", "own"):
            candidates.append(normalize_text(quote.get("translation") or ""))
        if actual not in [candidate for candidate in candidates if candidate]:
            add(f"html.quotes[{index}]", "quote_text_mismatch", f"{quote_id} 的可见文本与核准原文/译文不一致")

    artifact_docs = artifacts
    for index, node in enumerate(book.values):
        path = f"html.values[{index}]"
        raw_ref = node.attr("data-value-ref") or ""
        try:
            artifact_id, pointer = _parse_data_ref(raw_ref)
            if artifact_id not in artifact_docs:
                raise KeyError(f"artifact 不存在或已失效: {artifact_id}")
            actual_value = _resolve_pointer(artifact_docs[artifact_id], pointer)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            add(path + ".data-value-ref", "invalid_value_ref", str(exc))
            continue
        if actual_value is None:
            add(path, "missing_value_rendered", "data-value-ref 指向缺值；不得将缺值绘制为 0 或其他数值")
            continue
        shown_value = node.attr("data-value")
        unit = node.attr("data-unit")
        if not node.has_attr("data-unit"):
            add(path + ".data-unit", "missing_value_unit", "data-value 节点必须显式提供 data-unit（无单位时留空）")
        try:
            if shown_value is None or Decimal(str(shown_value)) != Decimal(str(actual_value)):
                add(path + ".data-value", "value_binding_mismatch", "data-value 与 artifact 原始值不一致")
            precision_text = node.attr("data-precision")
            precision = int(precision_text) if precision_text is not None else -1
            if precision < 0 or precision > 12:
                raise ValueError("data-precision 必须是 0–12 的整数")
            formatted = _display_number(actual_value, precision)
            visible = normalize_text(node.text())
            if formatted not in visible or (unit and unit not in visible):
                add(path, "visible_value_mismatch", f"可见文本必须呈现 {formatted}{unit or ''}")
        except (InvalidOperation, ValueError, TypeError) as exc:
            add(path, "invalid_value_format", str(exc))

    for index, svg in enumerate(book.svg_nodes):
        issues.extend(_svg_issues(svg, index))

    # Chart data refs must be resolvable and agree with references rendered in the figure.
    for index, row in enumerate(rows):
        chart_id = row.get("chart_id") if isinstance(row, dict) else None
        if not chart_id:
            continue
        refs = row.get("data_refs", [])
        if not isinstance(refs, list):
            add(f"plan.chart_table[{index}].data_refs", "invalid_data_refs", "data_refs 必须为数组")
            continue
        figure = figure_by_id.get(chart_id)
        for ref in refs:
            try:
                artifact_id, pointer = _parse_data_ref(ref)
                if artifact_id not in artifact_docs:
                    raise KeyError(f"artifact 不存在或已失效: {artifact_id}")
                value = _resolve_pointer(artifact_docs[artifact_id], pointer)
                matching_refs = [n.attr("data-value-ref") for n in (figure.descendants() if figure else ())
                                 if n.attr("data-value-ref")]
                covered = any(_data_ref_covers(ref, rendered_ref) for rendered_ref in matching_refs)
                if value is None:
                    if covered or (figure is not None and any(n.attr("data-value") == "0"
                        for n in figure.descendants() if n.has_attr("data-value"))):
                        add(f"plan.chart_table[{index}].data_refs", "missing_plotted_as_zero", f"{ref} 缺值却在图中绘制")
                elif figure is not None and not covered:
                    add(f"plan.chart_table[{index}].data_refs", "unrendered_data_ref", f"{ref} 未在对应 figure 中绑定")
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                add(f"plan.chart_table[{index}].data_refs", "invalid_data_ref", str(exc))

    return issues


def _visible(node: Node) -> bool:
    return not is_hidden(node) and not any(is_hidden(a) for a in node.ancestors())


def _limitation_marks(book: BookHTML) -> dict[str, list[tuple[str, str]]]:
    """limitation_id -> [(content_kind, section_id)] for every visible data-limitation-id token."""
    marks: dict[str, list[tuple[str, str]]] = {}
    for node in book.nodes:
        if not node.has_attr("data-limitation-id") or not _visible(node):
            continue
        section = book.containing_section(node)
        kind = section.attr("data-content-kind") if section is not None else None
        section_id = (section.attr("data-section-id") or section.attr("id") or kind) if section is not None else None
        for limitation_id in (node.attr("data-limitation-id") or "").split():
            marks.setdefault(limitation_id, []).append((str(kind), str(section_id)))
    return marks


def _limitation_issues(book: BookHTML, planned_sections: list, evidence: dict, add) -> None:
    rows = evidence.get("limitations", [])
    registry = {r.get("limitation_id"): r for r in rows if isinstance(r, dict)} if isinstance(rows, list) else {}
    marks = _limitation_marks(book)
    for limitation_id in sorted(set(marks) - set(registry)):
        add(f"html.limitations[{limitation_id}]", "unknown_limitation", f"data-limitation-id 未在 case_evidence 登记: {limitation_id}")
    for section in (s for s in planned_sections if isinstance(s, dict)):
        section_id = section.get("section_id")
        ids = section.get("limitation_ids", [])
        for limitation_id in ids if isinstance(ids, list) else []:
            if limitation_id not in registry:
                add(f"plan.sections[{section_id}].limitation_ids", "unknown_limitation", f"计划限制未在 case_evidence 登记: {limitation_id}")
                continue
            here = sum(1 for kind, sid in marks.get(limitation_id, []) if kind == "body" and sid == section_id)
            if here == 0:
                add(f"html.sections[{section_id}]", "limitation_missing", f"{limitation_id} 须在 {section_id} 正文就近出现（data-limitation-id）")
            elif here > 1:
                add(f"html.sections[{section_id}]", "limitation_repeated", f"{limitation_id} 在 {section_id} 正文出现 {here} 次；只写一次，其后用短从句回扣")
    for node in book.nodes:
        if not node.has_attr("data-limitation-id") or not _visible(node):
            continue
        reader_ids = [lid for lid in (node.attr("data-limitation-id") or "").split()
                      if registry.get(lid, {}).get("required_placement") in ("opening", "adjacent")]
        if reader_ids and limitation_text_size(node) < MIN_LIMITATION_HAN:
            add(f"html:{node.line}:{node.column}", "limitation_empty",
                f"限制标记 {' '.join(reader_ids)} 去掉编号后可见文字不足 {MIN_LIMITATION_HAN} 个汉字；限制须写出条件本身")
    planned = {lid: s.get("section_id") for s in planned_sections if isinstance(s, dict)
               for lid in (s.get("limitation_ids") if isinstance(s.get("limitation_ids"), list) else [])}
    for limitation_id, row in registry.items():
        placement = row.get("required_placement")
        found = marks.get(limitation_id, [])
        body = [sid for kind, sid in found if kind == "body"]
        if placement == "opening":
            count = sum(1 for kind, _ in found if kind == "disclosure")
            if count != 1:
                add(f"html.disclosure[{limitation_id}]", "limitation_repeated" if count else "limitation_missing",
                    f"opening 限制 {limitation_id} 须在必要披露中恰好出现一次，当前 {count} 次")
            if body:
                add(f"html.sections[{body[0]}]", "limitation_wrong_placement", f"opening 限制 {limitation_id} 不以 data-limitation-id 重复出现在正文")
        elif placement == "appendix":
            if body:
                add(f"html.sections[{body[0]}]", "appendix_limitation_in_body", f"审计层限制 {limitation_id} 只放附录，不进正文")
        elif placement == "adjacent":
            stray = [sid for kind, sid in found if not (kind == "body" and sid == planned.get(limitation_id))]
            if stray:
                add(f"html.limitations[{limitation_id}]", "limitation_wrong_placement",
                    f"adjacent 限制 {limitation_id} 只在计划 section {planned.get(limitation_id)} 标记一次，另见于 {sorted(set(stray))}")


def _sentence_around(text: str, index: int, length: int) -> str:
    left = max((text.rfind(d, 0, index) + 1 for d in SENTENCE_DELIMITERS), default=0)
    right_positions = [text.find(d, index + length) for d in SENTENCE_DELIMITERS]
    right = min((pos + 1 for pos in right_positions if pos >= 0), default=len(text))
    return normalize_text(text[left:right])


def _review_candidates(book: BookHTML, evidence: Any = None) -> list[dict]:
    candidates = []
    for section in book.sections:
        text = section.text()
        kind = section.attr("data-content-kind")
        section_id = section.attr("data-section-id") or section.attr("id") or "disclosure"
        for word in HARD_FORBIDDEN:
            start = 0
            while (index := text.find(word, start)) >= 0:
                candidates.append({"location": f"{section_id}:{index}", "kind": "forbidden_term",
                                   "snippet": _sentence_around(text, index, len(word)), "term": word})
                start = index + len(word)
        if kind == "appendix":
            continue
        hits = []
        for word in PROCESS_TERMS:
            pattern = re.escape(word) if not word.isascii() else r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])"
            hits.extend((m.start(), m.group(0), word) for m in re.finditer(pattern, text, re.I))
        for label, pattern in PROCESS_PATTERNS:
            hits.extend((m.start(), m.group(0), label) for m in re.finditer(pattern, text))
        covered: list[tuple[int, int]] = []
        for index, matched, term in sorted(hits, key=lambda h: (h[0], -len(h[1]))):
            if any(a <= index < b for a, b in covered):
                continue  # 工具虚岁 already reported; skip the nested 工具
            covered.append((index, index + len(matched)))
            candidates.append({"location": f"{section_id}:{index}", "kind": "process_term",
                               "snippet": _sentence_around(text, index, len(matched)), "term": term})
        if kind != "body":
            continue
        for p_index, para in enumerate(n for n in section.descendants() if n.tag == "p" and _visible(n)):
            opening = normalize_text(para.text()).lstrip("“\"「（(")
            for label, words in (("opening_negation", OPENING_NEGATIONS), ("opening_method", OPENING_METHODS)):
                term = next((w for w in words if opening.startswith(w)), None)
                if term:
                    candidates.append({"location": f"{section_id}:p{p_index}", "kind": label,
                                       "snippet": _sentence_around(opening, 0, 0), "term": term})
                    break
    if isinstance(evidence, dict) and isinstance(evidence.get("limitations"), list):
        opening_ids = {r.get("limitation_id") for r in evidence["limitations"]
                       if isinstance(r, dict) and r.get("required_placement") == "opening"}
        rendered = {lid for lid, found in _limitation_marks(book).items()
                    if lid in opening_ids and any(kind == "disclosure" for kind, _ in found)}
        if len(rendered) > OPENING_LIMITATION_ADVISORY:
            candidates.append({"location": "disclosure", "kind": "opening_limitation_count",
                               "snippet": f"必要披露中有 {len(rendered)} 条 opening 限制", "term": str(len(rendered))})
    return candidates


def main(argv=None):
    ap = argparse.ArgumentParser(description="destiny-matrix 语义 HTML 校验")
    ap.add_argument("book", help="命书 HTML 文件")
    ap.add_argument("--plan", required=True, help="chart_plan.json")
    ap.add_argument("--evidence", required=True, help="case_evidence.json")
    ap.add_argument("--sources", help="sources.json（默认技能 references/sources.json）")
    ap.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    args = ap.parse_args(argv)
    book_path = Path(args.book)
    plan_path, evidence_path = Path(args.plan), Path(args.evidence)
    sources_path = Path(args.sources) if args.sources else Path(__file__).resolve().parents[1] / "references" / "sources.json"
    try:
        source_html = book_path.read_text(encoding="utf-8")
        plan = _read_json(plan_path, "chart_plan")
        evidence = _read_json(evidence_path, "case_evidence")
        sources = _read_json(sources_path, "sources.json")
    except (OSError, UnicodeError, InputFailure) as exc:
        payload = {"ok": False, "issues": [{"path": "input", "code": "input_error", "message": str(exc)}],
                   "review_required": [], "stats": {}}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return 2
    book = BookHTML(source_html)
    preissues = []
    artifacts = _artifact_documents(evidence, evidence_path.resolve().parent, preissues)
    issues = preissues + _issues_for_html(book, plan, evidence, artifacts, sources, evidence_path.resolve().parent)
    result = {"ok": not issues, "issues": issues, "review_required": _review_candidates(book, evidence),
              "stats": {"sections": len([s for s in book.sections if s.attr("data-content-kind") == "body"]),
                        "figures": len(book.figures), "values": len(book.values),
                        "quotes": len(book.quotes), "issues": len(issues)}}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("命书语义校验：%s" % ("通过" if result["ok"] else "失败"))
        for issue in issues:
            print("%s [%s] %s" % (issue["path"], issue["code"], issue["message"]))
        print("review_required: %d 条候选" % len(result["review_required"]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
