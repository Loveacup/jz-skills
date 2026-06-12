# Cross-substrate audit + review loop

Use this when a real Kanban task validates one execution substrate and a different review substrate, especially for vault/doc audits.

## Pattern

1. **Implementation card** runs the production task on the substrate being validated (for example `cccmux/cmux`).
2. **Review child card** uses an independent substrate/profile (for example `regent` + `claude-code/tmux`, or a direct Hermes review if CC is unavailable) and must answer an adversarial prompt.
3. If review returns `request changes`, create a **bounded follow-up implementation card** linked from the review card. Do not rerun the original parent with vague instructions.
4. Create a second review child for the follow-up. Close the chain only when the latest review passes.
5. Backfill the mother design/CQI doc with both the failed review finding and the final pass; the request-changes turn is the learning signal.

## What the review should attack

- **Scope fork**: the requested path or target may be stale or ambiguous. Verify current filesystem/source of truth, not just the card prose. If exact path is missing, enumerate plausible candidates and require explicit resolution or supplemental audit.
- **Parser/category false confidence**: a report can have correct file-level verdicts but wrong issue categories. Example: malformed YAML inline lists (`tags: [` or `aliases: [` without closing `]`) should be classified as YAML/list damage, not exploded into phantom bare tags.
- **Terminology drift**: labels such as `41-type enum` can be wrong even when the actual enum values are correct. Count and compare against the current source of truth.
- **Read-only claims**: do not rely on mtime alone. Cross-check script write targets, git diff/content changes, artifact paths, and any user-supplied concurrent-edit context.

## Profile/skill preflight

Before creating a review card with `skills=[...]`, verify that the **assignee profile** can see those skills (`hermes -p <profile> skills list` when available). If not, either:

- fix skill visibility before dispatch,
- omit nonessential `skills` and make the card body self-contained, or
- assign the review to a profile that actually has the required skills.

A crash due to `Unknown skill(s)` is a routing/config failure, not evidence about the reviewed artifact. If the retry completes without the skills, record that the review was skill-light and consider a later profile-visibility fix.

## Evidence bundle checklist

- implementation task id, review task id, follow-up task id(s)
- report paths + line/byte counts
- exact scanned scopes + file counts
- adversarial findings and final decision
- substrate metadata (`metadata.cc_lane.substrate` or equivalent)
- no-forbidden-writes evidence
