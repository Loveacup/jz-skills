---
name: skill-authoring
description: Guides creating, auditing, importing, slimming, and revising reusable Agent Skills. Use when a task changes a skill's trigger, instructions, references, source/canonical relationship, or release path. Applies progressive disclosure, behavior contracts, risk-tier verification, and controlled deployment. Do not use for general documentation, one-off tasks, or automatic publication/deployment.
type: routine
version: 4.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skill-authoring, behavior-contracts, progressive-disclosure, governance]
    related_skills: [skill-creator, grill-with-docs]
---

# Skill Authoring

Build the smallest reusable instruction surface that produces the intended behavior and can be checked against observable evidence.

## Core contract

- **Behavior before ceremony.** Every instruction protects an observable outcome, boundary, or failure mode. Do not require a scorecard, warning table, checklist shape, line position, or fixed test count unless the skill's actual risk calls for it.
- **Progressive disclosure by need.** Keep the common execution path in `SKILL.md`. Put audience-, environment-, history-, and recovery-specific material in references with an explicit load condition.
- **One active authority per plane.** Source, canonical pool, runtime entry, and published repository are separate states. Compare them before merging; never treat recency, version text, or file count as authority.
- **External writes are separate actions.** Preparing a skill does not authorize commit, push, runtime deployment, profile sync, baseline changes, or deletion. Execute only the explicitly authorized named target.
- **Evidence follows risk.** Small wording edits need focused static checks. Behavior changes need scenario evidence. High-impact changes need a fresh independent verifier and safe execution evidence.

## Decide whether a skill is appropriate

Create or expand a skill when the capability is reusable, benefits from a stable trigger, and does not already have an owner. Otherwise improve the existing owner, put a narrow rule in the relevant project instructions, or handle the request directly.

Before asking the user, read the target skill, its owning rules, and available source/canonical records. Ask only for a decision the repository or task context cannot answer.

## Authoring flow

### 1. Define the behavior contract

Write down:

- the tasks that should and should not trigger the skill;
- the consumer-visible result;
- the boundaries and failure states that matter;
- the files and state planes in scope;
- the risk tier and proof needed for this change.

Descriptions are discovery contracts, not advertising. Use concrete task language and anti-triggers; avoid urgency, hype, and claims that the skill must always load.

### 2. Inspect ownership and current state

For an existing skill, compare the relevant source, canonical, and runtime copies before editing. Preserve local or runtime-only material until it is classified as active portable guidance, host-specific operations, historical evidence, generated output, or obsolete content.

When a runtime copy is richer, perform a component-level semantic merge. Do not whole-copy the richest or newest tree. Back up each changed file, keep unrelated dirty work untouched, and update only the reviewed mirror files.

For centralized SkillHub work, read `references/agent-skillhub-context-map.md` only when a governance/config/ledger decision is actually involved. It is a router, not a mandatory pre-read list.

### 3. Draft the common path

Keep generally applicable decisions in the body:

- when to invoke;
- the main branch or procedure;
- non-negotiable safety boundaries;
- the evidence required before reporting success.

Move conditional depth to references. A body is too large when an ordinary task must hold unrelated modes, environments, history, or recovery procedures at once—not when it crosses an arbitrary line count.

Use examples only where a format, precedence rule, or decision branch would otherwise be ambiguous. Use directive language for required behavior, but reserve `MUST` for genuine safety or correctness boundaries.

### 4. Harden only demonstrated risks

Add a warning, checklist item, script, or example only when it closes a plausible bypass or observed failure. Prefer a positive executable instruction over a prohibition. Merge repeated rules and remove ceremony that does not change behavior.

For format-sensitive output, show the contract. For tool-heavy or security-sensitive work, prefer mechanical checks over prompt-only claims.

### 5. Verify by risk

| Risk tier | Typical change | Required evidence |
|---|---|---|
| Low | wording, descriptions, reference pointers, historical clarification with no behavior change | focused reread, link/path resolution, and mirror comparison when applicable |
| Medium | trigger routing, workflow order, output contract, tool selection, or error handling | realistic changed-path scenarios, including relevant positive and negative cases; use a fresh context when invocation or instruction following is at issue |
| High | security boundary, destructive action, external publication, runtime mutation, cross-profile behavior, or orchestration policy | isolated safe execution plus a fresh independent agent reviewing the original acceptance contract and current artifact; unresolved evidence blocks acceptance |

Choose cases from the changed behavior rather than filling a quota. Reuse unaffected evidence; repeat checks only after a new edit, a failure, or an unresolved risk.

A fresh review is not permission to deploy. Test a candidate in an isolated copy or non-production target unless the user separately authorized a named runtime mutation.

### 6. Classify failures before revising

| Failure | Evidence | Response |
|---|---|---|
| Discovery | the skill did not load for an in-scope request | refine trigger and anti-trigger language |
| Comprehension | it loaded but the contract was misread | simplify the implicated instruction or add one clarifying example |
| Contract defect | the skill prescribed wrong or incomplete behavior | correct only the affected contract |
| Execution lapse | the contract was correct but not followed | improve salience or enforcement; do not rewrite unrelated guidance |
| Capability/environment | the contract was followed but the tool or environment could not perform it | fix the procedure, capability, or declared prerequisite |

Do not turn one failure into a whole-skill rewrite. Direct user correction is evidence and may be acted on immediately; repeated telemetry is useful when the signal is ambiguous.

## Source, privacy, and release boundaries

- Treat an upstream update as a proposal. Preserve richer local content through semantic review rather than source-blind overwrite.
- Keep private paths, credentials, personal identifiers, runtime state, caches, and generated evidence out of portable/public skill sources. Scan the complete intended publication set, not only `SKILL.md`.
- Import/preparation, canonical application, runtime exposure, publication, and retirement are distinct actions. Report which state was actually reached.
- A dry run or plan does not authorize apply. A request to import, audit, or prepare does not imply commit or push.
- Deploy only to explicitly named targets. Do not broaden to every profile/platform, use blanket sync, run `rsync --delete`, change a watchdog baseline, or remove an old entry without separate scope and authorization.
- If required evidence is unavailable, mark the affected claim `BLOCKED`. Independent downstream work may continue only when it does not rely on that claim.
- A timeout is missing evidence, not proof that a reviewer or writer stopped. Before replacing a worker on the same mutable scope, obtain process-exit or lock/lease-release evidence; never create overlapping writers.

Read `references/deployment.md` for preparation/publication/deployment state gates. Use `references/desensitization-audit.md` when material may become public. Use `references/repo-import-profile-local-and-staged-audit.md` for profile-local sources or dirty repositories.

## Conditional reference routing

| Situation | Read |
|---|---|
| Centralized SkillHub config, ledger, pool, runtime exposure, or Obsidian writeback | `references/agent-skillhub-context-map.md`, then the applicable section of `references/agent-skillhub-workflow.md` |
| Publication or named-target deployment | `references/deployment.md` |
| Profile-local runtime source or unrelated dirty repository state | `references/repo-import-profile-local-and-staged-audit.md` |
| Public-source privacy review | `references/desensitization-audit.md` |
| Runtime/canonical divergence or same-version mismatch | `references/runtime-grounded-cqi-audit.md` |
| High-impact independent/adversarial review | `references/dual-role-patterns.md` |
| Failure-driven evolution research | `references/skill-evolution-research.md` |
| External capability absorption | `references/absorption-analysis.md` |

Historical case studies and research references are evidence, not automatically active procedure.

## Before returning

- The trigger, anti-trigger, result, boundaries, risk tier, and proof are explicit.
- The body contains the common path; conditional detail has a load condition.
- Every reference named by the root exists in the changed mirrors.
- Source/canonical/runtime states are reported accurately; no unverified consumer claim is presented as passed.
- No commit, push, deployment, blanket sync, deletion, or baseline mutation was inferred from preparation work.
- Medium/high behavior changes have the risk-appropriate scenario evidence; high-impact acceptance has a fresh independent verdict.

If an item is false, fix it or report the precise blocked claim and evidence gap.

> Change history: `references/changelog.md`
