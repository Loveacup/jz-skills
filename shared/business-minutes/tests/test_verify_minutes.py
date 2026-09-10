# -*- coding: utf-8 -*-
"""Tests for scripts/verify_minutes.py. Run: python3 -m unittest discover -s tests  (or pytest -q tests)."""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import verify_minutes as vm  # noqa: E402

FIX = HERE / "fixtures"


def run(md: Path, transcript: Path | None = None, mode="standard"):
    res = vm.evaluate(md, transcript, mode)
    return {r["gate"].split()[0]: r for r in res}


class PassFixture(unittest.TestCase):
    def test_all_gates_pass_with_transcript(self):
        g = run(FIX / "minutes_pass.md", FIX / "transcript_pass.txt")
        failed = [k for k, r in g.items() if not r["pass"]]
        self.assertEqual(failed, [], msg={k: g[k]["detail"] for k in failed})

    def test_all_gates_pass_without_transcript(self):
        g = run(FIX / "minutes_pass.md")
        self.assertTrue(all(r["pass"] for r in g.values()), {k: r["detail"] for k, r in g.items() if not r["pass"]})


class Mutations(unittest.TestCase):
    """Each mutation must trip exactly the gate it targets."""

    def _mutate(self, fn):
        src = io.open(FIX / "minutes_pass.md", encoding="utf-8").read()
        out = fn(src)
        self.assertNotEqual(src, out, "mutation did not change the fixture")
        tmp = Path(tempfile.mkdtemp()) / "m.md"
        io.open(tmp, "w", encoding="utf-8", newline="\n").write(out)
        return run(tmp, FIX / "transcript_pass.txt")

    def test_g1_missing_participants(self):
        g = self._mutate(lambda s: s.replace("participants: [周总, 林总, 何经理]\n", ""))
        self.assertFalse(g["G1"]["pass"])

    def test_g4_decision_without_timestamp(self):
        g = self._mutate(lambda s: s.replace("| D: 周总；C: 何经理 | [00:19:48] |", "| D: 周总；C: 何经理 | 见转写 |"))
        self.assertFalse(g["G4"]["pass"])
        self.assertIn("no-timestamp", g["G4"]["detail"])

    def test_g5_action_without_owner_node(self):
        g = self._mutate(lambda s: s.replace("| 26W37-A03 | 核实微信支付对公结算与开票要求 | 林总 | 2026-09-17 |", "| 26W37-A03 | 核实微信支付对公结算与开票要求 |  | 待定 |"))
        self.assertFalse(g["G5"]["pass"])

    def test_g6_too_few_quotes(self):
        g = self._mutate(lambda s: s.replace("> [!quote] 周总 [00:19:48]\n> 规则必须统一，哪家店有特殊情况来找我批。\n", ""))
        self.assertFalse(g["G6"]["pass"])

    def test_g7_missing_external_section(self):
        g = self._mutate(lambda s: s.replace("## 七、外部情报与决策依据", "## 七、其他"))
        self.assertFalse(g["G7"]["pass"])

    def test_g10_placeholder(self):
        g = self._mutate(lambda s: s.replace("旺季前上线优先于定制功能", "[待填]"))
        self.assertFalse(g["G10"]["pass"])

    def test_g10_transcript_dump(self):
        dump = "".join(io.open(FIX / "transcript_pass.txt", encoding="utf-8").read().split())[:260]
        g = self._mutate(lambda s: s.replace("## 三、背景与目标\n", "## 三、背景与目标\n\n" + dump + "\n"))
        self.assertFalse(g["G10"]["pass"])
        self.assertIn("dump_windows=", g["G10"]["detail"])


class LengthFloor(unittest.TestCase):
    def test_floor_scales_with_transcript(self):
        big = Path(tempfile.mkdtemp()) / "big.txt"
        with io.open(big, "w", encoding="utf-8") as fh:
            fh.write("[00:00:01] 甲：测试。\n" * 3000)  # ≈ 42k chars → floor 8000
        g = run(FIX / "minutes_pass.md", big)
        self.assertFalse(g["G9"]["pass"])
        self.assertIn("floor=8000", g["G9"]["detail"])


if __name__ == "__main__":
    unittest.main()
