# Research and Design Notes

Load this reference only to understand the design rationale, compare a documented historical failure, or investigate evidence that the active workflows do not explain. These notes are attributable but non-normative: they do not add gates, authorize actions, or override `SKILL.md` and the task-specific workflows.

## Current model guidance

OpenAI's [Using GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra) says newer models can be more sensitive to instructions in skills and repository guidance. It recommends auditing accessible instructions for conflicts, stating desired initiative and completion boundaries, specifying delegation when an application depends on it, and matching verification effort to the change rather than automatically repeating broad tests. The guide also distinguishes routine work that can proceed from material decisions that need user input.

This supports a small router, explicit task ownership, proportional evidence, and continued work inside already authorized scope. It does not establish behavior for every model or runtime, and example prompts in the guide are not security enforcement.

Eric Provencher's [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) on the OpenAI Developers blog (announced in his [post](https://x.com/pvncher/status/2095991462416490862)) argues that accumulated skills, overlapping descriptions, and elaborate recipes can make discovery and execution worse as model behavior changes. It recommends short descriptions with concrete task boundaries, progressive disclosure for conditional workflows, periodic removal of instructions that no longer earn their context cost, and completion boundaries that match the user's intended stopping point. Three points the earlier post capture did not state: a consumer with many skills shortens descriptions to fit, so the deciding clause must come first; strong ask-first wording added to rein in an earlier model can make a better-aligned model stop where the user wanted it to continue, and the remedy is a scoped permission grant with its safety basis stated; a newer model can be more tentative about stopping, so completion must be defined rather than left to a "stop for review after the first pass" default.

Its three illustrations are reproduced as distinctions, not required wording: the migration-description pair in [Author](author.md#make-the-skill-discoverable), the contextual document-pointer pair and the disposable-test-suite grant in [Agent instructions](agent-instructions.md#revise-the-implicated-guidance).

That article is practitioner guidance written against Codex and GPT-6 Astra, not an evaluation result. This family adopts its testable design ideas—precise discovery, conditional loading, fewer simultaneous obligations, explicit completion—without treating model-specific observations, popularity signals, or prescriptive size limits as proof.

## Source-to-governance mapping

The two sources above remain direct references for [collection governance](collection-governance.md) and [agent instruction governance](agent-instructions.md). They motivate the following design choices; the workflows specify how to test them. Reading these sources is optional during an ordinary governance run, not a mandatory network preflight.

| Source and section | Source claim | Governance application and limit |
|---|---|---|
| OpenAI guide, “Instruction following” | Accessible skill and repository instructions can create conflicts or premature stopping; identify the exact instruction behind a pause. | Quote the implicated rule, its owner and scope. Distinguish an explicit requirement from the agent's interpretation. Do not invent a host-independent precedence order. |
| Provencher article, “Better skills” | Descriptions compete in shared discovery context and get truncated when many are exposed; overbroad triggers and elaborate recipes can be counterproductive. | Evaluate a named collection's exposed descriptions together, including rejection cases, using the text as actually shown. A file on disk is not proof it was exposed; character totals are not token counts or measured session cost. |
| Provencher article, cross-model paragraph; OpenAI model-specific guidance | Repository skills guide other contributors' agents on other models; a constraint that helps one model can overconstrain another. | Keep portable constraints separate from demonstrated host/model adjustments; record the reason for a model-compensating rule; measure with the named consumer before claiming transfer or improvement. |
| Provencher article, “Up-to-date AGENTS.md” | Always-on preparation is disproportionate to a small task; contextual pointers remain useful only while their targets are current; encouragement to test written for an earlier model causes repeated tests now. | Separate broadly applicable constraints from conditional procedures. Preserve required repository checks and operational knowledge when relocating rules; a stale pointer target is its own finding. Do not convert proportionality into “never test.” |
| Provencher article, “Decision boundaries” and “Persistence”; OpenAI guide, initiative | Ambiguous ask-first and stopping rules interrupt intended completion; a newer model may take boundary language more seriously. | Classify ask-first rules by origin: keep real boundaries, convert compensation for an earlier model into a scoped grant with its safety basis. Define completion before starting; retain explicit approvals for consequential actions. Model initiative is not a grant of user permission. |

The official guide was re-fetched on 2026-09-22 and matched the earlier captured body. The blog article was fetched on 2026-10-20 and supersedes the earlier post capture. These are provenance observations, not proof of later source freshness or of a universal model behavior.

## Decision-design rationale

The user supplied a visual series on investigation, context selection, concrete task analysis, priority, practice-based verification, and avoiding rule accumulation. Its five-stage loop (understand, focus, act, verify, learn) and ten-module outline are design prompts, not a mandatory output format or evidence of improved model performance. The images' attribution of ideas to historical thinkers and model practitioners has not been independently verified here; no claim about their original authorship is required by the workflow.

The [agent-instruction workflow](agent-instructions.md) adopts targeted investigation, explicit decision branches, relevant counterevidence, task-specific routing, observable completion, and selective learning. It rejects a single priority ladder that could put goals above mandatory constraints, a universal ranking of documents over observations, indiscriminate context collection, and automatic memory/rule writes after every task. Stable facts, exact commands, hard prohibitions, and required checks remain valid direct instructions when their scope earns the context cost.

Official documentation read on 2026-10-13 supports narrower claims:

- [Codex AGENTS.md discovery](https://developers.openai.com/codex/guides/agents-md) describes Codex-specific scope, file discovery and instruction-chain rebuilding. This supports checking the named consumer, not copying its resolution rules into every host.
- [Codex customization](https://developers.openai.com/codex/concepts/customization) distinguishes persistent project guidance, reusable skills and tools, and recommends a small relevant instruction surface. Its feedback suggestions are not authorization to add schedules, install hooks, or change every instruction file.
- [Claude Code memory](https://code.claude.com/docs/en/memory) distinguishes instruction context from enforced configuration and explains that imported files expand at startup. Splitting a document therefore does not itself reduce always-loaded context; conditional disclosure must be checked through the actual loading mechanism.

The research retrieval returned usable body excerpts but marked completeness unknown or truncated (`degraded`). These claims are limited to the retrieved sections; no full-document audit, installed-version compatibility, or cross-host runtime validation is implied. Original/revised artifact scenarios decide this change's bounded behavior, not source popularity or philosophical analogy. Do not make these external reads a prerequisite for ordinary skill use.

## Transferable lessons from historical cases

The prior skill-authoring material recorded useful failures even where its procedures became obsolete:

- A valid body can be silently bypassed when the description overlaps another owner or the runtime does not expose the intended entry. Evaluate discovery separately from body quality.
- A failed run can be an omitted instruction, confusing contract, actual contract defect, execution lapse, or environment failure. Changing correct prose does not repair a broken consumer or unavailable capability.
- Progressive disclosure fails when conditional modes, platform details, and recovery material drift back into the always-loaded root. Trace the common task path and move only genuine conditional depth.
- A design document, version label, scorecard, hash, or source-side test does not prove runtime integration. Observe the artifact and consumer named by the claim.
- Cross-plane replacement can erase legitimate runtime or private adaptations. Classify differences semantically and keep release authority separate from preparation.
- Historical cleanup can resurrect through generators, mappings, or consumers. Retirement requires its own inventory, authorization, and proof rather than a broad delete.

These are diagnostic hypotheses until the current artifact or runtime supplies evidence. They do not require a fixed number of scenarios, reflections, reviewers, or research passes.

## SROF design concepts worth retaining

The historical Skill Runtime Orchestration Framework documents were designs, not demonstrated deployed infrastructure. Several concepts remain useful when a real executable skill presents the corresponding problem:

- Provisioning an environment and deciding whether a particular action may run are different lifecycles and can require different state and authority.
- Observers should report facts, actuators should change state, and the decision owner should interpret evidence and authorization. A check that cannot determine an answer must not be presented as a pass.
- Cached state records prior work; it is not current-world proof. Cheap, side-effect-free observations can re-establish facts when the claim depends on them.
- Verification of a mutating action should inspect captured results or an idempotent status interface, not repeat the mutation.
- Secrets should travel through a controlled non-transcript channel when the substrate provides one; skill prose alone cannot guarantee secrecy.

Do not infer that the proposed manifests, gates, state machines, background jobs, or integrations exist. Introduce no orchestration framework, recurring job, log store, or quality system unless a separate task establishes the need, implementation surface, and authorization.

## Historical preservation

The prior public source is recoverable from repository history at commit `862dc7a1d96f12a539ba530a7ed3b97ad9978ed1`. The complete pre-refactor payload is also retained in a dated private audit backup. The backup is evidence, not an active workflow, and its private location is intentionally absent from public source. Transferable capability is summarized here; obsolete scorecards, quotas, implicit publication steps, environment-specific paths, and unverified deployment claims are not reactivated.