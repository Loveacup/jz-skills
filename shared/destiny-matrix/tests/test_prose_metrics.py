import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prose_metrics.py"
sys.path.insert(0, str(ROOT / "scripts"))

import prose_metrics as pm  # noqa: E402
from book_html import BookHTML  # noqa: E402

# 全部为合成文本，不取自任何个案。
AUDIT = (
    "<h2>正印格是讨论入口，不是成败结论</h2>"
    "<p>章节副题 · 没有句号的一行</p>"
    "<p>本章采用子平读法。本次未核藏干细则，不裁定，不代表缺陷，也不能说明能力。</p>"
    "<p>日主身弱，财多身弱，印星为用，官杀混杂，食伤不足。</p>"
    "<p>这也许可能在某种程度上说明一些问题。</p>"
    "<aside data-disclosure-id=\"d1\" data-limitation-id=\"L-1\"><p>量程来自说明；这一限制不能忽略。</p></aside>"
    "<figure class=\"chart-container\" data-chart-id=\"chart-bazi-01\"><figcaption>图题不是正文，本次不计</figcaption>"
    "<table><tr><td>表格里的工具与字段不计入</td></tr></table></figure>"
    "<p><a href=\"#appendix-bazi\">查看本章方法</a></p>"
)
READER = (
    "<h2>密林里的太阳</h2>"
    "<p>你这张盘，是一轮春天的太阳照着一片太密的林子。在子平的读法里，木是供养你的那一路，传统上叫“印”，"
    "也就是让你有所凭依的东西；按这个读法，你的底气多半来自学过的东西。</p>"
    "<p>例如要写一份方案，你会先把资料读完才动笔。如果你通常是这样，这一节大概贴合；"
    "如果你更常边做边改，这条读法就不太贴合你。</p>"
)


def book(*chapters, appendix="<p>附录里的本次、工具、口径都不计。</p>"):
    body = "".join(
        f'<section data-content-kind="body" data-section-id="{sid}" id="ch-{sid}">{html}</section>'
        for sid, html in chapters)
    return ('<html><head><style>p{color:#111}</style><script>var x="不是";</script></head><body><main id="book">'
            '<section data-content-kind="disclosure" id="disclosure-basis"><p>披露里的不是与不能不计。</p></section>'
            f'{body}<section data-content-kind="appendix" id="appendix"><details id="a1" data-appendix-id="a1">'
            f'<summary>方法</summary>{appendix}</details></section></main></body></html>')


def analyse(html, **kwargs):
    return pm.analyse(BookHTML(html), pm.load_terms(None, False), **kwargs)


class ProseMetricsTests(unittest.TestCase):
    def setUp(self):
        self.result = analyse(book(("bazi", AUDIT), ("ziwei", READER)))
        self.bazi, self.ziwei = self.result["chapters"]

    def test_counts_body_only(self):
        self.assertEqual([c["id"] for c in self.result["chapters"]], ["bazi", "ziwei"])
        text = json.dumps(self.result, ensure_ascii=False)
        for outside in ("附录里", "披露里", "图题", "表格里", "查看本章方法", "var x"):
            self.assertNotIn(outside, text)
        self.assertEqual(self.result["totals"]["chars"], self.bazi["chars"] + self.ziwei["chars"])
        self.assertEqual(pm.count_chars("你有 3 个 Fe 选项。"), 7)

    def test_negation_density_and_densest_paragraph(self):
        self.assertEqual(self.bazi["negation"]["hits"], 3)
        self.assertEqual(self.bazi["negation"]["terms"], {"不代表": 1, "不能说明": 1, "不能": 1})
        self.assertGreater(self.bazi["negation"]["sentence_ratio"], self.ziwei["negation"]["sentence_ratio"])
        densest = self.result["totals"]["negation"]["densest_paragraphs"]
        self.assertEqual(densest[0]["location"], "bazi:b1")
        self.assertEqual(densest[0]["negations"], 2)

    def test_questions_are_not_negations(self):
        result = analyse(book(("bazi", "<p>你是不是也这样？你能不能先停一下？这并不是结论。</p>")))
        self.assertEqual(result["totals"]["negation"]["hits"], 1)

    def test_not_but_pattern(self):
        result = analyse(book(("bazi", "<p>你要的不是答案，而是一个出口。</p>")))
        self.assertEqual(result["totals"]["negation"]["not_but"], 1)

    def test_fixed_phrases_and_titles_are_not_negations(self):
        result = analyse(book(("bazi", "<p>你不得不先停下来。这件事不可思议，也谈不上无法无天。"
                                       "你读过《不能承受的生命之轻》。</p>")))
        self.assertEqual(result["totals"]["negation"]["hits"], 0)
        self.assertEqual(result["totals"]["negation"]["quoted"], 0)
        kept = analyse(book(("bazi", "<p>你不得不先停下来，但这不代表你慢。</p>")))
        self.assertEqual(kept["totals"]["negation"]["terms"], {"不代表": 1})

    def test_quoted_speech_is_counted_apart(self):
        result = analyse(book(("bazi", "<p>下一次你可以说：“我不能马上答应。这不是拒绝。”然后停一停。这并不难。</p>")))
        negation = result["totals"]["negation"]
        self.assertEqual(negation["hits"], 1)
        self.assertEqual(negation["terms"], {"并不": 1})
        self.assertEqual(negation["quoted"], 2)
        self.assertEqual(negation["sentences"], 1)

    def test_not_but_across_sentences(self):
        result = analyse(book(("bazi", "<p>你要的不是答案。而是一个出口。</p><p>这不是终点；而是中途。</p>")))
        self.assertEqual(result["totals"]["negation"]["not_but"], 2)
        apart = analyse(book(("bazi", "<p>这不是终点。</p><p>而是中途。</p>")))
        self.assertEqual(apart["totals"]["negation"]["not_but"], 0)

    def test_chapter_without_prose_gets_no_hints(self):
        table = "<h2>数据</h2><figure class=\"chart-container\"><table><tr><td>只有表格</td></tr></table></figure>"
        result = analyse(book(("ziwei", READER), ("timing", table)))
        row = result["chapters"][1]
        self.assertEqual((row["chars"], row["priority"], row["problems"]), (0, 0.0, []))
        self.assertEqual(result["totals"]["mirrors"]["chapters_without"], [])
        self.assertEqual(result["totals"]["mirrors"]["chapters_without_example"], [])

    def test_falsifiable_branch_variants(self):
        for phrase in ("这条读法就不太贴合你", "七杀独坐这一条在你身上就落了空", "月土合相说的就不是你",
                       "这一节的综合在你身上就对不上", "这条读法在孩子身上就不成立", "这一段就不太像你"):
            result = analyse(book(("bazi", f"<p>如果你更常边做边改，{phrase}。</p>")))
            self.assertEqual(result["totals"]["mirrors"]["falsifiable"], 1, phrase)

    def test_fallback_uses_h3_when_there_is_no_h2(self):
        html = ("<html><body><h1>书名</h1><h3>第一章</h3><p>你先动手。</p><h3>第二章</h3><p>本次未核。</p>"
                "</body></html>")
        result = analyse(html)
        self.assertEqual(result["structure"], "fallback")
        self.assertEqual([c["title"] for c in result["chapters"]], ["第一章", "第二章"])
        self.assertEqual([len(c["process_terms"]) for c in result["chapters"]], [0, 2])

    def test_falsifiable_branch_is_not_a_negation(self):
        result = analyse(book(("bazi", "<p>要是你向来话不过夜，月土合相说的就不是你。</p>")))
        self.assertEqual(result["totals"]["negation"]["hits"], 0)
        self.assertEqual(result["totals"]["mirrors"]["falsifiable"], 1)

    def test_process_terms_with_location(self):
        terms = [(hit["term"], hit["location"]) for hit in self.bazi["process_terms"]]
        self.assertEqual(terms, [("本次", "bazi:b1"), ("未核", "bazi:b1"), ("不裁定", "bazi:b1")])
        self.assertEqual(self.ziwei["process_terms"], [])
        self.assertEqual(self.result["totals"]["process_terms"]["hits"], 3)

    def test_title_negation(self):
        self.assertEqual([t["text"] for t in self.bazi["title_negations"]], ["正印格是讨论入口，不是成败结论"])
        self.assertEqual(self.ziwei["title_negations"], [])
        self.assertEqual(self.result["totals"]["title_negations"], {"count": 1, "headings": 2})

    def test_opening_types(self):
        cases = {
            "你这张盘，是一轮春天的太阳。": "judgement",
            "在紫微的读法里，你的命宫坐着一颗将星。": "judgement",
            "这组分数里最高的两项是内倾感觉和外倾思维。": "judgement",
            "本章采用三合派读法。": "method",
            "先在图上找太阳、月亮与上升。": "method",
            "这不代表你缺乏领导能力。": "denial",
            "你并不是一个固定的类型。": "denial",
            "需要注意，测验分数有量程。": "limitation",
            "月令是申，月干庚为正印。": "chart_fact",
            "例如要写一份方案，你会先把资料读完。": "mirror",
            "春天的雨下了一整夜。": "other",
        }
        terms_re = pm.term_pattern(pm.load_terms(None, False))
        for sentence, expected in cases.items():
            self.assertEqual(pm.classify_opening(sentence, terms_re), expected, sentence)

    def test_chapter_opening_skips_subtitle_and_limitation(self):
        openings = self.bazi["openings"]["items"]
        self.assertEqual(openings[0]["location"], "bazi:b1")
        self.assertEqual((openings[0]["role"], openings[0]["type"]), ("chapter", "method"))
        self.assertEqual(self.ziwei["openings"]["items"][0]["type"], "judgement")
        self.assertEqual(self.result["totals"]["openings"]["chapter_openings"]["judgement"], 1)

    def test_long_paragraph_openings_are_classified(self):
        long_para = "<p>本节先说明取法的来历。" + "这一句只是为了把段落撑长到需要统计首句的长度。" * 6 + "</p>"
        result = analyse(book(("bazi", "<p>你先动手。</p><p>短段不计。</p>" + long_para)))
        items = result["chapters"][0]["openings"]["items"]
        self.assertEqual([(i["role"], i["type"]) for i in items], [("chapter", "judgement"), ("long_paragraph", "method")])
        self.assertEqual(result["totals"]["openings"]["judgement_ratio"], 0.5)

    def test_voice_labels(self):
        labels = self.ziwei["voice_labels"]["by_label"]
        self.assertEqual(labels["在…的读法里"], 1)
        self.assertEqual(labels["传统上"], 1)
        self.assertGreaterEqual(labels["按…派／按…的读法"], 1)
        self.assertGreater(self.ziwei["voice_labels"]["total"], self.bazi["voice_labels"]["total"])

    def test_mirrors_and_chapters_without(self):
        self.assertEqual(self.ziwei["mirrors"], {"example": 1, "conditional": 2, "falsifiable": 1})
        mirrors = self.result["totals"]["mirrors"]
        self.assertEqual(mirrors["chapters_without"], ["bazi"])
        self.assertEqual(mirrors["chapters_without_example"], ["bazi"])

    def test_hedge_stacking(self):
        self.assertEqual(len(self.bazi["hedge_stacking"]), 1)
        self.assertEqual(self.bazi["hedge_stacking"][0]["hedges"], ["也许", "可能", "在某种程度上"])
        single = analyse(book(("bazi", "<p>你可能会先动手。也许明天再说。</p>")))
        self.assertEqual(single["totals"]["hedge_stacking"], 0)

    def test_jargon_density_and_gloss(self):
        flagged = self.bazi["jargon"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["location"], "bazi:b2")
        self.assertIn("财多身弱", flagged[0]["unexplained"])
        self.assertEqual(self.ziwei["jargon"], [])
        glossed = analyse(book(("bazi",
            "<p>代表你的那个字力量偏轻，传统叫“身弱”；能补给你的那一路叫作印星；管表达的食伤（食神与伤官）在后面。</p>"
            "<p>身弱、印星、食伤三样连起来读。</p>")))
        self.assertEqual(glossed["totals"]["jargon_sentences"], 0)

    def test_custom_terms(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "terms.txt"
            path.write_text("甲术语\n乙术语 # 注释\n丙术语\n丁术语\n", encoding="utf-8")
            terms = pm.load_terms(str(path), True)
            self.assertEqual(sorted(terms), ["丁术语", "丙术语", "乙术语", "甲术语"])
            result = pm.analyse(BookHTML(book(("bazi", "<p>甲术语、乙术语、丙术语与丁术语同时出现，日主用神忌神不算。</p>"))), terms)
            self.assertEqual(result["chapters"][0]["jargon"][0]["unexplained"], ["甲术语", "乙术语", "丙术语", "丁术语"])
            path.write_text(json.dumps({"a": ["甲术语"], "b": ["乙术语"]}, ensure_ascii=False), encoding="utf-8")
            self.assertIn("甲术语", pm.load_terms(str(path), False))
            self.assertIn("日主", pm.load_terms(str(path), False))

    def test_length_distribution_and_long_items(self):
        long_sentence = "你" + "很长的句子" * 13 + "。"
        long_para = "<p>" + "你把事情一件一件排好。" * 30 + "</p>"
        result = analyse(book(("bazi", f"<p>{long_sentence}</p>{long_para}<p>短句。</p>")))
        row = result["chapters"][0]
        self.assertEqual(len(row["long_sentences"]), 1)
        self.assertEqual(row["long_sentences"][0]["chars"], 66)
        self.assertEqual(len(row["long_paragraphs"]), 1)
        self.assertEqual(row["paragraph_length"]["max"], 300)
        self.assertEqual(row["sentence_length"]["max"], 66)
        self.assertEqual(row["paragraph_length"]["count"], 3)

    def test_limitation_share(self):
        self.assertEqual(self.bazi["limitation_blocks"], 1)
        self.assertGreater(self.bazi["limitation_share"], 0)
        self.assertEqual(self.ziwei["limitation_share"], 0)

    def test_summary_ranks_audit_chapter_first(self):
        summary = self.result["summary"]
        self.assertEqual(summary[0]["id"], "bazi")
        self.assertGreater(summary[0]["priority"], summary[1]["priority"])
        self.assertTrue(any("流程词" in p for p in self.bazi["problems"]))
        self.assertTrue(any("假设镜像" in p for p in self.bazi["problems"]))
        self.assertEqual(self.ziwei["problems"], [])

    def test_hidden_content_is_ignored(self):
        result = analyse(book(("bazi", '<p>你先动手。</p><p hidden>本次不是。</p><div style="display:none"><p>工具。</p></div>')))
        self.assertEqual(result["totals"]["negation"]["hits"], 0)
        self.assertEqual(result["totals"]["process_terms"]["hits"], 0)

    def test_list_and_definition_blocks(self):
        result = analyse(book(("practice",
            "<ul><li>你可以先写三句。</li><li><p>嵌套段落也算一次。</p></li></ul>"
            "<dl><dt>可以做什么</dt><dd>如果卡住，就先停两分钟。</dd></dl><div>直接写在容器里的文字。</div>")))
        row = result["chapters"][0]
        self.assertEqual(row["paragraphs"], 4)
        self.assertEqual(row["mirrors"]["conditional"], 1)

    def test_fallback_structure(self):
        html = ("<html><body><h1>书名</h1><h2>第一章</h2><p>你先动手。</p><h2>第二章，不是结论</h2><p>本次未核。</p>"
                '<div class="appendix"><h2>附录</h2><p>工具口径。</p></div></body></html>')
        result = analyse(html)
        self.assertEqual(result["structure"], "fallback")
        self.assertEqual([c["title"] for c in result["chapters"]], ["第一章", "第二章，不是结论"])
        self.assertEqual(result["totals"]["process_terms"]["hits"], 2)
        self.assertEqual(result["totals"]["title_negations"]["count"], 1)

    def test_no_snippets_mode_drops_book_text(self):
        result = analyse(book(("bazi", AUDIT), ("ziwei", READER)), snippets=False)
        text = json.dumps(result, ensure_ascii=False)
        for fragment in ("密林", "讨论入口", "春天的太阳", "藏干细则"):
            self.assertNotIn(fragment, text)
        self.assertEqual(result["totals"]["negation"]["hits"], self.result["totals"]["negation"]["hits"])

    def test_deterministic(self):
        html = book(("bazi", AUDIT), ("ziwei", READER))
        self.assertEqual(json.dumps(analyse(html), ensure_ascii=False, sort_keys=True),
                         json.dumps(analyse(html), ensure_ascii=False, sort_keys=True))


class ProseMetricsCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "book.html"
        self.path.write_text(book(("bazi", AUDIT), ("ziwei", READER)), encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_json_output(self):
        proc = self.run_cli(str(self.path), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["ok"])
        self.assertIn("不是门槛", result["notice"])
        self.assertEqual(result["structure"], "semantic")

    def test_text_report_states_it_is_not_a_gate(self):
        proc = self.run_cli(str(self.path))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("这是诊断，不是门槛", proc.stdout)
        for heading in ("分章概览", "否定限定句", "流程词", "标题里的否定式", "章首句与长段首句", "声源标签",
                        "假设镜像标记", "虚词连用", "术语密集句", "句长与段长", "汇总"):
            self.assertIn(heading, proc.stdout)

    def test_diagnosis_never_fails_a_book(self):
        self.path.write_text(book(("bazi", AUDIT * 5)), encoding="utf-8")
        self.assertEqual(self.run_cli(str(self.path), "--json").returncode, 0)

    def test_input_errors_exit_2(self):
        missing = self.run_cli(str(Path(self.tmp.name) / "none.html"), "--json")
        self.assertEqual(missing.returncode, 2)
        payload = json.loads(missing.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["issues"][0]["code"], "input_error")
        self.path.write_text("<html><body><main id=\"book\"></main></body></html>", encoding="utf-8")
        self.assertEqual(self.run_cli(str(self.path)).returncode, 2)
        self.assertEqual(self.run_cli(str(self.path), "--terms", str(Path(self.tmp.name) / "none.txt")).returncode, 2)
        self.assertEqual(self.run_cli().returncode, 2)


class ExemplarTests(unittest.TestCase):
    """references/exemplars.md 的范文（引用块）应当经得起自己的诊断。"""

    @classmethod
    def setUpClass(cls):
        import html
        import re
        source = (ROOT / "references" / "exemplars.md").read_text(encoding="utf-8")
        sections = []
        for part in re.split(r"^## ", source, flags=re.M):
            head = re.match(r"(\d+)\. (.+)\n", part)
            if not head:
                continue
            blocks = []
            for line in (l[1:].strip() for l in part.splitlines() if l.startswith(">")):
                title = re.match(r"\*\*(.+)\*\*$", line)
                if title:
                    blocks.append("<h3>%s</h3>" % html.escape(title.group(1)))
                elif line:
                    blocks.append("<p>%s</p>" % html.escape(line))
            sections.append(("ex" + head.group(1), "".join(blocks)))
        cls.source = source
        cls.result = analyse(book(*sections))
        cls.rows = {row["id"]: row for row in cls.result["chapters"]}

    def test_all_ten_exemplars_present(self):
        self.assertEqual(sorted(self.rows, key=lambda k: int(k[2:])), ["ex%d" % i for i in range(1, 11)])
        for row in self.rows.values():
            self.assertGreater(row["chars"], 100, row["id"])
        self.assertGreaterEqual(self.rows["ex2"]["chars"], 600)
        self.assertLessEqual(self.rows["ex2"]["chars"], 900)

    def test_reader_language(self):
        totals = self.result["totals"]
        self.assertEqual(totals["process_terms"]["hits"], 0)
        self.assertEqual(totals["title_negations"]["count"], 0)
        self.assertEqual(totals["hedge_stacking"], 0)
        self.assertEqual(totals["negation"]["not_but"], 0)
        self.assertEqual(totals["dashes"], 0)
        self.assertLess(totals["negation"]["sentence_ratio"], 0.05)
        from validate_book import HARD_FORBIDDEN
        quoted = "\n".join(l for l in self.source.splitlines() if l.startswith(">"))
        for word in HARD_FORBIDDEN:
            self.assertNotIn(word, quoted)

    def test_system_sections_open_with_judgement_and_offer_a_falsifiable_mirror(self):
        for key in ("ex2", "ex3", "ex4", "ex5", "ex6"):
            row = self.rows[key]
            self.assertEqual(row["openings"]["items"][0]["type"], "judgement", key)
            self.assertGreaterEqual(row["mirrors"]["example"] + row["mirrors"]["conditional"], 1, key)
            self.assertGreaterEqual(row["mirrors"]["falsifiable"], 1, key)
            self.assertGreaterEqual(row["voice_labels"]["total"], 3, key)
            self.assertEqual(row["long_paragraphs"], [], key)
        for key in ("ex9", "ex10"):
            self.assertGreaterEqual(self.rows[key]["mirrors"]["falsifiable"], 1, key)

    def test_falsifiable_branch_is_not_one_formula(self):
        quoted = "\n".join(l for l in self.source.splitlines() if l.startswith(">"))
        self.assertLessEqual(quoted.count("不太贴合"), 2)
        kinds = [k for k in ("不太贴合", "落了空", "说的就不是你", "对不上", "不成立", "不太像你") if k in quoted]
        self.assertGreaterEqual(len(kinds), 3)
        self.assertNotIn("另一半", quoted)


if __name__ == "__main__":
    unittest.main()
