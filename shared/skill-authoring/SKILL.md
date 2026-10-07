---
name: skill-authoring
description: Create, revise, import, or audit Agent Skills; govern a named skill collection or agent instruction files such as AGENTS.md. Not for ordinary coding or executing a skill's subject task.
type: routine
version: 5.1.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, progressive-disclosure, governance]
    related_skills: [skill-creator]
---

# Skill Authoring

Produce skills and agent instructions that are selected or applied to the right task, give useful guidance, and can be checked through their intended use. Optimize for fewer irrelevant instructions, not a line-count target.

## Choose the work

Start from the user's requested deliverable and the target's governing instructions. Reuse an existing skill when it already owns the capability. State the intended result and the few observable conditions that decide success; a separate plan or checklist file is not required.

**Wording-only correction:** edit the target text, check that its meaning and any affected links are intact, then finish. Do not load the workflows below or inspect all source/runtime copies unless the change actually depends on them.

For other work, load the matching workflow, not the whole table:

| Requested work | Read |
|---|---|
| Create a skill, change its trigger, instructions, or bundled behavior | [Author](references/author.md) |
| Review quality, diagnose a failure, or restructure an existing skill | [Evaluate](references/evaluate.md) |
| Audit or revise discovery and responsibility across a named skill collection | [Collection governance](references/collection-governance.md) |
| Audit or revise AGENTS.md, CLAUDE.md, or equivalent agent instruction files | [Agent instructions](references/agent-instructions.md) |
| Import upstream content or reconcile source/canonical/runtime differences | [Import](references/import.md) |
| Apply across planes, deploy, publish, rename, or retire an entry | [Release](references/release.md) |

A workflow may link a reference for a specific decision. Read it only when that condition is present. Local SkillHub ownership or metadata decisions use the [SkillHub adapter](references/skillhub.md); this is not a universal preflight. [Research notes](references/research-notes.md) explain the design and historical lessons, not additional execution requirements.

## Shared boundaries

- Continue through the requested deliverable and relevant verification within the already authorized scope. Ask only for a material decision that the task, files, or governing rules cannot settle; do not turn guideline interpretation into another approval gate.
- Preparing, importing, or reviewing does not itself authorize commit/push, runtime deployment, deletion, repointing, credentials, or baseline changes. Honor explicit named-target authorization without asking for it again. If blocked, identify the missing permission or evidence and the exact governing instruction.
- Preserve unrelated work and legitimate private/runtime-only content. Do not choose an authority by version, recency, apparent richness, or byte equality. Follow the import workflow when those planes disagree.
- Governance supports review and explicitly authorized revision of named targets. Reviewing a collection does not authorize changing every member, editing generated outputs, or overriding the host's instruction hierarchy. Read-only findings may continue when an affected write is blocked.
- Missing required evidence is `BLOCKED`, not a low-confidence pass. Only work independent of that missing result may continue. A timeout is not proof a worker stopped: before replacing a writer on the same scope, obtain exit or lock/lease-release evidence.

## Finish at the requested state

Deliver the actual artifact or requested review, not just a proposal to continue. Check the changed behavior proportionally and complete the target project's required checks. For high-impact security, orchestration, or release changes, use the independent-review branch of [Evaluate](references/evaluate.md).

Once relevant checks pass, broaden or repeat them only for a new change, failure, or unresolved risk. Report the result, evidence, and any consequential state boundary that remains unverified. File identity, model scenario success, runtime loading, and real task execution are different claims.

Version history and the previous layout: [changelog](references/changelog.md).
