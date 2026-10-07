from __future__ import annotations

import plistlib
import time
from pathlib import Path

from ..clean import load_targets
from ..paths import account_home
from ..runner import check, Command
from . import result


@check("storage.apfs_container_free", "storage", "APFS container free space")
def apfs_free(command: Command, timeout: float):
    started = time.monotonic()
    rc, stdout, stderr = command(["/usr/sbin/diskutil", "info", "-plist", "/"], timeout)
    try:
        info = plistlib.loads(stdout.encode() if isinstance(stdout, str) else stdout)
    except Exception:
        info = {}
    free = info.get("APFSContainerFree") or info.get("ContainerFreeSpace")
    total = info.get("APFSContainerSize") or info.get("ContainerTotalSpace")
    if rc or not isinstance(free, int) or not isinstance(total, int) or total <= 0:
        state, value, evidence = "unknown", None, (stderr or "Could not read APFS container plist")[:300]
    else:
        pct = free * 100 / total
        state = "crit" if pct < 5 else "warn" if pct < 15 else "pass"
        value = {"free_bytes": free, "total_bytes": total, "free_percent": round(pct, 1)}
        evidence = f"APFS container free {free} of {total} bytes ({pct:.1f}%)"
    return result("storage.apfs_container_free", "storage", state, "APFS container free space", value=value, unit="bytes", evidence=evidence, source="diskutil info -plist /", started=started, recommendation="Review storage consumers" if state in ("warn", "crit") else None)


@check("storage.tm_local_snapshots", "storage", "Time Machine local snapshots")
def local_snapshots(command: Command, timeout: float):
    started = time.monotonic()
    rc, stdout, stderr = command(["/usr/bin/tmutil", "listlocalsnapshots", "/"], timeout)
    snapshots = [line.strip() for line in stdout.splitlines() if line.strip().startswith("com.apple.TimeMachine.")]
    state = "unknown" if rc else "pass"
    return result("storage.tm_local_snapshots", "storage", state, "Time Machine local snapshots", value=len(snapshots) if not rc else None, unit="count", evidence="; ".join(snapshots[:10]) if not rc else stderr[:300], source="tmutil listlocalsnapshots /", started=started)


_CACHE_TARGETS = (
    ("npm", "npm-cache"),
    ("uv", "uv-cache"),
    ("pip", "pip-cache"),
    ("playwright", "playwright-browsers"),
    ("xcode_derived_data", "xcode-derived-data"),
)
_CACHE_PATHS = (
    ("user_cache", "{home}/.cache"),
    ("library_caches", "{home}/Library/Caches"),
)


def _cache_check(check_id: str, name: str, template: str):
    @check(check_id, "storage", f"Development cache size: {name}")
    def cache_size(command: Command, timeout: float):
        started = time.monotonic()
        path = Path(template.format(home=account_home()))
        try:
            path.stat()
        except FileNotFoundError:
            return result(check_id, "storage", "pass", f"Development cache size: {name}", value=0, unit="MB", evidence=f"path absent: {path}", source=f"stat {path}", started=started)
        except OSError as exc:
            return result(check_id, "storage", "unknown", f"Development cache size: {name}", evidence=f"cannot inspect cache path: {exc}", source=f"stat {path}", started=started)
        rc, stdout, stderr = command(["/usr/bin/du", "-sk", str(path)], timeout)
        try:
            kb = int(stdout.split()[0])
        except (ValueError, IndexError):
            kb = None
        if rc or kb is None:
            state, size = "unknown", None
            evidence = (stderr or stdout or "du failed")[:300]
        else:
            size = round(kb / 1024, 1)
            state = "warn" if size > 5120 else "pass"
            evidence = f"{path}: {size:.1f} MB"
        return result(check_id, "storage", state, f"Development cache size: {name}", value=size, unit="MB", evidence=evidence, source="du -sk", started=started, recommendation="Review cache before planning cleanup" if state == "warn" else None)
    return cache_size
    
_targets = {target["id"]: target for target in load_targets()}
for _name, _target_id in _CACHE_TARGETS:
    _cache_check(f"storage.cache.{_name}", _name, _targets[_target_id]["paths"][0])
for _name, _template in _CACHE_PATHS:
    _cache_check(f"storage.cache.{_name}", _name, _template)
