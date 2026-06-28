"""P4-S1: install 幂等。"""
import mac_doctor


def test_install_idempotent(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(mac_doctor, "COLLECTOR", tmp_path / "collector-daemon.py")
    mac_doctor.COLLECTOR.write_text("# collector")
    monkeypatch.setattr(mac_doctor, "run_install_daemon", lambda: calls.append("daemon"))
    monkeypatch.setattr(mac_doctor, "register_cron_jobs", lambda: calls.append("cron"))
    monkeypatch.setattr(mac_doctor, "verify_install", lambda: True)

    assert mac_doctor.main(["install"]) == 0
    assert mac_doctor.main(["install"]) == 0
    assert capsys.readouterr().out.count("✓ Installed. Run `mac-doctor status` to verify.") == 2
