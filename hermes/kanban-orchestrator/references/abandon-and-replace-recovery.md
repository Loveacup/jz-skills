# Abandon-and-Replace Recovery Pattern

## Trigger
Multiple parallel engineer batches hit iteration budget exhaustion simultaneously. Example: 4 batches × 22 files, 3 of 4 fail with `Iteration budget exhausted (90/90)`.

## Anti-pattern: Repair-in-place
Unblocking and retrying the same tasks wastes time — they'll hit the same iteration ceiling. The partial state (workspace scripts, half-processed files) makes resumption fragile.

## Correct pattern: Abandon + Fresh Replacements

### Decision tree
```
Task blocked with "iteration budget exhausted"
├── Has comments with detailed results? → UNBLOCK (work done, just needs kanban_complete)
│   Example: T3b had full comment with 22-file processing log
│   Action: unblock → dispatch → worker calls kanban_complete in seconds
│
└── No comments OR empty workspace?
    ├── ARCHIVE the old task (don't reclaim, don't unblock)
    ├── CREATE fresh replacement with SMALLER batch
    └── Re-link dependencies (new task → same parents/children)
```

### Concrete example (2026-05-18 inbox processing)
```
Original:  T3a(22 files) + T3b(22) + T3c(22) + T3d(22)
Result:    T3a BLOCKED, T3b BLOCKED (work done), T3c BLOCKED, T3d DONE

Recovery:
  T3b → unblock (work done) → spawned → kanban_complete in seconds
  T3a → archive
  T3c → archive
  T3e(11 files) + T3f(11 files) → created fresh → immediate success

Why 11 not 22: 22 with Claude Code monitoring burned 90 iterations.
11 direct processing: ~35-55 tool calls, well within budget.
```

## When to use
- Multiple tasks in a parallel batch fail the same way
- Root cause is structural (batch too large), not transient (rate limit)
- Partial work exists but is too complex to resume
- Faster to start fresh than diagnose/resume partial state

## Emperor's rule
> "不修旧、开新路" — Don't fix the old, open a new path.

This applies especially when:
- Old tasks have messy partial state
- Multiple tasks failed simultaneously
- The fix involves structural changes (batch size, approach)
