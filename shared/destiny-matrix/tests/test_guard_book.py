import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "guard_book.py"


class GuardBookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.before = self.root / "before.html"
        self.after = self.root / "after.html"
        self.evidence = self.root / "evidence.json"
        self.revision = self.root / "revision.json"
        self.evidence_doc = {"claims": [{"claim_id": "J-001", "status": "active"},
                                         {"claim_id": "J-002", "status": "active"}],
                             "corrections": [{"correction_id": "C1", "invalidated_claim_ids": ["J-001"]}]}
        self.write_json(self.evidence, self.evidence_doc)
        self.write_json(self.revision, {"accepted": True, "revision_instructions": [{
            "check_id": "A3", "fix_type": "analysis", "owner": "analyst", "claim_ids": ["J-002"],
            "section_ids": ["personality"], "problem": "旧依据失效", "acceptance": "仅用有效依据"}]})
        self.before.write_text(self.html("旧数字12分，限制为候选。", "J-001", "另一章原文。"), encoding="utf-8")
        self.after.write_text(self.before.read_text(encoding="utf-8"), encoding="utf-8")

    @staticmethod
    def write_json(path, obj):
        path.write_text(json.dumps(obj), encoding="utf-8")

    @staticmethod
    def html(first, claim, second):
        return f'''<html><head><style>body{{color:#111}}</style></head><body><main id="book">
        <section data-content-kind="disclosure" id="basis">关键限制 disclosure。</section>
        <section data-content-kind="body" data-section-id="personality" id="ch-personality"><p data-claim-ids="{claim}">{first}</p>
        <figure class="chart-container" data-chart-id="chart-personality-01"><figcaption>稳定图</figcaption><svg><circle r="2"/></svg></figure></section>
        <section data-content-kind="body" data-section-id="bazi" id="ch-bazi"><p>{second}</p></section>
        <section data-content-kind="appendix" id="appendix"></section></main></body></html>'''

    def run_guard(self, scope, targets="", revision=None, evidence=None, before=None, after=None):
        args = [sys.executable, str(SCRIPT), "--before", str(before or self.before), "--after", str(after or self.after),
                "--scope", scope, "--targets", targets or "personality", "--json"]
        if revision:
            args += ["--revision", str(revision)]
        if evidence:
            args += ["--evidence", str(evidence)]
        proc = subprocess.run(args, capture_output=True, text=True)
        return proc.returncode, json.loads(proc.stdout)
    def test_layout_content_and_limit_changes_are_rejected(self):
        self.after.write_text(self.before.read_text().replace("12分", "13分"), encoding="utf-8")
        self.assertEqual(self.run_guard("layout")[0], 1)
        self.after.write_text(self.before.read_text().replace("为候选", "已确定"), encoding="utf-8")
        self.assertEqual(self.run_guard("layout")[0], 1)

    def test_citations_cannot_change_body_and_prose_cannot_change_other_section(self):
        self.after.write_text(self.before.read_text().replace("候选", "确定"), encoding="utf-8")
        self.assertEqual(self.run_guard("citations")[0], 1)
        self.after.write_text(self.before.read_text().replace("另一章原文", "另一章改写"), encoding="utf-8")
        self.assertEqual(self.run_guard("prose", "personality")[0], 1)

    def test_layout_style_change_passes(self):
        self.after.write_text(self.before.read_text().replace("#111", "#222"), encoding="utf-8")
        code, result = self.run_guard("layout")
        self.assertEqual(code, 0, result)

    def test_content_requires_revision_and_removes_invalidated_claim(self):
        self.after.write_text(self.html("新解释。", "J-001", "另一章原文。"), encoding="utf-8")
        self.assertEqual(self.run_guard("content", "personality")[0], 2)
        code, result = self.run_guard("content", "personality", self.revision, self.evidence)
        self.assertEqual(code, 1)
        self.assertIn("invalidated_claim_retained", {i["code"] for i in result["issues"]})
        self.after.write_text(self.html("新解释有依据。", "J-002", "另一章原文。"), encoding="utf-8")
        code, result = self.run_guard("content", "personality", self.revision, self.evidence)
        self.assertEqual(code, 0, result)

    def test_prepare_revision_scrubs_rejected_text_and_keeps_figure_hash(self):
        figure = '<figure class="chart-container" data-chart-id="chart-personality-01"><figcaption>稳定图</figcaption><svg><circle r="2"/></svg></figure>'
        out = self.root / "prepared"
        proc = subprocess.run([sys.executable, str(SCRIPT), "--before", str(self.before), "--prepare-revision",
            "--revision", str(self.revision), "--evidence", str(self.evidence), "--output", str(out), "--json"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        manifest = json.loads((out / "repair_manifest.json").read_text())
        self.assertNotIn("旧数字12分", "".join(p.read_text() for p in (out / "sections").glob("*.html")))
        figure_text = (out / "figures" / "chart-personality-01.html").read_text()
        self.assertEqual(manifest["retained_figures"][0]["sha256"], hashlib.sha256(figure_text.encode()).hexdigest())
        proc2 = subprocess.run([sys.executable, str(SCRIPT), "--before", str(self.before), "--prepare-revision",
            "--revision", str(self.revision), "--evidence", str(self.evidence), "--output", str(out), "--json"],
            capture_output=True, text=True)
        self.assertEqual(proc2.returncode, 2)

    # --- S8.5 reader-editor prose scope ---------------------------------------
    def reader_pair(self, after_body, before_body=None):
        base = ('<p data-claim-ids="J-001 J-002">不是说你冷淡。按 23 点的时辰前提，你先收缩再求证。</p>'
                '<aside data-disclosure-id="d1" data-limitation-id="L-ADJ">如果时辰前移，这一节改读为主动型。</aside>'
                '<p data-claim-ids="J-002">按 23 点的时辰前提，<q data-quote-id="Q1">原句</q>值为'
                '<span data-value-ref="a#/v" data-value="12" data-unit="分" data-precision="0">12分</span>。</p>')
        page = lambda body: self.html("x", "J-001", "另一章原文。").replace('<p data-claim-ids="J-001">x</p>', body)
        original = before_body or base
        self.before.write_text(page(original), encoding="utf-8")
        self.after.write_text(page(after_body(original)), encoding="utf-8")
        plan = self.root / "plan.json"
        self.write_json(plan, {"sections": [{"section_id": "personality", "limitation_ids": ["L-ADJ"]},
                                            {"section_id": "bazi", "limitation_ids": []}]})
        return plan

    def run_prose(self, plan=None):
        args = [sys.executable, str(SCRIPT), "--before", str(self.before), "--after", str(self.after),
                "--scope", "prose", "--targets", "personality,bazi", "--json"]
        if plan:
            args += ["--plan", str(plan)]
        proc = subprocess.run(args, capture_output=True, text=True)
        return proc.returncode, json.loads(proc.stdout)

    def test_reader_editor_may_reword_claim_paragraphs_and_drop_duplicate_clause(self):
        plan = self.reader_pair(lambda b: b.replace("不是说你冷淡。按 23 点的时辰前提，你先收缩再求证。", "你先收缩，再求证。")
                                .replace("如果时辰前移，这一节改读为主动型。", "要是时辰再早一些，这一节就改读为主动型。"))
        code, result = self.run_prose(plan)
        self.assertEqual(code, 0, result)

    def test_reader_editor_cannot_touch_numbers_claims_quotes_or_values(self):
        cases = {
            "prose_numbers_changed": lambda b: b.replace("23 点", "22 点"),
            "prose_binding_changed": lambda b: b.replace('data-claim-ids="J-001 J-002"', 'data-claim-ids="J-002"'),
        }
        for code_name, edit in cases.items():
            with self.subTest(code=code_name):
                plan = self.reader_pair(edit)
                code, result = self.run_prose(plan)
                self.assertEqual(code, 1)
                self.assertIn(code_name, {i["code"] for i in result["issues"]})
        plan = self.reader_pair(lambda b: b.replace(">原句</q>", ">改写原句</q>"))
        self.assertIn("prose_binding_changed", {i["code"] for i in self.run_prose(plan)[1]["issues"]})
        plan = self.reader_pair(lambda b: b.replace('data-precision="0">12分', 'data-precision="0">十二分'))
        self.assertEqual(self.run_prose(plan)[0], 1)

    def test_reader_editor_numbers_no_new_token_and_each_token_survives(self):
        plan = self.reader_pair(lambda b: b.replace("你先收缩再求证。", "你先收缩再求证，大约 3 次。"))
        self.assertIn("prose_numbers_changed", {i["code"] for i in self.run_prose(plan)[1]["issues"]})
        unique = ('<p data-claim-ids="J-001">你在 17 岁前后先收缩再求证。</p>'
                  '<aside data-disclosure-id="d1" data-limitation-id="L-ADJ">如果时辰前移，这一节改读。</aside>')
        plan = self.reader_pair(lambda b: b.replace("在 17 岁前后", ""), before_body=unique)
        self.assertIn("prose_numbers_changed", {i["code"] for i in self.run_prose(plan)[1]["issues"]})
        plan = self.reader_pair(lambda b: b.replace("在 17 岁前后先收缩再求证", "在 17 岁前后，你会先收缩，再求证"), before_body=unique)
        self.assertEqual(self.run_prose(plan)[0], 0)

    def test_reader_editor_cannot_hollow_out_a_limitation(self):
        plan = self.reader_pair(lambda b: b.replace("如果时辰前移，这一节改读为主动型。", ""))
        code, result = self.run_prose(plan)
        self.assertEqual(code, 1)
        self.assertIn("prose_limitation_emptied", {i["code"] for i in result["issues"]})

    def test_certainty_review_lists_sections_that_lost_voice_or_condition_markers(self):
        plan = self.reader_pair(lambda b: b.replace("如果时辰前移，这一节改读为主动型。", "时辰前移时，这一节改读为主动型。"))
        code, result = self.run_prose(plan)
        self.assertEqual(code, 0, result)  # hint only, never an issue
        row = result["certainty_review"][0]
        self.assertEqual((row["section"], row["before"]["如果"], row["after"]["如果"]), ("personality", 1, 0))
        plan = self.reader_pair(lambda b: b.replace("你先收缩再求证。", "你可能先收缩再求证。"))
        self.assertEqual(self.run_prose(plan)[1]["certainty_review"], [])

    def test_reader_editor_must_keep_each_planned_limitation_exactly_once(self):
        plan = self.reader_pair(lambda b: b.replace(' data-limitation-id="L-ADJ"', ""))
        codes = {i["code"] for i in self.run_prose(plan)[1]["issues"]}
        self.assertTrue({"prose_limitation_changed", "prose_limitation_count"} <= codes)
        self.assertIn("prose_limitation_changed", {i["code"] for i in self.run_prose()[1]["issues"]})
        plan = self.reader_pair(lambda b: b + '<p><span data-limitation-id="L-ADJ">按前面说的时辰前提</span></p>')
        self.assertIn("prose_limitation_count", {i["code"] for i in self.run_prose(plan)[1]["issues"]})
        plan = self.reader_pair(lambda b: b.replace('<aside data-disclosure-id="d1"', '<aside hidden data-disclosure-id="d1"'))
        codes = {i["code"] for i in self.run_prose(plan)[1]["issues"]}
        self.assertTrue({"prose_visibility_changed", "prose_limitation_changed"} <= codes)


if __name__ == "__main__":
    unittest.main()
