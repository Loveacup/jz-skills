from __future__ import annotations

import re
import time

from ..runner import check, Command, redact
from . import command_text, result

_FIREWALL = "/usr/libexec/ApplicationFirewall/socketfilterfw"


def _text_check(command: Command, timeout: float, check_id: str, title: str,
                argv: list[str], enabled: re.Pattern[str], disabled: re.Pattern[str],
                *, enabled_status: str = "pass", disabled_status: str = "warn"):
    started = time.monotonic()
    rc, text = command_text(command, argv, timeout)
    if enabled.search(text):
        state = enabled_status
    elif disabled.search(text):
        state = disabled_status
    else:
        state = "unknown"
    return result(check_id, "security", state, title, value=text.strip()[:160] or None,
                  evidence=text[:300], source=" ".join(argv), started=started,
                  recommendation="Review this security setting" if state == "warn" else None)


@check("security.sip", "security", "System Integrity Protection")
def sip(command: Command, timeout: float):
    return _text_check(command, timeout, "security.sip", "System Integrity Protection", ["/usr/bin/csrutil", "status"], re.compile(r"enabled"), re.compile(r"disabled"))


@check("security.gatekeeper", "security", "Gatekeeper")
def gatekeeper(command: Command, timeout: float):
    return _text_check(command, timeout, "security.gatekeeper", "Gatekeeper", ["/usr/sbin/spctl", "--status"], re.compile(r"assessments enabled"), re.compile(r"assessments disabled"))


@check("security.filevault", "security", "FileVault")
def filevault(command: Command, timeout: float):
    return _text_check(command, timeout, "security.filevault", "FileVault", ["/usr/bin/fdesetup", "status"], re.compile(r"FileVault is On", re.I), re.compile(r"FileVault is Off", re.I), disabled_status="crit")


@check("security.firewall", "security", "Application firewall")
def firewall(command: Command, timeout: float):
    return _text_check(command, timeout, "security.firewall", "Application firewall", [_FIREWALL, "--getglobalstate"], re.compile(r"Firewall is enabled", re.I), re.compile(r"Firewall is disabled", re.I), disabled_status="crit")


@check("security.firewall_stealth", "security", "Firewall stealth mode")
def firewall_stealth(command: Command, timeout: float):
    return _text_check(command, timeout, "security.firewall_stealth", "Firewall stealth mode", [_FIREWALL, "--getstealthmode"], re.compile(r"stealth mode (?:is )?(?:enabled|on)", re.I), re.compile(r"stealth mode (?:is )?(?:disabled|off)", re.I))


_PRINT_DISABLED = ["/bin/launchctl", "print-disabled", "system"]


def _launchd_overrides(command: Command, timeout: float) -> tuple[dict[str, bool] | None, str]:
    """Parse `launchctl print-disabled system` (no sudo): label -> True if enabled.

    Sharing daemons are socket-activated, so `state = not running` says nothing about
    whether they are on. The Sharing settings toggle writes this enable/disable override.
    """
    rc, text = command_text(command, _PRINT_DISABLED, timeout)
    if rc or "=>" not in text:
        return None, text[:200]
    overrides = {}
    for label, value in re.findall(r'"([^"]+)"\s*=>\s*(enabled|disabled|true|false)', text):
        # Current macOS prints enabled/disabled; older releases print the Disabled flag (true = off).
        overrides[label] = value in ("enabled", "false")
    return overrides, text[:200]


def _override_state(overrides: dict[str, bool], label: str) -> bool:
    """These daemons ship `Disabled=true`, so a missing override means off."""
    return overrides.get(label, False)


@check("security.ssh_remote_login", "security", "SSH remote login")
def ssh_remote_login(command: Command, timeout: float):
    started = time.monotonic()
    overrides, raw = _launchd_overrides(command, timeout)
    source = "launchctl print-disabled system"
    if overrides is None:
        return result("security.ssh_remote_login", "security", "unknown", "SSH remote login",
                      evidence=f"launchd overrides unreadable: {raw or 'no output'}", source=source, started=started)
    on = _override_state(overrides, "com.openssh.sshd")
    label = {True: "enabled", False: "disabled"}.get(overrides.get("com.openssh.sshd"), "no override (default off)")
    return result("security.ssh_remote_login", "security", "warn" if on else "pass", "SSH remote login",
                  value="enabled" if on else "disabled", evidence=f"com.openssh.sshd: {label}",
                  source=source, started=started,
                  recommendation="Remote Login is on; keep it only if you SSH into this Mac" if on else None)


@check("security.screen_lock", "security", "Screen lock setting")
def screen_lock(command: Command, timeout: float):
    started = time.monotonic()
    argv = ["/usr/sbin/sysadminctl", "-screenLock", "status"]
    rc, stdout, stderr = command(argv, timeout)
    text = redact("\n".join(part for part in (stdout, stderr) if part))
    message = re.sub(r"(?m)^.*sysadminctl\[\d+:\d+\]\s*", "", text).strip()
    delay = re.search(r"screenLock\s+delay\s+is\s+(immediate|off|[\d.]+)\s*(seconds?|s)?", message, re.I)
    if delay:
        raw = delay.group(1).lower()
        if raw == "immediate":
            state, value = "pass", "immediate"
        elif raw == "off":
            state, value = "warn", "off"
        else:
            value = float(raw)
            if value.is_integer():
                value = int(value)
            state = "pass" if value <= 5 else "warn"
        return result("security.screen_lock", "security", state, "Screen lock setting", value=value, unit="seconds", evidence=message[:300], source="sysadminctl -screenLock status", started=started)
    if re.search(r"screenLock.*(?:disabled|\boff\b)", message, re.I):
        return result("security.screen_lock", "security", "warn", "Screen lock setting", value="off", evidence=message[:300], source="sysadminctl -screenLock status", started=started)
    if re.search(r"screenLock.*enabled", message, re.I):
        return result("security.screen_lock", "security", "pass", "Screen lock setting", value="enabled", evidence=message[:300], source="sysadminctl -screenLock status", started=started)

    defaults_rc, defaults_out, defaults_err = command(
        ["/usr/bin/defaults", "-currentHost", "read", "com.apple.screensaver", "idleTime"],
        timeout,
    )
    defaults_text = redact("\n".join(part for part in (defaults_out, defaults_err) if part))
    seconds_match = re.fullmatch(r"\s*(\d+)\s*", defaults_text)
    seconds = int(seconds_match.group(1)) if seconds_match and not defaults_rc else None
    idle = f"idleTime={seconds} seconds" if seconds is not None else f"idleTime unavailable ({defaults_text or message or 'no readable setting'})"
    evidence = f"{idle}; this setting does not establish whether waking requires a password"
    return result("security.screen_lock", "security", "unknown", "Screen lock setting",
                  value={"idle_time_seconds": seconds}, evidence=evidence,
                  source="sysadminctl -screenLock status; defaults idleTime", started=started)


@check("security.auto_update", "security", "Automatic software updates")
def auto_update(command: Command, timeout: float):
    return _text_check(command, timeout, "security.auto_update", "Automatic software updates", ["/usr/sbin/softwareupdate", "--schedule"], re.compile(r"automatic.*(?:on|enabled)|schedule.*on", re.I), re.compile(r"automatic.*(?:off|disabled)|schedule.*off", re.I))


# Only daemons whose plist ships `Disabled=true`, so the override is the Sharing toggle.
_SHARING = {"com.apple.screensharing": "Screen Sharing", "com.apple.smbd": "File Sharing (SMB)"}


@check("security.sharing_services", "security", "Sharing services")
def sharing_services(command: Command, timeout: float):
    started = time.monotonic()
    overrides, raw = _launchd_overrides(command, timeout)
    source = "launchctl print-disabled system"
    if overrides is None:
        return result("security.sharing_services", "security", "unknown", "Sharing services",
                      evidence=f"launchd overrides unreadable: {raw or 'no output'}", source=source, started=started)
    enabled = [name for label, name in _SHARING.items() if _override_state(overrides, label)]
    return result("security.sharing_services", "security", "warn" if enabled else "pass", "Sharing services",
                  value={"enabled": enabled}, evidence=f"enabled: {', '.join(enabled) or 'none'}",
                  source=source, started=started,
                  recommendation="Keep only the sharing services you actually use" if enabled else None)


@check("security.sudo_only_controls", "security", "Privileged security controls")
def privileged_controls(command: Command, timeout: float):
    return result("security.sudo_only_controls", "security", "skip", "Privileged security controls", evidence="Not checked: sudo-only controls are intentionally not invoked", source="policy", recommendation=None)
