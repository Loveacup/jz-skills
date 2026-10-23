---
name: mac-doctor
description: >-
  Read-only macOS health, performance, storage, security, hardware, network and
  development-environment checks, with explicitly gated cleanup planning. Use for
  “check my mac”, “mac slow”, “disk full”, “cleanup mac”, “巡检”, “磁盘空间”,
  “清理缓存”, “安全检查”, “健康评分”, or related Mac diagnostics. Explicitly
  authorized reviewed cleanup may route to a native desktop operator; this skill
  does not itself drive the GUI or troubleshoot live networks.
type: routine
author: Hermes Agent
platforms: [macos]
metadata:
  hermes:
    category: apple
    tags: [macos, system-inspection, disk-audit, cache-cleanup, health-check, apfs,
           security-audit, hardware-audit, network-audit, history-tracking, smart-alerts]
---

# mac-doctor

mac-doctor is a read-only macOS CLI for evidence-based checks, scoped subsystem scores, storage inventory, and local history. It helps separate measured findings from missing evidence, while cleanup is a separate, reviewed operation—not a consequence of diagnosis.

## Safety contract

- Checks, score, storage, history, status, and verify are observational. No `sudo` or automatic cleanup. Unknown, error, and skip are not zero and never mean pass.
- Cleanup requires owner authorization for the current task and review of exact targets, methods and irreversible consequences. The owner may delegate item approval to an independent reviewer; then proceed within the approved manifest without repeated user confirmation. CLI plan/apply remains available, but it is not the only permitted execution route.
- If approval in the current turn explicitly includes renewal of that exact manifest, use `clean apply PLAN_ID --yes --renew-if-unchanged`. For an expired, nonempty SAFE/native plan only, the engine checks its host and plan-ID binding, creates a fresh one-hour plan for the same target IDs, and immediately applies it only when every complete item matches. Any mismatch refuses without cleanup; the old plan is not rewritten. Do not add this flag for ordinary approval, unclear approval, or a prior-turn approval. CAUTION/protected/report-only targets gain no permission.
- Renewal additionally requires known, nonnegative integer sizes in both the approved and fresh scans. Two `"unknown"` measurements are not proof of equality and refuse renewal. Ordinary non-renewing apply policy is unchanged.
- The CLI engine is unchanged: SAFE/native commands and their catalogue gates remain; CAUTION `apply` stays disabled, REPORT stays inventory-only, and NEVER remains protected. These engine capabilities do not impose a manual-only or GUI-only restriction on the separately reviewed owner-authorized workflow.
- Read `references/cleanup.md` → “Owner-authorized reviewed cleanup”. After approval, the agent may use a scoped tool-native command, an exact-path command/filesystem API, or an available native UI. Inactive Hermes backups and explicitly authorized Trash disposal are permitted. No desktop driver installation is required for command cleanup. A skill-edit request alone grants no deletion permission.
- Immediately before execution, recheck approved scope, identity and active use. Changed, unknown, in-use or live protected targets block that item; a CLI failure on those grounds cannot be bypassed by another method. Exact-path checks are not atomic inode binding: pathname replacement races remain and must not be hidden. No privilege escalation or credential/security-setting changes.
- Optional Jev push gating is fail-open and informational only; Jev never authorizes cleanup, process kills, security verdicts, or other actions.
- Record the reviewed manifest and durable attempt/outcome evidence; verify actual postconditions. Report measured APFS container free-byte delta separately from nominal sizes. Moving to Trash frees no space until emptied; permanent deletion and whole-Trash disposal require their own reviewed scope and consequences, not an extra GUI requirement.

## Resolve and run the CLI

Resolve the installed skill directory from this `SKILL.md` location (the skill's containing directory); do not assume a fixed installation path. Run `scripts/mac-doctor` relative to that directory, for example:

```sh
"$SKILL_DIR/scripts/mac-doctor" check
```

If `$SKILL_DIR` is unavailable, use the skill loader's resolved file path to locate the package and derive the relative script path. In OMP, read references through `skill://mac-doctor/references/<file>`. mac-doctor supports Darwin only.

## Problem → command

| Need | Command / next step |
|---|---|
| Health overview | `scripts/mac-doctor score` (or detailed `check`) |
| Slow Mac, memory pressure, swap | `scripts/mac-doctor check --category performance` |
| Disk full / storage attribution | `scripts/mac-doctor check --category storage`; `storage analyze --json` for bounded root groups/Top hotspots; `storage` for the existing cleanup catalogue; only then, if requested, `clean plan` |
| Offline storage report | `scripts/mac-doctor storage analyze --html ABSOLUTE_NEW_FILE --json`; read `references/storage-analysis.md` |
| Security posture | `scripts/mac-doctor check --category security` |
| Hardware, network, developer environment | `scripts/mac-doctor check --category hardware`, `network`, or `devenv` |
| History and trends | `scripts/mac-doctor history` |
| Collector / integration state | `scripts/mac-doctor status` and `verify` |
| Install collector | `scripts/mac-doctor install` |
| Hermes scheduled watchdog / triage | Read `adapters/hermes/README.md` |
| Optional watchdog alert gate | `scripts/mac-doctor jev preview` / `jev ask`; read `references/jev.md` |

`check` and `score` are on-demand CLI operations. A score is three subsystem scores plus coverage—not a single overall health grade.

`storage analyze` adds read-only attribution inspired by storage-analyzer, not a deletion backend. It uses the OS-account home rather than a profile's redirected HOME; default command budget is 30 seconds, each du at most 3 seconds, maximum 200 immediate entries per root. Unknown, partial and excluded paths are explicit; nested groups and same-inode aliases are not additive. Report occupied allocated bytes, never equate them to reclaimable space. `--html` only writes a new private static artifact, with no network assets, server or delete controls. Keep routine watchdog/collector cadence unchanged; do not run broad analysis on every tick or turn its findings into cleanup permission. Read `references/storage-analysis.md` for selective follow-up and limits.

## User-facing report contract

Report: (1) a one-line conclusion, (2) evidence with check IDs and measured values, (3) unknown/error/skip findings and coverage, (4) prioritized recommended actions, and (5) what was not done. Distinguish observations from inference; name the source/time when relevant. For cleanup, separately state approved target, per-item receipt outcome, nominal item size, measured Data-volume delta, and the fact Trash does not free space until emptied.

## Interpretation gotchas

- APFS `df` volume figures are not the container-level free-space measure; check `diskutil` container values.
- `brew upgrade` may exit 1 after partial package success; inspect its output rather than inferring all-or-nothing failure.
- Telegram Group Containers include message databases and are protected user data.
- qmd indexes/models and Hugging Face models may be production assets; never treat model/cache naming as cleanup authorization.
- Hermes can redirect profile `HOME`; mac-doctor resolves its account/data paths independently. Do not infer shared user paths from a profile's `~`.

## References

- `references/checks.md` — checks, IDs, thresholds, scoring and coverage.
- `references/storage-analysis.md` — bounded storage attribution, ownership hints, accounting, offline reports and cron-use boundaries.
- `references/cleanup.md` — target catalogue, gates, plans and receipts.
- `references/collector-and-alerts.md` — background collector, configuration, alerts and database.
- `references/cli.md` — command, JSON, and exit-code details.
- `references/diagnostics-playbook.md` — manual investigation and safe follow-up.
- `references/security-hardware-network.md` — scope and interpretation of those check groups.
- `adapters/hermes/README.md` — optional Hermes cron adapter.
