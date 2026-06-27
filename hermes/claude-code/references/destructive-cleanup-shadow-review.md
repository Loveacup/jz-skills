# Destructive Cleanup + CC Shadow-Review Pattern

Use when CC is asked to assist with irreversible or high-risk cleanup: deleting local trees, folding archives, pruning remote memory/documents, migration cutovers, or bulk repository hygiene.

## Lesson

Do not treat CC shadow-review as background commentary while the main agent races ahead. If CC is reviewing safety guards, its review is a gate. Execute destructive steps only after either:

1. CC has returned a clear `no blockers` / `safe to proceed`, or
2. the destructive command itself has independent hard guards that make later CC findings recoverable.

## Required sequence

1. **Prepare context for CC**
   - State the exact destructive action.
   - State what is forbidden (e.g. `do not delete Supermemory docs`).
   - Ask CC to review the script/guards before deletion.

2. **Build a script with hard gates**
   - Dry-run remote changes by default.
   - Full local archive before local deletion.
   - Archive integrity check (`tar -tf`, `zstd -t`, member counts).
   - Stable-source coverage check (prefer immutable L0/log source over moving derived L1 stores).
   - Manifest paths for every candidate and orphan.

3. **Wait for CC before destructive action**
   - Poll using the normal `📡 CC Agent Team [Xmin]` template.
   - If CC reports any blocker, stop and reconcile before deletion.

4. **If main agent already executed**
   - Immediately verify recoverability from archive.
   - Recompute the invariant using stable sources.
   - Adopt CC’s better invariant if it finds one.
   - Report the race honestly and show evidence that no data was lost.

## Stable invariant example

For Event Bridge markdown cleanup, `md event_id ∈ audit store` was insufficient because the audit store was moving while the daemon was catching up. The stable check was:

```text
md event_id ∈ (all profile L0 empire-thread.jsonl event_ids ∪ orphan salvage event_ids)
```

Then verify:

- archive md count equals pre-delete md count
- uncovered md ids = 0
- remote deletion performed = false for dry-run tasks
- qmd index refreshed after vault deletion

## Pitfalls

- **Moving target guard**: derived stores such as audit/backfill may change during cleanup. Use source logs or archive manifests for deletion gates.
- **Partial remote scope**: container/tag routing may split data across multiple containers. Dry-run all mapped containers before judging coverage.
- **Scoped git add**: cleanup sessions often leave `.hermes/`, `.claude/`, `output/`, or generated reports in the repo. Never use `git add -A`; stage only the files belonging to the code change.
