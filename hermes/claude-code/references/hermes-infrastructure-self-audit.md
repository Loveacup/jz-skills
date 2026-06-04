# CC Agent Team — Hermes Infrastructure Self-Audit Pattern

Use when Hermes's own infrastructure (gateways, launchd services, cron workers,
profiles, state stores, etc.) shows symptoms that need root-cause analysis
beyond Hermes's single-turn diagnosis.

## When to Use

- Gateway / launchd service failing on startup/reboot
- Cross-profile inconsistency (different profiles' services behaving differently)
- System-level migration residue (old configs, stale plists, naming migrations)
- Infrastructure health issues that recur across restarts

## Pattern

```
Hermes triages symptom → partial fix if urgent
         │
         ▼
Write context file → CC Agent Team (xhigh effort) audits:
  · Verify Hermes's fix completeness
  · Cross-check all profiles / launchd entries / configs
  · Trace git history for naming migrations
  · Read source code (e.g., gateway.py) for systemic gaps
  · Check logs for crash patterns
  · Identify additional issues beyond what Hermes found
         │
         ▼
CC reports: what was incomplete, systemic root cause, additional findings
         │
         ▼
Hermes + CC split remaining work:
  · CC: source code fix + tests + upstream PR (if applicable)
  · Hermes: runtime fixes (service restart, cleanup)
```

## Key Differences from jz-skills-cc-first-pattern

| Aspect | jz-skills-first | Hermes self-audit |
|--------|----------------|-------------------|
| Scope | External repos (jz-skills) | Hermes's own infrastructure |
| Hermes's role | Design reviewer | First responder + triager |
| CC's role | Code reviewer + implementer | Auditing Hermes's own diagnosis |
| Deliverable | Code changes + deployed skills | Audit report + source fix + health check |
| Key risk | Cross-profile write guard | Profile isolation blinds Hermes to files |

## Context File Template

Include:
1. What Hermes already found and what fix was applied
2. Full diagnostics `hermes --profile X gateway status`, `launchctl list`, `lsof -i`
3. File paths to inspect (plists, configs, logs)
4. Audit tasks: verify fix completeness, cross-profile consistency, root cause, preventive measures, execute additional fixes
5. Deliverable: report to `/tmp/cc-<topic>-audit-report.md` + any fixes

## Session Example (2026-06-03)

Symptom: 小黄 default gateway (port 8460) not starting after reboot.
Hermes diagnosis: stale `com.hermes.gateway.default` launchd entry, fix with `bootout` + `install --force`.
CC audit found: Hermes's fix was incomplete — `bootout` cleared memory but plist file remained on disk (RunAtLoad=true). Deeper root cause: legacy cleanup exists only for Linux/systemd, macOS code path completely blind to old labels. CC implemented upstream fix (11 tests, PR #38343) + health check watchdog.

## Pitfall: Profile Isolation

When running in a non-default Hermes profile (e.g., cron-worker), `~` resolves to the profile's sandbox home. This means:
- `ls ~/Library/LaunchAgents/` looks in the WRONG place
- `gh auth status` reads WRONG config
- `cd ~/.hermes/...` resolves to WRONG path

**Fix:** Always use absolute paths (`/Users/alexcai/...`) when operating on system-level files from a non-default profile. Pass `HOME=/Users/alexcai` to subprocesses like `gh` and `claude`.
