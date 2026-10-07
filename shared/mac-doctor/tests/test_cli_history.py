import json
import sqlite3
from datetime import datetime, timedelta, timezone

import mac_doctor


def test_history_summarizes_metrics_and_projects_disk_exhaustion(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "history.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE snapshots(timestamp TEXT, cpu_percent REAL, swap_used_mb REAL, swap_total_mb REAL, disk_free_gb REAL, disk_total_gb REAL, battery_health REAL, battery_cycles INTEGER, thermal_throttled INTEGER, load_avg_1min REAL, load_avg_5min REAL, load_avg_15min REAL)")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.executemany("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
            ((now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), 20, 100, 1000, 30, 100, 95, 10, 0, 1, 1, 1),
            (now.strftime("%Y-%m-%d %H:%M:%S"), 40, 200, 1000, 20, 100, 94, 11, 0, 2, 2, 2),
        ])
    monkeypatch.setattr(mac_doctor.paths, "history_db", lambda: db_path)
    assert mac_doctor.main(["history", "--hours", "24", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["metrics"]["cpu_percent"] == {"min": 20.0, "avg": 30.0, "max": 40.0}
    assert abs(output["disk_full_forecast_days"] - (1 / 6)) < 0.01
