# macOS Disk Audit Pattern

Source: upkeep (KyleNesium CC skill, 15-phase discovery-based macOS disk audit), tested on Alex's Mac mini 2026-05-30.

Use as a cron-worker change-detection heartbeat to monitor disk health without burning LLM tokens on every tick.

## ⚠️ APFS Disk Pitfall

**DO NOT use `df -h /` on macOS.** APFS multi-volume containers (Macintosh HD + Data + Preboot + Recovery + VM) share the same physical space. `df` shows per-volume usage with misleading percentages (e.g. 17Gi used / 28% when actual is 80%). Use `diskutil` instead:

```bash
# Correct APFS disk readout
diskutil info / | grep -E "Container Free Space|Container Total Space|Volume Used Space"
```

Example output on a 245GB Mac mini (2026-05-30):
- Container Total: 245.1 GB
- Container Free: 53.4 GB (21.8%)
- Volume Used: 17.8 GB (system only)

## Quick Audit Phases

For a cron-worker health-check heartbeat (read-only, no cleanup):

### Phase 1: Baseline
```bash
diskutil info / 2>/dev/null | grep -E "Container (Free|Total) Space|Volume Used"
sw_vers
brew --version 2>/dev/null || echo "brew not installed"
```

### Phase 2: Homebrew Audit
```bash
brew outdated 2>/dev/null | wc -l  # outdated count
brew cleanup --dry-run 2>/dev/null | tail -1  # reclaimable size
brew doctor 2>&1 | grep -ciE "warning|error"  # health issues
```

### Phase 3: Dev Caches (Top Consumers)
```bash
du -sh ~/Library/Caches/*/ ~/.cache/*/ ~/.npm 2>/dev/null | sort -rh | head -10
```

### Phase 5: Orphan LaunchAgents
```bash
for p in ~/Library/LaunchAgents/*.plist; do
  prog=$(/usr/libexec/PlistBuddy -c "Print :ProgramArguments:0" "$p" 2>/dev/null)
  [ -n "$prog" ] && [ ! -e "$prog" ] && echo "DEAD: $p → $prog"
done
```

## Change-Detection Integration

To make this a change-detection heartbeat that only fires the LLM when disk state changed:

```python
cronjob(
    name="disk-health-check",
    schedule="0 */6 * * *",  # every 6 hours
    script="disk-health-hash.py",  # compute hash of disk state
    prompt="Disk state changed: {SCRIPT_OUTPUT}. Analyze trends.",
    profile="cron-worker",
    deliver="local",
)
```

The hash script compares `diskutil info` output + `du` cache sizes — only outputs when numbers shifted by >1% or new cache dirs appeared.
