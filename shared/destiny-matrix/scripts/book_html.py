#!/usr/bin/env python3
"""Shared semantic HTML parsing for destiny-matrix book tooling."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from typing import Any

VOID_TAGS = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"))
SKIP_TEXT_TAGS = frozenset(("script", "style", "template", "noscript"))
PRESENTATION_ATTRS = frozenset(("class", "style", "width", "height", "role", "aria-label",
                                "aria-describedby", "tabindex", "focusable"))


def normalize_text(value: str) -> str:
    """Normalize visible text for HTML/PDF comparisons."""
    return " ".join(unicodedata.normalize("NFKC", value).split())


@dataclass
class Node:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    parent: "Node | None" = None
    children: list["Node | str"] = field(default_factory=list)
    line: int = 1
    column: int = 0

    def descendants(self, *, include_self: bool = True):
        if include_self:
            yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.descendants()

    def has_class(self, name: str) -> bool:
        return name in (self.attrs.get("class") or "").split()

    def has_attr(self, name: str) -> bool:
        return name in self.attrs

    def attr(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    def text(self, *, include_hidden: bool = False) -> str:
        if self.tag.startswith("#"):
            return self.children[0] if self.children and isinstance(self.children[0], str) else ""
        if self.tag in SKIP_TEXT_TAGS:
            return ""
        if not include_hidden and is_hidden(self):
            return ""
        parts: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif include_hidden or not is_hidden(child):
                parts.append(child.text(include_hidden=include_hidden))
        return "".join(parts)

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def serialize(self) -> str:
        if self.tag == "#text":
            return escape(self.children[0] if self.children else "", quote=False)
        if self.tag == "#comment":
            return "<!--" + (self.children[0] if self.children else "") + "-->"
        if self.tag.startswith("#"):
            return ""
        attrs = "".join(" " + key if val is None else " " + key + '=\"' + escape(str(val), quote=True) + '\"'
                        for key, val in self.attrs.items())
        opening = "<" + self.tag + attrs + ">"
        if self.tag in VOID_TAGS:
            return opening
        content = "".join(child.serialize() if isinstance(child, Node) else
                           (child if self.tag in ("style", "script") else escape(child, quote=False))
                           for child in self.children)
        return opening + content + "</" + self.tag + ">"

    def semantic_tree(self, *, ignore_presentation: bool = True) -> Any:
        if self.tag == "#text":
            text = normalize_text(self.children[0] if self.children else "")
            return ["#text", text] if text else None
        if self.tag == "#comment":
            return None
        attrs = {k: v for k, v in sorted(self.attrs.items())
                 if k not in PRESENTATION_ATTRS and not k.startswith("aria-")}
        children = [tree for child in self.children
                    if isinstance(child, Node) and (tree := child.semantic_tree(ignore_presentation=ignore_presentation)) is not None]
        text_parts = [normalize_text(child) for child in self.children if isinstance(child, str)]
        children.extend(["#text", text] for text in text_parts if text)
        return [self.tag, attrs, children]


class _TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.comments: list[dict[str, Any]] = []

    def _new(self, tag: str, attrs: list[tuple[str, str | None]]) -> Node:
        line, col = self.getpos()
        node = Node(tag.lower(), {k.lower(): v for k, v in attrs}, self.stack[-1], line=line, column=col)
        self.stack[-1].children.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        node = self._new(tag, attrs)
        if node.tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._new(tag, attrs)

    def handle_endtag(self, tag):
        target = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == target:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if data:
            node = Node("#text", parent=self.stack[-1], line=self.getpos()[0], column=self.getpos()[1])
            node.children.append(data)
            self.stack[-1].children.append(node)

    def handle_comment(self, data):
        line, col = self.getpos()
        node = Node("#comment", parent=self.stack[-1], line=line, column=col)
        node.children.append(data)
        self.stack[-1].children.append(node)
        self.comments.append({"line": line, "column": col, "text": data})

    def handle_decl(self, decl):
        self.stack[-1].children.append(Node("#declaration", children=[decl], parent=self.stack[-1]))

    def unknown_decl(self, data):
        self.stack[-1].children.append(Node("#declaration", children=[data], parent=self.stack[-1]))


class BookHTML:
    """Semantic view plus a lightweight tree used by guard and PDF tooling."""

    def __init__(self, source: str):
        parser = _TreeParser()
        parser.feed(source)
        parser.close()
        self.root = parser.root
        self.comments = parser.comments
        self.nodes = list(self.root.descendants(include_self=False))
        self.sections = [n for n in self.nodes if n.tag == "section" and
                         (n.has_attr("data-content-kind") or n.has_attr("data-section-id"))]
        self.figures = [n for n in self.nodes if n.tag == "figure" and n.has_class("chart-container")]
        self.details = [n for n in self.nodes if n.tag == "details"]
        self.disclosures = [n for n in self.nodes if n.tag == "aside" and n.has_attr("data-disclosure-id")]
        self.values = [n for n in self.nodes if n.has_attr("data-value-ref")]
        self.quotes = [n for n in self.nodes if n.tag in ("q", "blockquote") and n.has_attr("data-quote-id")]
        self.claim_nodes = [n for n in self.nodes if n.has_attr("data-claim-ids")]
        self.svg_nodes = [n for n in self.nodes if n.tag == "svg"]

    @classmethod
    def from_file(cls, path):
        from pathlib import Path
        return cls(Path(path).read_text(encoding="utf-8"))

    def containing_section(self, node: Node) -> Node | None:
        return next((ancestor for ancestor in node.ancestors() if ancestor in self.sections), None)

    def section_map(self) -> dict[str, Node]:
        return {n.attr("data-section-id"): n for n in self.sections if n.attr("data-section-id")}

    def figure_map(self) -> dict[str, Node]:
        return {n.attr("data-chart-id"): n for n in self.figures if n.attr("data-chart-id")}

    def text_manifest(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for node in self.sections:
            key = node.attr("data-section-id") or node.attr("id") or "section"
            text = normalize_text(node.text())
            if text:
                rows.append({"block_id": str(key), "kind": str(node.attr("data-content-kind") or "section"), "text": text})
        for index, node in enumerate(self.nodes):
            if node.tag in ("p", "li", "figcaption", "summary", "th", "td"):
                section = self.containing_section(node)
                key = node.attr("id") or "%s:%d" % (section.attr("data-section-id") if section else "document", index)
                text = normalize_text(node.text())
                if text:
                    rows.append({"block_id": str(key), "kind": node.tag, "text": text})
        return rows

    def fingerprints(self) -> dict[str, dict[str, str]]:
        def digest(node: Node) -> str:
            payload = json.dumps(node.semantic_tree(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return {
            "sections": {str(n.attr("data-section-id") or n.attr("id")): digest(n)
                         for n in self.sections if n.attr("data-section-id") or n.attr("id")},
            "figures": {str(n.attr("data-chart-id")): digest(n)
                        for n in self.figures if n.attr("data-chart-id")},
        }

    def serialize(self) -> str:
        return "".join(child.serialize() if isinstance(child, Node) else escape(child, quote=False)
                       for child in self.root.children)

    def visible_claim_ids(self) -> list[str]:
        return [claim for node in self.claim_nodes if not is_hidden(node)
                for claim in (node.attr("data-claim-ids") or "").split()]


def is_hidden(node: Node) -> bool:
    if node.tag.startswith("#"):
        return False
    attrs = node.attrs
    if "hidden" in attrs or (attrs.get("aria-hidden") or "").lower() == "true":
        return True
    style = (attrs.get("style") or "").lower().replace(" ", "")
    if re.search(r"(?:^|;)display:none(?:;|$)|(?:^|;)visibility:hidden(?:;|$)", style):
        return True
    if "hidden" in (attrs.get("class") or "").split():
        return True
    return False


# A reader-layer limitation marker must still say something once its IDs are stripped.
MIN_LIMITATION_HAN = 6


def limitation_text_size(node: Node) -> int:
    """Han characters in a limitation marker's visible text, excluding its own IDs."""
    text = node.text()
    for limitation_id in (node.attr("data-limitation-id") or "").split():
        text = text.replace(limitation_id, "")
    return len(re.findall(r"[\u3400-\u9fff]", text))


def section_role(node: Node) -> str:
    kind = node.attr("data-content-kind")
    return str(kind or node.attr("data-section-id") or node.tag)


def normalized_tree(node: Node) -> str:
    return json.dumps(node.semantic_tree(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
