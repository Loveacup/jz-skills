#!/usr/bin/env python3
"""mac-doctor unified watchdog — 每 30 分钟巡检，只在异常时输出。

六检：CPU+内存+磁盘+Swap / Kanban 完整性 / 僵尸进程 / MCP 孤儿清理
使用 collector-daemon.py 获取系统快照，附加进程级检查。
空 stdout = 静默 = 不推送。
"""

import json, os, re, signal, subprocess, sys
from datetime import datetime
from pathlib import Path

COLLECTOR = Path("/Users/alexcai/.hermes/skills/apple/mac-doctor/scripts/collector-daemon.py")
KANBAN_DB = Path("/Users/alexcai/.hermes/kanban.db")
ZOMBIE_MAX = 4
MCP_KEYWORDS = ['mcp', 'searxng', 'tavily', 'exa', 'brave',
                'codegraph', 'context7', 'playwright', 'chroma']


def check_kanban():
    """Kanban 数据库完整性检查。"""
    if not KANBAN_DB.exists():
        return ("warn", f"{KANBAN_DB.name} 文件不存在")
    try:
        r = subprocess.run(
            ["sqlite3", str(KANBAN_DB), "PRAGMA integrity_check"],
            capture_output=True, text=True, timeout=10
        )
        result = r.stdout.strip()
        if result != "ok":
            return ("fail", f"{KANBAN_DB.name}: {result[:200]}")
        return ("ok", None)
    except Exception as e:
        return ("error", f"Kanban 检查失败: {e}")


def check_zombies():
    """僵尸进程检测。"""
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
        zombies = []
        for line in r.stdout.splitlines():
            parts = line.split(None, 10)
            if len(parts) >= 8 and parts[7] == "Z":
                zombies.append({"pid": parts[1], "cmd": parts[10] if len(parts) > 10 else "?"})
        count = len(zombies)
        return ("ok", None) if count <= ZOMBIE_MAX else ("warn", zombies)
    except Exception as e:
        return ("error", str(e))


def check_mcp_cleanup():
    """MCP 孤儿进程检测与清理。"""
    try:
        # 找到所有 MCP 进程
        r = subprocess.run(["pgrep", "-f",
            "(mcp|codegraph|searxng|tavily-mcp|exa-mcp|brave-search|context7-mcp|playwright-mcp|chroma-mcp)"],
            capture_output=True, text=True, timeout=10)
        mcp_pids = set(r.stdout.strip().split())
        if not mcp_pids:
            return ("ok", None)

        # 找到合法锚点进程（gateway + tmux CC）
        # macOS pgrep 在某些 bootstrap namespace 下有盲区（如 cron-worker）
        # 改用 ps + grep 确保全覆盖
        r = subprocess.run(
            ["sh", "-c", "ps -eo pid,args | grep 'gateway run' | awk '{print $1}'"],
            capture_output=True, text=True, timeout=10)
        anchor_pids = set(r.stdout.strip().split())
        # 也找 tmux（CC 通过 tmux 启动 MCP）
        r = subprocess.run(["pgrep", "-x", "tmux"], capture_output=True, text=True, timeout=5)
        anchor_pids |= set(r.stdout.strip().split())
        if not anchor_pids:
            orphans = list(mcp_pids)
        else:
            valid = set(anchor_pids)
            queue = list(anchor_pids)
            while queue:
                parent = queue.pop()
                r = subprocess.run(["pgrep", "-P", parent],
                    capture_output=True, text=True, timeout=5)
                for child in r.stdout.strip().split():
                    if child and child not in valid:
                        valid.add(child)
                        queue.append(child)
            orphans = [p for p in mcp_pids if p not in valid]

        if not orphans:
            return ("ok", None)

        # 过滤确认是 MCP 进程
        real_orphans = []
        for pid in orphans:
            try:
                r = subprocess.run(["ps", "-p", pid, "-o", "comm="],
                    capture_output=True, text=True, timeout=3)
                cmd = r.stdout.strip().lower()
                if any(kw in cmd for kw in MCP_KEYWORDS):
                    real_orphans.append(pid)
            except:
                pass

        if not real_orphans:
            return ("ok", None)

        # SIGTERM
        killed, failed = [], []
        for pid in real_orphans:
            try:
                os.kill(int(pid), signal.SIGTERM)
                killed.append(pid)
            except Exception:
                failed.append(pid)

        if not killed:
            return ("ok", None)
        msg = f"清理了 {len(killed)} 个孤儿 MCP 进程"
        if failed:
            msg += f"（{len(failed)} 个清理失败）"
        return ("cleaned", msg)

    except Exception as e:
        return ("error", str(e))


STATE_FILE = Path("/Users/alexcai/.hermes/profiles/cron-worker/state/mac-doctor-watchdog-state.json")
COOLDOWN_HOURS = 3
DISK_CHANGE_THRESHOLD_GB = 1.0  # 磁盘变化超过此值才重新报告


def load_state():
    """加载上次报告状态。"""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {}


def save_state(state):
    """保存当前报告状态。"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))
    except Exception:
        pass


def is_duplicate_disk_alert(diagnosis, disk_free_gb, prev_state):
    """判断磁盘告警是否与上次重复，应跳过。

    条件：
    - diagnosis 与上次相同
    - 磁盘空闲值变化小于 DISK_CHANGE_THRESHOLD_GB
    - 距上次报告不到 COOLDOWN_HOURS 小时
    """
    if not prev_state:
        return False
    prev_diag = prev_state.get("diagnosis", "")
    # 比较诊断类型而非精确字符串 — diagnosis 包含动态磁盘数值，
    # "Disk low — 17.7GB free (7%)" vs "Disk low — 17.6GB free (7%)" 应视为同类告警
    if "Disk low" not in diagnosis or "Disk low" not in prev_diag:
        return False

    prev_disk = prev_state.get("disk_free_gb")
    if prev_disk is None or disk_free_gb is None:
        return False
    if abs(disk_free_gb - prev_disk) >= DISK_CHANGE_THRESHOLD_GB:
        return False  # 磁盘变化足够大，需要报告

    try:
        last_ts = datetime.fromisoformat(prev_state.get("last_report_ts", ""))
        elapsed = (datetime.now() - last_ts).total_seconds() / 3600
        if elapsed >= COOLDOWN_HOURS:
            return False  # 冷却时间已过
    except (ValueError, TypeError):
        return False
    return True


def main():
    checks = {}
    issues = []

    # 1. Collector 快照
    snap = {}
    alerts = []
    diagnosis = ""
    try:
        r = subprocess.run(
            ["python3", str(COLLECTOR), "--json"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            snap = data.get("snapshot", {})
            alerts = data.get("alerts", [])
            diagnosis = data.get("diagnosis", "")
        else:
            issues.append(("collector", f"collector-daemon 失败 (exit {r.returncode})"))
    except Exception as e:
        issues.append(("collector", f"collector 异常: {e}"))

    # Filter threshold alerts (exclude pure anomalies)
    threshold_alerts = [a for a in alerts if not a.get("is_anomaly", False)]

    # 2. Kanban
    status, data = check_kanban()
    checks["kanban"] = status
    if status != "ok":
        issues.append(("kanban", data))

    # 3. Zombie
    status, data = check_zombies()
    checks["zombie"] = status
    if status != "ok":
        issues.append(("zombie", data))

    # 4. MCP
    status, data = check_mcp_cleanup()
    checks["mcp"] = status
    if status != "ok":
        issues.append(("mcp", data))

    # 判断是否静默
    collector_ok = not threshold_alerts and diagnosis == "All clear" and not any(
        i[0] == "collector" for i in issues
    )
    other_ok = all(i[0] != "kanban" and i[0] != "zombie" for i in issues)
    mcp_cleaned_only = len(issues) == 1 and issues[0][0] == "mcp"

    if collector_ok and other_ok and not issues:
        sys.exit(0)

    # 去重：纯磁盘告警在冷却期内不重复推送
    only_disk_issue = (
        not any(i[0] != "collector" for i in issues)
        and diagnosis.startswith("Disk low")
    )
    if only_disk_issue:
        prev = load_state()
        disk_free = snap.get("disk_free_gb")
        if is_duplicate_disk_alert(diagnosis, disk_free, prev):
            sys.exit(0)  # 静默：与上次相同的磁盘告警

    # 有异常 → 输出
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"🩺 mac-doctor 统一巡检 | {ts}")
    print(f"状态: kanban={checks['kanban']}  zombie={checks['zombie']}  mcp={checks['mcp']}")
    print()

    # Collector snapshot
    cpu = snap.get('cpu_percent')
    mem = snap.get('memory_pressure', '?')
    swap_mb = snap.get('swap_used_mb')
    disk_gb = snap.get('disk_free_gb')
    print(f"CPU: {cpu if cpu is not None else '?'}%  |  Mem: {mem}  |  "
          f"Swap: {f'{swap_mb:.0f}MB' if swap_mb is not None else '?'}  |  "
          f"Disk: {f'{disk_gb:.1f}GB' if disk_gb is not None else '?'}")
    if diagnosis and diagnosis != "All clear":
        print(f"Root cause: {diagnosis}")
    if threshold_alerts:
        for a in threshold_alerts:
            print(f"  {a.get('text', a)}")
    print()

    # Other issues
    for check_name, data in issues:
        if check_name == "collector":
            print(f"⚠️ {data}")
        elif check_name == "kanban":
            print(f"📋 Kanban 异常: {data}")
        elif check_name == "zombie":
            zs = data if isinstance(data, list) else [data]
            print(f"👻 僵尸进程 ({len(zs)} 个):")
            for z in zs[:10]:
                if isinstance(z, dict):
                    print(f"  PID {z['pid']}: {z['cmd'][:60]}")
                else:
                    print(f"  {z}")
        elif check_name == "mcp":
            print(f"🧹 MCP: {data}")
        print()

    # 保存状态供下次去重
    save_state({
        "last_report_ts": datetime.now().isoformat(),
        "diagnosis": diagnosis,
        "disk_free_gb": snap.get("disk_free_gb"),
    })


if __name__ == "__main__":
    main()
