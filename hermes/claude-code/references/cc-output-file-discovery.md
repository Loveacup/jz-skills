# CC Output File Discovery

When Claude Code writes output files during agent team runs, they don't always land where you expect.

## The `/tmp` Assumption Trap

**Default assumption:** CC writes temporary/intermediate files to `/tmp/`.  
**Reality:** When CC agents are given an explicit target path (e.g., Obsidian vault path), they often write directly to the final destination, skipping `/tmp/` entirely.

## Discovery Methods (macOS)

### 1. `mdfind` (Spotlight) — fastest, recommended
```bash
# Search by filename keyword
mdfind -name "全球与中国影响" 2>/dev/null

# Search by content keyword in specific directory
mdfind "NVIDIA GTC Taipei 2026" -onlyin /tmp
```
- Near-instant on SSD Macs
- Works across the entire filesystem
- No need to know the exact path

### 2. `find` with recent modification time
```bash
# Files modified in last 15 minutes
find /Users/alexcai -name "*.md" -mmin -15 2>/dev/null | grep -v ".git"
```

### 3. `ls -lt` in likely output directories
```bash
ls -lt ~/Documents/Obsidian/AlexCai/00-Inbox/ | head -10
ls -lt /tmp/ | head -10
```

## When to Use Each

| Scenario | Method | Why |
|----------|--------|-----|
| CC was given explicit output path | `ls -lt <target_dir>` or `mdfind` | File likely already there |
| CC writes to `/tmp/` by default | `find /tmp -name "*keyword*"` | Narrow scope, fast |
| Can't find anywhere obvious | `mdfind -name "keyword"` | Full filesystem scan, instant |

## Real Example (2026-06-01)

CC SIL v5.0 finisher was tasked with polishing `战略洞察-NVIDIA GTC Taipei 2026 全球与中国影响分析.md`. Expected location: `/tmp/`. Actual location: `~/Documents/Obsidian/AlexCai/00-Inbox/` — written directly because the finisher was given the full Obsidian vault path.

```bash
# Failed:
find /tmp -name "*NVIDIA*"   # nothing

# Worked:
mdfind -name "全球与中国影响"  # instant hit
```
