import json
import sqlite3
from datetime import datetime, timedelta, timezone

import mac_doctor


def test_status_reads_max_timestamp_from_history_db(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "history.db"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    newest = (now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE snapshots(timestamp TEXT)")
        db.executemany("INSERT INTO snapshots VALUES (?)", [
            ((now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),),
            (newest,),
        ])
    monkeypatch.setattr(mac_doctor.paths, "history_db", lambda: db_path)
    monkeypatch.setattr(mac_doctor.paths, "hermes_home", lambda: None)
    monkeypatch.setattr(mac_doctor, "_launchctl_state", lambda: {"state": "loaded", "last_exit": "0", "run_interval": "600 seconds"})
    assert mac_doctor.main(["status", "--json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["last_snapshot"]["timestamp"] == newest
    assert value["last_snapshot"]["health"] == "ok"
    assert value["hermes_adapter"]["state"] == "not installed"


def test_snapshot_health_marks_old_data_stale():
    now = datetime(2026, 10, 4, tzinfo=timezone.utc)
    assert mac_doctor._snapshot_health("2026-10-03T23:00:00+00:00", now)["health"] == "stale"
