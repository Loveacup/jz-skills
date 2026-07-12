# P3-B usage surface — triad record (2026-07-02)

## Decision

P3-A made the release gate executable; P3-B makes it discoverable.

Before P3-B, the safest commands lived mostly in SKILL/reference files and chat history. That is fragile for future agents. The project root now has a concise `README.md` with the minimum commands someone needs before editing writer/render/fetch/report logic.

## Implementation

Changed / added:

```text
README.md
SKILL.md
references/content-engine-p3b-usage-surface-20260702.md
```

`README.md` now exposes:

1. cheap deterministic release gate:
   ```bash
   cd shared/bilibili-video-analyzer
   PYTHONPATH=scripts python3 scripts/release_gate.py
   ```
2. explicit real sample smoke:
   ```bash
   PYTHONPATH=scripts python3 scripts/release_gate.py \
     --real-sample /tmp/BV1B9T36nEvL_fetch_all.json \
     --real-writer-provider cli
   ```
3. core generate / verify / deterministic quality gate commands;
4. operational notes:
   - no formal report without transcript evidence;
   - keep one user-facing Obsidian note per video;
   - use `terminal cp` for Obsidian saves and verify after copy.

`SKILL.md` was updated to:

- list `release_gate.py` in Script Reference;
- add a P3-B reference bullet near P3-A.

## Verification

Commands to verify the documented entry points:

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --dry-run
PYTHONPATH=scripts python3 scripts/release_gate.py
```

Expected baseline from P3-A final run:

```text
release gate RUN PASS
fixture quality gate PASS
pytest: 108 passed, 4 warnings
```

## Key lesson

A gate that only exists in memory is not a gate. P3-B turns the quality ritual into the visible front door of the project.
