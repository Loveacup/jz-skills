from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "judge_payload.py"
BUNDLE = json.loads((ROOT / "tests/fixtures/chart_bundle.example.json").read_text(encoding="utf-8"))
SENTINELS = {
    "bazi": "SENTINEL_BAZI_DATA",
    "ziwei": "SENTINEL_ZIWEI_DATA",
    "astrology": "SENTINEL_ASTRO_DATA",
}


def run_payload(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT,
                          text=True, capture_output=True, check=False)


def output(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def synthetic_intake() -> dict:
    personality = {
        "instrument": "synthetic-functions8", "version": "1", "test_date": None,
        "construct": "functions8",
        "scores": {"Ni": 24, "Ne": 15, "Si": 13, "Se": 8, "Ti": 16, "Te": 11, "Fi": 19, "Fe": 22},
        "scale_min": 0, "scale_max": 30, "self_reported_type": None,
        "observations": ["SENTINEL_OBSERVATION"], "counterexamples": ["SENTINEL_COUNTER"],
        "transcription": None,
    }
    partner_personality = dict(personality, construct="mbti_type", scores=None,
                               scale_min=None, scale_max=None, self_reported_type="INFP",
                               observations=["SENTINEL_PARTNER_OBS"])
    return {
        "subject": {"birth_date": "2000-01-15", "date_calendar": "gregorian", "lunar_date": None,
                    "calculation_sex": "m", "name": "SENTINEL_NAME"},
        "known_events": ["SENTINEL_EVENT"], "open_gaps": [], "questions_for_user": [],
        "personality_input": personality,
        "time_input": {"precision": "minute", "start": "2000-01-15T12:00:00", "end": None,
                       "branch_label": None, "timezone_name": None, "utc_offset_hours": 8,
                       "fold": None, "clock_basis": "civil"},
        "scope": {"mode": "full", "requested_topics": [], "accepted_limits": []},
        "timing_request": {"years": [2026], "months": [], "systems": ["bazi"]},
        "analysis_as_of": "2026-01-15",
        "privacy": {"external_chart_submission": False, "retain_case_memory": False},
        "synastry": {"enabled": True, "partner": {
            "subject": {"birth_date": "1999-03-01"}, "time_input": {},
            "personality_input": partner_personality, "known_events": ["SENTINEL_PARTNER_EVENT"]}},
        "age_years": 26, "minor_mode": False, "audience": "subject", "cost_policy": None,
    }


class JudgePayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        bundle = copy.deepcopy(BUNDLE)
        for key, marker in SENTINELS.items():
            bundle["dimensions"][key]["limitations"].append(marker)
        bundle["limitations"] = ["SENTINEL_TOPLEVEL_LIMIT"]
        bundle["time_context"]["input"]["subject"]["name"] = "SENTINEL_NAME"
        self.bundle_path = self.dir / "chart_bundle.json"
        self.bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        self.intake_path = self.dir / "intake_brief.json"
        self.intake_path.write_text(json.dumps(synthetic_intake(), ensure_ascii=False), encoding="utf-8")
        jung = subprocess.run(
            [sys.executable, str(ROOT / "scripts/jung_calc.py"), "--scores",
             json.dumps(synthetic_intake()["personality_input"]["scores"]), "--scale", "30"],
            text=True, capture_output=True, check=True)
        self.jung_path = self.dir / "jung.json"
        self.jung_path.write_text(jung.stdout, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, *args: str) -> tuple[dict, str]:
        result = run_payload(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = output(result)
        return report, report["payload"]

    def test_traditional_payload_contains_only_its_own_dimension(self):
        for dimension, key in (("bazi", "bazi"), ("ziwei", "ziwei"), ("astro", "astrology")):
            with self.subTest(dimension=dimension):
                _, text = self.payload("--dimension", dimension, "--subject", "primary",
                                       "--input", str(self.bundle_path), "--intake", str(self.intake_path))
                self.assertIn(SENTINELS[key], text)
                for other, marker in SENTINELS.items():
                    if other != key:
                        self.assertNotIn(marker, text)
                for leaked in ("SENTINEL_TOPLEVEL_LIMIT", "SENTINEL_NAME", "SENTINEL_EVENT",
                               "SENTINEL_OBSERVATION", "SENTINEL_PARTNER_OBS", "raw_scores"):
                    self.assertNotIn(leaked, text)
                self.assertIn(f"agents/judge-{dimension}.md", text)

    def test_method_keys_are_filtered_per_dimension(self):
        _, bazi = self.payload("--dimension", "bazi", "--subject", "primary", "--input", str(self.bundle_path))
        _, astro = self.payload("--dimension", "astro", "--subject", "primary", "--input", str(self.bundle_path))
        self.assertIn('"zi_hour_rule"', bazi)
        self.assertNotIn('"house_system"', bazi)
        self.assertIn('"house_system"', astro)
        self.assertNotIn('"zi_hour_rule"', astro)

    def test_first_read_contracts_are_inlined_from_judge_contract(self):
        report, text = self.payload("--dimension", "bazi", "--subject", "primary", "--input", str(self.bundle_path))
        self.assertEqual(report["included"][:6], [
            "agents/judge-bazi.md", "references/team-orchestration.md#§3,§7",
            "schemas/judge_verdicts.json", "references/bazi-framework.md", "references/classical-texts.md",
            "references/bazi-symbolism.md"])
        self.assertIn("## 3. 判官输入隔离与 chief 复核", text)
        self.assertIn("## 7. 主题与专业边界", text)
        self.assertNotIn("## 4. 证据、artifact 与复用", text)

    def test_hash_is_deterministic_and_matches_written_payload(self):
        args = ("--dimension", "ziwei", "--subject", "primary", "--input", str(self.bundle_path),
                "--intake", str(self.intake_path))
        first, text = self.payload(*args)
        second, again = self.payload(*args)
        self.assertEqual(text, again)
        self.assertEqual(first["input_payload_sha256"], second["input_payload_sha256"])
        self.assertEqual(first["input_payload_sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        out = self.dir / "payload.txt"
        written = run_payload(*args, "--output", str(out))
        self.assertEqual(written.returncode, 0, written.stderr)
        report = output(written)
        self.assertNotIn("payload", report)
        self.assertEqual(report["input_payload_sha256"], hashlib.sha256(out.read_bytes()).hexdigest())
        self.assertEqual(report["input_payload_sha256"], first["input_payload_sha256"])

    def test_jung_payload_uses_personality_slice_and_calc_result_only(self):
        report, text = self.payload("--dimension", "jung", "--subject", "primary",
                                    "--input", str(self.jung_path), "--intake", str(self.intake_path))
        self.assertIn('"raw_scores"', text)
        self.assertIn("#/personality_input", text)
        for leaked in ("SENTINEL_EVENT", "SENTINEL_OBSERVATION", "SENTINEL_NAME", "2000-01-15",
                       "SENTINEL_PARTNER_OBS", *SENTINELS.values()):
            self.assertNotIn(leaked, text)
        self.assertEqual(len(report["input_artifact_ids"]), 2)

    def test_partner_jung_reads_partner_slice(self):
        _, text = self.payload("--dimension", "jung", "--subject", "partner", "--intake", str(self.intake_path))
        self.assertIn('"INFP"', text)
        self.assertIn("#/synastry/partner/personality_input", text)
        for leaked in ("SENTINEL_PARTNER_EVENT", "SENTINEL_PARTNER_OBS", "SENTINEL_OBSERVATION", '"Ni": 24'):
            self.assertNotIn(leaked, text)

    def test_construct_mismatch_is_contract_failure(self):
        result = run_payload("--dimension", "jung", "--subject", "partner",
                             "--input", str(self.jung_path), "--intake", str(self.intake_path))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output(result)["error"]["code"], "construct_mismatch")

    def test_artifact_ids_come_from_case_evidence(self):
        digest = hashlib.sha256(self.bundle_path.read_bytes()).hexdigest()
        evidence = {"artifacts": [{"artifact_id": "A-chart-primary", "path": "chart_bundle.json",
                                   "sha256": digest, "depends_on_claim_ids": [],
                                   "depends_on_artifact_ids": [], "status": "current"}],
                    "sources": [], "claims": [], "corrections": [], "limitations": []}
        evidence_path = self.dir / "case_evidence.json"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        report, text = self.payload("--dimension", "bazi", "--subject", "primary",
                                    "--input", str(self.bundle_path), "--evidence", str(evidence_path))
        self.assertEqual(report["input_artifact_ids"], ["A-chart-primary"])
        self.assertEqual(report["artifact_id_source"], "case_evidence")
        self.assertIn("A-chart-primary#/dimensions/bazi", text)
        missing = run_payload("--dimension", "bazi", "--subject", "primary", "--input", str(self.bundle_path),
                              "--intake", str(self.intake_path), "--evidence", str(evidence_path))
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(output(missing)["error"]["code"], "artifact_not_registered")

    def test_unavailable_dimension_is_not_dispatched(self):
        bundle = copy.deepcopy(BUNDLE)
        bundle["dimensions"]["astrology"] = {"status": "not_applicable", "data": None,
                                             "candidates": [], "limitations": []}
        path = self.dir / "na.json"
        path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        result = run_payload("--dimension", "astro", "--subject", "primary", "--input", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output(result)["error"]["code"], "dimension_unavailable")

    def test_missing_or_invalid_files_exit_2_with_error_json(self):
        cases = [
            ("--dimension", "bazi", "--subject", "primary", "--input", str(self.dir / "missing.json")),
            ("--dimension", "jung", "--subject", "primary", "--intake", str(self.dir / "missing.json")),
            ("--dimension", "bazi", "--subject", "primary"),
            ("--dimension", "tarot", "--subject", "primary", "--input", str(self.bundle_path)),
        ]
        bad = self.dir / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        cases.append(("--dimension", "ziwei", "--subject", "primary", "--input", str(bad)))
        for args in cases:
            with self.subTest(args=args):
                result = run_payload(*args)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(output(result)["status"], "error")
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()


class SplitLayoutTests(unittest.TestCase):
    """The static contracts live in dm-judge-<dimension>; the split payload carries case data only."""

    def run_payload(self, *extra):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/judge_payload.py"), "--dimension", "bazi",
             "--subject", "primary", "--input", str(ROOT / "tests/fixtures/chart_bundle.example.json"),
             *extra], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_split_payload_has_case_data_but_no_contracts(self):
        inline, split = self.run_payload(), self.run_payload("--layout", "split")
        self.assertEqual((inline["layout"], inline["adapter"]), ("inline", "dm-judge"))
        self.assertEqual((split["layout"], split["adapter"]), ("split", "dm-judge-bazi"))
        self.assertEqual(split["static_sha256"], inline["static_sha256"])
        self.assertNotEqual(split["input_payload_sha256"], inline["input_payload_sha256"])
        self.assertLess(split["payload_bytes"], 40_000)
        self.assertIn("本维原始数据", split["payload"])
        self.assertIn('"四柱"', split["payload"])
        self.assertNotIn("角色合同", split["payload"].split("=====")[1])
        self.assertNotIn("独立解读路径与完成边界", split["payload"])
        self.assertIn("独立解读路径与完成边界", inline["payload"])

    def test_adapter_body_plus_split_payload_covers_the_inline_payload(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_judge_adapters import adapter_text
        from judge_payload import static_text
        static, included = static_text("bazi", ROOT)
        inline = self.run_payload()
        self.assertEqual(included, inline["included"])
        for runtime in ("cc", "omp"):
            text = adapter_text(runtime, "bazi", ROOT)
            self.assertTrue(text.endswith(static))
            self.assertIn("name: dm-judge-bazi", text)
            self.assertIn(inline["static_sha256"], text)
        self.assertIn("tools: ToolSearch", adapter_text("cc", "bazi", ROOT))
        self.assertIn("tools: []", adapter_text("omp", "bazi", ROOT))
        for section in static.split("\n\n===== 第")[1:3]:
            self.assertIn(section[:200], inline["payload"])

    def test_adapters_on_disk_match_current_contracts(self):
        import subprocess
        result = subprocess.run([sys.executable, str(ROOT / "scripts/build_judge_adapters.py"), "--check"],
                                capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0,
                         f"判官席位定义过期，运行 build_judge_adapters.py 重新生成: {report['stale']}")
        self.assertEqual(len(report["adapters"]), 8)
        self.assertNotIn("SENTINEL", "".join(
            (ROOT / row["path"]).read_text(encoding="utf-8") for row in report["adapters"]))
