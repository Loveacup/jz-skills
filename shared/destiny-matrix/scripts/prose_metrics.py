#!/usr/bin/env python3
"""Diagnose the reader-facing prose of a destiny-matrix book. Advisory only: it never gates a release."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

from book_html import BookHTML, Node, is_hidden

try:  # single word list with the validator; the copy below only serves a standalone run
    from validate_book import PROCESS_TERMS, PROCESS_PATTERNS, OPENING_METHODS
except Exception:  # pragma: no cover
    PROCESS_TERMS = ("本次", "工具虚岁", "工具", "字段", "口径", "未核", "绑定", "浮点", "引擎回退", "MOSEPH",
                     "artifact", "JSON Pointer", "claim", "judge", "chief", "parallel", "tension",
                     "not_comparable", "跨会话记忆", "外部提交", "未采用", "不裁定", "审稿", "星历文件")
    PROCESS_PATTERNS = (("S0–S10", r"(?<![A-Za-z0-9])S(?:10|[0-9])(?:\.5)?(?![A-Za-z0-9])"),
                        ("sect1/2", r"sect[12]"),
                        ("ISO 时间戳", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"))
    OPENING_METHODS = ("这张盘该怎么读", "该怎么读", "读法上", "按照", "按本书", "本节", "这一节", "本章", "以下",
                       "下面先", "先说明", "需要说明", "说明一下", "严格来说", "在解读之前", "方法上")

NOTICE = "这是诊断，不是门槛：所有阈值只用于排序和提示，不拦截发布；是否修改由编辑对照 book-writer 文风节判断。"

# Thresholds rank and hint; none of them is a pass/fail line.
LONG_SENTENCE = 60
LONG_PARAGRAPH = 280
OPENING_PARAGRAPH = 120
JARGON_UNEXPLAINED = 4
JARGON_DENSE = 6
HINTS = {"negation_sentence_ratio": 0.15, "process_per_k": 1.0, "opening_non_judgement": 0.30,
         "long_sentence_ratio": 0.10, "limitation_share": 0.12}

SKIP_TAGS = frozenset(("figure", "table", "nav", "details", "footer", "svg", "script", "style", "template",
                       "noscript", "header", "form", "button"))
HEADINGS = frozenset(("h1", "h2", "h3", "h4", "h5", "h6"))
BLOCKS = frozenset(("p", "li", "dd", "blockquote"))
CONTAINERS = frozenset(("div", "section", "aside", "article", "main", "body", "dl", "ul", "ol"))

HAN = re.compile(r"[㐀-鿿]")
LATIN_WORD = re.compile(r"[A-Za-z0-9]+(?:[.\-'][A-Za-z0-9]+)*")
SENTENCE = re.compile(r"[^。！？；!?\n]+[。！？；!?…]*[”’」』）)]*")
TERMINATOR = re.compile(r"[。！？；!?]")

# Longest first; 是不是/能不能 are questions, not limitations.
NEGATIONS = ("不能说明", "不能证明", "不意味着", "不意味", "不代表", "不等于", "不属于", "不构成", "不表示",
             "不证明", "不说明", "不承诺", "不预示", "不是", "不能", "不得", "不应", "不宜", "不算", "不作", "不可",
             "并不", "并非", "而非", "无法", "别把")
NEGATION_RE = re.compile(r"(?<![是能])(?:" + "|".join(map(re.escape, NEGATIONS)) + ")")
NOT_BUT_RE = re.compile(r"(?:不是|并非|不在于)[^。！？；!?\n]{1,40}?[，,]?而(?:是|在于)")
NOT_BUT_SPLIT_RE = re.compile(r"(?:不是|并非|不在于)[^。！？；!?\n]{1,40}[。；!?！？]\s*而(?:是|在于)")
# Fixed phrases that contain a negation word without limiting anything.
IDIOMS = ("不得不", "不能不", "不可不", "不可思议", "不可或缺", "不可开交", "不可多得", "不可磨灭", "不可收拾",
          "不可一世", "不可救药", "不可避免", "不得了", "不得已", "不得而知", "不能自已", "不能自拔", "不是滋味",
          "无法无天", "并不见得")
IDIOM_RE = re.compile("|".join(map(re.escape, IDIOMS)))
TITLE_MARK_RE = re.compile(r"《[^》]*》|〈[^〉]*〉")
QUOTE_RE = re.compile(r"“[^”]*”|「[^」]*」|『[^』]*』")
MASKABLE = re.compile(r"[^\s，。！？；：、,.!?;:“”‘’「」『』（）()《》〈〉…—]")
TITLE_NEGATION_RE = re.compile(r"(?:^|[，,：:、—\s])(?:而)?(?:不是|并非|不等于|不代表|而非|不能|不必|别把|不只是)")

HEDGES = ("在某种程度上", "某种程度上", "一定程度上", "某种意义上", "或多或少", "可能", "也许", "或许", "大概",
          "似乎", "恐怕", "未必", "说不定")
HEDGE_RE = re.compile("|".join(map(re.escape, HEDGES)))

VOICE_LABELS = (
    ("在…的读法里", r"在[^，。；！？\n]{1,16}的(?:常见)?(?:读法|讲法|看法|语境)(?:里|中)"),
    ("按…派／按…的读法", r"按[^，。；！？\n]{1,12}(?:派|的(?:读法|讲法|取法|算法|看法))|[按照依](?:这个|这一|这种|这条|这几种|这三种|这两种|这张盘的|这本书的)(?:读法|讲法|看法)|[依照][^，。；！？\n]{1,12}的(?:读法|讲法|看法)"),
    ("传统上", r"传统上|传统里|传统中|在传统[^，。；！？\n]{0,6}(?:里|中)|传统的讲法|传统叫|古人"),
    ("体系里的讲法", r"(?:八字|紫微|斗数|占星|星盘|子平|命理)(?:(?:里|中)[，,]?(?:把|讲|说|看|称|叫|常见)?|看见|看到|讲的是|眼里|看来)"),
    ("常见读法", r"常见(?:的)?(?:读法|讲法)"),
    ("子平家／斗数家／占星师", r"子平家?|斗数家|占星师|占星学里|命理家"),
    ("排盘显示", r"排盘显示|盘面显示|星盘显示|排盘软件"),
    ("测验／量表事实", r"原始分|你在[^，。；！？\n]{1,20}上(?:的)?得分|测验(?:给出|记下|把)"),
    ("如果它适用于你", r"如果(?:它|这条|这个假说|这一条)[^，。；！？\n]{0,6}(?:适用于|贴合)你"),
    ("一种…看法是", r"一种[^，。；！？\n]{0,12}(?:看法|假说|解释)是|这是(?:一个|一条)假说|假说"),
    ("如果你想试试", r"如果你(?:想|愿意)(?:试|做)"),
)
VOICE_RE = tuple((label, re.compile(pattern)) for label, pattern in VOICE_LABELS)

MIRROR_EXAMPLE_RE = re.compile(r"例如|比如|比方说|譬如")
MIRROR_IF_RE = re.compile(r"如果|假如|假设|要是|设想")
MIRROR_OPENING_RE = re.compile(r"^(?:例如|比如|比方说|譬如|假如|假设|设想|如果你|要是你)")
FALSIFIABLE_RE = re.compile(r"不太贴合|不怎么贴合|贴合得不多|不大贴合|就不贴合|不太像[你他她]|落了空|落空了|对不上"
                            r"|说的就?不是[你他她]|(?:读法|这一条|这条|假说)[^，。；]{0,10}不成立")

# Opening-sentence types.
SUBJECTS = ("你", "这张盘", "这张命盘", "这张星盘", "这张四柱", "这组分数", "这份分数", "这组数字", "盘里", "盘中",
            "四柱里", "星盘里", "孩子", "他", "她")
LEADING_LABEL_RE = re.compile(
    r"^(?:在[^，。；！？]{1,16}的(?:常见)?(?:读法|讲法|看法)(?:里|中)|按[^，。；！？]{1,12}(?:派|的(?:读法|讲法|取法|看法))|[按照依](?:这个|这一|这种|这条|这张盘的|这本书的)(?:读法|讲法|看法)|[依照][^，。；！？]{1,12}的(?:读法|讲法|看法)|子平家看来|占星师会说|在(?:斗数|子平|占星)眼里"
    r"|传统上(?:常见的讲法是)?|排盘显示|子平家(?:看|说|讲)?[^，。；！？]{0,8}|三种读法|几种读法)[，,：:]?")
OPENING_DENIALS = ("不是", "并不", "并非", "不代表", "不等于", "不意味", "不能", "不证明", "不说明", "不表示", "无法", "没有资格")
OPENING_LIMITS = ("需要注意", "需注意", "请注意", "注意", "由于", "受限于", "限于", "前提是", "仅", "只能", "只在",
                  "本书只", "这里只", "严格来说", "目前", "现有资料", "量程", "出生时间只", "因为资料")
METHOD_WORDS = ("本章", "本节", "这一章", "这一节", "本次", "本书采用", "采用", "取法", "算法", "口径", "读法上", "方法上",
                "读法为主", "先说明", "下面", "以下", "我们先", "先看", "先读", "先在图上", "再看", "使用的是", "依据的是",
                "计数", "官网")

# Built-in glossary; extend or replace with --terms.
TERMS_BAZI = ("日主", "日元", "日干", "月令", "旺衰", "身强", "身弱", "身旺", "格局", "用神", "喜神", "忌神", "喜用", "十神",
              "正官", "七杀", "偏官", "正印", "偏印", "枭神", "正财", "偏财", "食神", "伤官", "比肩", "劫财", "官杀",
              "食伤", "印星", "财星", "比劫", "印绶", "调候", "扶抑", "通关", "通根", "透干", "透出", "藏干", "本气",
              "中气", "余气", "得令", "失令", "得地", "得势", "大运", "流年", "纳音", "空亡", "六合", "三合", "三会",
              "半合", "刑冲", "相冲", "相刑", "相害", "伤官见官", "财多身弱", "杀印相生", "食神制杀", "官印相生",
              "伤官配印", "伤官生财", "食神生财", "财滋弱杀", "羊刃", "建禄", "从格", "化气")
TERMS_ZIWEI = ("命宫", "身宫", "三方四正", "三方", "对宫", "空宫", "借星", "四化", "化禄", "化权", "化科", "化忌",
               "生年四化", "主星", "辅星", "煞星", "庙旺", "落陷", "紫微星", "天机", "武曲", "天同", "廉贞",
               "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "破军", "左辅", "右弼", "文昌", "文曲", "天魁", "天钺",
               "擎羊", "陀罗", "铃星", "地空", "地劫", "禄存", "天马", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
               "迁移宫", "交友宫", "仆役宫", "官禄宫", "田宅宫", "福德宫", "父母宫", "大限", "小限", "机月同梁",
               "杀破狼", "紫府", "日月", "阳梁昌禄", "五行局")
TERMS_ASTRO = ("上升点", "上升星座", "上升", "下降点", "天顶", "中天", "天底", "命主星", "盘主", "守护星", "定位星",
               "合相", "对分相", "对分", "四分相", "刑相", "三分相", "拱相", "六分相", "相位", "容许度", "入相位",
               "出相位", "逆行", "入庙", "入旺", "失势", "落陷", "互容", "宫头", "宫主星", "角宫", "续宫", "果宫",
               "始宫", "北交点", "南交点", "凯龙",
               "日月升", "元素", "三分性", "基本宫", "固定宫", "变动宫", "Placidus", "ASC", "MC", "IC", "DSC")
TERMS_JUNG = ("认知功能", "八功能", "主导功能", "辅助功能", "第三功能", "劣势功能", "功能栈", "阴影功能", "外倾情感",
              "内倾情感", "外倾思维", "内倾思维", "外倾直觉", "内倾直觉", "外倾感觉", "内倾感觉", "判断功能",
              "感知功能", "英雄位", "父母位", "永恒少年", "阿尼玛", "阿尼姆斯", "对立人格", "批评者", "捣蛋鬼",
              "恶魔位", "Fe", "Fi", "Te", "Ti", "Ne", "Ni", "Se", "Si", "MBTI", "Beebe")
TYPE_CODE = r"[EI][NS][TF][JP]"
GLOSS_AFTER = r"[”’」』]?(?:（|\(|[）)]?[，、]?(?:也就是|就是|指的是|是指|指|即|意思是|代表|在[^，。；]{1,10}里?管|管|说的是|讲的?是?|看的是|是|主))"
GLOSS_BEFORE = r"(?:叫作|叫做|称为|称作|称之为|叫|所谓|名为|名叫|术语是)[“‘「『]?"


OPENING_NAMES = {"judgement": "判断", "mirror": "镜像", "chart_fact": "盘面罗列", "method": "方法说明", "limitation": "限定",
                 "denial": "否认", "other": "其他"}


class InputFailure(Exception):
    pass


def clean(text: str) -> str:
    """Collapse whitespace only; NFKC would turn ，；： into ASCII and blur sentence boundaries."""
    return " ".join(text.split())


def count_chars(text: str) -> int:
    """Chinese word count: one per Han character, one per Latin/number token."""
    return len(HAN.findall(text)) + len(LATIN_WORD.findall(HAN.sub(" ", text)))


def _blank(match: re.Match) -> str:
    return MASKABLE.sub("□", match.group(0))


def mask_for_negation(text: str) -> tuple[str, str]:
    """(author, quoted): fixed phrases and titles blanked; quoted speech moved to its own copy.

    Blanking keeps length and punctuation, so both copies split into the same sentences as the text."""
    base = TITLE_MARK_RE.sub(_blank, IDIOM_RE.sub(_blank, FALSIFIABLE_RE.sub(_blank, text)))  # 落空支另计
    author = QUOTE_RE.sub(_blank, base)
    quoted = "".join(b if a == "□" and b != "□" else ("□" if MASKABLE.match(b) else b)
                     for a, b in zip(author, base))
    return author, quoted


def split_sentences(text: str) -> list[str]:
    return [s for s in (clean(m.group(0)) for m in SENTENCE.finditer(text)) if count_chars(s)]


def snippet(text: str, limit: int = 60) -> str:
    text = clean(text)
    return text if len(text) <= limit else text[:limit] + "…"


def _own_text(node: Node) -> str:
    return "".join(c.children[0] for c in node.children
                   if isinstance(c, Node) and c.tag == "#text" and c.children)


def _link_only(node: Node) -> bool:
    linked = "".join(a.text() for a in node.descendants() if a.tag == "a")
    rest = node.text()
    for part in (a.text() for a in node.descendants() if a.tag == "a"):
        rest = rest.replace(part, "", 1)
    return bool(linked) and not HAN.search(rest)


def _walk(node: Node, chapter: dict, limited: bool, new_chapter=None) -> dict:
    """Collect headings and prose blocks in document order; returns the chapter in effect."""
    for child in node.children:
        if not isinstance(child, Node) or child.tag.startswith("#") or is_hidden(child):
            continue
        if child.tag in SKIP_TAGS:
            continue
        if new_chapter is not None:
            kind = child.attr("data-content-kind")
            marker = " ".join(filter(None, (child.attr("class"), child.attr("id")))).lower()
            if kind in ("appendix", "disclosure") or "appendix" in marker or "disclosure" in marker:
                continue
        if child.tag in HEADINGS:
            text = clean(child.text())
            if new_chapter is not None and child.tag == new_chapter["tag"]:
                chapter = new_chapter["make"](text)
            if text:
                chapter["headings"].append({"level": int(child.tag[1]), "text": text})
            continue
        in_limit = limited or child.has_attr("data-limitation-id") or child.has_attr("data-disclosure-id")
        nested = any(isinstance(c, Node) and c.tag in (BLOCKS | CONTAINERS | HEADINGS) for c in child.children)
        if child.tag in BLOCKS and not nested:
            text = clean(child.text())
            if text and not _link_only(child):
                chapter["blocks"].append({"text": text, "tag": child.tag, "limitation": in_limit})
            continue
        if child.tag in CONTAINERS | BLOCKS:
            own = clean(_own_text(child))
            if HAN.search(own):
                chapter["blocks"].append({"text": own, "tag": child.tag, "limitation": in_limit})
        chapter = _walk(child, chapter, in_limit, new_chapter)
    return chapter


def collect_chapters(book: BookHTML) -> tuple[list[dict], str]:
    body = [s for s in book.sections if s.attr("data-content-kind") == "body" and not is_hidden(s)]
    chapters: list[dict] = []
    if body:
        for section in body:
            chapter = {"id": str(section.attr("data-section-id") or section.attr("id") or len(chapters) + 1),
                       "headings": [], "blocks": []}
            _walk(section, chapter, False)
            chapter["title"] = next((h["text"] for h in chapter["headings"]), "")
            chapters.append(chapter)
        return chapters, "semantic"
    # Older books without content kinds: split at the top heading level, leave appendices out.
    root = next((n for n in book.nodes if n.tag == "main"), None) or \
        next((n for n in book.nodes if n.tag == "body"), None) or book.root
    found = [n.tag for n in root.descendants() if n.tag in ("h1", "h2", "h3", "h4")]
    # h2 when the book has it; otherwise the shallowest level that repeats (h1 alone is the book title).
    level = "h2" if "h2" in found else next(
        (t for t in ("h1", "h3", "h4") if found.count(t) >= 2), next((t for t in ("h3", "h1", "h4") if t in found), "h2"))

    def make(title: str) -> dict:
        chapters.append({"id": "c%02d" % (len(chapters) + 1), "title": title, "headings": [], "blocks": []})
        return chapters[-1]

    front = {"id": "front", "title": "", "headings": [], "blocks": []}
    _walk(root, front, False, {"tag": level, "make": make})
    if front["blocks"]:
        chapters.insert(0, front)
    return [c for c in chapters if c["blocks"]], "fallback"


def load_terms(path: str | None, replace: bool) -> list[str]:
    terms = [] if replace else list(TERMS_BAZI + TERMS_ZIWEI + TERMS_ASTRO + TERMS_JUNG)
    if path:
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise InputFailure(f"无法读取术语表: {exc}") from exc
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                loaded = [t for group in loaded.values() for t in (group if isinstance(group, list) else [group])]
        except json.JSONDecodeError:
            loaded = [line.split("#", 1)[0].strip() for line in raw.splitlines()]
        if not isinstance(loaded, list) or not all(isinstance(t, str) for t in loaded):
            raise InputFailure("术语表须为每行一词的文本，或 JSON 字符串数组／分组对象")
        terms.extend(t.strip() for t in loaded if t.strip())
    if not terms:
        raise InputFailure("术语表为空")
    return sorted(set(terms), key=lambda t: (-len(t), t))


def term_pattern(terms: list[str]) -> re.Pattern:
    parts = [r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])" if t.isascii() else re.escape(t) for t in terms]
    parts.append(r"(?<![A-Za-z])" + TYPE_CODE + r"(?![A-Za-z])")
    return re.compile("|".join(parts))


def is_glossed(sentence: str, term: str) -> bool:
    t = re.escape(term)
    return bool(re.search(t + GLOSS_AFTER, sentence) or re.search(GLOSS_BEFORE + t, sentence)
                or re.search(r"[“‘「『（(]" + t + r"[”’」』）)]", sentence))


def classify_opening(sentence: str, terms_re: re.Pattern | None = None) -> str:
    """Type of the first sentence of a chapter or long paragraph.

    judgement: about the reader, this chart or these scores; mirror: a marked hypothetical scene; chart_fact: lists positions without reaching the
    reader; method / limitation / denial: what book-writer 文风 §1–§2 keeps out of openings; other: the rest."""
    text = sentence.lstrip("“\"「（(")
    if MIRROR_OPENING_RE.match(text):
        return "mirror"
    if any(text.startswith(w) for w in OPENING_METHODS):
        return "method"
    core = LEADING_LABEL_RE.sub("", text, count=1)
    clause = re.split(r"[，,：:]", core, maxsplit=1)[0]
    subject = any(core.startswith(w) for w in SUBJECTS) or any(w in core[:14] for w in ("你", "这张盘", "这组分数"))
    if any(clause.startswith(w) for w in ("这不", "这并", "这里不", "本书不", "它不", "这些不", "以上不")) or \
            any(clause.startswith(w) for w in OPENING_DENIALS) or (subject and NEGATION_RE.search(clause)):
        return "denial"
    if any(text.startswith(w) for w in OPENING_LIMITS):
        return "limitation"
    if any(w in clause for w in METHOD_WORDS) and not core.startswith("你"):
        return "method"
    if subject:
        return "judgement"
    if NEGATION_RE.search(core):
        return "denial"
    if terms_re is not None and terms_re.search(core):
        return "chart_fact"
    return "other"


def _distribution(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "mean": 0, "median": 0, "p90": 0, "max": 0}
    ordered = sorted(values)
    return {"count": len(ordered), "mean": round(statistics.fmean(ordered), 1),
            "median": statistics.median(ordered), "p90": ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))],
            "max": ordered[-1]}


def _process_hits(text: str) -> list[tuple[int, str, str]]:
    hits = []
    for word in PROCESS_TERMS:
        pattern = re.escape(word) if not word.isascii() else r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])"
        hits.extend((m.start(), m.group(0), word) for m in re.finditer(pattern, text, re.I))
    for label, pattern in PROCESS_PATTERNS:
        hits.extend((m.start(), m.group(0), label) for m in re.finditer(pattern, text))
    kept, covered = [], []
    for index, matched, term in sorted(hits, key=lambda h: (h[0], -len(h[1]))):
        if any(a <= index < b for a, b in covered):
            continue
        covered.append((index, index + len(matched)))
        kept.append((index, matched, term))
    return kept


def analyse_chapter(chapter: dict, terms_re: re.Pattern, explained: set[str]) -> dict:
    blocks = chapter["blocks"]
    chars = sum(count_chars(b["text"]) for b in blocks)
    limit_chars = sum(count_chars(b["text"]) for b in blocks if b["limitation"])
    sentences, sentence_lengths, paragraph_lengths = 0, [], []
    negation_hits = negation_sentences = not_but = hedge_stacked_count = dashes = quoted_negations = 0
    negation_terms: dict[str, int] = {}
    paragraphs, long_sentences, long_paragraphs, stacked, jargon, process, openings = [], [], [], [], [], [], []
    voice = {label: 0 for label, _ in VOICE_RE}
    mirrors = {"example": 0, "conditional": 0, "falsifiable": 0}
    first_prose = True
    for index, block in enumerate(blocks):
        text, where = block["text"], "%s:b%d" % (chapter["id"], index)
        size = count_chars(text)
        paragraph_lengths.append(size)
        if size > LONG_PARAGRAPH:
            long_paragraphs.append({"location": where, "chars": size, "snippet": snippet(text)})
        block_hits = 0
        parts = split_sentences(text)
        author, quoted = mask_for_negation(text)
        # same spans as the visible sentences, read from the blanked copy
        author_parts = [author[m.start():m.end()] for m in SENTENCE.finditer(text) if count_chars(clean(m.group(0)))]
        quoted_negations += len(NEGATION_RE.findall(quoted))
        not_but += len(NOT_BUT_SPLIT_RE.findall(author))
        # 首现即释 is judged per paragraph: a gloss anywhere in the paragraph covers its sentences.
        explained |= {m.group(0) for part in parts for m in terms_re.finditer(part) if is_glossed(part, m.group(0))}
        for s_index, sentence in enumerate(parts):
            sentences += 1
            length = count_chars(sentence)
            sentence_lengths.append(length)
            if length > LONG_SENTENCE:
                long_sentences.append({"location": where, "chars": length, "snippet": snippet(sentence)})
            found = NEGATION_RE.findall(author_parts[s_index])
            if found:
                negation_sentences += 1
                negation_hits += len(found)
                block_hits += len(found)
                for word in found:
                    negation_terms[word] = negation_terms.get(word, 0) + 1
            not_but += len(NOT_BUT_RE.findall(author_parts[s_index]))
            hedges = HEDGE_RE.findall(sentence)
            if len(hedges) >= 2:
                hedge_stacked_count += 1
                stacked.append({"location": where, "hedges": hedges, "snippet": snippet(sentence)})
            seen = list(dict.fromkeys(m.group(0) for m in terms_re.finditer(sentence)))
            unexplained = [t for t in seen if t not in explained]
            if len(unexplained) >= JARGON_UNEXPLAINED or len(seen) >= JARGON_DENSE:
                jargon.append({"location": where, "terms": seen, "unexplained": unexplained,
                               "snippet": snippet(sentence)})
        dashes += text.count("——")
        for label, pattern in VOICE_RE:
            voice[label] += len(pattern.findall(text))
        mirrors["example"] += len(MIRROR_EXAMPLE_RE.findall(text))
        mirrors["conditional"] += len(MIRROR_IF_RE.findall(text))
        mirrors["falsifiable"] += len(FALSIFIABLE_RE.findall(text))
        for position, matched, term in _process_hits(text):
            process.append({"location": where, "term": term, "snippet": snippet(_sentence_at(text, position))})
        if size:
            paragraphs.append({"location": where, "chars": size, "negations": block_hits,
                               "per_100": round(block_hits * 100 / size, 2), "snippet": snippet(text)})
        has_sentence = bool(parts) and bool(TERMINATOR.search(text))
        if not has_sentence or block["limitation"]:
            continue  # subtitles, labels and limitation boxes are not chapter openings
        role = "chapter" if first_prose else ("long_paragraph" if size >= OPENING_PARAGRAPH else None)
        first_prose = False
        if role:
            openings.append({"location": where, "role": role, "type": classify_opening(parts[0], terms_re),
                             "snippet": snippet(parts[0])})
    titles = [{"location": chapter["id"], "level": h["level"], "text": h["text"]}
              for h in chapter["headings"] if TITLE_NEGATION_RE.search(h["text"])]
    counts = {k: sum(1 for o in openings if o["type"] == k)
              for k in OPENING_NAMES}
    return {
        "id": chapter["id"], "title": chapter["title"], "chars": chars, "paragraphs": len(blocks),
        "sentences": sentences, "headings": len(chapter["headings"]),
        "limitation_blocks": sum(1 for b in blocks if b["limitation"]),
        "limitation_share": round(limit_chars / chars, 3) if chars else 0,
        "negation": {"hits": negation_hits, "sentences": negation_sentences,
                     "sentence_ratio": round(negation_sentences / sentences, 3) if sentences else 0,
                     "per_k": round(negation_hits * 1000 / chars, 2) if chars else 0,
                     "not_but": not_but, "quoted": quoted_negations, "terms": dict(sorted(negation_terms.items(), key=lambda kv: -kv[1]))},
        "process_terms": process, "title_negations": titles,
        "openings": {"items": openings, "counts": counts,
                     "judgement_ratio": round(counts["judgement"] / len(openings), 3) if openings else None},
        "voice_labels": {"total": sum(voice.values()), "by_label": {k: v for k, v in voice.items() if v}},
        "mirrors": mirrors, "hedge_stacking": stacked, "jargon": jargon, "dashes": dashes,
        "sentence_length": _distribution(sentence_lengths), "paragraph_length": _distribution(paragraph_lengths),
        "long_sentences": long_sentences, "long_paragraphs": long_paragraphs, "_paragraphs": paragraphs,
    }


def _sentence_at(text: str, index: int) -> str:
    left = max((text.rfind(d, 0, index) + 1 for d in "。！？；!?"), default=0)
    ends = [pos for pos in (text.find(d, index) for d in "。！？；!?") if pos >= 0]
    return text[left:(min(ends) + 1) if ends else len(text)]


def chapter_problems(row: dict) -> tuple[float, list[str]]:
    """Editing priority for one chapter: a ranking aid built from the hints above, not a score to pass."""
    score, notes = 0.0, []
    if not row["chars"]:
        return 0.0, []  # a chapter of tables and figures only has no prose to edit

    def add(weight: float, note: str):
        nonlocal score
        score += weight
        notes.append((weight, note))

    ratio = row["negation"]["sentence_ratio"]
    if ratio > HINTS["negation_sentence_ratio"]:
        add(min(3.0, ratio / HINTS["negation_sentence_ratio"]),
            "否定限定句占 %d%%（%d 处）" % (round(ratio * 100), row["negation"]["hits"]))
    if row["chars"]:
        per_k = len(row["process_terms"]) * 1000 / row["chars"]
        if per_k > HINTS["process_per_k"]:
            add(min(3.0, per_k / HINTS["process_per_k"]), "流程词 %d 处" % len(row["process_terms"]))
    openings = row["openings"]
    if openings["items"]:
        facing = openings["counts"]["judgement"] + openings["counts"]["mirror"]
        off = 1 - facing / len(openings["items"])
        if off > HINTS["opening_non_judgement"]:
            add(min(3.0, off / HINTS["opening_non_judgement"]),
                "章首与长段首句只有 %d/%d 句落在读者或本盘上" % (facing, len(openings["items"])))
        if openings["items"][0]["role"] == "chapter" and openings["items"][0]["type"] != "judgement":
            add(1.0, "章首句属于“%s”" % OPENING_NAMES[openings["items"][0]["type"]])
    if row["mirrors"]["example"] + row["mirrors"]["conditional"] == 0:
        add(2.0, "没有任何假设镜像标记（例如／如果／假如）")
    elif row["mirrors"]["falsifiable"] == 0:
        add(0.5, "有镜像但没有“不太贴合”的落空一支")
    if row["title_negations"]:
        add(min(2.0, 0.5 * len(row["title_negations"])), "标题含否定式 %d 个" % len(row["title_negations"]))
    if row["jargon"]:
        add(min(2.0, 0.4 * len(row["jargon"])), "术语密集或连用未释术语的句子 %d 句" % len(row["jargon"]))
    if row["hedge_stacking"]:
        add(min(1.5, 0.5 * len(row["hedge_stacking"])), "虚词连用 %d 句" % len(row["hedge_stacking"]))
    if row["sentences"]:
        long_ratio = len(row["long_sentences"]) / row["sentences"]
        if long_ratio > HINTS["long_sentence_ratio"]:
            add(min(2.0, long_ratio / HINTS["long_sentence_ratio"]), "过长的句子 %d 句" % len(row["long_sentences"]))
    if row["long_paragraphs"]:
        add(min(1.5, 0.5 * len(row["long_paragraphs"])), "过长的段落 %d 段" % len(row["long_paragraphs"]))
    if row["limitation_share"] > HINTS["limitation_share"]:
        add(min(2.0, row["limitation_share"] / HINTS["limitation_share"]),
            "限制框占本章 %d%%" % round(row["limitation_share"] * 100))
    if row["voice_labels"]["total"] == 0 and row["chars"] >= 300:
        add(1.0, "没有声源标签")
    notes.sort(key=lambda item: -item[0])
    return round(score, 2), [note for _, note in notes]





def analyse(book: BookHTML, terms: list[str], top: int = 5, snippets: bool = True) -> dict:
    chapters, structure = collect_chapters(book)
    if not chapters or not any(c["blocks"] for c in chapters):
        raise InputFailure("没有找到正文：需要 data-content-kind=\"body\" 的 section，或带标题的正文段落")
    explained: set[str] = set()
    terms_re = term_pattern(terms)
    rows = [analyse_chapter(c, terms_re, explained) for c in chapters]
    paragraphs = [p for r in rows for p in r.pop("_paragraphs")]
    dense = sorted((p for p in paragraphs if p["negations"] >= 2),
                   key=lambda p: (-p["per_100"], -p["negations"], p["location"]))[:top]
    chars = sum(r["chars"] for r in rows)
    sentences = sum(r["sentences"] for r in rows)
    openings = [o for r in rows for o in r["openings"]["items"]]
    counts = {k: sum(1 for o in openings if o["type"] == k) for k in OPENING_NAMES}
    hits = sum(r["negation"]["hits"] for r in rows)
    negation_sentences = sum(r["negation"]["sentences"] for r in rows)
    negation_terms: dict[str, int] = {}
    voice: dict[str, int] = {}
    for r in rows:
        for k, v in r["negation"]["terms"].items():
            negation_terms[k] = negation_terms.get(k, 0) + v
        for k, v in r["voice_labels"]["by_label"].items():
            voice[k] = voice.get(k, 0) + v
    process_terms: dict[str, int] = {}
    for r in rows:
        for hit in r["process_terms"]:
            process_terms[hit["term"]] = process_terms.get(hit["term"], 0) + 1
    ranking = []
    for r in rows:
        score, notes = chapter_problems(r)
        r["priority"], r["problems"] = score, notes
        ranking.append({"id": r["id"], "title": r["title"], "priority": score, "problems": notes[:4]})
    ranking.sort(key=lambda item: -item["priority"])
    headings = sum(r["headings"] for r in rows)
    result = {
        "ok": True, "notice": NOTICE, "structure": structure,
        "thresholds": {"long_sentence": LONG_SENTENCE, "long_paragraph": LONG_PARAGRAPH,
                       "opening_paragraph": OPENING_PARAGRAPH, "jargon_unexplained": JARGON_UNEXPLAINED,
                       "jargon_dense": JARGON_DENSE, **HINTS},
        "totals": {
            "chapters": len(rows), "chars": chars, "paragraphs": sum(r["paragraphs"] for r in rows),
            "sentences": sentences, "headings": headings,
            "negation": {"hits": hits, "sentences": negation_sentences,
                         "sentence_ratio": round(negation_sentences / sentences, 3) if sentences else 0,
                         "per_k": round(hits * 1000 / chars, 2) if chars else 0,
                         "not_but": sum(r["negation"]["not_but"] for r in rows),
                         "quoted": sum(r["negation"]["quoted"] for r in rows),
                         "terms": dict(sorted(negation_terms.items(), key=lambda kv: -kv[1])),
                         "densest_paragraphs": dense},
            "process_terms": {"hits": sum(process_terms.values()),
                              "per_k": round(sum(process_terms.values()) * 1000 / chars, 2) if chars else 0,
                              "terms": dict(sorted(process_terms.items(), key=lambda kv: -kv[1]))},
            "title_negations": {"count": sum(len(r["title_negations"]) for r in rows), "headings": headings},
            "openings": {"count": len(openings), "counts": counts,
                         "judgement_ratio": round(counts["judgement"] / len(openings), 3) if openings else None,
                         "chapter_openings": {k: sum(1 for o in openings if o["role"] == "chapter" and o["type"] == k)
                                              for k in OPENING_NAMES}},
            "voice_labels": {"total": sum(voice.values()), "per_k": round(sum(voice.values()) * 1000 / chars, 2) if chars else 0,
                             "by_label": dict(sorted(voice.items(), key=lambda kv: -kv[1]))},
            "mirrors": {"example": sum(r["mirrors"]["example"] for r in rows),
                        "conditional": sum(r["mirrors"]["conditional"] for r in rows),
                        "falsifiable": sum(r["mirrors"]["falsifiable"] for r in rows),
                        "chapters_without": [r["id"] for r in rows if r["chars"]
                                             and r["mirrors"]["example"] + r["mirrors"]["conditional"] == 0],
                        "chapters_without_example": [r["id"] for r in rows
                                                     if r["chars"] and r["mirrors"]["example"] == 0]},
            "hedge_stacking": sum(len(r["hedge_stacking"]) for r in rows),
            "jargon_sentences": sum(len(r["jargon"]) for r in rows),
            "dashes": sum(r["dashes"] for r in rows),
            "limitation_blocks": sum(r["limitation_blocks"] for r in rows),
            "limitation_share": round(sum(r["limitation_share"] * r["chars"] for r in rows) / chars, 3) if chars else 0,
            "long_sentences": sum(len(r["long_sentences"]) for r in rows),
            "long_paragraphs": sum(len(r["long_paragraphs"]) for r in rows),
        },
        "chapters": rows, "summary": ranking,
    }
    if not snippets:
        _strip_snippets(result)
    return result


def _strip_snippets(value: Any) -> None:
    """Keep numbers and locations only, so a report can be shared without quoting the book."""
    if isinstance(value, dict):
        for key in ("snippet", "text"):
            value.pop(key, None)
        if "title" in value:
            value["title"] = ""
        for child in value.values():
            _strip_snippets(child)
    elif isinstance(value, list):
        for child in value:
            _strip_snippets(child)


def render(result: dict, top: int) -> str:
    t = result["totals"]
    out = ["命书文风诊断", NOTICE, ""]
    if result["structure"] == "fallback":
        out.append("（未找到 data-content-kind 语义结构，已按标题切分正文；附录按 class/id 排除，统计仅供参考。）")
    out.append("全书：%d 章，%d 字，%d 段，%d 句，%d 个标题" %
               (t["chapters"], t["chars"], t["paragraphs"], t["sentences"], t["headings"]))
    out.append("")
    out.append("分章概览")
    out.append("  章节 | 字数 | 否定句占比 | 否定/千字 | 流程词 | 声源标签 | 例如 | 如果类 | 首句为判断")
    for r in result["chapters"]:
        ratio = r["openings"]["judgement_ratio"]
        out.append("  %s | %d | %d%% | %.1f | %d | %d | %d | %d | %s" % (
            r["id"], r["chars"], round(r["negation"]["sentence_ratio"] * 100), r["negation"]["per_k"],
            len(r["process_terms"]), r["voice_labels"]["total"], r["mirrors"]["example"],
            r["mirrors"]["conditional"], "—" if ratio is None else "%d%%" % round(ratio * 100)))
    n = t["negation"]
    out += ["", "否定限定句：%d 处，出现在 %d 句（占全部句子 %d%%），每千字 %.1f 处；“不是……而是”%d 处" %
            (n["hits"], n["sentences"], round(n["sentence_ratio"] * 100), n["per_k"], n["not_but"])]
    out.append("  已排除：固定词组（不得不、不可思议等）与书名号内的词；引号内的否定另计 %d 处，不进上面的数字" % n["quoted"])
    if n["terms"]:
        out.append("  用词：" + "、".join("%s %d" % kv for kv in list(n["terms"].items())[:10]))
    for p in n["densest_paragraphs"]:
        out.append("  密度最高 %s：%d 字 %d 处 %s" % (p["location"], p["chars"], p["negations"], p.get("snippet", "")))
    p = t["process_terms"]
    out += ["", "流程词：%d 处（每千字 %.1f）" % (p["hits"], p["per_k"])]
    if p["terms"]:
        out.append("  " + "、".join("%s %d" % kv for kv in p["terms"].items()))
    for r in result["chapters"]:
        for hit in r["process_terms"][:top]:
            out.append("  %s [%s] %s" % (hit["location"], hit["term"], hit.get("snippet", "")))
    out += ["", "标题里的否定式：%d / %d" % (t["title_negations"]["count"], t["title_negations"]["headings"])]
    for r in result["chapters"]:
        for title in r["title_negations"]:
            out.append("  %s h%d %s" % (title["location"], title["level"], title.get("text", "")))
    o = t["openings"]
    out += ["", "章首句与长段首句（共 %d 句）：%s" % (
        o["count"], "，".join("%s %d" % (OPENING_NAMES[k], v) for k, v in o["counts"].items()))]
    if o["judgement_ratio"] is not None:
        out.append("  以“你／这张盘／这组分数”为主语的判断占 %d%%；章首句：%s" % (
            round(o["judgement_ratio"] * 100),
            "，".join("%s %d" % (OPENING_NAMES[k], v) for k, v in o["chapter_openings"].items() if v)))
    for r in result["chapters"]:
        for item in r["openings"]["items"]:
            if item["type"] not in ("judgement", "mirror"):
                out.append("  %s [%s] %s" % (item["location"], OPENING_NAMES[item["type"]], item.get("snippet", "")))
    v = t["voice_labels"]
    out += ["", "声源标签：%d 次（每千字 %.1f）" % (v["total"], v["per_k"])]
    if v["by_label"]:
        out.append("  " + "、".join("%s %d" % kv for kv in v["by_label"].items()))
    m = t["mirrors"]
    out += ["", "假设镜像标记：例如类 %d，如果类 %d，“不太贴合”落空支 %d" % (m["example"], m["conditional"], m["falsifiable"])]
    out.append("  一个标记都没有的章：" + ("、".join(m["chapters_without"]) or "无"))
    out.append("  没有“例如”类标记的章：" + ("、".join(m["chapters_without_example"]) or "无"))
    out += ["", "虚词连用（同句两个以上）：%d 句" % t["hedge_stacking"]]
    for r in result["chapters"]:
        for item in r["hedge_stacking"][:top]:
            out.append("  %s %s %s" % (item["location"], "／".join(item["hedges"]), item.get("snippet", "")))
    out += ["", "术语密集句（一句内未释术语 ≥%d 个，或术语 ≥%d 个）：%d 句" %
            (JARGON_UNEXPLAINED, JARGON_DENSE, t["jargon_sentences"])]
    for r in result["chapters"]:
        for item in r["jargon"][:top]:
            out.append("  %s 未释：%s %s" % (item["location"], "、".join(item["unexplained"]) or "—", item.get("snippet", "")))
    out += ["", "句长与段长（字）"]
    for r in result["chapters"]:
        s, g = r["sentence_length"], r["paragraph_length"]
        out.append("  %s 句：中位 %s／P90 %s／最长 %s；段：中位 %s／P90 %s／最长 %s；过长句 %d，过长段 %d" % (
            r["id"], s["median"], s["p90"], s["max"], g["median"], g["p90"], g["max"],
            len(r["long_sentences"]), len(r["long_paragraphs"])))
    out.append("  限制框 %d 个，占正文 %d%%；破折号 %d 处" % (
        t["limitation_blocks"], round(t["limitation_share"] * 100), t["dashes"]))
    out += ["", "汇总：最需要编辑的章（按提示信号排序，供安排顺序用）"]
    for row in result["summary"]:
        out.append("  %s（%.1f）：%s" % (row["id"], row["priority"], "；".join(row["problems"]) or "未见明显信号"))
    out += ["", NOTICE]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="destiny-matrix 成书文风诊断（只出报告，不拦截发布）")
    ap.add_argument("book", help="命书 HTML 文件")
    ap.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    ap.add_argument("--terms", help="追加的术语表：每行一词，或 JSON 数组／分组对象")
    ap.add_argument("--terms-only", action="store_true", help="只用 --terms 给出的术语，不用内置术语表")
    ap.add_argument("--top", type=int, default=5, help="每类清单列出的条数（默认 5）")
    ap.add_argument("--no-snippets", action="store_true", help="只输出统计与位置，不摘录正文与标题")
    args = ap.parse_args(argv)
    try:
        if args.top < 1:
            raise InputFailure("--top 须为正整数")
        if args.terms_only and not args.terms:
            raise InputFailure("--terms-only 需要同时给出 --terms")
        try:
            source = Path(args.book).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise InputFailure(f"无法读取命书 HTML: {exc}") from exc
        result = analyse(BookHTML(source), load_terms(args.terms, args.terms_only), args.top, not args.no_snippets)
    except InputFailure as exc:
        if args.as_json:
            print(json.dumps({"ok": False, "notice": NOTICE, "issues": [
                {"path": "input", "code": "input_error", "message": str(exc)}]}, ensure_ascii=False, indent=2))
        else:
            print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else render(result, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
