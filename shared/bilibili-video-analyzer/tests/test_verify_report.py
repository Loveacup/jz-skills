#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_verify_report.py — verify_report.py 的 stdlib-only 回归测试（无需 pytest）。

运行: python3 tests/test_verify_report.py   （在 skill 根目录）
断言:
  1. report_pass.md   full  → exit 0
  2. report_fail.md   full  → exit 1，且报告点名 G3/G4/G5 未通过
  3. report_fail.md   condensed → exit 1（洞察/模块仍不足）
  4. --json 输出包含 RESULT_JSON 块且 overall_pass 与退出码一致
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "scripts", "verify_report.py")
PASS_MD = os.path.join(HERE, "fixtures", "report_pass.md")
FAIL_MD = os.path.join(HERE, "fixtures", "report_fail.md")


def run(*args):
    """运行 verify_report.py，返回 (returncode, stdout)。"""
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def extract_json(out):
    s = out.find("RESULT_JSON_START")
    e = out.find("RESULT_JSON_END")
    assert s != -1 and e != -1, "缺少 RESULT_JSON 标记"
    return json.loads(out[s + len("RESULT_JSON_START"):e].strip())


def main():
    failures = []

    # 1. PASS fixture, full → exit 0
    rc, out = run(PASS_MD)
    if rc != 0:
        failures.append(f"[1] report_pass full 期望 exit 0，实际 {rc}\n{out}")

    # 2. FAIL fixture, full → exit 1, 点名 G3/G4/G5
    rc, out = run(FAIL_MD)
    if rc != 1:
        failures.append(f"[2] report_fail full 期望 exit 1，实际 {rc}")
    for g in ("G3", "G4", "G5"):
        # 该门那一行应判为 FAIL
        if f"❌ {g} " not in out:
            failures.append(f"[2] report_fail full 未将 {g} 判为 FAIL\n{out}")

    # 3. FAIL fixture, condensed → 仍 exit 1
    rc, out = run(FAIL_MD, "--mode", "condensed")
    if rc != 1:
        failures.append(f"[3] report_fail condensed 期望 exit 1，实际 {rc}")

    # 4. --json overall_pass 与退出码一致（pass=0, fail=1）
    rc, out = run(PASS_MD, "--json")
    data = extract_json(out)
    if not data.get("overall_pass") or rc != 0:
        failures.append(f"[4] report_pass --json overall_pass={data.get('overall_pass')} rc={rc}")
    rc, out = run(FAIL_MD, "--json")
    data = extract_json(out)
    if data.get("overall_pass") or rc != 1:
        failures.append(f"[4] report_fail --json overall_pass={data.get('overall_pass')} rc={rc}")

    if failures:
        print("❌ 测试失败:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("✅ test_verify_report: 全部通过 (4 组断言)")


if __name__ == "__main__":
    main()
