from __future__ import annotations

import re
import time

from ..runner import check, Command
from . import command_text, result

_DESKTOP = re.compile(r"Mac\s+(?:mini|Studio|Pro)\b", re.I)


def _model(command: Command, timeout: float) -> tuple[int, str]:
    return command_text(command, ["/usr/sbin/system_profiler", "SPHardwareDataType"], timeout)


@check("hardware.battery", "hardware", "Battery condition and cycles")
def battery(command: Command, timeout: float):
    started = time.monotonic()
    model_rc, model_text = _model(command, timeout)
    model_match = re.search(r"Model Name:\s*(.+)", model_text)
    model = model_match.group(1).strip() if model_match else ""
    if model_rc:
        return result("hardware.battery", "hardware", "unknown", "Battery condition and cycles", evidence="Could not identify Mac model", source="system_profiler SPHardwareDataType", started=started)
    if _DESKTOP.search(model):
        return result("hardware.battery", "hardware", "skip", "Battery condition and cycles", value={"model": model}, evidence=f"Desktop model ({model}) has no battery; battery checks skipped", source="system_profiler SPHardwareDataType", started=started)
    iorc, iotext = command_text(command, ["/usr/sbin/ioreg", "-rc", "AppleSmartBattery"], timeout)
    sp_rc, sptext = command_text(command, ["/usr/sbin/system_profiler", "SPPowerDataType"], timeout)
    def prop(key: str):
        m = re.search(r'"' + re.escape(key) + r'"\s*=\s*(\d+)', iotext)
        return int(m.group(1)) if m else None
    cycles, maximum, design = prop("CycleCount"), prop("MaxCapacity"), prop("DesignCapacity")
    condition_match = re.search(r"Condition:\s*(.+)", sptext, re.I)
    if maximum is not None and design:
        health = round(maximum / design * 100, 1)
    else:
        health = None
    condition = condition_match.group(1).strip() if condition_match else None
    if iorc and sp_rc:
        state = "unknown"
    elif health is not None:
        state = "crit" if health < 70 else "warn" if health < 80 or (cycles is not None and cycles > 1000) else "pass"
    elif condition:
        state = "warn" if condition.lower() not in ("normal", "good") else "pass"
    else:
        state = "unknown"
    return result("hardware.battery", "hardware", state, "Battery condition and cycles", value={"model": model, "cycles": cycles, "health_percent": health, "condition": condition}, unit="%", evidence=f"{condition or ''}; cycles={cycles}; capacity={maximum}/{design}", source="ioreg AppleSmartBattery; system_profiler SPPowerDataType", started=started)


@check("hardware.thermal", "hardware", "Thermal pressure")
def thermal(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/bin/pmset", "-g", "therm"], timeout)
    limit = re.search(r"CPU_Scheduler_Limit\s*=\s*(\d+)", text)
    val = int(limit.group(1)) if limit else None
    if rc:
        state = "unknown"
    elif val is not None:
        state = "warn" if val < 100 else "pass"
    elif re.search(r"No thermal warning", text, re.I):
        state = "pass"
    else:
        state = "unknown"
    return result("hardware.thermal", "hardware", state, "Thermal pressure", value=val, unit="CPU scheduler %", evidence=text[:400], source="pmset -g therm", started=started)


@check("hardware.recent_panics", "hardware", "Kernel panics in last 30 days")
def panics(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/bin/find", "/Library/Logs/DiagnosticReports", "-type", "f", "-name", "kernel*", "-mtime", "-30", "-print"], timeout)
    if rc:
        state, count = "unknown", None
    else:
        count = len([line for line in text.splitlines() if line.strip()])
        state = "warn" if count else "pass"
    return result("hardware.recent_panics", "hardware", state, "Kernel panics in last 30 days", value=count, unit="count", evidence=text[:400] if count else ("No recent kernel panic reports" if not rc else text[:300]), source="find /Library/Logs/DiagnosticReports -name kernel* -mtime -30", started=started)
