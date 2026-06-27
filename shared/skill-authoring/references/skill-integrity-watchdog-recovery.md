# Skill Integrity Watchdog Recovery Pattern

Use this reference when `skill-integrity-watchdog` reports profile-local shadows, missing pool skills, or baseline drift across Hermes profiles.

## Durable lesson

Fix the *source of regeneration*, not just the visible shadow directory. In multi-profile Hermes setups, profile-local `skills/` entries can be recreated by a runtime `skills_sync.py` imported from the active venv, even when the repo copy has already been fixed.

## Recovery workflow

1. **Read the watchdog output literally**
   - `real-dir skill '<name>' shadows external pool skill` means the profile-local entry must disappear.
   - Converting it to a symlink is still shadowing and still creates `skill_view()` ambiguity.

2. **Find the creator, not only the artifact**
   - Check profile-local shadow timestamps.
   - Compare repo `tools/skills_sync.py` with the runtime import path, commonly:
     - `~/.hermes/hermes-agent/venv/lib/python*/site-packages/tools/skills_sync.py`
   - If the runtime version lacks current skip/opt-out logic, patch/replace the runtime copy or reinstall the package; deleting shadows alone will not persist.

3. **Use profile opt-out for external-pool profiles**
   - For profiles that load shared skills via `external_dirs`, create a marker such as `.no-bundled-skills` if supported by the current syncer.
   - Verify `sync_skills()` reports the opt-out path, e.g. `skipped_opt_out: True`.

4. **Delete profile-local shadows**
   - Remove only the local duplicate entry under the profile's `skills/` directory.
   - Keep the shared pool copy intact.
   - After deletion, verify `skill_view(<name>)` no longer returns ambiguous matches.

5. **Handle missing baseline skills by restoration, not blind baseline shrink**
   - If watchdog says a skill disappeared from the pool, search other active profiles/lane profiles for surviving copies.
   - Compare file counts and hashes; restore the most complete copy to the shared pool.
   - Only update the baseline after confirming the disappearance is intentional or after restoring the pool.

6. **Verify both local and cron paths**
   - Run the watchdog script locally and require exit 0.
   - Trigger or wait for the cron job and verify `last_status: ok`.

## Pitfalls

- **Updated wrong baseline file — deprecated `.skill_baseline.json` vs active `.skill-watchdog-baseline.json`** 🆕: The watchdog reads from `~/.hermes/.skill-watchdog-baseline.json` (line 90 of the script). An older deprecated file `cron-worker/scripts/.skill_baseline.json` exists but is NOT read by the watchdog. If you update the deprecated file, the watchdog will keep reporting the same alert. **Fix**: always use `--update-baseline` via the script itself: `HERMES_HOME=~/.hermes python3 .../skill-integrity-watchdog.py --update-baseline`. Alternatively, pass `--baseline /path/to/.skill-watchdog-baseline.json` to explicitly target the active file. Case: 2026-06-06 — `dingtalk-local-decrypt` reported 2x because `cron-worker/scripts/.skill_baseline.json` was patched instead of `~/.hermes/.skill-watchdog-baseline.json`.
- **Repo fixed, runtime still stale**: Hermes may import `skills_sync.py` from the venv site-packages, not the repo checkout.
- **Baseline update can hide data loss**: never update the baseline before checking whether a missing pool skill has recoverable copies elsewhere.
- **Identical local duplicate still hurts**: even if a profile-local skill is byte-identical to the shared pool copy, it can break `skill_view()` by creating ambiguous skill names.
- **One-time cleanup is not a root fix**: if sync still writes bundled/local skills into an external-pool profile, shadows will recur on next profile load.

## Session case study

2026-06-04: `calendar-manager` and `cron-worker` shadows repeatedly reappeared in `cron-worker` and `regent`. Root cause was stale runtime `venv/.../tools/skills_sync.py` lacking `.no-bundled-skills` opt-out support. Fix: update runtime syncer from repo, create `.no-bundled-skills` markers, delete profile-local shadows, restore missing `openai-compatible-model-evaluation` from the most complete lane profile copy, then verify watchdog local exit 0 and cron `last_status: ok`.
