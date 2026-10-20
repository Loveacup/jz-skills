# Core Requirements

Read this before changing this skill's trigger, instructions, or bundled behavior. Each requirement is what the skill must keep delivering regardless of layout or wording. A change is in scope when it serves one of these; a change that weakens one needs the user's explicit decision, recorded in the [changelog](./changelog.md).

A behavior change (trigger, instructions, bundled behavior; not a wording-only edit) ends with a changelog entry stating what it improved, preserved and how that was confirmed, citing the affected IDs, and updates this file only when a requirement was added, narrowed or retired. Full rule: [Author](author.md#keep-the-skill-traceable).

| ID | Requirement | Owner |
|---|---|---|
| CR01 | Discovery is precise: a skill's name and description select it for its task and reject neighboring tasks, with the deciding clause first so truncation does not remove it. | [Author](author.md#make-the-skill-discoverable), [Collection governance](collection-governance.md) |
| CR02 | Progressive disclosure: the entrypoint carries the common direction; specialist depth sits behind links that say when it helps; no mandatory index chains, and a split that still eagerly loads everything does not count. | `SKILL.md`, [Author](author.md#organize-around-use) |
| CR03 | Instructions supply expertise and decision cues the agent cannot infer, not itineraries of ordinary steps; portable behavior is separated from model- or host-compensating rules, which carry their reason or live in an adapter. | `SKILL.md`, [Author](author.md#give-direction-and-usable-knowledge) |
| CR04 | Completion is defined: result, checks that count, stopping point. Work continues through the authorized scope; a review pause is added only where a material decision sits. | `SKILL.md`, [Agent instructions](agent-instructions.md#revise-the-implicated-guidance) |
| CR05 | Verification is proportional to the change and preserves the target project's required checks; no line ceilings, scorecards, scenario quotas, or test quotas act as gates. | [Evaluate](evaluate.md) |
| CR06 | Preparation, canonical application, runtime deployment, publication, and retirement are separate claims with separate authorization; none implies another. | [Release](release.md), [Import](import.md) |
| CR07 | Authority is never chosen by version, recency, apparent richness, or byte equality; disagreeing planes are merged semantically and legitimate private or runtime-only content is preserved. | [Import](import.md), [SkillHub](skillhub.md) |
| CR08 | Missing evidence leaves the claim blocked, not a low-confidence pass; no fallback returns a success-shaped result; independent judgment for high-impact changes. | [Evaluate](evaluate.md) |
| CR09 | Governance of a collection or instruction file revises only named targets, keeps real safety boundaries, and converts rules that merely compensated for an earlier model into scoped grants with a stated safety basis. | [Collection governance](collection-governance.md), [Agent instructions](agent-instructions.md) |
| CR10 | Every skill this workflow produces or revises carries its own core-requirements document and change history; behavior changes read the former first, record improved/preserved/confirmed in the latter, and update the requirements only when one changed. | [Author](author.md#keep-the-skill-traceable) |

Non-goals, kept here so they are not re-proposed: a new orchestration layer, registry, scoring system, mandatory PRD or plan file, fixed description length, or a universal instruction precedence order.
