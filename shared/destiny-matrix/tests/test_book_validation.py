import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_book.py"


class BookValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.html = self.root / "book.html"
        self.plan = self.root / "plan.json"
        self.evidence = self.root / "evidence.json"
        self.sources = self.root / "sources.json"
        artifact = self.root / "chart.json"
        payload = json.dumps({"value": 12, "missing": None}).encode()
        artifact.write_bytes(payload)
        self.data_ref = "chart#"
        evidence = {"artifacts": [{"artifact_id": "chart", "path": "chart.json",
                                    "sha256": hashlib.sha256(payload).hexdigest(), "status": "current"}],
                    "claims": [{"claim_id": "J-001", "status": "active"},
                               {"claim_id": "J-002", "status": "superseded"}]}
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        self.sources.write_text(json.dumps({"sources": [{"source_id": "S1", "verification_status": "verified",
            "quotes": [{"quote_id": "Q1", "original": "核准原句", "translation": "已核译文", "translation_kind": "own"}]},
            {"source_id": "S2", "verification_status": "unverified", "quotes": [
                {"quote_id": "Q2", "original": "未核原句", "translation_kind": "none"}]}]}), encoding="utf-8")
        self.plan.write_text(json.dumps(self.plan_doc()), encoding="utf-8")
        self.html.write_text(self.html_doc(), encoding="utf-8")

    def plan_doc(self):
        return {"sections": [{"section_id": x} for x in ("personality", "bazi", "ziwei")],
                "chart_table": [{"chart_id": f"chart-{s}-01", "section_id": s,
                    "data_refs": ["chart#/value" if s == "personality" else "chart#/missing"],
                    "missing_policy": "omit_with_disclosure"} for s in ("personality", "bazi")]}

    def html_doc(self, extra="", body_details="", hidden="", bad_claim=""):
        return f'''<html><body><main id="book"><section data-content-kind="disclosure" id="disclosure-basis">口径说明</section>
        <section data-content-kind="body" data-section-id="personality" id="ch-personality"><h2>一</h2>
        <p data-claim-ids="J-001">正文 {extra} {bad_claim}</p><a href="#appendix-personality">方法</a>{body_details}{hidden}
        <q data-quote-id="Q1">核准原句</q><figure class="chart-container" data-chart-id="chart-personality-01" data-section-id="personality"><figcaption>值为 <span data-value-ref="chart#/value" data-value="12" data-unit="分" data-precision="0">12分</span></figcaption><svg><circle id="c1" cx="2" cy="2" r="1"/></svg></figure></section>
        <section data-content-kind="body" data-section-id="bazi" id="ch-bazi"><p>二</p><figure class="chart-container" data-chart-id="chart-bazi-01" data-section-id="bazi"><figcaption>缺值</figcaption><svg><circle cx="2" cy="2" r="1"/></svg></figure></section>
        <section data-content-kind="body" data-section-id="ziwei" id="ch-ziwei"><p>三</p></section>
        <section data-content-kind="appendix" id="appendix"><details id="appendix-personality" data-appendix-id="appendix-personality"><summary>方法</summary><a href="#ch-personality">返回正文</a></details></section></main></body></html>'''

    def run_check(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), str(self.html), "--plan", str(self.plan),
            "--evidence", str(self.evidence), "--sources", str(self.sources), "--json"],
            capture_output=True, text=True)
        return proc.returncode, json.loads(proc.stdout)

    def test_three_section_two_chart_focused_book_passes(self):
        code, result = self.run_check()
        self.assertEqual(code, 0, result)
        self.assertTrue(result["ok"])
        self.assertEqual(result["stats"]["sections"], 3)

    def test_extra_26_figures_do_not_make_plan_mismatch_pass(self):
        extra = "".join(f'<figure class="chart-container" data-chart-id="extra-{i}"><svg><circle r="1"/></svg></figure>' for i in range(26))
        self.html.write_text(self.html_doc(extra=extra), encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("chart_plan_mismatch", {i["code"] for i in result["issues"]})

    def test_wrong_and_unverified_quotes_fail(self):
        self.html.write_text(self.html_doc().replace("核准原句</q>", "伪造引文</q>"), encoding="utf-8")
        self.assertIn("quote_text_mismatch", {i["code"] for i in self.run_check()[1]["issues"]})
        self.html.write_text(self.html_doc().replace('data-quote-id="Q1">核准原句', 'data-quote-id="Q2">未核原句'), encoding="utf-8")
        self.assertIn("unverified_quote", {i["code"] for i in self.run_check()[1]["issues"]})

    def test_numeric_binding_and_missing_zero_fail(self):
        self.html.write_text(self.html_doc().replace('data-value="12"', 'data-value="13"'), encoding="utf-8")
        self.assertIn("value_binding_mismatch", {i["code"] for i in self.run_check()[1]["issues"]})
        self.html.write_text(self.html_doc().replace('<figcaption>缺值</figcaption>', '<figcaption><span data-value-ref="chart#/missing" data-value="0" data-unit="分" data-precision="0">0分</span></figcaption>'), encoding="utf-8")
        self.assertTrue({"missing_value_rendered", "missing_plotted_as_zero"} & {i["code"] for i in self.run_check()[1]["issues"]})
    def test_data_ref_container_matches_pointer_descendants_by_segment(self):
        pairs = [{"left": 12 if i == 0 or i == 10 else i} for i in range(11)]
        payload = json.dumps({"pairs": pairs, "missing": None}).encode()
        (self.root / "chart.json").write_bytes(payload)
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["artifacts"][0]["sha256"] = hashlib.sha256(payload).hexdigest()
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        plan = self.plan_doc()
        plan["chart_table"][0]["data_refs"] = ["chart#/pairs"]
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        html = self.html_doc().replace("chart#/value", "chart#/pairs/0/left")
        self.html.write_text(html, encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 0, result)

        plan["chart_table"][0]["data_refs"] = ["chart#/pairs/1"]
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        self.html.write_text(html.replace("chart#/pairs/0/left", "chart#/pairs/10/left"), encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("unrendered_data_ref", {issue["code"] for issue in result["issues"]})

    def test_body_details_hidden_text_and_comments_fail(self):
        for markup in ('<details><summary>隐藏正文</summary></details>', '<p hidden>隐藏正文</p>',
                       '<p style="display:none">隐藏正文</p>', '<p aria-hidden="true">隐藏正文</p>',
                       '<style>.secret{display:none}</style><p class="secret">隐藏正文</p>'):
            self.html.write_text(self.html_doc(body_details=markup), encoding="utf-8")
            self.assertTrue({"details_outside_appendix", "hidden_dom"} & {i["code"] for i in self.run_check()[1]["issues"]})
        self.html.write_text(self.html_doc().replace("</main>", "<!--审稿日志--></main>"), encoding="utf-8")
        self.assertIn("html_comment", {i["code"] for i in self.run_check()[1]["issues"]})

    def test_superseded_claim_fails_but_forbidden_term_is_review_only(self):
        self.html.write_text(self.html_doc(bad_claim='<span data-claim-ids="J-002">旧结论</span>', extra='历史引文说“命中注定”，本文明确否定。'), encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("inactive_claim", {i["code"] for i in result["issues"]})
        self.assertTrue(any(row["term"] == "命中注定" and "明确否定" in row["snippet"] for row in result["review_required"]))
        self.html.write_text(self.html_doc(extra='历史引文说“命中注定”，本文明确否定。'), encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 0, result)
        self.assertTrue(any(row["term"] == "命中注定" for row in result["review_required"]))

    # --- v5.2 reader-layer limitations and style hints ------------------------
    def use_limitations(self, adjacent_section="personality"):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        row = lambda lid, changes, placement: {"limitation_id": lid, "affected_claim_ids": ["J-001"], "impact": "i",
                                               "changes_reading": changes, "reader_text": "t", "required_placement": placement}
        evidence["limitations"] = [row("L-OPEN", True, "opening"), row("L-ADJ", True, "adjacent"), row("L-AUD", False, "appendix")]
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        plan = self.plan_doc()
        for section in plan["sections"]:
            section["limitation_ids"] = ["L-ADJ"] if section["section_id"] == adjacent_section else []
        self.plan.write_text(json.dumps(plan), encoding="utf-8")

    def limited_html(self, body_marks='<aside data-disclosure-id="d-adj" data-limitation-id="L-ADJ">如果时辰改动，这一节改读。</aside>',
                     opening_mark=' data-limitation-id="L-OPEN"', ziwei_extra=""):
        html = self.html_doc(extra=body_marks).replace('id="disclosure-basis">口径说明',
                                                       f'id="disclosure-basis"><p{opening_mark}>这是反思读物。</p>')
        return html.replace("<p>三</p>", "<p>三</p>" + ziwei_extra)

    def codes(self):
        return {i["code"] for i in self.run_check()[1]["issues"]}

    def test_reader_limitations_render_once_where_planned(self):
        self.use_limitations()
        self.html.write_text(self.limited_html(), encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 0, result)

    def test_adjacent_limitation_missing_or_repeated_fails(self):
        self.use_limitations()
        self.html.write_text(self.limited_html(body_marks=""), encoding="utf-8")
        self.assertIn("limitation_missing", self.codes())
        twice = '<span data-limitation-id="L-ADJ">按时辰前提</span><span data-limitation-id="L-ADJ">按时辰前提</span>'
        self.html.write_text(self.limited_html(body_marks=twice), encoding="utf-8")
        self.assertIn("limitation_repeated", self.codes())
        hidden = '<span hidden data-limitation-id="L-ADJ">按时辰前提</span>'
        self.html.write_text(self.limited_html(body_marks=hidden), encoding="utf-8")
        self.assertTrue({"limitation_missing", "hidden_dom"} <= self.codes())

    def test_hollow_limitation_marker_fails(self):
        self.use_limitations()
        for hollow in ('<span data-limitation-id="L-ADJ"></span>', '<span data-limitation-id="L-ADJ">L-ADJ</span>',
                       '<span data-limitation-id="L-ADJ">按时辰</span>'):
            with self.subTest(markup=hollow):
                self.html.write_text(self.limited_html(body_marks=hollow), encoding="utf-8")
                self.assertIn("limitation_empty", self.codes())
        self.html.write_text(self.limited_html(body_marks='<span data-limitation-id="L-ADJ">按前面说的时辰前提</span>'), encoding="utf-8")
        self.assertNotIn("limitation_empty", self.codes())

    def test_limitation_layer_placement_is_enforced(self):
        self.use_limitations()
        self.html.write_text(self.limited_html(opening_mark=""), encoding="utf-8")
        self.assertIn("limitation_missing", self.codes())
        self.html.write_text(self.limited_html(ziwei_extra='<p data-limitation-id="L-AUD">排版软件版本。</p>'), encoding="utf-8")
        self.assertIn("appendix_limitation_in_body", self.codes())
        self.html.write_text(self.limited_html(ziwei_extra='<p data-limitation-id="L-ADJ">再说一次。</p>'), encoding="utf-8")
        self.assertIn("limitation_wrong_placement", self.codes())
        self.html.write_text(self.limited_html(ziwei_extra='<p data-limitation-id="L-OPEN">再说一次。</p>'), encoding="utf-8")
        self.assertIn("limitation_wrong_placement", self.codes())
        self.html.write_text(self.limited_html(ziwei_extra='<p data-limitation-id="L-GHOST">未登记。</p>'), encoding="utf-8")
        self.assertIn("unknown_limitation", self.codes())

    def test_common_reading_source_cannot_be_quoted(self):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["sources"] = [{"source_id": "S1", "kind": "common_reading"}]
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        self.assertIn("common_reading_quoted", self.codes())

    def test_process_words_and_denial_openings_are_review_only(self):
        body = '</p><p>不是说你冷淡，而是先观察。</p><p>本次按工具虚岁计算，已绑定 artifact。</p><p>'
        appendix_note = '<p>本次使用的工具与字段见此。</p>'
        html = self.html_doc(extra=body).replace('<summary>方法</summary>', '<summary>方法</summary>' + appendix_note)
        self.html.write_text(html, encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 0, result)
        rows = result["review_required"]
        process = [r for r in rows if r["kind"] == "process_term"]
        terms = {r["term"] for r in process}
        self.assertTrue({"本次", "工具虚岁", "绑定", "artifact", "口径"} <= terms, rows)
        self.html.write_text(self.html_doc(extra="审稿后未采用这条读法。"), encoding="utf-8")
        terms = {r["term"] for r in self.run_check()[1]["review_required"] if r["kind"] == "process_term"}
        self.assertTrue({"审稿", "未采用"} <= terms)
        self.assertNotIn("工具", terms)  # nested inside 工具虚岁, reported once
        self.assertFalse(any(r["location"].startswith("appendix") for r in process))
        self.assertTrue(any(r["kind"] == "opening_negation" and r["term"] == "不是" for r in rows))

    def test_many_opening_limitations_raise_review_hint(self):
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["limitations"] = [{"limitation_id": f"L-{i}", "affected_claim_ids": [], "impact": "i", "changes_reading": True,
                                    "reader_text": "t", "required_placement": "opening"} for i in range(6)]
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        marks = "".join(f'<p data-limitation-id="L-{i}">这是第{i}条通用阅读边界</p>' for i in range(6))
        self.html.write_text(self.html_doc().replace('id="disclosure-basis">口径说明', f'id="disclosure-basis">{marks}'), encoding="utf-8")
        code, result = self.run_check()
        self.assertEqual(code, 0, result)
        self.assertTrue(any(r["kind"] == "opening_limitation_count" for r in result["review_required"]))


if __name__ == "__main__":
    unittest.main()
