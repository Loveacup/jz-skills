# Runtime-grounded CQI audits for skills

Use this when a skill has a CQI plan, version scorecard, deployment sync process, or multi-profile copies. The core lesson: audit the skill copy that agents actually load, not only the source repo.

## Problem pattern: “测A跑B”

A skill CQI report may look healthy if it measures the repository source while Hermes actually loads a different deployed copy. Matching version labels do not prove content identity; establish which artifact the evidence covers before applying its verdict.

## Required checks before declaring a skill healthy

1. **Identify runtime path** — the path returned by `skill_view()` / the active profile, e.g. `~/.hermes/skills/...` or `~/.hermes/profiles/<profile>/skills/...`.
2. **Identify source path** — the repo or canonical skill library copy, if any.
3. **Compare version and content hash** — classify each difference as an intended host/privacy adaptation, an authorized local change, or unresolved drift. Severity follows behavioral and safety impact, not a version/hash mismatch alone.
4. **Verify the runtime behavior** — use the root skill's risk tier and relevant scenarios against the artifact actually loaded. Line counts, scorecards, pitfall counts, and checklist shape are not acceptance gates.
5. **Reconcile only the authorized scope** — preserve legitimate plane-specific content, record intentional differences, and update each affected named mirror. Do not silently hotfix one side or deploy to additional profiles.

## Minimal command pattern

```bash
SRC=/path/to/repo/skill/SKILL.md
DEP=/path/to/runtime/skill/SKILL.md
# Hashes identify bytes; they do not grade quality or authorize synchronization.
md5 "$SRC" "$DEP"  # macOS; use md5sum on Linux
diff -q "$SRC" "$DEP" || true
grep -n '^version:' "$SRC" "$DEP"
```

## CQI plan update pattern

When a divergence is found:

- Record the relevant divergence, its classification, and its evidence without overwriting history.
- Add calibration to an existing plan only when that plan depends on the mismatched artifact.
- Supersede prior verdicts only where they measured the wrong artifact; reuse unaffected evidence.
- Separate **Execution Lapse** from **Skill Defect** before changing SKILL.md.
- Prefer automation/harness fixes for monitoring, drift detection, session cleanup, and artifact verification; avoid reflexively adding more MUST rules.

## Evidence to preserve in the authorized audit location

- Paths compared.
- Runtime/source hashes and intentional-difference classification.
- Version strings.
- Relevant behavior verdicts and evidence limits.
- User decisions that remain necessary; do not remove authorization boundaries.
