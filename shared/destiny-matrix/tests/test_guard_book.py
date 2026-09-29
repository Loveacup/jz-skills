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


if __name__ == "__main__":
    unittest.main()
