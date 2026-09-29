from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chart_data.py"


def run_chart(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def output(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


class ChartDataTests(unittest.TestCase):
    def test_radar_keeps_only_supplied_dimensions_and_rejects_out_of_range_values(self):
        result = run_chart("radar", "--values", "Ti=0,Fe=5,Ni=10", "--max", "10")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = output(result)
        self.assertEqual([axis["label"] for axis in data["axes"]], ["Ti", "Fe", "Ni"])
        self.assertEqual(len(data["axes"]), 3)
        for invalid in ("Ti=-1,Fe=5,Ni=10", "Ti=0,Fe=11,Ni=10"):
            failed = run_chart("radar", "--values", invalid, "--max", "10")
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(output(failed)["status"], "error")

    def test_arc_rejects_negative_and_over_max(self):
        for value in ("-0.1", "101"):
            failed = run_chart("arc", "--value", value, "--max", "100")
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(output(failed)["status"], "error")
        valid = run_chart("arc", "--value", "50", "--max", "100")
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(output(valid)["fraction"], 0.5)

    def test_wheel_uses_actual_unequal_cusps_across_zero_from_nonzero_asc(self):
        cusps = "350,10,35,70,110,150,190,225,260,290,320,340"
        result = run_chart(
            "wheel", "--cusps", cusps, "--asc", "350",
            "--planets", "Sun=5,Moon=345",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = output(result)
        lines = data["cusp_lines"]
        self.assertEqual(len(lines), 12)
        self.assertEqual([line["longitude"] for line in lines], [350, 10, 35, 70, 110, 150, 190, 225, 260, 290, 320, 340])
        self.assertEqual(lines[0]["offset_deg"], 0)
        self.assertEqual(lines[1]["offset_deg"], 20)
        self.assertEqual(lines[2]["offset_deg"], 45)
        self.assertEqual(data["planets"][0]["offset_deg"], 15)
        self.assertNotEqual(lines[1]["offset_deg"] - lines[0]["offset_deg"], lines[2]["offset_deg"] - lines[1]["offset_deg"])

    def test_timeline_marks_now_outside_range_without_clamping(self):
        result = run_chart(
            "timeline", "--start", "0", "--end", "10", "--step", "5", "--now", "12",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output(result)["now"], {"value": 12.0, "x": None, "status": "outside_range"})

    def test_dumbbell_preserves_raw_values_delta_and_missing_endpoint_has_no_line(self):
        pairs = [
            {"function": "Fe", "left_key": "FeA", "right_key": "FeH", "left": 12, "right": 20},
            {"function": "Si", "left_key": "SiO", "right_key": "SiB", "left": 14, "right": 18},
            {"function": "Te", "left_key": "TeA", "right_key": "TeH", "left": 9, "right": None},
        ]
        result = run_chart("dumbbell", "--pairs", json.dumps(pairs), "--min", "0", "--max", "30")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = output(result)
        self.assertEqual(data["type"], "dumbbell")
        fe, si, te = data["pairs"]
        self.assertEqual((fe["left"], fe["right"], fe["delta"]), (12, 20, 8))
        self.assertAlmostEqual(fe["left_x"], 40 + 12 / 30 * 620, places=2)
        self.assertAlmostEqual(fe["right_x"], 40 + 20 / 30 * 620, places=2)
        self.assertEqual((si["left"], si["right"], si["delta"]), (14, 18, 4))
        self.assertEqual(te["status"], "missing_endpoint")
        self.assertEqual(te["missing"], ["right"])
        self.assertNotIn("line", te)
        self.assertNotIn("delta", te)

    def test_dumbbell_rejects_nonfinite_and_out_of_scale_data(self):
        for left in (-1, 31, math.nan):
            pairs = [{"function": "Ti", "left_key": "TiA", "right_key": "TiH", "left": left, "right": 12}]
            failed = run_chart("dumbbell", "--pairs", json.dumps(pairs), "--min", "0", "--max", "30")
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(output(failed)["status"], "error")


if __name__ == "__main__":
    unittest.main()
