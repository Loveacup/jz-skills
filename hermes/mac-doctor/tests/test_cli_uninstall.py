"""P4-S2: uninstall 默认 dry-run，--force 才真删。

契约关系链:
  Codex 推断 red_test: main(["uninstall"]) 默认即 pause+unload
  → Hermes 验收契约红线: 默认 dry-run，--force 才真删（destructive 需确认）
  → 本测试以 Hermes 决策为准（同 S6 PRD §2.3 先例）。
"""
import mac_doctor


def test_uninstall_dry_run_default_and_force(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(mac_doctor, "pause_cron_jobs", lambda ids: calls.append(("pause", ids)))
    monkeypatch.setattr(mac_doctor, "unload_launchagent", lambda: calls.append(("unload", None)))

    # 默认 = dry-run：不触碰任何 cron / LaunchAgent
    assert mac_doctor.main(["uninstall"]) == 0
    assert calls == []
    assert "dry-run" in capsys.readouterr().out.lower()

    # --force = 真执行：pause 4 个 job（不删）后 unload LaunchAgent
    assert mac_doctor.main(["uninstall", "--force"]) == 0
    assert calls == [
        ("pause", ["mac-doctor-quick", "mac-doctor-triage", "mac-doctor-deep", "mac-doctor-weekly"]),
        ("unload", None),
    ]
