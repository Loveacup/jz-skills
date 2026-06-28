"""P4-S4: triage 经 subprocess 调 mac-doctor-triage.py 一次。"""
import mac_doctor


def test_triage_runs_l3_once(monkeypatch):
    calls = []
    monkeypatch.setattr(mac_doctor, "run_triage_once", lambda: calls.append("triage") or 0)

    assert mac_doctor.main(["triage"]) == 0
    assert calls == ["triage"]
