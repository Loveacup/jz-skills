import sqlite3

import mac_doctor_triage as triage

# 真实 snapshots 表 schema（Hermes 修正：非 Codex 假设的 inspections 表）
_SCHEMA = (
    "CREATE TABLE snapshots ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,"
    "cpu_percent REAL, memory_pressure TEXT,"
    "swap_used_mb REAL, swap_total_mb REAL,"
    "disk_free_gb REAL, disk_total_gb REAL,"
    "battery_health REAL, battery_cycles INTEGER,"
    "thermal_throttled INTEGER,"
    "load_avg_1min REAL, load_avg_5min REAL, load_avg_15min REAL,"
    "top_cpu_process TEXT, top_mem_process TEXT)"
)


def _seed(db):
    con = sqlite3.connect(db)
    con.execute(_SCHEMA)
    rows = [
        # 窗口内：abnormal(cpu>70) + critical(mem) + low_disk(<15)
        ("2026-06-28 11:00:00", 85.0, "critical", 10.0, "hog"),
        # 窗口内：全正常 → normal
        ("2026-06-28 11:30:00", 20.0, "low", 50.0, "hog"),
        # 窗口外（>24h 前）：不计入
        ("2026-06-25 00:00:00", 99.0, "critical", 5.0, "old"),
    ]
    for ts, cpu, mem, disk, proc in rows:
        con.execute(
            "INSERT INTO snapshots(timestamp,cpu_percent,memory_pressure,"
            "disk_free_gb,top_cpu_process) VALUES (?,?,?,?,?)",
            (ts, cpu, mem, disk, proc),
        )
    con.commit()
    con.close()


def test_read_trend_uses_real_schema_and_last_24h(tmp_path):
    db = tmp_path / "history.db"
    _seed(str(db))

    trend = triage.read_trend(db, now="2026-06-28 12:00:00")

    assert trend["window_hours"] == 24
    assert trend["total"] == 2  # 仅窗口内 2 行
    assert trend["by_status"] == {
        "abnormal": 1, "critical": 1, "low_disk": 1, "normal": 1,
    }
    assert trend["top_cpu_processes"] == [{"process": "hog", "count": 2}]
    assert trend["latest_snapshot"]["timestamp"] == "2026-06-28 11:30:00"
    assert "columns" in trend
    assert "timestamp" in trend["columns"]
    assert "cpu_percent" in trend["columns"]


def test_read_trend_missing_db_returns_empty_shape(tmp_path):
    trend = triage.read_trend(tmp_path / "nope.db")
    assert trend["total"] == 0
    assert trend["by_status"] == {}
    assert trend["window_hours"] == 24
