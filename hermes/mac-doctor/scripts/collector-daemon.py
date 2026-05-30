#!/usr/bin/env python3
"""
macOS System Inspection Collector Daemon
Layer 1: Continuous data collection + smart alerts

Reads config from ~/.hermes/inspection/config.json
Stores snapshots in ~/.hermes/inspection/history.db (SQLite)
Sends macOS notifications on threshold breaches.

Intended to be run as a LaunchAgent every N minutes.
"""
import sqlite3
import json
import subprocess
import os
import sys
import time
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".hermes" / "inspection"
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_FILE = CONFIG_DIR / "history.db"
LOG_FILE = CONFIG_DIR / "collector.log"

DEFAULT_CONFIG = {
    "collection": {
        "interval_seconds": 600,
        "retention_days": 90,
        "quiet_hours": {"enabled": True, "start": 23, "end": 7}
    },
    "alerts": {
        "cpu_threshold": 80,
        "memory_pressure_threshold": "high",
        "swap_threshold_gb": 4,
        "disk_threshold_percent": 10,
        "battery_health_threshold": 80
    },
    "anomaly": {
        "enabled": True,
        "baseline_days": 7,
        "sigma": 2.0
    }
}


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG


def init_db():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_pressure TEXT,
            swap_used_mb REAL,
            swap_total_mb REAL,
            disk_free_gb REAL,
            disk_total_gb REAL,
            battery_health REAL,
            battery_cycles INTEGER,
            thermal_throttled INTEGER,
            load_avg_1min REAL,
            load_avg_5min REAL,
            load_avg_15min REAL,
            top_cpu_process TEXT,
            top_mem_process TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON snapshots(timestamp)")
    conn.commit()
    return conn


# ── Data Collection ───────────────────────────────────────────────────────
_C_ENV = {**os.environ, "LANG": "C", "LC_ALL": "C"}


def run_cmd(cmd, timeout=15):
    """Run a shell command, return stripped stdout or None.

    Forces LANG=C / LC_ALL=C so regex matches work on non-English Macs
    (system_profiler / defaults can otherwise emit translated keys).
    """
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, env=_C_ENV)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def collect_cpu():
    """Returns: (cpu_percent_used, load_1, load_5, load_15)"""
    out = run_cmd("top -l 1 -n 0 | head -4")
    if not out:
        return None, None, None, None
    # Parse Load Avg line
    load_match = re.search(r'Load Avg: ([\d.]+), ([\d.]+), ([\d.]+)', out)
    load1 = float(load_match.group(1)) if load_match else None
    load5 = float(load_match.group(2)) if load_match else None
    load15 = float(load_match.group(3)) if load_match else None
    # Parse CPU usage line
    cpu_match = re.search(r'(\d+\.?\d*)% idle', out)
    cpu_idle = float(cpu_match.group(1)) if cpu_match else 50
    cpu_pct = 100.0 - cpu_idle
    return cpu_pct, load1, load5, load15


def collect_memory():
    """Returns: (memory_pressure, swap_used_mb, swap_total_mb)"""
    mp = run_cmd("memory_pressure")
    pressure = "low"
    if mp:
        if "critical" in mp.lower():
            pressure = "critical"
        elif "warning" in mp.lower() or "high" in mp.lower():
            pressure = "high"

    swap = run_cmd("sysctl vm.swapusage")
    swap_used = swap_total = None
    if swap:
        m = re.search(r'used = ([\d.]+)([GMB])', swap)
        if m:
            val = float(m.group(1))
            unit = m.group(2)
            if unit == 'G':
                swap_used = val * 1024
            elif unit == 'B':
                swap_used = val / (1024 * 1024)
            else:
                swap_used = val

        m2 = re.search(r'total = ([\d.]+)([GMB])', swap)
        if m2:
            val2 = float(m2.group(1))
            unit2 = m2.group(2)
            if unit2 == 'G':
                swap_total = val2 * 1024
            elif unit2 == 'B':
                swap_total = val2 / (1024 * 1024)
            else:
                swap_total = val2

    return pressure, swap_used, swap_total


def collect_disk():
    """Returns: (free_gb, total_gb)"""
    out = run_cmd("diskutil info / | grep 'Container'")
    free = total = None
    if out:
        for line in out.split('\n'):
            if 'Free' in line:
                m = re.search(r'([\d.]+)\s*GB', line)
                if m:
                    free = float(m.group(1))
            elif 'Total' in line:
                m = re.search(r'([\d.]+)\s*GB', line)
                if m:
                    total = float(m.group(1))
    return free, total


_CHASSIS_CACHE = None


def is_desktop_mac():
    """Cache chassis detection. True for Mac mini/Studio/Pro (no battery)."""
    global _CHASSIS_CACHE
    if _CHASSIS_CACHE is not None:
        return _CHASSIS_CACHE
    model = run_cmd("system_profiler SPHardwareDataType 2>/dev/null | awk -F': ' '/Model Name/{print $2}'") or ""
    _CHASSIS_CACHE = any(kw in model for kw in ("mini", "Studio", "Pro")) and "MacBook" not in model
    return _CHASSIS_CACHE


def collect_battery():
    """Returns: (health_pct, cycles). None/None on desktop Macs (no battery)."""
    if is_desktop_mac():
        return None, None
    out = run_cmd("system_profiler SPPowerDataType 2>/dev/null")
    health = cycles = None
    if out:
        m = re.search(r'Maximum Capacity:\s*(\d+)%', out)
        if m:
            health = float(m.group(1))
        m2 = re.search(r'Cycle Count:\s*(\d+)', out)
        if m2:
            cycles = int(m2.group(1))
    if health == 0:  # MaxCapacity=0 sentinel
        health = None
    return health, cycles


def collect_thermal():
    """Returns: 1 if thermally limited, 0 otherwise.

    Uses `pmset -g therm` (snapshot). DO NOT use `pmset -g thermlog` — that's a
    streaming subscription that never exits and would hang the collector every cycle.

    Healthy output: "No thermal warning level has been recorded" → 0.
    Throttled: "CPU_Scheduler_Limit = N" (N<100), or "Active warning level: N" (N>0).
    """
    out = run_cmd("pmset -g therm 2>/dev/null", timeout=5)
    if not out:
        return 0
    m = re.search(r'CPU_Scheduler_Limit\s*=\s*(\d+)', out)
    if m and int(m.group(1)) < 100:
        return 1
    m2 = re.search(r'Active warning level\s*:\s*(\d+)', out)
    if m2 and int(m2.group(1)) > 0:
        return 1
    return 0


# Electron / Chromium 多进程后缀（与 macmonica STRIP_SUFFIXES 对齐）
_PROC_NORM_RE = re.compile(
    r"(?: Helper(?: \([A-Za-z]+\))?"
    r"| Renderer"
    r"| Web Content(?: \(Prewarmed\))?"
    r"| Worker"
    r"| \(GPU\)"
    r"| \(Plugin\))$"
)


def normalize_proc(name):
    """Strip Electron/Chromium suffixes; keep basename. 'Chrome Helper (GPU)' → 'Chrome'."""
    if not name:
        return ""
    name = os.path.basename(name)
    prev = None
    while name != prev:  # nested suffixes like " Helper (GPU)"
        prev = name
        name = _PROC_NORM_RE.sub("", name)
    return name


def collect_top_process():
    """Returns: (top_cpu_name, top_mem_name). Names are normalized (Chrome Helper → Chrome)."""
    out = run_cmd("ps -eo %cpu,%mem,comm -r 2>/dev/null | head -3")
    cpu_proc = mem_proc = ""
    if out:
        lines = out.strip().split('\n')
        if len(lines) >= 2 and lines[1].strip():
            cpu_proc = normalize_proc(lines[1].strip().split()[-1])
    mem_out = run_cmd("ps -eo %mem,comm -m 2>/dev/null | head -3")
    if mem_out:
        lines = mem_out.strip().split('\n')
        if len(lines) >= 2 and lines[1].strip():
            mem_proc = normalize_proc(lines[1].strip().split()[-1])
    return cpu_proc, mem_proc


def collect_snapshot():
    """Collect full snapshot, return dict."""
    cpu_pct, l1, l5, l15 = collect_cpu()
    pressure, swap_u, swap_t = collect_memory()
    disk_f, disk_t = collect_disk()
    bat_h, bat_c = collect_battery()
    thermal = collect_thermal()
    cpu_p, mem_p = collect_top_process()

    return {
        "cpu_percent": cpu_pct,
        "load_avg_1min": l1,
        "load_avg_5min": l5,
        "load_avg_15min": l15,
        "memory_pressure": pressure,
        "swap_used_mb": swap_u,
        "swap_total_mb": swap_t,
        "disk_free_gb": disk_f,
        "disk_total_gb": disk_t,
        "battery_health": bat_h,
        "battery_cycles": bat_c,
        "thermal_throttled": thermal,
        "top_cpu_process": cpu_p,
        "top_mem_process": mem_p,
    }


# ── Anomaly Detection ────────────────────────────────────────────────────
def check_anomalies(conn, snapshot, config):
    """Compare current snapshot against baseline."""
    alerts = []
    baseline_days = config.get("anomaly", {}).get("baseline_days", 7)
    sigma = config.get("anomaly", {}).get("sigma", 2.0)

    cutoff = (datetime.now() - timedelta(days=baseline_days)).isoformat()

    metrics = ["cpu_percent", "swap_used_mb", "disk_free_gb"]
    labels = {"cpu_percent": "CPU", "swap_used_mb": "Swap (MB)", "disk_free_gb": "磁盘 (GB)"}

    for metric in metrics:
        cur_val = snapshot.get(metric)
        if cur_val is None:
            continue
        row = conn.execute(
            f"SELECT AVG({metric}), AVG({metric}*{metric}) FROM snapshots WHERE timestamp >= ?",
            (cutoff,)
        ).fetchone()
        if not row or row[0] is None:
            continue
        mean = row[0]
        variance = max(0, row[1] - mean * mean)
        std = variance ** 0.5
        if std == 0:
            continue
        z = abs(cur_val - mean) / std
        if z > sigma:
            direction = "↑" if cur_val > mean else "↓"
            alerts.append(f"[异常] {labels[metric]}: {cur_val:.1f} (基线 {mean:.1f}±{std:.1f}, z={z:.1f}{direction})")

    return alerts


# ── Threshold Alerts ──────────────────────────────────────────────────────
def check_thresholds(snapshot, config):
    """Check snapshot against configured thresholds."""
    alerts = []
    ac = config.get("alerts", {})

    cpu = snapshot.get("cpu_percent")
    if cpu and cpu > ac.get("cpu_threshold", 80):
        alerts.append(f"🔴 CPU 持续高负载: {cpu:.0f}%")

    mp = snapshot.get("memory_pressure")
    mp_thresh = ac.get("memory_pressure_threshold", "high")
    pressure_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if mp and pressure_rank.get(mp, 0) >= pressure_rank.get(mp_thresh, 2):
        alerts.append(f"🔴 内存压力: {mp}")

    swap = snapshot.get("swap_used_mb")
    swap_thresh = ac.get("swap_threshold_gb", 4) * 1024
    if swap and swap > swap_thresh:
        alerts.append(f"🟡 Swap 使用: {swap/1024:.1f}GB")

    disk = snapshot.get("disk_free_gb")
    disk_total = snapshot.get("disk_total_gb")
    if disk and disk_total and disk_total > 0:
        pct = disk / disk_total * 100
        if pct < ac.get("disk_threshold_percent", 10):
            alerts.append(f"🔴 磁盘剩余: {disk:.0f}GB ({pct:.0f}%)")

    bat = snapshot.get("battery_health")
    if bat and bat < ac.get("battery_health_threshold", 80):
        alerts.append(f"🟡 电池健康: {bat:.0f}%")

    return alerts


# ── Notification ──────────────────────────────────────────────────────────
def is_quiet_hours(config):
    """Handles both midnight-wrap (23→7) and same-day (9→17) quiet windows."""
    qh = config.get("collection", {}).get("quiet_hours", {})
    if not qh.get("enabled", True):
        return False
    hour = datetime.now().hour
    start, end = qh["start"], qh["end"]
    if start == end:
        return False
    if start > end:  # wraps midnight, e.g. 23→7
        return hour >= start or hour < end
    return start <= hour < end  # same-day window, e.g. 9→17


def send_webhook(title, message, severity, config, is_anomaly=False):
    """POST alert to Slack/Discord/ntfy webhook. Quiet during quiet hours unless severity=red."""
    wh = config.get("webhooks", {})
    if not wh.get("enabled") or not wh.get("url"):
        return
    if is_anomaly and not wh.get("include_anomaly", False):
        return
    rank = {"yellow": 1, "red": 2}
    if rank.get(severity, 0) < rank.get(wh.get("min_severity", "red"), 2):
        return
    body = json.dumps({
        "title": title, "message": message, "severity": severity,
        "timestamp": datetime.now().isoformat()
    }).encode("utf-8")
    req = urllib.request.Request(wh["url"], data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5).close()
    except Exception as e:
        log(f"  webhook failed: {e}")


def notify(title, message, severity="yellow", config=None, is_anomaly=False):
    """Send macOS notification + optional webhook. severity = yellow|red."""
    cfg = config or DEFAULT_CONFIG
    critical = (severity == "red")
    if not is_quiet_hours(cfg) or critical:
        sound = "Glass" if critical else "default"
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "{sound}"'
        ], capture_output=True)
    send_webhook(title, message, severity, cfg, is_anomaly=is_anomaly)


# ── Database Maintenance ──────────────────────────────────────────────────
def cleanup_old(conn, retention_days):
    """Delete snapshots older than retention_days."""
    cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
    deleted = conn.execute("DELETE FROM snapshots WHERE timestamp < ?", (cutoff,)).rowcount
    if deleted:
        conn.execute("VACUUM")
    return deleted


# ── Forecasting ──────────────────────────────────────────────────────────
def _linreg_days(rows):
    """Linear regression over (julianday, y). Returns (slope_per_day, intercept_y, last_y)."""
    if len(rows) < 30:
        return None, None, None
    n = len(rows)
    sx = sum(r[0] for r in rows); sy = sum(r[1] for r in rows)
    sxy = sum(r[0] * r[1] for r in rows); sxx = sum(r[0] * r[0] for r in rows)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None, None, None
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept, rows[-1][1]


def forecast_disk_full(conn):
    """Predict days until disk hits 0 GB free. Returns None if not decreasing."""
    rows = conn.execute(
        "SELECT julianday(timestamp), disk_free_gb FROM snapshots "
        "WHERE disk_free_gb IS NOT NULL ORDER BY timestamp"
    ).fetchall()
    slope, _, current = _linreg_days(rows)
    if slope is None or slope >= 0 or current is None:
        return None
    return current / -slope  # days until disk_free_gb hits 0


def predict_battery(conn):
    """Simple linear regression: predict days until battery health hits 75%."""
    rows = conn.execute(
        "SELECT julianday(timestamp), battery_health FROM snapshots "
        "WHERE battery_health IS NOT NULL ORDER BY timestamp"
    ).fetchall()
    if len(rows) < 30:  # need at least 30 data points
        return None

    n = len(rows)
    sum_x = sum(r[0] for r in rows)
    sum_y = sum(r[1] for r in rows)
    sum_xy = sum(r[0] * r[1] for r in rows)
    sum_x2 = sum(r[0] * r[0] for r in rows)

    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
    intercept = (sum_y - slope * sum_x) / n

    if slope >= 0:  # battery not degrading (or improving)
        return None

    current = rows[-1][1]
    days_to_75 = (75 - current) / slope if slope < 0 else None
    return days_to_75


# ── Main ──────────────────────────────────────────────────────────────────
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, file=sys.stderr)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    config = load_config()
    json_mode = "--json" in sys.argv
    conn = init_db()

    if not json_mode:
        log("collector-daemon: starting snapshot collection")

    # Collect
    snap = collect_snapshot()
    if not json_mode:
        log(f"  CPU: {snap['cpu_percent']}%, Memory: {snap['memory_pressure']}, "
            f"Swap: {snap['swap_used_mb']}, Disk: {snap['disk_free_gb']}GB")

    # Insert
    conn.execute("""
        INSERT INTO snapshots (cpu_percent, memory_pressure, swap_used_mb, swap_total_mb,
            disk_free_gb, disk_total_gb, battery_health, battery_cycles,
            thermal_throttled, load_avg_1min, load_avg_5min, load_avg_15min,
            top_cpu_process, top_mem_process)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        snap["cpu_percent"], snap["memory_pressure"],
        snap["swap_used_mb"], snap["swap_total_mb"],
        snap["disk_free_gb"], snap["disk_total_gb"],
        snap["battery_health"], snap["battery_cycles"],
        snap["thermal_throttled"],
        snap["load_avg_1min"], snap["load_avg_5min"], snap["load_avg_15min"],
        snap["top_cpu_process"], snap["top_mem_process"]
    ))
    conn.commit()

    # Alerts
    all_alerts = []
    all_alerts.extend(check_thresholds(snap, config))
    if config.get("anomaly", {}).get("enabled", True):
        all_alerts.extend(check_anomalies(conn, snap, config))

    critical_keywords = ["CPU", "内存 pressure: critical", "磁盘剩余", "critical"]
    if json_mode:
        # JSON mode: dump and exit BEFORE side-effects (no notify, no weekly forecasts)
        out = {
            "schema_version": config.get("output", {}).get("json_schema_version", "2.0"),
            "timestamp": datetime.now().isoformat(),
            "snapshot": snap,
            "alerts": [
                {"text": a, "severity": "red" if any(k in a for k in critical_keywords) else "yellow",
                 "is_anomaly": a.startswith("[异常]")}
                for a in all_alerts
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    for alert in all_alerts:
        is_critical = any(kw in alert for kw in critical_keywords)
        is_anomaly = alert.startswith("[异常]")
        notify("⚠️ 系统巡检", alert,
               severity="red" if is_critical else "yellow",
               config=config, is_anomaly=is_anomaly)
        log(f"  ALERT: {alert}")

    # Weekly forecasts (run on Sundays)
    if datetime.now().weekday() == 6:  # Sunday
        days = predict_battery(conn)
        if days and 0 < days < 365:
            notify("🔋 电池预测", f"按当前退化率，预计 {days:.0f} 天后电池健康降到 75%",
                   severity="yellow", config=config)

        disk_days = forecast_disk_full(conn)
        if disk_days and 0 < disk_days < 365:
            sev = "red" if disk_days < 30 else "yellow"
            notify("💾 磁盘预测", f"按当前使用率，预计 {disk_days:.0f} 天后磁盘耗尽",
                   severity=sev, config=config)

    # Cleanup
    retention = config.get("collection", {}).get("retention_days", 90)
    deleted = cleanup_old(conn, retention)
    if deleted:
        log(f"  Cleanup: removed {deleted} old snapshots")

    log(f"collector-daemon: done ({len(all_alerts)} alerts)")


if __name__ == "__main__":
    main()
