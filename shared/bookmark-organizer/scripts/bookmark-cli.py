#!/usr/bin/env python3
"""bookmark-cli.py — Hermes bookmark-organizer 管线 CLI（stdlib-only）

管线: parse → classify(L1) → [agent 做 L2] → merge → render

  parse <输入>           Netscape HTML / Chrome 原生 JSON → bookmarks.json（格式自动嗅探）
  classify <bookmarks>   L1 规则打分 → classified.json + unmatched.json；--dry-run 仅打印统计
  merge <classified> <patch>  回灌 L2 分类补丁（宽容解析 LLM 输出，幂等可增量）
  render <classified>    → Netscape HTML（可重导入）+ Markdown 索引（Obsidian 格式）
"""
import argparse
import hashlib
import html as html_mod
import json
import re
import sys
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RULES = SKILL_DIR / "references" / "classification-rules.json"
WEBKIT_EPOCH_OFFSET = 11644473600  # Chrome date_added 为 1601 纪元微秒
BUILTIN_NAMES = {"bookmarklet": "书签脚本", "uncategorized": "未分类",
                 "browser-internal": "浏览器内部页"}
INTERNAL_SCHEMES = ("chrome-extension://", "chrome://", "about:", "edge://",
                    "brave://", "moz-extension://", "opera://", "vivaldi://")


def bid(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def make_item(url, title, folder_path, add_date=None):
    if not title:
        title = urlparse(url).netloc or url[:50]
    return {"id": bid(url), "url": url, "title": title,
            "folder_path": [f for f in folder_path if f], "add_date": add_date}


# ---------- parse ----------

class NetscapeParser(HTMLParser):
    """事件流 + 文件夹栈；容忍 Netscape 格式不闭合的 </DT>/<p>。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.items, self.buf = [], [], []
        self.pending_folder, self.cur_link, self.in_h3 = None, None, False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "h3":
            self.in_h3, self.buf = True, []
        elif tag == "dl":
            self.stack.append(self.pending_folder or "")
            self.pending_folder = None
        elif tag == "a":
            self.cur_link, self.buf = dict(attrs), []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "h3":
            self.pending_folder = "".join(self.buf).strip()
            self.in_h3 = False
        elif tag == "dl" and self.stack:
            self.stack.pop()
        elif tag == "a" and self.cur_link is not None:
            url = self.cur_link.get("href", "")
            ts = self.cur_link.get("add_date")
            ts = int(ts) if ts and str(ts).lstrip("-").isdigit() else None
            if url:
                self.items.append(make_item(url, "".join(self.buf).strip(), self.stack, ts))
            self.cur_link = None

    def handle_data(self, data):
        if self.in_h3 or self.cur_link is not None:
            self.buf.append(data)


def parse_chrome_json(data):
    items = []

    def walk(node, path):
        if node.get("type") == "url":
            ts = None
            da = node.get("date_added")
            if da and str(da).isdigit():
                ts = max(0, int(int(da) / 1_000_000 - WEBKIT_EPOCH_OFFSET))
            items.append(make_item(node.get("url", ""), node.get("name", "").strip(), path, ts))
        else:
            for c in node.get("children", []):
                walk(c, path + [node.get("name", "")])

    for root in data.get("roots", {}).values():
        if isinstance(root, dict):
            for c in root.get("children", []):
                walk(c, [])
    return items


def cmd_parse(args):
    text = Path(args.input).read_text(encoding="utf-8", errors="replace")
    head = text.lstrip()[:1]
    if head == "{":
        items = parse_chrome_json(json.loads(text))
        fmt = "chrome-json"
    else:
        p = NetscapeParser()
        p.feed(text)
        items = p.items
        fmt = "netscape-html"
    Path(args.output).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    dup = len(items) - len({i["url"] for i in items})
    print(f"parse: {fmt} → {len(items)} 条（重复 URL {dup} 条，保留未删）→ {args.output}")


# ---------- classify ----------

def load_rules(path):
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    ids, names = set(), set()
    for c in rules["categories"]:
        if c["id"] in ids or c["name"] in names:
            sys.exit(f"规则校验失败: id/name 重复 → {c['id']}")
        if not c.get("keywords") and not c.get("url_patterns"):
            sys.exit(f"规则校验失败: {c['id']} 无 keywords 且无 url_patterns")
        ids.add(c["id"]); names.add(c["name"])
    return rules


def score_item(item, cat, w):
    t, u = item["title"].lower(), item["url"].lower()
    dom = urlparse(u).netloc
    s = 0
    for kw in cat.get("keywords", []):
        k = kw.lower()
        if t == k:
            s += w["title_exact"]
        elif k in t:
            s += w["title_partial"]
        if k in dom:
            s += w["domain_keyword"]
    for p in cat.get("url_patterns", []):
        if p.lower() in u:
            s += w["url_pattern"]
    return s


def cmd_classify(args):
    rules = load_rules(args.rules)
    w, threshold = rules["scoring"], rules["threshold"]
    items = json.loads(Path(args.input).read_text(encoding="utf-8"))
    unmatched, seen_unmatched, n_script, n_internal = [], set(), 0, 0
    for it in items:
        if it["url"].startswith(("javascript:", "data:")):
            it.update(category="bookmarklet", score=0, source="builtin")
            n_script += 1
            continue
        if it["url"].startswith(INTERNAL_SCHEMES):
            it.update(category="browser-internal", score=0, source="builtin")
            n_internal += 1
            continue
        best, best_s = None, 0
        for cat in rules["categories"]:
            s = score_item(it, cat, w)
            if s > best_s or (s == best_s and best and s > 0 and cat.get("priority", 0) > best.get("priority", 0)):
                best, best_s = cat, s
        if best_s >= threshold:
            it.update(category=best["id"], score=best_s, source=f"rule:{best['id']}")
        else:
            it.update(category="uncategorized", score=best_s, source="none")
            if it["url"] not in seen_unmatched:  # 唯一 URL 去重导出，merge 按 URL 扩散应用
                seen_unmatched.add(it["url"])
                unmatched.append({"id": it["id"], "url": it["url"].split("?")[0][:120], "title": it["title"][:80]})

    n = len(items)
    n_un_total = sum(1 for i in items if i["source"] == "none")
    matched = n - n_un_total - n_script - n_internal
    classifiable = max(n - n_script - n_internal, 1)
    top = Counter(i["category"] for i in items if i["source"].startswith("rule:")).most_common(10)
    name_of = {c["id"]: c["name"] for c in rules["categories"]}
    print(f"classify: 共 {n} 条 | 浏览器内部页 {n_internal} | 书签脚本 {n_script} | "
          f"L1 命中 {matched}/{classifiable} ({matched / classifiable:.1%}) | "
          f"待 L2 {n_un_total} 条（唯一 URL {len(unmatched)}）")
    for cid, cnt in top:
        print(f"  {name_of.get(cid, cid):<12} {cnt}")
    if args.dry_run:
        return
    Path(args.output).write_text(json.dumps({"items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(args.unmatched).write_text(json.dumps(unmatched, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {args.output} / {args.unmatched}")


# ---------- merge ----------

def clean_and_parse(text):
    """6 层 fallback 解析 LLM 输出（移植自 AI-Bookmark-Manager cleanAndParseJson）。"""
    text = text.strip()
    try:
        return json.loads(text)                                            # 1 直接解析
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)             # 2 markdown 代码块
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    a, b = text.find("["), text.rfind("]")                                 # 3 最外层 [...]
    if 0 <= a < b:
        try:
            return json.loads(text[a:b + 1])
        except json.JSONDecodeError:
            pass
    a, b = text.find("{"), text.rfind("}")                                 # 4 最外层 {...}
    if 0 <= a < b:
        try:
            return json.loads(text[a:b + 1])
        except json.JSONDecodeError:
            pass
    objs = re.findall(r'\{[^{}]*"id"[^{}]*\}', text)                       # 5 逐个对象抢救
    if objs:
        out = []
        for o in objs:
            try:
                out.append(json.loads(o))
            except json.JSONDecodeError:
                continue
        if out:
            return out
    sys.exit("merge: 补丁解析失败（6 层 fallback 均未命中）")               # 6 报错


def cmd_merge(args):
    rules = load_rules(args.rules)
    valid = {c["id"] for c in rules["categories"]} | set(BUILTIN_NAMES)
    doc = json.loads(Path(args.classified).read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in doc["items"]}
    by_url = {}
    for i in doc["items"]:
        by_url.setdefault(i["url"], []).append(i)
    patch = clean_and_parse(Path(args.patch).read_text(encoding="utf-8"))
    if isinstance(patch, dict):
        patch = patch.get("results", patch.get("items", []))
    applied = invalid_cat = unknown_id = protected = retitled = 0
    for p in patch:
        ref = by_id.get(p.get("id"))
        if ref is None:
            unknown_id += 1
            continue
        cid = p.get("category_id")
        new_title = p.get("title")
        for it in by_url[ref["url"]]:  # 同 URL 重复条目一并应用
            if new_title and new_title != it["title"]:
                it.setdefault("orig_title", it["title"])  # 标题优化不受分类保护限制
                it["title"] = new_title
                retitled += 1
            if p.get("subcategory"):
                it["subcategory"] = p["subcategory"]  # 二级文件夹，render 时呈现
            if cid is None:
                continue  # title-only 补丁
            if it["source"] not in ("none", "llm", "llm-invalid"):
                protected += 1  # 规则/手工分类受保护，补丁只作用于待分类池
                continue
            if cid not in valid:
                it.update(category="uncategorized", source="llm-invalid")
                invalid_cat += 1
                continue
            it.update(category=cid, source="llm")
            applied += 1
    Path(args.classified).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"merge: 应用 {applied} | 改名 {retitled} | 非法类别→未分类 {invalid_cat} | "
          f"未知 id 跳过 {unknown_id} | 受保护跳过 {protected}")


# ---------- render ----------

def cmd_render(args):
    rules = load_rules(args.rules)
    name_of = {c["id"]: c["name"] for c in rules["categories"]} | BUILTIN_NAMES
    doc = json.loads(Path(args.classified).read_text(encoding="utf-8"))
    items = doc["items"]
    by_cat = {}
    for it in items:
        by_cat.setdefault(it["category"], []).append(it)

    def esc(s):
        return html_mod.escape(s, quote=True)

    def split_subcats(rows):
        """子分类分组：子文件夹按条数降序在前，无子分类散条目在后。"""
        subs, loose = {}, []
        for it in rows:
            sc = it.get("subcategory")
            if sc:
                subs.setdefault(sc, []).append(it)
            else:
                loose.append(it)
        return sorted(subs.items(), key=lambda kv: -len(kv[1])), loose

    def a_line(it, indent):
        ad = f' ADD_DATE="{it["add_date"]}"' if it.get("add_date") else ""
        return f'{indent}<DT><A HREF="{esc(it["url"])}"{ad}>{esc(it["title"])}</A>'

    # Netscape HTML：分类 = 一级文件夹，子分类 = 二级文件夹；类内保持原始顺序；不回填 ICON
    out = ["<!DOCTYPE NETSCAPE-Bookmark-file-1>",
           '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
           "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>"]
    order = sorted(by_cat, key=lambda c: -len(by_cat[c]))
    for cid in order:
        subs, loose = split_subcats(by_cat[cid])
        out.append(f"    <DT><H3>{esc(name_of.get(cid, cid))}</H3>")
        out.append("    <DL><p>")
        for sub, rows in subs:
            out.append(f"        <DT><H3>{esc(sub)}</H3>")
            out.append("        <DL><p>")
            out.extend(a_line(it, "            ") for it in rows)
            out.append("        </DL><p>")
        out.extend(a_line(it, "        ") for it in loose)
        out.append("    </DL><p>")
    out.append("</DL><p>")
    Path(args.output).write_text("\n".join(out), encoding="utf-8")

    # Markdown 索引：未分类置顶；🤖 标记 LLM 分类条目
    if args.md:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        n = len(items)
        n_rule = sum(1 for i in items if i["source"].startswith("rule:"))
        n_llm = sum(1 for i in items if i["source"] == "llm")
        n_un = len(by_cat.get("uncategorized", []))
        md = ["---", "status: 种子", "type: 索引", "priority: 正常",
              "aliases: [Bookmark Index]", "tags: [bookmark, type/索引, src/工具]",
              f"created: {now}", f"modified: {now}", "---", "",
              f"# 书签索引（{n} 条）", "",
              "> [!abstract] 📊 分类统计",
              f"> 总数 **{n}** ｜ 规则分类 **{n_rule}** ｜ LLM 分类 **{n_llm}** 🤖 ｜ 未分类 **{n_un}**",
              f"> 生成时间 {now} ｜ 工具 bookmark-organizer", ""]
        md_order = (["uncategorized"] if "uncategorized" in by_cat else []) + \
                   [c for c in order if c not in ("uncategorized", "bookmarklet")] + \
                   (["bookmarklet"] if "bookmarklet" in by_cat else [])
        def md_line(it):
            t = it["title"].replace("[", "［").replace("]", "］")
            mark = " 🤖" if it["source"] == "llm" else ""
            path = f" · `{'/'.join(it['folder_path'])}`" if it["folder_path"] else ""
            u = it["url"]
            if any(c in u for c in "() <>"):
                u = f"<{u}>"  # 括号/空格破坏 MD 链接语法
            return f"- [{t}]({u}){mark}{path}"

        for cid in md_order:
            rows = by_cat[cid]
            subs, loose = split_subcats(rows)
            md.append(f"## {name_of.get(cid, cid)} ({len(rows)})")
            md.append("")
            if loose:
                md.extend(md_line(it) for it in loose)
                md.append("")
            for sub, srows in subs:
                md.append(f"### {sub} ({len(srows)})")
                md.append("")
                md.extend(md_line(it) for it in srows)
                md.append("")
        Path(args.md).write_text("\n".join(md), encoding="utf-8")
    print(f"render: {len(items)} 条 → {args.output}" + (f" + {args.md}" if args.md else ""))


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(prog="bookmark-cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse", help="解析书签文件（HTML/Chrome JSON 自动嗅探）")
    p.add_argument("input")
    p.add_argument("-o", "--output", default="bookmarks.json")
    p.set_defaults(fn=cmd_parse)

    p = sub.add_parser("classify", help="L1 规则分类")
    p.add_argument("input")
    p.add_argument("--rules", default=str(DEFAULT_RULES))
    p.add_argument("-o", "--output", default="classified.json")
    p.add_argument("--unmatched", default="unmatched.json")
    p.add_argument("--dry-run", action="store_true", help="仅打印统计，不写文件")
    p.set_defaults(fn=cmd_classify)

    p = sub.add_parser("merge", help="回灌 L2 分类补丁（幂等，可多次增量）")
    p.add_argument("classified")
    p.add_argument("patch")
    p.add_argument("--rules", default=str(DEFAULT_RULES))
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("render", help="输出 Netscape HTML + Markdown 索引")
    p.add_argument("classified")
    p.add_argument("-o", "--output", default="bookmarks-organized.html")
    p.add_argument("--md", default=None, help="Markdown 索引输出路径")
    p.add_argument("--rules", default=str(DEFAULT_RULES))
    p.set_defaults(fn=cmd_render)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
