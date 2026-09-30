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


# ---------------------------------------------------------------------------
# Core chart rendering: 四柱盘 (P08), 紫微十二宫盘 (P06), 占星星盘 (P07).
# Geometry, class names and sizes follow references/output-template.md §5 and
# references/chart-patterns.md. Renderers draw only what the calculator output
# contains; they never derive, fill or re-round chart values.
# ---------------------------------------------------------------------------

BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
STEM_ELEMENT = dict(zip("甲乙丙丁戊己庚辛壬癸", "木木火火土土金金水水"))
BRANCH_ELEMENT = dict(zip(BRANCHES, "水土木木土火火土金金土水"))
ELEMENT_CLASS = {"木": "wx-wood", "火": "wx-fire", "土": "wx-earth", "金": "wx-metal", "水": "wx-water"}
SIGNS = ("白羊", "金牛", "双子", "巨蟹", "狮子", "处女", "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼")
# Anchor of each palace on the border of the 2×2 centre area, in a 0–100 box.
ZIWEI_ANCHOR = {"巳": (0, 0), "午": (25, 0), "未": (75, 0), "申": (100, 0), "酉": (100, 25), "戌": (100, 75),
                "亥": (100, 100), "子": (75, 100), "丑": (25, 100), "寅": (0, 100), "卯": (0, 75), "辰": (0, 25)}
WHEEL_SIZE = 720
WHEEL_RADII = {"outer": 300, "sign": 264, "label": 222, "house_out": 184, "house_in": 158}
WHEEL_LABEL_BOX = (62.0, 42.0)  # width, height of a two-line planet label in viewBox units
ASPECT_STYLE = {"三合": "harmonic", "六合": "harmonic", "三分": "harmonic", "六分": "harmonic",
                "四分": "tense", "对冲": "tense", "对分": "tense", "刑": "tense", "冲": "tense"}


class RenderError(ValueError):
    pass


def _e(value: Any) -> str:
    return escape(str(value), quote=True)


def _num(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def pillars_html(pillars: list[dict[str, Any]], *, caption: str = "四柱") -> str:
    """四柱盘：年、月、日、时四列的语义表格；日主与月令以文字标签标出。"""
    if len(pillars) != 4:
        raise RenderError("四柱盘需要恰好四柱")
    for pillar in pillars:
        if not all(pillar.get(key) for key in ("柱", "天干", "地支")):
            raise RenderError("每柱须有 柱、天干、地支")

    def glyph(char: str, element: str | None, mark: str = "") -> str:
        cls = "pillar-glyph " + ELEMENT_CLASS[element] if element else "pillar-glyph"
        tag = f'<span class="pillar-mark">{_e(mark)}</span>' if mark else ""
        wx = f'<span class="pillar-wx">{_e(element)}</span>' if element else ""
        return f'<td class="{cls}"><span class="glyph">{_e(char)}</span>{wx}{tag}</td>'

    def row(label: str, cells: list[str], cls: str = "") -> str:
        attr = f' class="{cls}"' if cls else ""
        return f'<tr{attr}><th scope="row">{_e(label)}</th>' + "".join(cells) + "</tr>"

    head = '<thead><tr><th scope="col">柱</th>' + "".join(
        f'<th scope="col">{_e(p["柱"])}</th>' for p in pillars) + "</tr></thead>"
    rows = []
    if any(p.get("天干十神") for p in pillars):
        rows.append(row("天干十神", [f'<td>{_e(p.get("天干十神") or "—")}</td>' for p in pillars], "pillar-gods"))
    rows.append(row("天干", [glyph(p["天干"], STEM_ELEMENT.get(p["天干"]),
                                  "日主" if p["柱"] == "日柱" else "") for p in pillars], "pillar-stems"))
    rows.append(row("地支", [glyph(p["地支"], BRANCH_ELEMENT.get(p["地支"]),
                                  "月令" if p["柱"] == "月柱" else "") for p in pillars], "pillar-branches"))
    if any(p.get("地支藏干") for p in pillars):
        rows.append(row("藏干", [f'<td>{_e("、".join(p.get("地支藏干") or []) or "—")}</td>' for p in pillars]))
    if any(p.get("地支藏干十神") for p in pillars):
        rows.append(row("藏干十神", [f'<td>{_e("、".join(p.get("地支藏干十神") or []) or "—")}</td>'
                                     for p in pillars], "pillar-gods"))
    if any(p.get("纳音") for p in pillars):
        rows.append(row("纳音", [f'<td>{_e(p.get("纳音") or "—")}</td>' for p in pillars]))
    return (f'<table class="chart-data pillar-chart"><caption>{_e(caption)}</caption>{head}'
            f'<tbody>{"".join(rows)}</tbody></table>')


def ziwei_relations(ming_branch: str) -> dict[str, str]:
    """命宫的对宫与三合两宫所在地支。"""
    if ming_branch not in BRANCHES or len(ming_branch) != 1:
        raise RenderError(f"未知地支: {ming_branch!r}")
    index = BRANCHES.index(ming_branch)
    return {"对宫": BRANCHES[(index + 6) % 12], "三合一": BRANCHES[(index + 4) % 12],
            "三合二": BRANCHES[(index + 8) % 12]}


def ziwei_grid_html(palaces: list[dict[str, Any]], *, basics: dict[str, Any] | None = None,
                    title: str = "本命十二宫", include_minor: bool = True) -> str:
    """紫微十二宫盘：固定地支位置的 4×4 外围十二格，中心画命宫三方四正连线。"""
    by_branch = {p.get("地支"): p for p in palaces}
    if len(palaces) != 12 or set(by_branch) != set(BRANCHES):
        raise RenderError("十二宫盘需要十二个地支各一宫")
    ming = next((p for p in palaces if p.get("宫位") == "命宫"), None)
    if ming is None:
        raise RenderError("十二宫缺少命宫")
    start = BRANCHES.index(ming["地支"])
    names = {p["地支"]: p.get("宫位") for p in palaces}

    def star(item: dict[str, Any], cls: str) -> str:
        extra = ""
        if item.get("亮度"):
            extra += f'<span class="zw-bright">{_e(item["亮度"])}</span>'
        if item.get("四化"):
            extra += f'<span class="zw-hua">化{_e(item["四化"])}</span>'
        return f'<span class="{cls}">{_e(item.get("名称"))}{extra}</span>'

    cells = []
    # Reading order follows the palace sequence from 命宫; grid placement comes from data-branch.
    for step in range(12):
        palace = by_branch[BRANCHES[(start - step) % 12]]
        classes = ["ziwei-cell"]
        if palace.get("宫位") == "命宫":
            classes.append("is-ming")
        if palace.get("是否身宫"):
            classes.append("is-shen")
        majors = palace.get("主星") or []
        stars = "".join(star(s, "zw-star") for s in majors) or '<span class="zw-empty">空宫</span>'
        minors = palace.get("辅星") or []
        minor = ('<div class="zw-minor">' + "".join(star(s, "zw-aux") for s in minors) + "</div>"
                 if include_minor and minors else "")
        label = f'<span class="palace-label">{_e(palace.get("宫位"))}</span>'
        if palace.get("是否身宫"):
            label += '<span class="palace-label is-shen-label">身宫</span>'
        limit = (palace.get("大限") or {}).get("范围")
        span = f'<span class="zw-limit">{_e(limit[0])}–{_e(limit[1])}</span>' if limit and len(limit) == 2 else ""
        ganzhi = f'<span class="zw-gz">{_e(palace.get("天干") or "")}{_e(palace["地支"])}</span>'
        cells.append(f'<div class="{" ".join(classes)}" data-branch="{_e(palace["地支"])}">'
                     f'<div class="zw-stars">{stars}</div>{minor}'
                     f'<div class="zw-foot"><span class="zw-names">{label}</span>'
                     f'<span class="zw-meta">{span}{ganzhi}</span></div></div>')

    rel = ziwei_relations(ming["地支"])
    (mx, my), (ox, oy) = ZIWEI_ANCHOR[ming["地支"]], ZIWEI_ANCHOR[rel["对宫"]]
    (ax, ay), (bx, by) = ZIWEI_ANCHOR[rel["三合一"]], ZIWEI_ANCHOR[rel["三合二"]]
    aria = (f'命宫在{ming["地支"]}；三合为{names[rel["三合一"]]}（{rel["三合一"]}）与'
            f'{names[rel["三合二"]]}（{rel["三合二"]}），对宫为{names[rel["对宫"]]}（{rel["对宫"]}）')
    lines = (f'<svg class="zw-lines" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
             f'preserveAspectRatio="none" role="img" aria-label="{_e(aria)}">'
             f'<polygon class="zw-trine" points="{mx},{my} {ax},{ay} {bx},{by}" fill="none" '
             f'stroke="#9b2d23" stroke-width="1.2" vector-effect="non-scaling-stroke"/>'
             f'<line class="zw-oppose" x1="{mx}" y1="{my}" x2="{ox}" y2="{oy}" stroke="#574f44" '
             f'stroke-width="1.2" stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/></svg>')
    info = [f'<span class="zw-title">{_e(title)}</span>']
    for key in ("五行局", "命主", "身主"):
        if basics and basics.get(key):
            info.append(f'<span class="zw-info">{_e(key)}　{_e(basics[key])}</span>')
    info.append(f'<span class="zw-legend">实线：命宫三合　虚线：命宫对宫</span>')
    centre = f'<div class="ziwei-cell is-center">{lines}<div class="zw-centre-text">{"".join(info)}</div></div>'
    return '<div class="ziwei-grid">' + "".join(cells) + centre + "</div>"


def _wheel_point(radius: float, offset_deg: float) -> tuple[float, float]:
    import math
    centre = WHEEL_SIZE / 2
    angle = math.radians(offset_deg)
    return centre - radius * math.cos(angle), centre + radius * math.sin(angle)


def label_gap(offset_deg: float, radius: float = WHEEL_RADII["label"]) -> float:
    """Angular room an upright label needs at this position: its height at the sides, its width at top and bottom."""
    import math
    width, height = WHEEL_LABEL_BOX
    return math.degrees((height + (width - height) * abs(math.sin(math.radians(offset_deg)))) / radius)


def spread_angles(angles: list[float], gap: float | None = None) -> list[float]:
    """Move label angles apart until neighbours no longer overlap; order is kept.

    `gap` fixes the minimum separation in degrees; by default it follows `label_gap`."""
    count = len(angles)
    if count < 2:
        return list(angles)
    if count * (gap if gap is not None else label_gap(90)) > 360:
        raise RenderError("星体过多，标签无法在轮上排开")
    order = sorted(range(count), key=lambda i: angles[i] % 360)
    placed = [angles[i] % 360 for i in order]
    for _ in range(600):
        moved = False
        for k in range(count):
            nxt = (k + 1) % count
            # Unwrapped distance: a label pushed past its neighbour reads as negative, not as far away.
            distance = placed[nxt] - placed[k] + (360 if nxt == 0 else 0)
            need = gap if gap is not None else label_gap(placed[k] + distance / 2)
            if distance < need - 1e-6:
                shift = (need - distance) / 2
                placed[k] -= shift
                placed[nxt] += shift
                moved = True
        if not moved:
            break
    result = [0.0] * count
    for slot, index in enumerate(order):
        result[index] = placed[slot] % 360
    return result


def degree_label(longitude: float) -> str:
    """Degrees and minutes inside the sign, truncated (never rounded up into the next sign)."""
    within = longitude % 30
    minutes = int(within * 60 + 1e-9)
    return f"{minutes // 60}°{minutes % 60:02d}′"


def wheel_svg(cusps: list[float], asc: float, mc: float, planets: list[dict[str, Any]],
              aspects: list[dict[str, Any]] | None = None, *, label_id: str | None = None,
              desc_id: str | None = None) -> str:
    """占星星盘：黄道带、真实宫始、轴点、星体与所选相位。planets 每项含 名称、黄经，可含 逆行。"""
    import math
    values = list(cusps) + [asc, mc] + [p.get("黄经") for p in planets]
    if len(cusps) != 12 or len(set(cusps)) != 12:
        raise RenderError("星盘需要十二个互异的宫始黄经")
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or not 0 <= v < 360
           for v in values):
        raise RenderError("黄经须为 [0,360) 内的有限数")
    names = [p.get("名称") for p in planets]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise RenderError("星体名称缺失或重复")
    r = WHEEL_RADII
    centre = WHEEL_SIZE / 2
    off = lambda longitude: (longitude - asc) % 360

    def line(r1: float, r2: float, angle: float, cls: str, stroke: str, width: float, dash: str = "") -> str:
        (x1, y1), (x2, y2) = _wheel_point(r1, angle), _wheel_point(r2, angle)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<line class="{cls}" x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" y2="{_num(y2)}" '
                f'stroke="{stroke}" stroke-width="{width}"{extra}/>')

    def text(radius: float, angle: float, content: str, cls: str, size: int, fill: str, weight: str = "",
             dy: float = 0.0) -> str:
        x, y = _wheel_point(radius, angle)
        y += dy
        bold = f' font-weight="{weight}"' if weight else ""
        # The paper-coloured halo keeps labels legible where axis or cusp lines pass behind them.
        return (f'<text class="{cls}" x="{_num(x)}" y="{_num(y)}" font-size="{size}" fill="{fill}"{bold} '
                f'stroke="#faf7f0" stroke-width="4" stroke-linejoin="round" paint-order="stroke" '
                f'text-anchor="middle" dominant-baseline="central">{_e(content)}</text>')

    parts = []
    aria = "".join(f' {key}="{_e(value)}"' for key, value in
                   (("aria-labelledby", label_id), ("aria-describedby", desc_id)) if value)
    if not label_id:
        aria += ' aria-label="占星星盘"'
    parts.append(f'<svg class="wheel" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WHEEL_SIZE} {WHEEL_SIZE}" '
                 f'role="img"{aria}>')
    ring = lambda radius, stroke, width, fill="none": (
        f'<circle cx="{_num(centre)}" cy="{_num(centre)}" r="{radius}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{width}"/>')
    parts.append(ring(r["outer"], "#211d18", 1.25, "#f3eee2"))
    parts.append(ring(r["sign"], "#211d18", 1, "#faf7f0"))
    parts.append(ring(r["house_out"], "#8c826e", 0.75))
    parts.append(ring(r["house_in"], "#8c826e", 0.75))
    for index, sign in enumerate(SIGNS):
        parts.append(line(r["sign"], r["outer"], off(index * 30), "wheel-sign-line", "#211d18", 1))
        parts.append(text((r["sign"] + r["outer"]) / 2, off(index * 30 + 15), sign, "wheel-sign", 15, "#211d18"))
        for tick in (10, 20):
            parts.append(line(r["sign"], r["sign"] + 7, off(index * 30 + tick), "wheel-tick", "#574f44", 0.75))
    axis = {round(asc % 360, 6), round((asc + 180) % 360, 6), round(mc % 360, 6), round((mc + 180) % 360, 6)}
    for house, cusp in enumerate(cusps, start=1):
        if round(cusp % 360, 6) not in axis:
            parts.append(line(r["house_in"], r["sign"], off(cusp), "wheel-cusp", "#8c826e", 0.75))
        following = cusps[house % 12]
        middle = cusp + ((following - cusp) % 360) / 2
        parts.append(text((r["house_in"] + r["house_out"]) / 2, off(middle), str(house),
                          "wheel-house", 14, "#574f44"))
    for label, longitude in (("上升", asc), ("下降", (asc + 180) % 360), ("天顶", mc), ("天底", (mc + 180) % 360)):
        parts.append(line(r["house_in"], r["outer"] + 10, off(longitude), "wheel-axis", "#211d18", 1.75))
        parts.append(text(r["outer"] + 32, off(longitude), label, "wheel-axis-label", 15, "#211d18", "600"))

    position = {p["名称"]: off(p["黄经"]) for p in planets}
    for aspect in aspects or []:
        a, b, kind = aspect.get("行星A"), aspect.get("行星B"), aspect.get("相位")
        if a not in position or b not in position:
            raise RenderError(f"相位引用了盘上没有的星体: {a}–{b}")
        style = ASPECT_STYLE.get(str(kind))
        if style is None:
            continue  # 合相由相邻位置表达，不画弦线
        (x1, y1), (x2, y2) = _wheel_point(r["house_in"], position[a]), _wheel_point(r["house_in"], position[b])
        if (round(x1, 2), round(y1, 2)) == (round(x2, 2), round(y2, 2)):
            continue
        stroke, dash = (("#2e4a62", "") if style == "harmonic" else ("#9b2d23", ' stroke-dasharray="7 5"'))
        parts.append(f'<line class="wheel-aspect is-{style}" x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" '
                     f'y2="{_num(y2)}" stroke="{stroke}" stroke-width="1.5"{dash}/>')

    spread = spread_angles([position[n] for n in names])
    for planet, shown in zip(planets, spread):
        true = position[planet["名称"]]
        parts.append(line(r["sign"] - 9, r["sign"], true, "wheel-mark", "#211d18", 1.5))
        (x1, y1), (x2, y2) = _wheel_point(r["sign"] - 9, true), _wheel_point(r["label"] + 24, shown)
        if abs(((shown - true + 180) % 360) - 180) > 0.5:
            parts.append(f'<line class="wheel-leader" x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" '
                         f'y2="{_num(y2)}" stroke="#8c826e" stroke-width="0.75"/>')
        parts.append(text(r["label"], shown, planet["名称"], "wheel-planet", 15, "#211d18", "600", dy=-9))
        detail = degree_label(planet["黄经"]) + ("逆" if planet.get("逆行") else "")
        parts.append(text(r["label"], shown, detail, "wheel-degree", 14, "#574f44", dy=10))
    parts.append("</svg>")
    return "".join(parts)


def _render_cli(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    from pathlib import Path
    parser = argparse.ArgumentParser(description="把 chart_bundle 的盘面数据渲染为命书图形片段")
    parser.add_argument("chart", choices=("pillars", "ziwei", "wheel"))
    parser.add_argument("--bundle", required=True, help="chart_bundle.json")
    parser.add_argument("--bodies", help="wheel：逗号分隔的星体名，默认十大行星")
    parser.add_argument("--aspects", help="wheel：要画的相位，如 太阳-木星,月亮-海王星；默认不画")
    parser.add_argument("--no-minor", action="store_true", help="ziwei：辅星不上图")
    parser.add_argument("--label-id")
    parser.add_argument("--desc-id")
    args = parser.parse_args(argv)
    try:
        dims = json.loads(Path(args.bundle).read_text(encoding="utf-8"))["dimensions"]
        if args.chart == "pillars":
            out = pillars_html(dims["bazi"]["data"]["四柱"])
        elif args.chart == "ziwei":
            data = dims["ziwei"]["data"]
            out = ziwei_grid_html(data["十二宫"], basics=data.get("基础信息"), include_minor=not args.no_minor)
        else:
            data = dims["astrology"]["data"]
            table = data["十大行星+北交+凯龙+莉莉丝"]
            wanted = ([x.strip() for x in args.bodies.split(",") if x.strip()] if args.bodies else
                      ["太阳", "月亮", "水星", "金星", "火星", "木星", "土星", "天王星", "海王星", "冥王星"])
            missing = [n for n in wanted if not isinstance(table.get(n), dict) or "黄经" not in table[n]]
            if missing:
                raise RenderError("计算输出中没有这些星体的黄经: " + "、".join(missing))
            planets = [{"名称": n, "黄经": table[n]["黄经"], "逆行": bool(table[n].get("逆行"))} for n in wanted]
            pairs = {frozenset(x.strip().split("-")) for x in (args.aspects or "").split(",") if x.strip()}
            aspects = [a for a in data.get("主要相位", []) if frozenset((a["行星A"], a["行星B"])) in pairs]
            found = {frozenset((a["行星A"], a["行星B"])) for a in aspects}
            if pairs - found:
                raise RenderError("计算输出中没有这些相位: " + "、".join("-".join(sorted(p)) for p in pairs - found))
            axes = data["ASC_MC_原始黄经"]
            out = wheel_svg(data["十二宫始黄经"], axes["ASC"], axes["MC"], planets, aspects,
                            label_id=args.label_id, desc_id=args.desc_id)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"book_html: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(_render_cli())
