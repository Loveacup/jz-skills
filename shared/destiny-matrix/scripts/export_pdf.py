#!/usr/bin/env python3
"""Contract-checked HTML to PDF export for destiny-matrix v5."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from book_html import BookHTML, Node, normalize_text, is_hidden
from quality_contracts import check

PDF_MARGIN = {"top": "20mm", "bottom": "18mm", "left": "14mm", "right": "14mm"}
FOOTER_FONT = "'Songti SC',STSong,'Noto Serif CJK SC',SimSun,serif"


def _strip_cover_chrome(pdf_path: Path, bare_path: Path) -> bool:
    """Replace page 1 with the same page rendered without header/footer.

    Chromium cannot suppress header/footer templates per page. Both renders come
    from the same DOM and margins, so pagination and marked-content IDs match.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    main, bare = PdfReader(str(pdf_path)), PdfReader(str(bare_path))
    if len(main.pages) != len(bare.pages) or not main.pages:
        return False
    writer = PdfWriter(clone_from=main)
    source, target = bare.pages[0], writer.pages[0]
    # Clone only the two entries; cloning the page would drag in its whole page tree via /Parent.
    for key in ("/Contents", "/Resources"):
        if key in source:
            target[NameObject(key)] = source.raw_get(key).clone(writer)
    with pdf_path.open("wb") as stream:
        writer.write(stream)
    return True


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_title(source: str, fallback: str) -> str:
    from html.parser import HTMLParser
    class TitleParser(HTMLParser):
        title = ""
        in_title = False
        def handle_starttag(self, tag, attrs):
            if tag == "title": self.in_title = True
        def handle_endtag(self, tag):
            if tag == "title": self.in_title = False
        def handle_data(self, data):
            if self.in_title: self.title += data
    parser = TitleParser(); parser.feed(source)
    return normalize_text(parser.title) or fallback




def inspect_html(source: str) -> tuple[BookHTML, list[dict[str, str]], list[dict[str, str]]]:
    book = BookHTML(source)
    errors: list[dict[str, str]] = []
    details_ids: set[str] = set()
    for node in book.details:
        appendix = next((a for a in node.ancestors() if a.tag == "section" and a.attr("data-content-kind") == "appendix"), None)
        appendix_id = node.attr("data-appendix-id")
        if appendix is None or not appendix_id:
            errors.append({"block_id": node.attr("id") or "details", "reason": "uncategorized_details"})
        elif appendix_id in details_ids:
            errors.append({"block_id": appendix_id, "reason": "duplicate_appendix_id"})
        details_ids.add(str(appendix_id))
    for node in book.nodes:
        if is_hidden(node) and normalize_text(node.text(include_hidden=True)):
            errors.append({"block_id": node.attr("id") or node.attr("data-disclosure-id") or node.tag,
                           "reason": "hidden_content"})
    return book, errors, content_manifest(book)

 
def content_manifest(book: BookHTML) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    index = 0
    for node in book.nodes:
        eligible = node.tag in {"p", "li", "a", "figcaption", "caption", "th", "td", "blockquote", "q",
                                "summary", "h2", "h3", "text", "tspan", "section"}
        if node.tag == "section" and node.attr("data-content-kind") != "disclosure":
            eligible = False
        if node.tag == "aside" and node.attr("data-disclosure-id"):
            eligible = True
        if not eligible or is_hidden(node):
            continue
        text = normalize_text(node.text())
        if not text:
            continue
        if node.tag in {"th", "td", "caption"}:
            minimum = 9.5
        elif node.tag in {"blockquote", "q"}:
            minimum = 11.5
        elif node.tag == "figcaption" or any(a.has_class("chart-description") or a.has_class("appendix-note")
                                              for a in node.ancestors()):
            minimum = 10
        elif any(a.attr("data-content-kind") == "appendix" for a in node.ancestors()):
            minimum = 10
        elif node.tag in {"text", "tspan"}:
            minimum = 9
        else:
            minimum = 12
        key = node.attr("id") or node.attr("data-disclosure-id") or node.attr("data-quote-id") or f"block-{index:04d}"
        rows.append({"block_id": str(key), "text": text, "kind": node.tag, "minimum_pt": str(minimum)})
        index += 1
    return rows


def _print_dom(page) -> dict[str, Any]:
    return page.evaluate("""() => {
      const details = [...document.querySelectorAll('details[data-appendix-id]')];
      const before = details.map(d => ({id:d.id, text:d.textContent}));
      for (const d of details) {
        const summary = d.querySelector(':scope > summary');
        if (!summary) throw new Error('appendix details has no direct summary: ' + d.id);
        const heading = document.createElement('h3');
        heading.className = 'appendix-title'; heading.id = summary.id || (d.id + '-title');
        while (summary.firstChild) heading.appendChild(summary.firstChild);
        summary.replaceWith(heading);
        const section = document.createElement('section');
        section.className = 'appendix-entry'; section.id = d.id;
        Array.from(d.attributes).forEach(attr => {
          if (attr.name !== 'open' && attr.name !== 'class' && attr.name !== 'id')
            section.setAttribute(attr.name, attr.value);
        });
        while (d.firstChild) section.appendChild(d.firstChild);
        d.replaceWith(section);
      }
      const after = details.map((d,i) => ({id:d.id, text:document.getElementById(d.id).textContent}));
      return {before,after};
    }""")


def _font_audit(page) -> list[dict[str, Any]]:
    return page.evaluate("""() => {
      const min = {body:12, quote:11.5, caption:10, appendix:10, table:9.5, svg:9, chrome:8};
      const out=[];
      const classify = el => {
        if (el.closest('header,footer')) return ['chrome',min.chrome];
        if (el.closest('svg')) return ['svg',min.svg];
        if (el.closest('blockquote,q')) return ['quote',min.quote];
        if (el.closest('figcaption,.appendix-note,.chart-description,.chart-note')) return ['caption',min.caption];
        if (el.closest('td,th') || el.tagName.toLowerCase()==='caption') return ['table',min.table];
        if (el.closest('[data-content-kind="appendix"]')) return ['appendix',min.appendix];
        return ['body',min.body];
      };
      const nodes=[...document.querySelectorAll('p,li,td,th,caption,figcaption,blockquote,q,summary,h1,h2,h3,svg text,svg tspan')];
      nodes.forEach(el => {
        const text=(el.textContent||'').trim(); if(!text) return;
        const [role,limit]=classify(el); const style=getComputedStyle(el);
        let px=parseFloat(style.fontSize)||0, scale=1;
        if(el.closest('svg')) { const m=el.getScreenCTM(); if(m) scale=Math.hypot(m.c,m.d); }
        else {
          for(let n=el; n && n!==document.documentElement; n=n.parentElement) {
            const transform=getComputedStyle(n).transform;
            if(transform && transform!=='none') { const m=new DOMMatrix(transform); scale*=Math.hypot(m.c,m.d); }
          }
        }
        const pt=px*scale*0.75;
        if (pt + 1e-6 < limit) out.push({text:text.slice(0,120), role, actual_pt:+pt.toFixed(3), minimum_pt:limit, source:'dom'});
      });
      return out;
    }""")

def _pdf_text_and_fonts(path: Path) -> tuple[list[str], list[dict[str, Any]], int, list[int]]:
    from pypdf import PdfReader
    reader = PdfReader(str(path), strict=True)
    page_text: list[str] = []
    sizes: list[dict[str, Any]] = []
    blank: list[int] = []
    for page_no, page in enumerate(reader.pages, 1):
        def capture(text, cm, tm, font, size):
            if not text or not text.strip():
                return
            c = cm[0] * tm[2] + cm[2] * tm[3]
            d = cm[1] * tm[2] + cm[3] * tm[3]
            sizes.append({"text": text, "pt": float(size) * (c * c + d * d) ** 0.5})
        text = page.extract_text(visitor_text=capture) or ""
        page_text.append(text)
        if not normalize_text(text):
            blank.append(page_no)
    return page_text, sizes, len(reader.pages), blank


_PDF_CJK_RADICAL_ALIASES = str.maketrans({
    "⺒": "巳", "⺠": "民", "⻄": "西", "⻅": "见", "⻆": "角",
    "⻓": "长", "⻔": "门", "⻚": "页", "⻛": "风",
    "⻥": "鱼", "⻩": "黄", "⻬": "齐", "⻰": "龙",
})


def _content_text(value: str) -> str:
    # Chromium's PDF ToUnicode map can emit CJK radical glyph aliases for Han text.
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).translate(_PDF_CJK_RADICAL_ALIASES)).casefold()


def _verify_content(manifest: list[dict[str, str]], pages: list[str]) -> tuple[list, list]:
    pdf_text = _content_text("\n".join(pages))
    missing, ambiguous = [], []
    for row in manifest:
        needle = _content_text(row["text"])
        if needle and needle in pdf_text:
            continue
        tokens = [part for part in re.split(r"\s+", row["text"]) if len(part) > 4]
        found = sum(_content_text(token) in pdf_text for token in tokens)
        coverage = sum(char in pdf_text for char in needle) / max(1, len(needle))
        issue = {"block_id": row["block_id"], "kind": row["kind"], "text": row["text"]}
        (ambiguous if found or coverage >= 0.75 else missing).append(issue)
    return missing, ambiguous

def _audit_pdf_fonts(sizes: list[dict[str, Any]], manifest: list[dict[str, str]],
                     title: str) -> tuple[list, list]:
    violations, ambiguous = [], []
    ambiguous_counts: dict[float, int] = {}
    rows = [(re.sub(r"\s+", "", normalize_text(row["text"])).casefold(), row) for row in manifest]
    header_title = re.sub(r"\s+", "", normalize_text(title)).casefold()
    for sample in sizes:
        text = re.sub(r"\s+", "", normalize_text(sample["text"])).casefold()
        if not text:
            continue
        if len(text) >= 4 and text in header_title and sample["pt"] < 12:
            if sample["pt"] + 1e-6 < 8:
                violations.append({"text": sample["text"][:120], "role": "page_header",
                                   "actual_pt": round(sample["pt"], 3), "minimum_pt": 8,
                                   "source": "pdf_text_matrix"})
            continue
        if len(text) < 4:
            if sample["pt"] + 1e-6 < 12:
                size = round(sample["pt"], 2); ambiguous_counts[size] = ambiguous_counts.get(size, 0) + 1
            continue
        if sample["pt"] + 1e-6 < 8:
            violations.append({"text": sample["text"][:120], "role": "unmapped_text",
                               "actual_pt": round(sample["pt"], 3), "minimum_pt": 8,
                               "source": "pdf_text_matrix"})
            continue
        matches = [row for content, row in rows if text in content or content in text]
        thresholds = {float(row["minimum_pt"]) for row in matches}
        if len(thresholds) != 1:
            if sample["pt"] + 1e-6 < 12:
                size = round(sample["pt"], 2); ambiguous_counts[size] = ambiguous_counts.get(size, 0) + 1
            continue
        minimum = thresholds.pop()
        if sample["pt"] + 1e-6 < minimum:
            violations.append({"text": sample["text"][:120], "role": matches[0]["kind"],
                               "actual_pt": round(sample["pt"], 3), "minimum_pt": minimum,
                               "source": "pdf_text_matrix"})
    ambiguous = [{"reason": "PDF text span could not be mapped to a semantic DOM block",
                  "pdf_pt": size, "span_count": count}
                 for size, count in sorted(ambiguous_counts.items())]
    return violations, ambiguous


def render_pdf(html_path: Path, pdf_path: Path, title: str,
               expected_manifest: list[dict[str, str]]) -> tuple[list, list, list[int], tuple[list, list]]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            resource_errors: list[str] = []
            page.on("requestfailed", lambda request: resource_errors.append(request.url))
            page.on("response", lambda response: resource_errors.append(
                f"{response.status} {response.url}") if response.status >= 400 else None)
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=60000)
            page.emulate_media(media="print")
            hidden = page.evaluate("""() => [...document.querySelectorAll('#book *')].filter(el => {
              if (!el.textContent.trim() || el.closest('details[data-appendix-id]')) return false;
              const style=getComputedStyle(el);
              return !el.getClientRects().length || style.display==='none' || style.visibility==='hidden';
            }).map(el=>({tag:el.tagName.toLowerCase(),id:el.id,text:el.textContent.trim().slice(0,100)}))""")
            if hidden:
                raise RuntimeError("hidden or collapsed body content detected: " + json.dumps(hidden, ensure_ascii=False))
            page.evaluate("""async () => {
              await document.fonts.ready;
              const failedFonts=[...document.fonts].filter(face=>face.status==='error');
              if (failedFonts.length) throw new Error('font load failed: '+failedFonts.map(f=>f.family).join(', '));
              const images=[...document.images];
              await Promise.all(images.map(async image => {
                if (!image.complete) await new Promise((resolve,reject) => {
                  image.addEventListener('load',resolve,{once:true});
                  image.addEventListener('error',()=>reject(new Error('image load failed: '+image.src)),{once:true});
                });
                if (image.decode) {
                  try { await image.decode(); }
                  catch (_) { throw new Error('image decode failed: '+image.src); }
                }
                if (!image.naturalWidth || !image.naturalHeight) throw new Error('image decode failed: '+image.src);
              }));
            }""")
            if resource_errors:
                raise RuntimeError("browser resource load failed: " + "; ".join(resource_errors))
            conversion = _print_dom(page)
            before = [normalize_text(row["text"]) for row in conversion["before"]]
            after = [normalize_text(row["text"]) for row in conversion["after"]]
            if before != after:
                raise RuntimeError("appendix text changed while expanding details")
            font_violations = _font_audit(page)
            safe_title = html.escape(title, quote=True)
            header = ('<div style="width:100%;padding:0 26mm;font-family:' + FOOTER_FONT +
                      ';font-size:8.5pt;letter-spacing:.2em;color:#6b6256;text-align:right;">' + safe_title + '</div>')
            footer = ('<div style="width:100%;font-family:' + FOOTER_FONT +
                      ';font-size:9pt;color:#574f44;text-align:center;"><span class="pageNumber"></span></div>')
            page.pdf(path=str(pdf_path), format="A4", print_background=True, tagged=True, outline=True,
                     display_header_footer=True, header_template=header, footer_template=footer, margin=PDF_MARGIN)
            if page.query_selector("header.book-cover"):
                bare_path = pdf_path.with_suffix(".cover.tmp.pdf")
                try:
                    page.pdf(path=str(bare_path), format="A4", print_background=True, tagged=True,
                             outline=True, display_header_footer=False, margin=PDF_MARGIN)
                    if not _strip_cover_chrome(pdf_path, bare_path):
                        raise RuntimeError("cover page could not be rendered without header/footer: "
                                           "page count differs between the two renders")
                finally:
                    bare_path.unlink(missing_ok=True)
            dom_manifest = page.evaluate("""() => [...document.querySelectorAll(
              'section[data-content-kind="disclosure"],p,li,a,figcaption,caption,th,td,blockquote,q,h2,h3,svg text,svg tspan,aside[data-disclosure-id]')]
              .filter(e => e.getClientRects().length && !e.closest('[hidden]'))
              .map((e,i) => {
                const tag=e.tagName.toLowerCase();
                let min=(tag==='td'||tag==='th'||tag==='caption')?9.5:
                  (tag==='blockquote'||tag==='q')?11.5:
                  (tag==='figcaption'||e.closest('.chart-description,.chart-note,.appendix-note'))?10:
                  e.closest('svg')?9:e.closest('[data-content-kind="appendix"]')?10:12;
                return {block_id:e.id||e.getAttribute('data-disclosure-id')||e.getAttribute('data-quote-id')||('print-block-'+i),
                  kind:tag,minimum_pt:min,text:(e.textContent||e.innerText||'').replace(/\\s+/g,' ').trim()};
              }).filter(x=>x.text)""")
            source_text = [normalize_text(row["text"]) for row in expected_manifest]
            print_text = [normalize_text(row["text"]) for row in dom_manifest]
            if source_text != print_text:
                mismatch = next((i for i, pair in enumerate(zip(source_text, print_text)) if pair[0] != pair[1]), None)
                detail = {"index": mismatch, "source_count": len(source_text), "print_count": len(print_text)}
                if mismatch is not None:
                    detail.update(source=source_text[mismatch], printed=print_text[mismatch])
                raise RuntimeError("semantic text changed during browser appendix expansion: " +
                                   json.dumps(detail, ensure_ascii=False))
            pages, sizes, count, blank = _pdf_text_and_fonts(pdf_path)
            missing, ambiguous = _verify_content(dom_manifest, pages)
            pdf_violations, ambiguous_fonts = _audit_pdf_fonts(sizes, dom_manifest, title)
            font_violations.extend(pdf_violations)
            return font_violations, ambiguous_fonts, blank, (missing, ambiguous)
        finally:
            browser.close()


def _result(status: str, html_path: Path, pdf_path: Path, page_count: int,
            missing: list, ambiguous: list, violations: list, font_ambiguous: list,
            diagnostics: list[str]) -> dict[str, Any]:
    return {"status": status, "html_sha256": sha256(html_path) if html_path.exists() else None,
            "pdf_sha256": sha256(pdf_path) if pdf_path.exists() else None,
            "pdf_path": str(pdf_path), "page_count": page_count,
            "size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
            "content_check": {"missing_blocks": missing, "ambiguous_blocks": ambiguous},
            "font_size_check": {"violations": violations, "ambiguous": font_ambiguous},
            "diagnostics": diagnostics}


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "failed", "error": message}), file=sys.stdout)
        print(message, file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = JSONArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path); parser.add_argument("pdf", type=Path)
    parser.add_argument("--verdict", required=True, type=Path); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.html.is_file() or not args.verdict.is_file():
        print(json.dumps({"error": "HTML or verdict file not found"}), file=sys.stdout); return 2
    try:
        source_bytes = args.html.read_bytes(); source = source_bytes.decode("utf-8")
        verdict = json.loads(args.verdict.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stdout); return 2
    digest = hashlib.sha256(source_bytes).hexdigest()
    issues = check("final_verdict", verdict)
    if (issues or verdict.get("review_phase") != "pre_export" or verdict.get("decision") != "awaiting_export"
            or verdict.get("artifact_hashes", {}).get("html") != digest):
        return emit_failure(args, digest, "verdict contract, phase, decision, or HTML hash is invalid", issues)
    if args.html.resolve() == args.pdf.resolve() or args.pdf.resolve() == args.verdict.resolve():
        print(json.dumps({"error": "input, verdict, and PDF paths must be distinct"}), file=sys.stdout); return 2
    _, html_errors, manifest = inspect_html(source)
    if html_errors:
        return emit_failure(args, digest, "HTML structure contains unclassified or hidden content", html_errors)
    diagnostics: list[str] = []
    violations: list[dict[str, Any]] = []
    font_ambiguous: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    pages = 0
    try:
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        title = extract_title(source, args.html.stem)
        violations, font_ambiguous, blank, checks = render_pdf(args.html, args.pdf, title, manifest)
        missing, ambiguous = checks
        _, _, pages, _ = _pdf_text_and_fonts(args.pdf)
        if pages < 1:
            diagnostics.append("PDF contains no pages")
        if blank:
            diagnostics.append("possibly blank pages: " + ", ".join(map(str, blank)))
        if missing:
            diagnostics.append("one or more semantic blocks were not found in extracted PDF text")
        if violations:
            diagnostics.append("one or more rendered text blocks are below the minimum print font size")
        if pages < 1 or missing or violations:
            result = _result("failed", args.html, args.pdf, pages, missing, ambiguous,
                             violations, font_ambiguous, diagnostics)
            print(json.dumps(result, ensure_ascii=False)); return 1
        result = _result("rendered", args.html, args.pdf, pages, missing, ambiguous,
                         violations, font_ambiguous, diagnostics)
        print(json.dumps(result, ensure_ascii=False)); return 0
    except Exception as exc:
        diagnostics.append(f"{type(exc).__name__}: {str(exc)}")
        result = _result("failed", args.html, args.pdf, pages, missing, ambiguous,
                         violations, font_ambiguous, diagnostics)
        print(json.dumps(result, ensure_ascii=False)); return 1


def emit_failure(args, digest: str, message: str, details: Any) -> int:
    result = {"status": "failed", "html_sha256": digest, "pdf_sha256": None,
              "pdf_path": str(args.pdf), "page_count": 0, "size_bytes": 0,
              "content_check": {"missing_blocks": [], "ambiguous_blocks": []},
              "font_size_check": {"violations": [], "ambiguous": []},
              "diagnostics": [message, *([str(x) for x in details] if isinstance(details, list) else [])]}
    print(json.dumps(result, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    sys.exit(main())
