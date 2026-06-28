"""P4-S3: status 三层表 + Prefs 摘要。"""
import mac_doctor


def test_status_three_layer_table(monkeypatch, capsys):
    monkeypatch.setattr(mac_doctor, "collect_status", lambda: {
        "layer1": {"pid": "123", "last_snapshot": "2026-06-28T10:00:00", "next_run": "active"},
        "layer2": {"last_run": "2026-06-28T10:30:00", "suppressed_sigs": 2, "pushed_today": 1},
        "layer3": {"last_triage": "2026-06-28T11:00:00", "pending_triggers": 0},
        "prefs": {"facts_count": 3, "interpretations_count": 4, "suppressions_count": 2, "size": 512},
    })

    assert mac_doctor.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "Layer 1" in out and "PID" in out and "Last snapshot" in out and "Next run" in out
    assert "Layer 2" in out and "Last run" in out and "Suppressed sigs" in out and "Pushed today" in out
    assert "Layer 3" in out and "Last triage" in out and "Pending triggers" in out
    assert "Prefs" in out and "facts count" in out and "interpretations count" in out
