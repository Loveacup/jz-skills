from __future__ import annotations

import re
import time

from ..runner import check, Command
from . import command_text, result

_RISKY = {22: "SSH", 23: "Telnet", 445: "SMB", 5900: "VNC", 3389: "RDP"}


@check("network.listening_tcp", "network", "Listening TCP ports")
def listening_tcp(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/sbin/lsof", "-iTCP", "-sTCP:LISTEN", "-nP"], timeout)
    entries = []
    if rc == 0:
        for line in text.splitlines():
            match = re.search(r"\bTCP\s+(.+):(\d+)\s+\(LISTEN\)\s*$", line)
            if not match:
                continue
            port = int(match.group(2))
            entries.append({
                "process": line.split(None, 1)[0],
                "endpoint": match.group(1) + ":" + match.group(2),
                "port": port,
                "risk": _RISKY.get(port),
            })
    if rc:
        state, value = "unknown", None
    else:
        state, value = ("warn", entries) if any(e["risk"] in ("Telnet", "VNC", "RDP") for e in entries) else ("pass", entries)
    evidence = "; ".join(f"{e['process']} {e['endpoint']}" + (f" ({e['risk']})" if e["risk"] else "") for e in entries[:20])
    return result("network.listening_tcp", "network", state, "Listening TCP ports", value=value, unit="ports", evidence=evidence or (text[:300] if rc else "No TCP listeners"), source="lsof -iTCP -sTCP:LISTEN -nP", started=started)


@check("network.dns_servers", "network", "DNS servers")
def dns_servers(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/sbin/scutil", "--dns"], timeout)
    servers = sorted(set(re.findall(r"nameserver\[\d+\]\s*:\s*([^\s]+)", text)))
    state = "unknown" if rc or not servers else "pass"
    return result("network.dns_servers", "network", state, "DNS servers", value=servers or None, evidence=", ".join(servers) if servers else text[:300], source="scutil --dns", started=started)


@check("network.proxy", "network", "System proxy configuration")
def proxy(command: Command, timeout: float):
    started = time.monotonic()
    rc, text = command_text(command, ["/usr/sbin/scutil", "--proxy"], timeout)
    values = {}
    for key in ("HTTPEnable", "HTTPSEnable", "SOCKSEnable", "ProxyAutoConfigEnable", "ProxyAutoDiscoveryEnable"):
        match = re.search(rf"{key}\s*:\s*(\d+)", text)
        if match:
            values[key] = int(match.group(1))
    if rc or not values:
        state = "unknown"
    else:
        state = "pass"
    enabled = [key for key, value in values.items() if value == 1]
    return result("network.proxy", "network", state, "System proxy configuration", value=values or None, evidence="enabled: " + ", ".join(enabled) if values else text[:300], source="scutil --proxy", started=started)
