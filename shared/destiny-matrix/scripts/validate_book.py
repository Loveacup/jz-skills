#!/usr/bin/env python3
"""destiny-matrix v4 命书机器验收（V4_PLAN §6，检查 ID 对齐 references/locked-checklist.md）。

用法: python3 validate_book.py <book.html> [--plan <图表规划表.json>] [--json]
纯标准库（html.parser + re + json），零第三方依赖。任何红级 fail -> exit 1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser

# ---------- 常量（与 locked-checklist.md 锁定同步，改动需过版本升级） ----------

CHAPTER_QUOTAS = {1: 6, 2: 4, 3: 4, 4: 4, 7: 4, 8: 1}  # C2；Ch5+Ch6 合计 >=3 单独处理
COMBINED_56_QUOTA = 3
TOTAL_QUOTA = 26  # C3

# M-LEN 章节篇幅目标（占 Ch1-8 可见文本比例，%）；Ch7 无数值目标
CHAPTER_WEIGHTS = {1: (35.0, 45.0), 2: (15.0, 15.0), 3: (15.0, 15.0),
                   4: (15.0, 15.0), 5: (5.0, 5.0), 6: (5.0, 5.0), 8: (5.0, 5.0)}
LEN_TOLERANCE = 10.0  # 偏差 >10 个百分点报 warning

HARD_FORBIDDEN = ["命中注定", "这辈子注定", "天注定", "克夫", "克妻", "改命",
                  "真命天子", "真爱", "不可改变", "无法逆转", "克应", "命定"]
NEGATION_CUES = ("而非", "并非", "不是", "并不是", "不等于", "绝非", "不叫", "不算",
                 "未使用", "未用", "没有使用", "不使用", "禁用", "严禁", "避免", "禁止", "不得")
SENTENCE_DELIMITERS = "。！？；\n"
NEGATION_WINDOW = 40

# W2 语境禁词（仅计数供 finalizer 复核，不影响 exit code）
REVIEW_WORDS = ["可能", "也许", "大概率"]

# C5 锚点六图关键词启发式（在图表容器全文里匹配；机器 fail 需 finalizer 目验确认）
ANCHOR_CHARTS = {
    "八维雷达(P01)": [["雷达"]],
    "四柱全表(P08)": [["四柱"]],
    "五行权重(P02)": [["五行", "权重"], ["五行", "能量"], ["五行", "分布"], ["五行", "比例"]],
    "十二宫命盘(P06)": [["十二宫"], ["命盘"]],
    "星盘轮(P07)": [["星盘"]],
    "双轨时间线(P11)": [["双轨"], ["时间轴"], ["时间线"]],
}


class BookParser(HTMLParser):
    """单趟解析：章节边界、可见文本、图表容器、SVG 健康。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chapter = 0                 # 0 = 序/头部，1..N = 第 N 章
        self.chapter_titles = []         # h2.section-title 文本
        self.chapter_text = {}           # 章 -> 可见文本累积
        self.text_offsets = {}
        self.text_boundaries = {}
        self.skip_depth = 0              # style/script 内部
        self.h2_capture = False
        self._h2_buf = []
        # 图表容器
        self.charts = []                 # {chapter, chart_id, text, svg_count}
        self._chart_stack = []           # 嵌套深度计数（进入容器后的 div 层级）
        # SVG
        self.svgs = []                   # {chapter, viewbox, draw_elems, issues:[]}
        self._svg = None
        self._svg_depth = 0

    # -- helpers --
    @staticmethod
    def _cls(attrs):
        return dict(attrs).get("class", "") or ""

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        cls = ad.get("class", "") or ""
        if tag in ("style", "script"):
            self.skip_depth += 1
            return
        if tag == "h2" and "section-title" in cls.split():
            self.chapter += 1
            self.h2_capture = True
            self._h2_buf = []
        if tag in ("div", "p", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.text_boundaries.setdefault(self.chapter, []).append(
                self.text_offsets.get(self.chapter, 0))
        if "chart-container" in cls.split():
            self.charts.append({"chapter": self.chapter,
                                "chart_id": ad.get("data-chart-id"),
                                "text": [], "svg_count": 0})
            self._chart_stack.append(1)
        elif self._chart_stack and tag == "div":
            self._chart_stack[-1] += 1
        if tag == "svg":
            self._svg_depth += 1
            if self._svg_depth == 1:
                self._svg = {"chapter": self.chapter, "viewbox": ad.get("viewbox"),
                             "draw_elems": 0, "issues": []}
                if self._chart_stack and self.charts:
                    self.charts[-1]["svg_count"] += 1
        elif self._svg is not None:
            self._check_svg_elem(tag, ad)

    def handle_startendtag(self, tag, attrs):
        ad = dict(attrs)
        if self._svg is not None and tag != "svg":
            self._check_svg_elem(tag, ad)

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag == "h2" and self.h2_capture:
            self.h2_capture = False
            self.chapter_titles.append("".join(self._h2_buf).strip())
        if tag == "div" and self._chart_stack:
            self._chart_stack[-1] -= 1
            if self._chart_stack[-1] == 0:
                self._chart_stack.pop()
        if tag == "svg":
            if self._svg_depth == 1 and self._svg is not None:
                s = self._svg
                if not s["viewbox"]:
                    s["issues"].append("viewBox 缺失")
                else:
                    parts = s["viewbox"].replace(",", " ").split()
                    ok = len(parts) == 4
                    if ok:
                        try:
                            w, h = float(parts[2]), float(parts[3])
                            ok = w > 0 and h > 0
                        except ValueError:
                            ok = False
                    if not ok:
                        s["issues"].append("viewBox 非法: %r" % s["viewbox"])
                if s["draw_elems"] == 0:
                    s["issues"].append("无有效绘图元素")
                self.svgs.append(s)
                self._svg = None
            self._svg_depth = max(0, self._svg_depth - 1)

    def _check_svg_elem(self, tag, ad):
        s = self._svg
        ok = False
        if tag in ("polygon", "polyline"):
            pts, degenerate = _parse_points(ad.get("points", ""))
            if pts < (3 if tag == "polygon" else 2):
                s["issues"].append("%s points 过少(%d)" % (tag, pts))
            elif degenerate:
                s["issues"].append("%s points 退化（所有点重合/共点）" % tag)
            else:
                ok = True
        elif tag == "path":
            d = (ad.get("d") or "").strip()
            if not d:
                s["issues"].append("path d 为空")
            elif not re.search(r"[0-9]", d):
                s["issues"].append("path d 无坐标: %r" % d[:40])
            else:
                ok = True
        elif tag == "circle":
            ok = _fnum(ad.get("r")) > 0
            if not ok:
                s["issues"].append("circle r 非正")
        elif tag == "ellipse":
            ok = _fnum(ad.get("rx")) > 0 and _fnum(ad.get("ry")) > 0
        elif tag == "rect":
            ok = _fnum(ad.get("width")) > 0 and _fnum(ad.get("height")) > 0
        elif tag == "line":
            ok = (ad.get("x1"), ad.get("y1")) != (ad.get("x2"), ad.get("y2"))
        elif tag == "text":
            ok = True  # 文本内容在 handle_data 里，出现即认可
        if ok:
            s["draw_elems"] += 1

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.h2_capture:
            self._h2_buf.append(data)
        self.chapter_text.setdefault(self.chapter, []).append(data)
        self.text_offsets[self.chapter] = self.text_offsets.get(self.chapter, 0) + len(data)
        if self._chart_stack and self.charts:
            self.charts[-1]["text"].append(data)


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _parse_points(raw):
    """返回 (点数, 是否退化)。退化 = 全部点重合或包围盒零面积且零长度。"""
    nums = re.findall(r"-?\d+(?:\.\d+)?", raw)
    pts = [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums) - 1, 2)]
    if not pts:
        return 0, True
    xs, ys = {p[0] for p in pts}, {p[1] for p in pts}
    degenerate = len(set(pts)) == 1 or (len(xs) == 1 and len(ys) == 1)
    return len(pts), degenerate


def scan_forbidden(text_by_chapter, text_boundaries=None):
    hard_hits, review_counts = [], {w: 0 for w in REVIEW_WORDS}
    for ch, chunks in sorted(text_by_chapter.items()):
        text = "".join(chunks)
        boundaries = (text_boundaries or {}).get(ch, [])
        for w in HARD_FORBIDDEN:
            for m in re.finditer(re.escape(w), text):
                sentence_start = max(
                    (text.rfind(delimiter, 0, m.start()) + 1
                     for delimiter in SENTENCE_DELIMITERS), default=0)
                element_start = max((pos for pos in boundaries if pos <= m.start()), default=0)
                lookback_start = max(sentence_start, element_start, m.start() - NEGATION_WINDOW)
                preceding = text[lookback_start:m.start()]
                if any(cue in preceding for cue in NEGATION_CUES):
                    continue
                ctx = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ")
                hard_hits.append({"chapter": ch, "word": w, "context": ctx.strip()})
        for w in REVIEW_WORDS:
            review_counts[w] += len(re.findall(re.escape(w), text))
    return hard_hits, review_counts


def main():
    ap = argparse.ArgumentParser(description="destiny-matrix v4 命书机器验收")
    ap.add_argument("book", help="命书 HTML 文件")
    ap.add_argument("--plan", help="图表规划表 JSON（chart-director 产出）")
    ap.add_argument("--json", action="store_true", dest="as_json", help="机读输出")
    args = ap.parse_args()

    try:
        with open(args.book, encoding="utf-8") as f:
            html = f.read()
    except (OSError, UnicodeError) as e:
        print("无法读取文件: %s" % e, file=sys.stderr)
        return 2

    p = BookParser()
    p.feed(html)
    p.close()

    checks = []   # {id, level(red|warn|info), status(pass|fail|warn), detail}
    def add(cid, level, status, detail):
        checks.append({"id": cid, "level": level, "status": status, "detail": detail})

    n_ch = p.chapter
    titles = p.chapter_titles

    # ---- M1-M8 章锚点 ----
    for i in range(1, 9):
        if i <= n_ch:
            add("M%d" % i, "red", "pass", "第 %d 章锚点存在：「%s」" % (i, titles[i - 1][:40]))
        else:
            add("M%d" % i, "red", "fail", "第 %d 章锚点缺失（全书仅 %d 个 h2.section-title）" % (i, n_ch))
    if n_ch > 8:
        add("M-EXTRA", "red", "fail", "章锚点多于 8 个（%d），全书必须恰好 8 个" % n_ch)

    # ---- M-LEN 章节篇幅占比 ----
    lens = {ch: len(re.sub(r"\s", "", "".join(p.chapter_text.get(ch, []))))
            for ch in range(1, n_ch + 1)}
    total_len = sum(lens.values()) or 1
    len_rows, len_warns = [], []
    for ch in range(1, min(n_ch, 8) + 1):
        share = 100.0 * lens.get(ch, 0) / total_len
        if ch in CHAPTER_WEIGHTS:
            lo, hi = CHAPTER_WEIGHTS[ch]
            dev = (lo - share) if share < lo else (share - hi if share > hi else 0.0)
            mark = ""
            if dev > LEN_TOLERANCE:
                mark = " ← 偏差 %.1fpp" % dev
                len_warns.append("Ch%d 占比 %.1f%%（目标 %g-%g%%）" % (ch, share, lo, hi))
            len_rows.append("Ch%d %.1f%% (目标 %g-%g%%)%s" % (ch, share, lo, hi, mark))
        else:
            len_rows.append("Ch%d %.1f%% (无数值目标)" % (ch, share))
    add("M-LEN", "warn", "warn" if len_warns else "pass",
        "; ".join(len_rows) + ("；超容忍项: " + "、".join(len_warns) if len_warns else ""))

    # ---- C2/C3 图表配额 ----
    ids_in_html = [c["chart_id"] for c in p.charts if c["chart_id"] and c["chart_id"].strip()]
    missing_attr = len(p.charts) - len(ids_in_html)
    per_ch = {}
    for c in p.charts:
        if c["chart_id"] and c["chart_id"].strip():
            per_ch[c["chapter"]] = per_ch.get(c["chapter"], 0) + 1
    c2_fails = []
    for ch, quota in sorted(CHAPTER_QUOTAS.items()):
        if per_ch.get(ch, 0) < quota:
            c2_fails.append("Ch%d %d/%d" % (ch, per_ch.get(ch, 0), quota))
    combo = per_ch.get(5, 0) + per_ch.get(6, 0)
    if combo < COMBINED_56_QUOTA:
        c2_fails.append("Ch5+Ch6 %d/%d" % (combo, COMBINED_56_QUOTA))
    dist = ", ".join("Ch%d=%d" % (ch, n) for ch, n in sorted(per_ch.items()))
    add("C2", "red", "fail" if c2_fails else "pass",
        ("配额未达标: " + "; ".join(c2_fails) + "；" if c2_fails else "各章配额达标；") +
        "分布: " + (dist or "无带非空 data-chart-id 的图表容器") +
        "；缺 data-chart-id: %d 个" % missing_attr)
    total_charts = len(ids_in_html)
    add("C3", "red", "pass" if total_charts >= TOTAL_QUOTA else "fail",
        "带非空 data-chart-id 的图表容器 %d 个（下限 %d；缺属性容器 %d 个）"
        % (total_charts, TOTAL_QUOTA, missing_attr))

    # ---- C1 data-chart-id 清单 / 规划表核销 ----
    if args.plan:
        try:
            with open(args.plan, encoding="utf-8") as f:
                plan = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeError) as e:
            print("无法读取规划表: %s" % e, file=sys.stderr)
            return 2
        # Accept chart-director chart_table, legacy charts, or bare row list.
        if isinstance(plan, dict):
            rows = plan.get("chart_table") if "chart_table" in plan else plan.get("charts")
        else:
            rows = plan
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            print("规划表结构不符：需 chart_plan.chart_table（对象数组，见 schemas/chart_plan.json）",
                  file=sys.stderr)
            return 2
        plan_ids = []
        for row in rows:
            chart_id = row.get("chart_id") or row.get("id") or row.get("图表 ID")
            if not isinstance(chart_id, str) or not chart_id.strip():
                print("规划表结构不符：每行必须包含非空 chart_id / id / 图表 ID", file=sys.stderr)
                return 2
            plan_ids.append(chart_id.strip())
        html_ids = [i.strip() for i in ids_in_html]
        from collections import Counter
        html_duplicates = sorted(i for i, count in Counter(html_ids).items() if count > 1)
        plan_duplicates = sorted(i for i, count in Counter(plan_ids).items() if count > 1)
        missing = sorted(set(plan_ids) - set(html_ids))
        extra = sorted(set(html_ids) - set(plan_ids))
        details = ["规划 %d 行，HTML 带 id 图表 %d 个" % (len(plan_ids), len(html_ids))]
        if missing:
            details.append("未核销: " + ", ".join(missing))
        if extra:
            details.append("计划外 id: " + ", ".join(extra))
        if html_duplicates:
            details.append("HTML 重复 id: " + ", ".join(html_duplicates))
        if plan_duplicates:
            details.append("计划重复 id: " + ", ".join(plan_duplicates))
        if missing_attr:
            details.append("缺 data-chart-id 的容器: %d 个" % missing_attr)
        failed = missing or extra or html_duplicates or plan_duplicates or missing_attr
        add("C1", "red", "fail" if failed else "pass", "；".join(details))
    else:
        add("C1", "red", "fail", "S9 必须提供 --plan")

    # ---- C4 SVG 健康 ----
    bad = [s for s in p.svgs if s["issues"]]
    if bad:
        add("C4", "red", "fail", "%d/%d 个 SVG 异常: " % (len(bad), len(p.svgs)) +
            "; ".join("Ch%d[%s]" % (s["chapter"], ", ".join(s["issues"])) for s in bad[:8]))
    else:
        add("C4", "red", "pass", "%d 个 SVG 全部健康（viewBox 正常、绘图元素非空非退化）" % len(p.svgs))

    # ---- C5 锚点六图（关键词启发式） ----
    chart_texts = ["".join(c["text"]) for c in p.charts]
    missing_anchor = []
    for name, groups in ANCHOR_CHARTS.items():
        found = any(all(k in t for k in g) for t in chart_texts for g in groups)
        if not found:
            missing_anchor.append(name)
    add("C5", "red", "fail" if missing_anchor else "pass",
        ("缺失: " + "、".join(missing_anchor) + "（启发式判定，finalizer 须目验确认）")
        if missing_anchor else "锚点六图关键词均命中（仍需 finalizer 目验图形正确性）")

    # ---- W1/W2 禁词 ----
    hard_hits, review_counts = scan_forbidden(p.chapter_text, p.text_boundaries)
    if hard_hits:
        add("W1", "block", "fail", "硬禁词命中 %d 处: " % len(hard_hits) +
            "; ".join("Ch%d「%s」…%s…" % (h["chapter"], h["word"], h["context"])
                      for h in hard_hits))
    else:
        add("W1", "block", "pass", "硬禁词 0 命中（否定性提及已豁免）")
    add("W2", "info", "warn" if any(review_counts.values()) else "pass",
        "语境词计数（供 finalizer 复核，不判红）: " +
        ", ".join("%s×%d" % (w, n) for w, n in review_counts.items()))

    # ---- E4 玄学解释力评级（每章最多计一块） ----
    eval_chapters = [
        ch for ch in (2, 3, 4)
        if re.search(r"解释力[：:]?\s*★", "".join(p.chapter_text.get(ch, [])))
    ]
    n_eval = len(eval_chapters)
    add("E4", "info", "pass" if n_eval >= 3 else "warn",
        "Ch2/Ch3/Ch4 中含解释力评级的章节 %d 个（最多各计 1 块；应为 3）" % n_eval)

    # ---- 输出 ----
    reds = [c for c in checks if c["level"] == "red" and c["status"] == "fail"]
    blocks = [c for c in checks if c["level"] == "block" and c["status"] == "fail"]
    warns = [c for c in checks if c["status"] == "warn"]
    result = {"file": args.book, "chapters": n_ch, "charts_total": total_charts,
              "svg_total": len(p.svgs), "chart_ids": ids_in_html,
              "checks": checks, "red_fails": len(reds), "block_fails": len(blocks),
              "warnings": len(warns),
              "verdict": "FAIL" if (reds or blocks) else "PASS"}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        icon = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}
        print("destiny-matrix validate_book — %s" % args.book)
        print("章节 %d · 图表 %d · SVG %d\n" % (n_ch, total_charts, len(p.svgs)))
        for c in checks:
            print("%s %-7s %s" % (icon[c["status"]], c["id"], c["detail"]))
        print("\n结论: %s（🔴 fail %d · 🟠 阻断 fail %d · warning %d）"
              % (result["verdict"], len(reds), len(blocks), len(warns)))
    return 1 if (reds or blocks) else 0


if __name__ == "__main__":
    sys.exit(main())
