from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PYTHON = sys.executable


def run_cli(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_stdout(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def json_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value} | set().union(*(json_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(json_keys(item) for item in value)) if value else set()
    return set()
class JungInputTests(unittest.TestCase):
    def test_subtypes16_retains_raw_pairs_and_reports_no_derived_functions(self):
        scores = {
            "TiA": 10, "TiH": 12, "TeA": 9, "TeH": 11,
            "FiA": 13, "FiH": 15, "FeA": 12, "FeH": 20,
            "NiO": 8, "NiB": 10, "NeO": 11, "NeB": 13,
            "SiO": 14, "SiB": 18, "SeO": 12, "SeB": 14,
        }
        result = run_cli("jung_calc.py", "--scores16", json.dumps(scores), "--scale", "20")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = parse_stdout(result)

        self.assertEqual(output["construct"], "subtypes16")
        self.assertEqual(output["raw_scores"], scores)
        self.assertEqual(output["scale"], 20)
        pairs = {pair["function"]: pair for pair in output["pairs"]}
        self.assertEqual((pairs["Fe"]["left"], pairs["Fe"]["right"], pairs["Fe"]["delta"]), (12, 20, 8))
        self.assertEqual((pairs["Si"]["left"], pairs["Si"]["right"], pairs["Si"]["delta"]), (14, 18, 4))
        self.assertIsNone(output["derived_functions"])
        self.assertIn("interpretation_limits", output)
        serialized = json.dumps(output, ensure_ascii=False).lower()
        for forbidden in ("confidence", "置信度", "能力薄弱", "均值雷达", "弱项", "低能力"):
            self.assertNotIn(forbidden, serialized)

    def test_subtypes16_requires_all_keys_and_rejects_duplicate_out_of_range_and_nan(self):
        full = {
            "TiA": 1, "TiH": 2, "TeA": 1, "TeH": 2,
            "FiA": 1, "FiH": 2, "FeA": 1, "FeH": 2,
            "NiO": 1, "NiB": 2, "NeO": 1, "NeB": 2,
            "SiO": 1, "SiB": 2, "SeO": 1, "SeB": 2,
        }
        missing = dict(full)
        missing.pop("SeB")
        self.assertEqual(run_cli("jung_calc.py", "--scores16", json.dumps(missing), "--scale", "20").returncode, 2)

        duplicate_json = json.dumps(full)[:-1] + ', "FeH": 3}'
        duplicate = run_cli("jung_calc.py", "--scores16", duplicate_json, "--scale", "20")
        self.assertEqual(duplicate.returncode, 2)
        self.assertEqual(parse_stdout(duplicate)["status"], "error")

        beyond = dict(full, FeH=21)
        self.assertEqual(run_cli("jung_calc.py", "--scores16", json.dumps(beyond), "--scale", "20").returncode, 2)
        nonfinite = dict(full, FeH=float("nan"))
        self.assertEqual(run_cli("jung_calc.py", "--scores16", json.dumps(nonfinite), "--scale", "20").returncode, 2)

    def test_functions8_scale_is_explicit_linear_and_ties_are_not_a_unique_type(self):
        scores_30 = {name: value for name, value in zip(
            ("Se", "Si", "Ne", "Ni", "Te", "Ti", "Fe", "Fi"),
            (30, 24, 18, 12, 6, 3, 0, 15),
        )}
        scores_10 = {key: value / 3 for key, value in scores_30.items()}
        result_30 = run_cli("jung_calc.py", "--scores", json.dumps(scores_30), "--scale", "30")
        result_10 = run_cli("jung_calc.py", "--scores", json.dumps(scores_10), "--scale", "10")
        self.assertEqual((result_30.returncode, result_10.returncode), (0, 0))
        out30, out10 = parse_stdout(result_30), parse_stdout(result_10)
        self.assertEqual(out30["raw_scores"], scores_30)
        self.assertEqual(out30["scale"], 30)
        self.assertEqual(out10["scale"], 10)
        self.assertEqual(out30["normalized_scores"], out10["normalized_scores"])

        tied = {name: 0 for name in scores_30}
        tied_result = run_cli("jung_calc.py", "--scores", json.dumps(tied), "--scale", "30")
        self.assertEqual(tied_result.returncode, 0, tied_result.stderr)
        tied_output = parse_stdout(tied_result)
        self.assertEqual(len(tied_output["ranked_tiers"]), 1)
        self.assertEqual(set(tied_output["ranked_tiers"][0]["functions"]), set(tied))
        self.assertNotIn("type", tied_output)
        self.assertNotIn("confidence", tied_output)
        self.assertNotIn("置信度", tied_output)

        implicit_scale = run_cli("jung_calc.py", "--scores", json.dumps(scores_10))
        self.assertEqual(implicit_scale.returncode, 2)
        self.assertEqual(parse_stdout(implicit_scale)["status"], "error")

    def test_functions8_rejects_invalid_keys_nonfinite_and_unknown_options(self):
        valid = {name: 1 for name in ("Se", "Si", "Ne", "Ni", "Te", "Ti", "Fe", "Fi")}
        missing = dict(valid)
        missing.pop("Fe")
        extra = dict(valid, NiB=1)
        beyond = dict(valid, Se=31)
        nan = dict(valid, Se=float("nan"))
        for scores in (missing, extra, beyond, nan):
            result = run_cli("jung_calc.py", "--scores", json.dumps(scores), "--scale", "30")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(parse_stdout(result)["status"], "error")
        duplicate_json = json.dumps(valid)[:-1] + ', "Se": 2}'
        self.assertEqual(run_cli("jung_calc.py", "--scores", duplicate_json, "--scale", "30").returncode, 2)
        unknown = run_cli("jung_calc.py", "--scores", json.dumps(valid), "--scale", "30", "--unknown-option")
        self.assertEqual(unknown.returncode, 2)
        self.assertEqual(parse_stdout(unknown)["status"], "error")

    def test_type_mode_is_explicit_theory_mapping(self):
        result = run_cli("jung_calc.py", "--type", "INTJ")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = parse_stdout(result)
        self.assertEqual(output["construct"], "mbti_type")
        self.assertEqual(output["self_reported_type"], "INTJ")
        self.assertEqual(output["theory_mapping"]["basis"], "Beebe theory_mapping")
        self.assertEqual(len(output["theory_mapping"]["stack"]), 8)
        self.assertNotIn("confidence", json.dumps(output).lower())


class SynastryInputTests(unittest.TestCase):
    @staticmethod
    def bundle(*, bazi=None, ziwei=None, astrology=None):
        dimensions = {}
        for key, data in (("bazi", bazi), ("ziwei", ziwei), ("astrology", astrology)):
            dimensions[key] = {"status": "ok", "data": data} if data is not None else {
                "status": "missing_input", "data": None
            }
        return {"schema_version": 2, "status": "partial", "dimensions": dimensions}

    def test_synastry_layers_are_unrated_and_missing_data_is_unavailable(self):
        a = self.bundle(bazi={"四柱": [{"柱": "日柱", "天干": "甲"}]})
        b = self.bundle()
        b["dimensions"]["bazi"] = {"status": "partial", "data": None}
        with tempfile.TemporaryDirectory() as directory:
            pa, pb = Path(directory) / "a.json", Path(directory) / "b.json"
            pa.write_text(json.dumps(a), encoding="utf-8")
            pb.write_text(json.dumps(b), encoding="utf-8")
            result = run_cli("synastry_calc.py", "--a", str(pa), "--b", str(pb))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = parse_stdout(result)
        for dimension in ("jung", "bazi", "ziwei", "astrology"):
            layer = output["dimensions"][dimension]
            self.assertEqual(set(layer), {"status", "input_refs", "observations", "limits"})
            if dimension in ("bazi", "ziwei", "astrology"):
                self.assertEqual(layer["status"], "unavailable")
        keys = {key.lower() for key in json_keys(output)}
        for forbidden in ("score", "rating", "评级", "吸引力", "挑战度", "一致度"):
            self.assertNotIn(forbidden, keys)
        self.assertNotIn("★", json.dumps(output, ensure_ascii=False))

    def test_synastry_aspect_profile_and_inclusive_orb_boundary(self):
        a = self.bundle(astrology={"十大行星+北交+凯龙+莉莉丝": {"太阳": {"黄经": 0.0}}})
        b = self.bundle(astrology={"十大行星+北交+凯龙+莉莉丝": {"月亮": {"黄经": 8.0}}})
        with tempfile.TemporaryDirectory() as directory:
            pa, pb = Path(directory) / "a.json", Path(directory) / "b.json"
            pa.write_text(json.dumps(a), encoding="utf-8")
            pb.write_text(json.dumps(b), encoding="utf-8")
            result = run_cli("synastry_calc.py", "--a", str(pa), "--b", str(pb))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = parse_stdout(result)
        self.assertEqual(output["aspect_profile"], "standard-v1")
        aspects = output["dimensions"]["astrology"]["observations"]
        self.assertTrue(any(item.get("aspect") == "conjunction" and item.get("exact_diff") == 8.0 for item in aspects))
        self.assertEqual(output["dimensions"]["astrology"]["status"], "available")

    def test_synastry_exposes_supplied_ziwei_palace_data_without_ranking(self):
        a = self.bundle(ziwei={"十二宫": [{"宫位": "夫妻宫", "主星": [{"名称": "紫微", "四化": ""}]}]})
        b = self.bundle(ziwei={"十二宫": [{"宫位": "夫妻宫", "主星": [{"名称": "天府", "四化": ""}]}]})
        with tempfile.TemporaryDirectory() as directory:
            pa, pb = Path(directory) / "a.json", Path(directory) / "b.json"
            pa.write_text(json.dumps(a), encoding="utf-8")
            pb.write_text(json.dumps(b), encoding="utf-8")
            result = run_cli("synastry_calc.py", "--a", str(pa), "--b", str(pb))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = parse_stdout(result)
        layer = output["dimensions"]["ziwei"]
        self.assertEqual(layer["status"], "available")
        self.assertEqual(layer["observations"][0]["palace"], "夫妻宫")
        self.assertEqual(layer["observations"][0]["a"]["main_stars"], ["紫微"])

    def test_synastry_rejects_invalid_jung_type(self):
        a, b = self.bundle(), self.bundle()
        jung = {"construct": "mbti_type", "self_reported_type": "WXYZ"}
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"{name}.json" for name in ("a", "b", "jung")]
            for path, data in zip(paths, (a, b, jung)):
                path.write_text(json.dumps(data), encoding="utf-8")
            result = run_cli("synastry_calc.py", "--a", str(paths[0]), "--b", str(paths[1]), "--a-jung", str(paths[2]))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(parse_stdout(result)["status"], "error")

    def test_synastry_rejects_invalid_theory_stack_even_when_peer_is_omitted(self):
        a, b = self.bundle(), self.bundle()
        mapped = parse_stdout(run_cli("jung_calc.py", "--type", "INTJ"))
        mapped["theory_mapping"]["stack"][0]["role"] = "not-a-Beebe-role"
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"{name}.json" for name in ("a", "b", "jung")]
            for path, data in zip(paths, (a, b, mapped)):
                path.write_text(json.dumps(data), encoding="utf-8")
            result = run_cli("synastry_calc.py", "--a", str(paths[0]), "--b", str(paths[1]), "--a-jung", str(paths[2]))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(parse_stdout(result)["status"], "error")


if __name__ == "__main__":
    unittest.main()
