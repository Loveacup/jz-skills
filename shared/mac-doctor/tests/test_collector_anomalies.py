import importlib.util
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collector-daemon.py"
spec = importlib.util.spec_from_file_location("collector_anomaly_tests", SCRIPT)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def _baseline():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE snapshots(timestamp TEXT, cpu_percent REAL, swap_used_mb REAL, disk_free_gb REAL, disk_total_gb REAL, memory_pressure TEXT)")
    now = datetime.now()
    for index, swap in enumerate([900, 1000, 1100, 950, 1050, 980]):
        db.execute("INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?)", ((now - timedelta(minutes=index + 1)).isoformat(), 20 + index, swap, 50 + index, 100, "low"))
    db.commit()
    return db


def test_swap_anomaly_only_alerts_when_usage_rises():
    db = _baseline()
    config = {"anomaly": {"baseline_days": 7, "sigma": 1}}
    recovered = collector.check_anomalies(db, {"swap_used_mb": 10}, config)
    assert not any("Swap" in alert for alert in recovered)
    rising = collector.check_anomalies(db, {"swap_used_mb": 5000}, config)
    assert any("Swap" in alert for alert in rising)


def test_disk_free_anomaly_only_alerts_when_free_space_falls():
    db = _baseline()
    config = {"anomaly": {"baseline_days": 7, "sigma": 1}}
    recovery = collector.check_anomalies(db, {"disk_free_gb": 90, "disk_total_gb": 100}, config)
    assert not any("磁盘" in alert for alert in recovery)
    decline = collector.check_anomalies(db, {"disk_free_gb": 1, "disk_total_gb": 100}, config)
    assert any("磁盘" in alert for alert in decline)
