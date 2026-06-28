"""P4-S6: verify 跑 PRD §2.3 七项 checklist。

七项名称来源（三方关系链）:
  1) Codex 推断: collector/launchagent/cron_quick/cron_triage/cron_deep/cron_weekly/preferences
  2) Spec §2.4: 只声明 "verify 跑 PRD §2.3 七项"，未列出七项名称
  3) Hermes 决策: 以 PRD §2.3 实际七项为准（覆盖 Codex 推断），第 7 项 push 频次需 7 天观测 → PENDING
"""
from pathlib import Path

import mac_doctor


def test_verify_prints_seven_checklist_results(monkeypatch, capsys):
    monkeypatch.setattr(mac_doctor, "run_verify_checks", lambda: [
        ("L1 collector LaunchAgent 运行中", "PASS"),
        ("L2 watchdog 30min 巡检静默", "PASS"),
        ("L3 triage cron 触发 + 12h 兜底", "PASS"),
        ("preferences.json 存在并可读写", "PASS"),
        ("mac-doctor CLI 命令可用", "PASS"),
        ("cron-module.md 与 cronjob list 一致", "PASS"),
        ("7 天内 quick 推送频次降 ≥70%", "PENDING"),  # S7: 部署后观测
    ])

    assert mac_doctor.main(["verify"]) == 0          # 6 PASS + 1 PENDING，无 FAIL → exit 0
    out = capsys.readouterr().out
    assert out.count("PASS") == 6                     # PENDING 行不含 "PASS"
    assert "PENDING" in out
    assert "FAIL" not in out


def test_executable_under_300_lines():               # Codex 要求的行数 guard（红线 <300）
    path = Path(__file__).resolve().parent.parent / "scripts" / "mac-doctor"
    assert len(path.read_text().splitlines()) < 300
