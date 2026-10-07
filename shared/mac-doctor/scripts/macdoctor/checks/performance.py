from __future__ import annotations

import re
import time

from ..runner import check, Command
from . import command_text, number, result


@check("performance.cpu_load", "performance", "CPU load versus cores")
def cpu_load(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/bin/top", "-l", "1", "-n", "0"], timeout)
    cores_rc, cores_text = command_text(command, ["/usr/sbin/sysctl", "-n", "hw.ncpu"], timeout)
    match = re.search(r"Load Avg:\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)", text)
    idle = number(text, r"([\d.]+)%\s*idle")
    cores = number(cores_text, r"(\d+)", int) if cores_rc == 0 else None
    if rc or not match or not cores:
        return result("performance.cpu_load", "performance", "unknown", "CPU load versus cores", evidence=text, source="top, sysctl hw.ncpu", started=started)
    loads = [float(v) for v in match.groups()]
    state = "crit" if loads[0] > cores * 2 and idle is not None and idle < 10 else "warn" if loads[0] > cores or (idle is not None and idle < 20) else "pass"
    return result("performance.cpu_load", "performance", state, "CPU load versus cores", value={"load_avg": loads, "cores": cores, "idle_percent": idle}, evidence=text[:400], source="top -l 1; sysctl hw.ncpu", started=started, recommendation="Inspect sustained CPU consumers" if state != "pass" else None)


@check("performance.memory_pressure", "performance", "Memory pressure")
def memory_pressure(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/bin/memory_pressure"], timeout)
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", text, re.I)
    level = "critical" if re.search(r"critical", text, re.I) else "warn" if re.search(r"warn|pressure", text, re.I) else None
    if rc or (match is None and level is None):
        state, value = "unknown", None
    else:
        pct = int(match.group(1)) if match else None
        state = "crit" if level == "critical" else "warn" if level == "warn" or (pct is not None and pct < 10) else "pass"
        value = {"free_percent": pct, "level": level or "normal"}
    return result("performance.memory_pressure", "performance", state, "Memory pressure", value=value, unit="% free", evidence=text[:400], source="memory_pressure", started=started, recommendation="Review memory-intensive processes" if state in ("warn", "crit") else None)


@check("performance.swap_usage", "performance", "Swap usage")
def swap_usage(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/sbin/sysctl", "vm.swapusage"], timeout)
    used = re.search(r"used\s*=\s*([\d.]+)([KMGTP])", text, re.I)
    total = re.search(r"total\s*=\s*([\d.]+)([KMGTP])", text, re.I)
    units = {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024, "P": 1024 * 1024 * 1024}
    if rc or not used:
        value, state = None, "unknown"
    else:
        mb = float(used.group(1)) * units[used.group(2).upper()]
        total_mb = float(total.group(1)) * units[total.group(2).upper()] if total else None
        state = "crit" if mb > 5120 else "warn" if mb > 2048 else "pass"
        value = {"used_mb": round(mb, 1), "total_mb": round(total_mb, 1) if total_mb is not None else None}
    return result("performance.swap_usage", "performance", state, "Swap usage", value=value, unit="MB", evidence=text[:300], source="sysctl vm.swapusage", started=started, recommendation="Investigate sustained memory pressure" if state in ("warn", "crit") else None)


@check("performance.top_processes", "performance", "Top process aggregation")
def top_processes(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/bin/ps", "-eo", "%cpu,%mem,comm"], timeout)
    aggregate: dict[str, dict[str, float | int]] = {}
    if rc == 0:
        for line in text.splitlines()[1:]:
            fields = line.strip().split(None, 2)
            if len(fields) != 3:
                continue
            try:
                cpu, memory = float(fields[0]), float(fields[1])
            except ValueError:
                continue
            name = re.sub(r" (?:Helper(?: \([A-Za-z]+\))?|Renderer|Web Content(?: \(Prewarmed\))?|Worker|\(GPU\)|\(Plugin\))$", "", fields[2])
            item = aggregate.setdefault(name, {"cpu_percent": 0.0, "memory_percent": 0.0, "processes": 0})
            item["cpu_percent"] += cpu
            item["memory_percent"] += memory
            item["processes"] += 1
    if rc:
        state, top = "unknown", []
    else:
        top = [{"name": n, **v} for n, v in sorted(aggregate.items(), key=lambda pair: float(pair[1]["cpu_percent"]), reverse=True)[:10]]
        state = "warn" if any(float(row["cpu_percent"]) >= 20 for row in top) else "pass"
    return result("performance.top_processes", "performance", state, "Top process aggregation", value=top, unit="percent", evidence="; ".join(f"{p['name']} cpu={p['cpu_percent']:.1f}% mem={p['memory_percent']:.1f}% x{p['processes']}" for p in top), source="ps -eo %cpu,%mem,comm", started=started)
