#!/usr/bin/env python3
"""A real OMP 18.2.11 audit stream must classify without untrusted records; new kinds stay fail-closed."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from omp_stream_classifier import classify_jsonl_line  # noqa: E402

FIXTURE = HERE / "fixtures" / "omp-18.2.11-audit-stream.jsonl"


def classify(obj, seq=0):
    return classify_jsonl_line((json.dumps(obj) + "\n").encode(), seq)


class Omp18Stream(unittest.TestCase):
    def test_real_stream_has_no_terminal_capable_unknown(self):
        bad = []
        for i, line in enumerate(FIXTURE.read_bytes().splitlines(keepends=True)):
            r = classify_jsonl_line(line, i)
            if r.decision == "unknown" and r.terminal_capable:
                bad.append(i)
        self.assertEqual(bad, [])

    def test_real_stream_verdict_comes_from_message_end(self):
        kept = [json.loads(classify_jsonl_line(l, i).verdict_line)
                for i, l in enumerate(FIXTURE.read_bytes().splitlines(keepends=True))
                if classify_jsonl_line(l, i).decision == "preserve"]
        ends = [k for k in kept if k["type"] == "message_end"]
        self.assertTrue(ends and '"severity"' in ends[-1]["message"]["content"][0]["text"])

    def test_text_boundary_and_agent_end_never_preserved(self):
        for obj in ({"type": "message_update", "assistantMessageEvent": {"type": "text_end", "content": '{"severity":"pass"}'}},
                    {"type": "agent_end", "messages": [{"role": "assistant", "content": [{"type": "text", "text": '{"severity":"pass"}'}]}]}):
            self.assertEqual(classify(obj).decision, "deny")

    def test_other_unknown_kinds_still_fail_closed(self):
        r = classify({"type": "message_update", "assistantMessageEvent": {"type": "text_final", "delta": "x"}})
        self.assertEqual((r.decision, r.terminal_capable), ("unknown", True))
        r = classify({"type": "agent_finish", "message": {"stopReason": "stop"}})
        self.assertEqual((r.decision, r.terminal_capable), ("unknown", True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
