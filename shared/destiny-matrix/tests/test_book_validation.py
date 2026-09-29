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

if __name__ == "__main__":
    unittest.main()
