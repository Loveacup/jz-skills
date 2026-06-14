"""写入闸违规检测（不变量①「不乱写」）。

扫 vault 的 git staged diff，抓「未经 gate 直接置 lifecycle_state: core」的页：
合法置 core 必须由 promote 写，并在同次提交留下 PIPELINE_LOG 的 promote 记录。
建议挂到 vault 仓库的 .git/hooks/pre-commit。退出码 1=有违规。
用法：python3 check_write_gate.py
"""
import os
import re
import sys
import subprocess

import common


def main():
    os.chdir(common.VAULT)
    diff = subprocess.run(["git", "diff", "--cached", "-U0"],
                          capture_output=True, text=True).stdout
    log = subprocess.run(["git", "diff", "--cached", "PIPELINE_LOG.md"],
                         capture_output=True, text=True).stdout
    cur, violations = None, []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
        if re.match(r"\+lifecycle_state:\s*core", line):
            name = os.path.basename(cur)[:-3] if cur else ""
            if "promote" not in log or name not in log:
                violations.append(cur)
    if violations:
        print("❌ 写入闸违规（未经 gate 直接置 core）:")
        for v in violations:
            print("  -", v)
        sys.exit(1)
    print("✅ 写入闸通过")


if __name__ == "__main__":
    main()
