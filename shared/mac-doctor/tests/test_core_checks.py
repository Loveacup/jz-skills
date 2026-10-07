from __future__ import annotations

import plistlib

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from macdoctor.checks import hardware, performance, security, storage
from macdoctor.runner import CommandTimeout, execute

from macdoctor.checks import devenv, network



class FakeRunner:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def __call__(self, cmd, timeout=10):
        key = tuple(cmd)
        self.calls.append((key, timeout))
        value = self.outputs.get(key)
        if isinstance(value, Exception):
            raise value
        if value is None:
            return 0, "", ""
        if isinstance(value, tuple):
            return value
        return 0, value, ""


def test_apfs_container_plist_parsing():
    xml = plistlib.dumps({"APFSContainerFree": 20, "APFSContainerSize": 1000}, fmt=plistlib.FMT_XML).decode()
    fake = FakeRunner({("/usr/sbin/diskutil", "info", "-plist", "/"): (0, xml, "")})
    item = storage.apfs_free(fake, 2)
    assert item.status == "crit"
    assert item.value == {"free_bytes": 20, "total_bytes": 1000, "free_percent": 2.0}


def test_swap_usage_parsing():
    fake = FakeRunner({("/usr/sbin/sysctl", "vm.swapusage"): "vm.swapusage: total = 8.00G used = 2.50G free = 5.50G"})
    item = performance.swap_usage(fake, 2)
    assert item.status == "warn"
    assert item.value == {"used_mb": 2560.0, "total_mb": 8192.0}


def test_memory_pressure_parsing():
    fake = FakeRunner({("/usr/bin/memory_pressure",): "System-wide memory free percentage: 7%\n"})
    item = performance.memory_pressure(fake, 2)
    assert item.status == "warn"
    assert item.value["free_percent"] == 7


def test_firewall_and_filevault_parsing():
    fake = FakeRunner({
        ("/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"): "Firewall is disabled. (State = 0)",
        ("/usr/bin/fdesetup", "status"): "FileVault is Off.",
    })
    assert security.firewall(fake, 2).status == "crit"
    assert security.filevault(fake, 2).status == "crit"


def test_lsof_listener_output_parses_process_and_port():
    fixture = (
        "COMMAND     PID USER      FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
        "rapportd    123 _network  12u  IPv6 0xabc  0t0      TCP *:49153 (LISTEN)\n"
        "ControlCe   456 alex      18u  IPv6 0xdef  0t0      TCP *:7000 (LISTEN)\n"
    )
    fake = FakeRunner({("/usr/sbin/lsof", "-iTCP", "-sTCP:LISTEN", "-nP"): fixture})
    item = network.listening_tcp(fake, 2)
    assert item.status == "pass"
    assert [(entry["process"], entry["port"]) for entry in item.value] == [
        ("rapportd", 49153), ("ControlCe", 7000),
    ]

def test_late_tcp_listener_after_long_output_is_parsed():
    benign = "".join(
        f"Process{i:<4} 123 _network 12u IPv6 0xabc 0t0 TCP *:{10000 + i} (LISTEN)\n"
        for i in range(35)
    )
    fixture = "COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n" + benign + (
        "VNCServer 987 alex 18u IPv6 0xdef 0t0 TCP *:5900 (LISTEN)\n"
    )
    fake = FakeRunner({("/usr/sbin/lsof", "-iTCP", "-sTCP:LISTEN", "-nP"): fixture})
    item = network.listening_tcp(fake, 2)
    assert item.status == "warn"
    assert any(entry["port"] == 5900 and entry["risk"] == "VNC" for entry in item.value)


def test_top_process_parser_sees_records_after_long_output():
    fixture = "%CPU %MEM COMM\n"
    fixture += "0 0 /long/path/to/idle/process\n" * 40
    fixture += "95 2 hot-process\n"
    fake = FakeRunner({("/bin/ps", "-eo", "%cpu,%mem,comm"): fixture})
    item = performance.top_processes(fake, 2)
    assert item.status == "warn"
    assert item.value[0]["name"] == "hot-process"
    assert item.value[0]["cpu_percent"] == 95.0


def test_screen_lock_parses_sysadminctl_stderr_without_timestamp_integer():
    fake = FakeRunner({
        ("/usr/sbin/sysadminctl", "-screenLock", "status"): (
            0, "", "2026-10-04 15:54:08.996 sysadminctl[45498:468579] screenLock delay is immediate",
        ),
    })
    item = security.screen_lock(fake, 2)
    assert item.status == "pass"
    assert item.value == "immediate"

def test_screen_lock_idle_time_alone_remains_unknown():
    fake = FakeRunner({
        ("/usr/sbin/sysadminctl", "-screenLock", "status"): (1, "", "unavailable"),
        ("/usr/bin/defaults", "-currentHost", "read", "com.apple.screensaver", "idleTime"): (0, "0\n", ""),
    })
    item = security.screen_lock(fake, 2)
    assert item.status == "unknown"
    assert item.value == {"idle_time_seconds": 0}
    assert "idleTime=0 seconds" in item.evidence
    assert "does not establish whether waking requires a password" in item.evidence


PRINT_DISABLED = ("/bin/launchctl", "print-disabled", "system")


def _overrides(**states):
    body = "\n".join(f'\t\t"{label}" => {state}' for label, state in states.items())
    return {PRINT_DISABLED: (0, f"disabled services = {{\n{body}\n\t}}\n", "")}


@pytest.mark.parametrize("state, status", [("enabled", "warn"), ("disabled", "pass")])
def test_ssh_remote_login_reads_launchd_override(state, status):
    item = security.ssh_remote_login(FakeRunner(_overrides(**{"com.openssh.sshd": state})), 2)
    assert item.status == status
    assert item.value == state


def test_ssh_missing_override_is_default_off_and_unreadable_is_unknown():
    assert security.ssh_remote_login(FakeRunner(_overrides(**{"com.apple.ftpd": "disabled"})), 2).status == "pass"
    assert security.ssh_remote_login(FakeRunner({PRINT_DISABLED: (1, "", "denied")}), 2).status == "unknown"


def test_sharing_services_reports_enabled_overrides_only():
    fake = FakeRunner(_overrides(**{"com.apple.screensharing": "enabled", "com.apple.smbd": "disabled"}))
    item = security.sharing_services(fake, 2)
    assert item.status == "warn"
    assert item.value == {"enabled": ["Screen Sharing"]}
    assert security.sharing_services(FakeRunner(_overrides(**{"com.apple.smbd": "disabled"})), 2).status == "pass"


def test_firewall_stealth_off_is_a_known_warning():
    fake = FakeRunner({
        ("/usr/libexec/ApplicationFirewall/socketfilterfw", "--getstealthmode"):
            "Firewall stealth mode is off.",
    })
    item = security.firewall_stealth(fake, 2)
    assert item.status == "warn"
    assert item.value == "Firewall stealth mode is off."


def test_brew_tier_two_notice_is_not_a_warning(monkeypatch):
    monkeypatch.setattr(devenv.shutil, "which", lambda name: "/opt/homebrew/bin/brew")
    key = ("/opt/homebrew/bin/brew", "doctor")
    note = "Warning: Treating this as a Tier 2 configuration:\n  Diagnostic detail\n"
    fake = FakeRunner({key: (1, note, "")})
    item = devenv.brew_doctor(fake, 2)
    assert item.status == "pass"
    assert "Tier 2 configuration" in item.evidence

    fake = FakeRunner({key: (1, note + "Warning: Another issue\n", "")})
    assert devenv.brew_doctor(fake, 2).status == "warn"

def test_battery_health_parsing():
    fake = FakeRunner({
        ("/usr/sbin/system_profiler", "SPHardwareDataType"): "Model Name: MacBook Pro\n",
        ("/usr/sbin/ioreg", "-rc", "AppleSmartBattery"): '"CycleCount" = 120\n"MaxCapacity" = 7500\n"DesignCapacity" = 10000',
        ("/usr/sbin/system_profiler", "SPPowerDataType"): "Condition: Normal\n",
    })
    item = hardware.battery(fake, 2)
    assert item.status == "warn"
    assert item.value["cycles"] == 120
    assert item.value["health_percent"] == 75.0


def test_desktop_battery_check_is_skipped():
    fake = FakeRunner({("/usr/sbin/system_profiler", "SPHardwareDataType"): "Model Name: Mac mini\n"})
    item = hardware.battery(fake, 2)
    assert item.status == "skip"
    assert "Desktop" in item.evidence


def test_timeout_and_exception_are_isolated(monkeypatch):
    monkeypatch.setattr("macdoctor.runner.sys.platform", "darwin")
    monkeypatch.setattr("macdoctor.runner._load_checks", lambda: None)
    from macdoctor.runner import _REGISTRY, CheckSpec
    specs = list(_REGISTRY)
    _REGISTRY[:] = [
        CheckSpec("test.timeout", "performance", "timeout", lambda runner, timeout: (_ for _ in ()).throw(CommandTimeout("slow"))),
        CheckSpec("test.error", "performance", "error", lambda runner, timeout: (_ for _ in ()).throw(RuntimeError("bad"))),
    ]
    try:
        results = execute(ids={"test.timeout", "test.error"})
    finally:
        _REGISTRY[:] = specs
    assert [r.status for r in results] == ["unknown", "error"]


def test_command_exception_status_is_error(monkeypatch):
    monkeypatch.setattr("macdoctor.runner.sys.platform", "darwin")
    monkeypatch.setattr("macdoctor.runner._load_checks", lambda: None)
    from macdoctor.runner import _REGISTRY, CheckSpec
    specs = list(_REGISTRY)
    _REGISTRY[:] = [CheckSpec("test.raise", "storage", "raises", lambda runner, timeout: 1 / 0)]
    try:
        item = execute(ids={"test.raise"})[0]
    finally:
        _REGISTRY[:] = specs
    assert item.status == "error"


def test_brew_outdated_ignores_stderr_progress_lines(monkeypatch):
    from macdoctor.checks import devenv
    monkeypatch.setattr(devenv.shutil, "which", lambda name: "/opt/homebrew/bin/brew")
    progress = "==> Downloading Homebrew API data\n✔︎ JSON API packages.arm64_tahoe.jws.json\n"
    key = ("/opt/homebrew/bin/brew", "outdated", "--quiet")
    clean = devenv.brew_outdated(FakeRunner({key: (0, "", progress)}), 2)
    assert (clean.status, clean.value) == ("pass", 0)
    stale = devenv.brew_outdated(FakeRunner({key: (0, "poppler\nyt-dlp\n", progress)}), 2)
    assert (stale.status, stale.value) == ("warn", 2)
    assert "poppler" in stale.evidence


@pytest.mark.parametrize("name,relative", [
    ("pip", "Library/Caches/pip"),
    ("playwright", "Library/Caches/ms-playwright"),
    ("npm", ".npm/_cacache"),
])
def test_cache_check_reports_large_catalogued_cache(monkeypatch, tmp_path, name, relative):
    cache = tmp_path / relative
    cache.mkdir(parents=True)
    monkeypatch.setattr(storage, "account_home", lambda: tmp_path)
    monkeypatch.setattr("macdoctor.runner.sys.platform", "darwin")
    fake = FakeRunner({("/usr/bin/du", "-sk", str(cache)): (0, f"6291456\t{cache}\n", "")})

    item = execute(ids={f"storage.cache.{name}"}, command=fake)[0]

    assert (item.status, item.value) == ("warn", 6144.0)


@pytest.mark.parametrize("failure", ["stat", "du"])
def test_cache_access_failure_is_unknown_not_zero(monkeypatch, tmp_path, failure):
    cache = tmp_path / "Library/Caches/ms-playwright"
    cache.mkdir(parents=True)
    monkeypatch.setattr(storage, "account_home", lambda: tmp_path)
    monkeypatch.setattr("macdoctor.runner.sys.platform", "darwin")
    if failure == "stat":
        original = Path.stat

        def denied(path, *args, **kwargs):
            if path == cache:
                raise PermissionError("cache access denied")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", denied)
    fake = FakeRunner({("/usr/bin/du", "-sk", str(cache)): (1, "", "Permission denied")})

    item = execute(ids={"storage.cache.playwright"}, command=fake)[0]

    assert item.status == "unknown"
    assert item.value is None


@pytest.mark.parametrize("failure", ["stat", "lstat", "du"])
def test_storage_inventory_keeps_unreadable_cache_unknown(monkeypatch, tmp_path, failure):
    import os
    from subprocess import CompletedProcess
    from macdoctor import clean

    cache = tmp_path / "Library/Caches/ms-playwright"
    cache.mkdir(parents=True)
    os.utime(cache, (0, 0))
    monkeypatch.setattr(clean.paths, "account_home", lambda: tmp_path)
    if failure != "du":
        original = Path.stat

        def denied(path, *args, **kwargs):
            if path == cache and (failure == "stat" or kwargs.get("follow_symlinks") is False):
                raise PermissionError("cache access denied")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", denied)

    def runner(argv, **kwargs):
        return CompletedProcess(argv, 1, stdout="", stderr="Permission denied")

    target = next(t for t in clean.load_targets() if t["id"] == "playwright-browsers")
    records = clean.scan([target], runner=runner)

    assert len(records) == 1
    assert records[0]["path"] == str(cache)
    assert records[0]["size_bytes"] == "unknown"
