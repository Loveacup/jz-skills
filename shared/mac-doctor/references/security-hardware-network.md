# Security, hardware, and network checks

This reference describes the checks currently registered in `scripts/macdoctor/checks/`, not a claim of a complete macOS compliance audit. Use `scripts/mac-doctor check --category security|hardware|network`; see the exact IDs, statuses, and sources in [`checks.md`](checks.md). These checks do not change system configuration.

## Security

The implemented set covers SIP, Gatekeeper, FileVault, application firewall state and stealth mode, SSH remote-login status, screen-lock configuration, automatic software updates, selected sharing services, and a deliberately skipped sudo-only controls result. FileVault/firewall off are critical; SIP/Gatekeeper/stealth/update or confirmed active sharing findings warn according to check logic. SSH Remote Login and sharing state come from `launchctl print-disabled system` (no sudo): an `enabled` override warns, `disabled` or no override passes (these daemons ship `Disabled=true`). Screen-lock passes when `sysadminctl` reports an immediate delay or a delay ≤5 seconds; off/longer delays warn. The `defaults` idleTime fallback is unknown because it cannot establish the actual screen-lock/password delay. A skipped privileged control is not evidence that the control is secure.

Sharing daemons are socket-activated, so `state = not running` does not mean off; the enable/disable override written by the Sharing settings toggle is used instead. Only Screen Sharing and File Sharing (SMB) are covered, because their plists ship `Disabled=true`; Remote Apple Events and Internet Sharing are not, since their override does not reflect the toggle. Unreadable overrides are unknown.

This is not the old broader hand-run checklist: it does not establish MDM policy, Secure Boot policy, XProtect freshness, all profiles/extensions, every sharing service, or full TCC access. No `sudo` is invoked. macOS policy may be MDM-managed, and a reported value should be interpreted with the device administrator rather than automatically changed.

## Hardware

Battery condition and cycle data are inspected on portable models; desktop models skip the battery check. Thermal status comes from `pmset -g therm`; recent kernel panic reports are counted from the last 30 days. These checks do not measure all temperatures, SMART health, power, fan speed, or sleep/wake history. Missing permissions/tools or unparseable output remain unknown.

## Network

The current registry inspects TCP listeners, DNS server configuration, and system proxy settings. Listener findings label common service ports; Telnet/VNC/RDP findings warn, while SSH/SMB are shown as labeled evidence without automatically warning by port alone. This is configuration inventory, not live reachability testing, routing diagnosis, firewall packet analysis, Wi-Fi quality assessment, or Bluetooth audit. Use a separate, user-requested network troubleshooting workflow for ping/traceroute or interactive diagnostics.

## Reading findings

A warning means the check's implemented rule matched, not that compromise or exploitability is proven. A pass is bounded to the check's observable command and current output. Unknown/error/skip are explicit coverage gaps. Do not treat this report as authority to disable sharing, change security settings, rotate credentials, or stop processes; present evidence and ask for explicit scope-specific approval before any modification.
