# v4.1.0 CQI反审：同版本号分叉与“测A跑B”

Use when auditing, maintaining, or invoking `claude-code` after a CQI/quality incident. This is session-specific evidence distilled into reusable checks; do not copy this wholesale into the main skill unless implementing a proper fix.

## Trigger

A 2026-06-01 CC agent-team反审 found that the runtime `claude-code` skill and its source repo copy both claimed `version: 4.1.0` but were not the same file.

## Durable lessons

1. **Measure the runtime copy, not only the repo source.** A CQI scorecard that reads the repo while Hermes loads `~/.hermes/skills/...` is “测A跑B”.
2. **Same version must imply same content hash.** If two deployed/source copies share a version but differ by hash/line count, mark the version unhealthy before any further content patch.
3. **Do not patch only the deployed copy during a divergence incident.** Pick a single truth source, reconcile, then bump version (e.g. `4.1.1`). Single-side hotfixes deepen the fork.
4. **Avoid adding more MUSTs as a first response.** If the failure was Execution Lapse or missing harness automation, add cron/hook/Gate/logging support rather than increasing instruction density.
5. **CC agent-team summaries need artifact checks.** Treat “completed” as untrusted until file paths, line counts, hashes, or `find -newer` evidence are verified.

## Reusable audit checklist

```bash
SRC=/Users/alexcai/code/jz-skills/hermes/claude-code/SKILL.md
DEP=/Users/alexcai/.hermes/skills/autonomous-ai-agents/claude-code/SKILL.md
wc -l "$SRC" "$DEP"
md5 "$SRC" "$DEP"
diff -q "$SRC" "$DEP" || true
grep -n '^version:' "$SRC" "$DEP"
grep -n 'Surrogate Verifier\|★30\|#29' "$DEP" references/common-pitfalls.md 2>/dev/null || true
```

## CQI writeback pattern

- Record the incident in the CQI plan as an event, not as a silent rewrite.
- Add a Phase 0 “emergency calibration” before normal roadmap work.
- Explicitly list “requires user intervention” items: monitoring continuity, max-effort thought-time protection, cross-skill spec transmission, plan-approval gates, session close confirmation, memory sync, and version drift.
- State a pause rule: “No single-side deployed patch until source/runtime truth is reconciled.”

## What not to save as a rule

- Do not claim that a specific path is always missing or that a tool is broken.
- Do not freeze transient line counts as future truth; re-measure each time.
- Do not turn every incident detail into a new red-line rule. Use references + automation first.
