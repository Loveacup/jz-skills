#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_minutes.py — fail-closed gate for business minutes (G1–G10).

Usage:
  python3 verify_minutes.py <minutes.md> [--transcript <transcript.txt>] [--mode standard|deep] [--json]

Exit 0 when every gate passes, 1 otherwise, 2 on missing input.
Stdlib only. UTF-8 in/out regardless of console code page.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS = re.compile(r"\[(\d{1,2}):([0-5]\d)(?::([0-5]\d))?(?:[–\-](\d{1,2}):([0-5]\d)(?::([0-5]\d))?)?\]")
DEC_ID = re.compile(r"\b\d{2}W\d{2}-D\d{2,3}\b")
ACT_ID = re.compile(r"\b\d{2}W\d{2}-A\d{2,3}\b")
PLACEHOLDERS = re.compile(r"\[待填\]|\bTODO\b|\bTBD\b|\[人名\]|XXX|\[日期\]|\[内容\]|\[理由\]")
DATE_LIKE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}月\d{1,2}日|\d{2}W\d{2}|本周|下周|W\d{2}|前|后|内|之前|起|时|后续|会前|会后|交付|上线|签约|收到")
BAD_NODE = re.compile(r"^(待定|TBD|未定|-|—|无)?$")

LENGTH_FLOORS = [(8000, 1500, 3), (30000, 4000, 6), (80000, 8000, 10), (math.inf, 12000, 15)]


def read(path: Path) -> str:
    with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def split_frontmatter(md: str):
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            return md[3:end].strip("\n"), md[end + 4 :]
    return "", md


def sections(body: str):
    """Return list of (level, title, text) for H2/H3 blocks."""
    out = []
    cur_title, cur_lvl, buf = "(preamble)", 0, []
    for line in body.splitlines():
        m = re.match(r"^(#{2,3})\s+(.*)", line)
        if m:
            out.append((cur_lvl, cur_title, "\n".join(buf)))
            cur_lvl, cur_title, buf = len(m.group(1)), m.group(2).strip(), []
        else:
            buf.append(line)
    out.append((cur_lvl, cur_title, "\n".join(buf)))
    return out


def find_section(secs, *keywords):
    """First H2 section whose title contains any keyword; returns its text plus nested H3s."""
    text, capturing = [], False
    for lvl, title, body in secs:
        if lvl == 2:
            if capturing:
                break
            if any(k in title for k in keywords):
                capturing = True
                text.append(body)
        elif capturing:
            text.append(body)
    return "\n".join(text) if capturing else None


def table_rows(text: str):
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
    return rows[1:] if rows else []  # drop header


def strip_for_count(body: str) -> str:
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"^\|.*\|$", "", body, flags=re.M)  # tables are structure, not prose
    return re.sub(r"\s+", "", body)


def transcript_stats(path: Path | None):
    if not path:
        return None
    t = read(path)
    chars = len(re.sub(r"\s+", "", t))
    last = None
    for m in TS.finditer(t):
        last = m
    minutes = None
    if last:
        h, mnt = int(last.group(1)), int(last.group(2))
        minutes = h * 60 + mnt if last.group(3) is not None else h  # [mm:ss] vs [hh:mm:ss]
        if last.group(3) is None:
            minutes = h  # [mm:ss] form: first group is minutes
    if minutes is None:
        minutes = max(1, chars // 220)
    return {"chars": chars, "minutes": minutes, "text": re.sub(r"\s+", "", t)}


def evaluate(md_path: Path, transcript: Path | None, mode: str):
    md = read(md_path)
    fm, body = split_frontmatter(md)
    secs = sections(body)
    ts = transcript_stats(transcript)
    hours = (ts["minutes"] / 60.0) if ts else 1.0
    results = []

    def gate(name, ok, detail=""):
        results.append({"gate": name, "pass": bool(ok), "detail": detail})

    # G1 frontmatter
    need = ["type:", "tags:", "participants:", "meeting_date:", "related:"]
    missing = [k for k in need if k not in fm]
    wikilinks = len(re.findall(r"\[\[[^\]]+\]\]", fm))
    prefixed = bool(re.search(r"tags:.*\b(type|topic|status|src|biz)/", fm, flags=re.S))
    gate("G1 frontmatter", not missing and wikilinks >= 3 and prefixed,
         f"missing={missing} wikilinks={wikilinks} prefixed_tags={prefixed}")

    # G2 participants table
    overview = find_section(secs, "会议概况", "会议信息") or ""
    prow = [r for r in table_rows(overview) if len(r) >= 3 and r[0] and not r[0].startswith("项目")]
    gate("G2 参会表", len(prow) >= 2, f"rows={len(prow)}")

    # G3 executive summary
    summ = find_section(secs, "执行摘要", "会议摘要") or ""
    prose = strip_for_count(re.sub(r"^>.*$", "", summ, flags=re.M))
    gate("G3 执行摘要", len(prose) >= 120 and "[!decision]" in summ,
         f"prose_chars={len(prose)} decision_callout={'[!decision]' in summ}")

    # G4 decision table
    dec = find_section(secs, "决策记录", "核心决议", "决策") or ""
    drows = table_rows(dec)
    bad = []
    for i, r in enumerate(drows, 1):
        joined = " ".join(r)
        nonempty = [c for c in r if c]
        if not DEC_ID.search(joined):
            bad.append(f"row{i}:no-id")
        elif len(nonempty) < 6:
            bad.append(f"row{i}:cells<6")
        elif not TS.search(joined):
            bad.append(f"row{i}:no-timestamp")
    gate("G4 决策四要素", bool(drows) and not bad, f"rows={len(drows)} issues={bad[:6]}")

    # G5 action items
    act = find_section(secs, "行动项") or ""
    arows = table_rows(act)
    bad = []
    for i, r in enumerate(arows, 1):
        joined = " ".join(r)
        if not ACT_ID.search(joined):
            bad.append(f"row{i}:no-id"); continue
        if not TS.search(joined):
            bad.append(f"row{i}:no-timestamp")
        cells = [c for c in r if c]
        if len(cells) < 5:
            bad.append(f"row{i}:cells<5")
        node_ok = any(DATE_LIKE.search(c) for c in r[1:]) and not any(BAD_NODE.fullmatch(c) for c in r[2:4] if c in ("待定", "TBD", "未定"))
        if not node_ok:
            bad.append(f"row{i}:no-node")
    gate("G5 行动项", bool(arows) and not bad, f"rows={len(arows)} issues={bad[:6]}")

    # G6 quotes
    quotes = re.findall(r">\s*\[!quote\][^\n]*", body)
    quotes_ts = [q for q in quotes if TS.search(q)]
    q_floor = max(3, math.ceil(3 * hours)) if mode == "standard" else max(5, math.ceil(4 * hours))
    gate("G6 原话引用", len(quotes_ts) >= q_floor, f"quotes_with_ts={len(quotes_ts)} floor={q_floor}")

    # G7 external evidence
    ext = find_section(secs, "外部情报", "决策依据", "外部证据")
    ok7 = False
    if ext is not None:
        rows = table_rows(ext)
        url_rows = [r for r in rows if "http" in " ".join(r)]
        ok7 = bool(url_rows) or "未检索到" in ext or "无外部搜索触发项" in ext
        if mode == "deep":
            ok7 = bool(url_rows)
    gate("G7 外部依据", ok7, f"section={'yes' if ext is not None else 'no'}")

    # G8 correction table
    corr = find_section(secs, "订正表", "订正") or ""
    gate("G8 订正表", bool(table_rows(corr)) or "无新增订正" in corr, f"rows={len(table_rows(corr))}")

    # G9 length
    chars = len(strip_for_count(body))
    if ts:
        floor = next(f for lim, f, _ in LENGTH_FLOORS if ts["chars"] < lim)
    else:
        floor = 1500
    if mode == "deep":
        floor = int(floor * 1.25)
    gate("G9 字数下限", chars >= floor, f"body_chars={chars} floor={floor} transcript_chars={ts['chars'] if ts else 'n/a'}")

    # G10 placeholders / dump / giant paragraphs
    ph = PLACEHOLDERS.findall(body)
    paras = [p for p in re.split(r"\n\s*\n", body) if not p.strip().startswith("|")]
    giant = [len(p) for p in paras if len(re.sub(r"\s+", "", p)) > 1200]
    dump = 0
    if ts:
        flat = strip_for_count(body)
        for i in range(0, max(0, len(flat) - 200), 100):
            if flat[i : i + 200] in ts["text"]:
                dump += 1
    gate("G10 无占位符/无倾倒", not ph and not giant and dump == 0,
         f"placeholders={ph[:4]} giant_paragraphs={len(giant)} dump_windows={dump}")

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("minutes")
    ap.add_argument("--transcript")
    ap.add_argument("--mode", choices=["standard", "deep"], default="standard")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    mp = Path(a.minutes)
    if not mp.exists():
        print(f"minutes not found: {mp}"); return 2
    tp = Path(a.transcript) if a.transcript else None
    if tp and not tp.exists():
        print(f"transcript not found: {tp}"); return 2
    res = evaluate(mp, tp, a.mode)
    n_pass = sum(1 for r in res if r["pass"])
    if a.json:
        print(json.dumps({"file": str(mp), "mode": a.mode, "pass": n_pass, "fail": len(res) - n_pass, "gates": res}, ensure_ascii=False, indent=2))
    else:
        for r in res:
            print(f"{r['gate']:<22} {'PASS' if r['pass'] else 'FAIL'}  {r['detail']}")
        print(f"=== {n_pass} PASS / {len(res) - n_pass} FAIL → exit {0 if n_pass == len(res) else 1} ===")
    return 0 if n_pass == len(res) else 1


if __name__ == "__main__":
    sys.exit(main())
