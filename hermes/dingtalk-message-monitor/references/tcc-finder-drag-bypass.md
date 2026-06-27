# macOS TCC Container Bypass — Finder Drag-and-Drop (com.apple.macl)

> Reference for `dingtalk-message-monitor` skill. Captures the CVE-2026-28910 discovery and the Finder drag-and-drop workaround for accessing sandboxed app container files.

## The Problem

macOS 26.0–26.3.2 (fixed in 26.4): sandboxed app data containers (`~/Library/Containers/<bundle-id>/`) cannot be read even by processes with Full Disk Access. TCC's attribution chain dead-ends before reaching the container.

**Diagnostic fingerprint**: `stat` works (returns metadata), but `cat`/`cp`/`head`/`open()` all timeout.

## Root Cause: CVE-2026-28910

Disclosed by Mysk Blog (Talal Haj Bakry & Tommy Mysk), May 2026.
Source: https://mysk.blog/2026/05/19/cve-2026-28910/

- macOS treats sandboxed app data containers as fully isolated — even root and FDA-granted processes cannot read them
- Archive Utility had nearly unrestricted filesystem access until 26.4
- Combined with drag-and-drop sandbox quirk, this allowed full container bypass
- Apple patched in macOS 26.4 (March 2026)

## The Workaround: Finder Drag-and-Drop

macOS interprets drag-and-drop from Finder as "user intent." When a file is dragged from Finder to another app (Terminal, Desktop), macOS applies a `com.apple.macl` extended attribute that **permanently exempts** that file from TCC protection for the receiving process.

### Procedure

1. Open Finder → `Cmd+Shift+G` → paste container path (e.g., `~/Library/Containers/<bundle-id>/...`)
2. Drag the target file to **Desktop** or **Terminal**
3. The file is now readable without TCC interference — permanently

### Why this works

- `com.apple.macl` is an extended attribute protected by SIP — it cannot be removed via normal means
- The grant persists across Terminal sessions and reboots
- macOS treats drag-and-drop the same as choosing a file in an Open panel — it's an expression of user intent

## What Does NOT Work

| Attempt | Result |
|---------|--------|
| `cp -c` (APFS clone) | Timeout |
| Python `shutil.copy2` | 300s timeout |
| `sudo cat` | Requires terminal password |
| `osascript` file read | Timeout |
| `xattr` on file | Timeout |
| Cron-worker one-shot | Same TCC block |
| System Settings FDA toggle | FDA doesn't reach sandbox containers on 26.0–26.3 |

## Affected macOS Versions

- 26.0.0 – 26.3.2: affected (confirmed on 26.2)
- 26.4+: fixed
- Earlier versions likely affected but untested
