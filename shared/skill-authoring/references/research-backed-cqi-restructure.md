# Research-Backed CQI Restructure Pattern

Use this reference when restructuring a CQI plan or other skill-governance document using current research plus deployment evidence. Captured from the SA CQI rewrite session (2026-06-01).

## When to use

- User asks to improve a skill/CQI plan's theoretical foundation with papers.
- A plan has drifted from live infrastructure (cron/kanban/A2A/logs already exist but the document treats them as future work).
- A document needs restructuring, not just a small patch.

## Pattern

1. **Treat this as execution, not discussion, if user says “重构/修改/完善”.**
   - Read the target file and related references first.
   - Confirm whether design docs describe current state or aspirational state before citing them as fact.

2. **Build a live-state baseline before rewriting.**
   - Check existing orchestration/logging substrate: cron jobs, kanban/audit logs, A2A registry, inspection/health checks, sync scripts, source-of-truth repository.
   - Separate “already production” from “future MVP” so the rewrite does not invent a duplicate orchestration layer.

3. **For large research extracts, split before analysis.**
   - Web/Exa outputs may arrive as one huge JSON or markdown blob. Parse/split it into `/tmp/<topic>-papers/NN-name.md` before agent review.
   - Preserve source identifiers (title, URL/arXiv ID) at the top of each split file.

4. **Use concern-based CC agent teams for theory-to-plan synthesis.**
   - Better split by concern than by file when rewriting: paper mechanisms, infrastructure baseline, orchestration routing, future extension points.
   - Ask each worker for: actionable mechanisms, evidence level (`[C] confirmed` vs `[I] inference`), risks/limits, and concrete sections to alter.

5. **Synthesize into an explicit theory → loop mapping.**
   - For each CQI stage, map: observation/logging → evidence extraction → diagnosis → bounded edit → validation gate → deployment audit → evolution log.
   - Mark paper-backed claims as `[C]` and local design extrapolations as `[I]`.

6. **Promote user “notes” into decisions.**
   - If the user adds requirements in stray lines, convert them into formal decisions with: decision, owner, acceptance criteria, and roadmap position.

7. **Verify the rewritten document mechanically.**
   - `wc -l` for size.
   - grep for required paper names, target version, platform terms, and defect codes.
   - Check IDs that are easy to mix up (e.g. arXiv IDs).
   - If the target directory/file is untracked, `git diff` will be empty; use `git status --short` and `git diff --no-index <backup> <new>` or an explicit before/after copy for objective diff evidence.

8. **Avoid accidental post-completion execution in CC.**
   - After CC final report, clear any text accidentally sitting in the prompt line or kill the tmux session if no further task is intended.
   - Do not let CC execute a suggestion that appeared in its own “next steps” unless the user explicitly approved it.

## Output shape for rewritten CQI plans

Recommended sections:

- TL;DR and scope boundary
- `§0` Current-state baseline and design decisions
- `§1` Theory foundation / paper matrix
- `§2` Defect model and pattern library alignment
- `§3` CQI loop architecture
- `§4` Orchestration / routing table
- `§5` Roadmap and logs
- `§6` Acceptance criteria and risks
- Appendices for references and local file links

## Pitfalls

- **Paper ID drift:** worker agents may confuse closely named papers. Keep a task-level source map and verify final IDs by grep.
- **False “not implemented” baseline:** a plan can be stale even if the system already has cron/kanban/A2A/logging. Always inspect live state.
- **Diff blind spot:** untracked Obsidian plan directories make normal `git diff` empty. Report this as tracking state, not as “no changes”.
- **Overcoupled future modules:** reserve extension points as data fields or placeholder sections; avoid imports/symlinks to unpublished core modules.
