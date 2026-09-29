from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import re
import unicodedata
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIX = ROOT / "tests" / "fixtures"
SCRIPT = ROOT / "scripts" / "export_pdf.py"
PYTHON = Path.home() / ".local/share/destiny-matrix/venv/bin/python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ExportPDFTests(unittest.TestCase):
    def run_export(self, source: Path, output: Path, verdict: Path) -> subprocess.CompletedProcess:
        return subprocess.run([str(PYTHON), str(SCRIPT), str(source), str(output), "--verdict", str(verdict), "--json"],
                              capture_output=True, text=True, check=False)

    def make_case(self, root: Path, source_text: str | None = None, *, decision: str = "awaiting_export",
                  correct_hash: bool = True) -> tuple[Path, Path, bytes]:
        raw = (FIX / "reading_fixture.html").read_bytes() if source_text is None else source_text.encode()
        html_path = root / "case.html"; html_path.write_bytes(raw)
        verdict = json.loads((FIX / "reading_fixture_verdict_pre.json").read_text())
        verdict["artifact_hashes"]["html"] = digest(raw) if correct_hash else "0" * 64
        verdict["decision"] = decision
        verdict_path = root / "verdict.json"; verdict_path.write_text(json.dumps(verdict), encoding="utf-8")
        return html_path, verdict_path, raw

    def test_fixture_reflows_at_320px_without_page_overflow(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 320, "height": 844})
                page.goto((FIX / "reading_fixture.html").resolve().as_uri(), wait_until="networkidle")
                widths = page.evaluate("""() => ({
                  scroll: document.documentElement.scrollWidth,
                  client: document.documentElement.clientWidth
                })""")
                self.assertLessEqual(widths["scroll"], widths["client"], widths)
            finally:
                browser.close()

    def test_fixture_contract_and_complete_render(self):
        from scripts.quality_contracts import check
        evidence = json.loads((FIX / "reading_fixture_evidence.json").read_text())
        plan = json.loads((FIX / "reading_fixture_plan.json").read_text())
        verdict = json.loads((FIX / "reading_fixture_verdict_pre.json").read_text())
        self.assertEqual(check("case_evidence", evidence, base_dir=str(FIX)), [])
        self.assertEqual(check("chart_plan", plan), [])
        self.assertEqual(check("final_verdict", verdict), [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, pre, original = self.make_case(root)
            output = root / "fixture.pdf"
            result = self.run_export(source, output, pre)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "rendered")
            self.assertEqual(source.read_bytes(), original)
            reader = PdfReader(str(output)); self.assertGreaterEqual(len(reader.pages), 3)
            extracted = unicodedata.normalize("NFKC", "".join(page.extract_text() or "" for page in reader.pages))
            for marker in ["FX-DISC-01", "FX-BODY-01", "FX-BODY-02", "FX-BODY-03", "FX-LONG-01-A",
                           "FX-LONG-01-F", "FX-APPENDIX-FIRST", "FX-APPENDIX-LAST", "FX-APPENDIX-2-LAST",
                           "FX-QUOTE-01", "欲識三元萬物宗", "FX-TBL-01", "FX-TBL-60", "FX-VALUE-01"]:
                self.assertIn(marker, extracted)
            for row in range(1, 61):
                suffix = f"{row:02d}"
                self.assertIn(f"FX-TBL-{suffix}", extracted)
                self.assertIn(f"项目-{suffix}", extracted)
                self.assertIn(f"值-{suffix}", extracted)
            self.assertIn("数据与来源", extracted)
            self.assertIn("方法说明", extracted)
            self.assertIn("<PDF>", extracted)
            text_pages = [page.extract_text() or "" for page in reader.pages]
            long_callout_pages = {i for i, text in enumerate(text_pages)
                                  if "FX-LONG-01-A" in text or "FX-LONG-13" in text}
            self.assertGreaterEqual(len(long_callout_pages), 2)
            vector_pages = [page for page, text in zip(reader.pages, text_pages) if "FX-" not in text]
            self.assertTrue(any(b" m" in page.get_contents().get_data() for page in vector_pages))
            self.assertLess(len(reader.pages), 20)
            self.assertEqual(report["content_check"]["missing_blocks"], [])

    def test_preflight_failures_never_create_pdf(self):
        variants = [
            ("<details><summary>未分类</summary><p>隐藏正文</p></details>", "awaiting_export", True),
            ('<p style="display:none">隐藏正文</p>', "awaiting_export", True),
            (None, "awaiting_export", False),
            (None, "pass", True),
        ]
        for suffix, (addition, decision, correct_hash) in enumerate(variants):
            with self.subTest(case=suffix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source_text = None
                if addition is not None:
                    original = (FIX / "reading_fixture.html").read_text()
                    source_text = original.replace("</main>", addition + "</main>")
                source, pre, _ = self.make_case(root, source_text, decision=decision, correct_hash=correct_hash)
                output = root / "must-not-exist.pdf"
                result = self.run_export(source, output, pre)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["status"], "failed")
                self.assertFalse(output.exists())

    def test_font_and_image_load_failures_block_export(self):
        cases = [
            ('<style>@font-face{font-family:BrokenFixture;src:url("missing-font.woff2")}'
             '#book{font-family:BrokenFixture}</style>', "font load failed"),
            ('<img alt="missing fixture" src="missing-image.png">', "image decode failed"),
        ]
        base = (FIX / "reading_fixture.html").read_text()
        for addition, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if addition.startswith("<style>"):
                    text = base.replace("</head>", addition + "</head>")
                else:
                    text = base.replace("</main>", addition + "</main>")
                source, pre, _ = self.make_case(root, text)
                output = root / "resource-failure.pdf"
                result = self.run_export(source, output, pre)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertTrue(any(diagnostic in item for item in report["diagnostics"]), result.stdout)
                self.assertFalse(output.exists())

    def test_print_font_thresholds_and_transformed_svg(self):
        base = (FIX / "reading_fixture.html").read_text()
        additions = [
            '<p style="font-size:8pt">FX-FONT-LOW</p>',
            '<svg style="transform:scale(.7)" xmlns="http://www.w3.org/2000/svg"><text style="font-size:10px">FX-SVG-LOW</text></svg>',
            '<p style="font-size:16px">FX-FONT-AT-THRESHOLD</p>',
        ]
        for fragment, marker, should_violate in ((additions[0], "FX-FONT-LOW", True),
                                                 (additions[1], "FX-SVG-LOW", True),
                                                 (additions[2], "FX-FONT-AT-THRESHOLD", False)):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); text = base.replace("</main>", fragment + "</main>")
                source, pre, _ = self.make_case(root, text); output = root / "font.pdf"
                result = self.run_export(source, output, pre)
                report = json.loads(result.stdout)
                if should_violate:
                    self.assertEqual(result.returncode, 1, result.stdout)
                    compact = lambda value: re.sub(r"[^A-Za-z0-9]", "", value).upper()
                    self.assertTrue(any(compact(marker) in compact(v["text"])
                                        for v in report["font_size_check"]["violations"]), result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertFalse(any(marker in v["text"] for v in report["font_size_check"]["violations"]))


if __name__ == "__main__":
    unittest.main()
