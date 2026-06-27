# Runtime-grounded CQI audits for skills

Use this when a skill has a CQI plan, version scorecard, deployment sync process, or multi-profile copies. The core lesson: audit the skill copy that agents actually load, not only the source repo.

## Problem pattern: “测A跑B”

A skill CQI report may look healthy if it measures the repository source while Hermes actually loads a different deployed copy. If the two copies share the same `version:` but differ by hash or line count, every downstream scorecard is suspect.

## Required checks before declaring a skill healthy

1. **Identify runtime path** — the path returned by `skill_view()` / the active profile, e.g. `~/.hermes/skills/...` or `~/.hermes/profiles/<profile>/skills/...`.
2. **Identify source path** — the repo or canonical skill library copy, if any.
3. **Compare version + hash + line count** — same version with different content is a high-severity CQI event.
4. **Score the runtime copy** — progressive disclosure, body line count, pitfall hygiene, references, and checklist must be measured on what the agent actually reads.
5. **Only then patch** — if runtime/source diverge, reconcile first and bump version. Do not hotfix only one side.

## Minimal command pattern

```bash
SRC=/path/to/repo/skill/SKILL.md
DEP=/path/to/runtime/skill/SKILL.md
wc -l "$SRC" "$DEP"
md5 "$SRC" "$DEP"  # macOS; use md5sum on Linux
diff -q "$SRC" "$DEP" || true
grep -n '^version:' "$SRC" "$DEP"
```

## CQI plan update pattern

When a divergence is found:

- Append an incident entry; do not overwrite the previous plan history.
- Add a Phase 0 calibration section before automation roadmap items.
- Mark prior “all green” scorecards as superseded if they measured the wrong artifact.
- Separate **Execution Lapse** from **Skill Defect** before changing SKILL.md.
- Prefer automation/harness fixes for monitoring, drift detection, session cleanup, and artifact verification; avoid reflexively adding more MUST rules.

## Evidence to preserve in `references/`

- Paths compared.
- Runtime/source line counts and hashes.
- Version strings.
- Which scorecard dimensions changed after measuring the runtime copy.
- User-intervention points that automation should eliminate.
