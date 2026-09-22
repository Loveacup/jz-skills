# Research and Design Notes

Load this reference only to understand the design rationale, compare a documented historical failure, or investigate evidence that the active workflows do not explain. These notes are attributable but non-normative: they do not add gates, authorize actions, or override `SKILL.md` and the task-specific workflows.

## Current model guidance

OpenAI's [Using GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra) says newer models can be more sensitive to instructions in skills and repository guidance. It recommends auditing accessible instructions for conflicts, stating desired initiative and completion boundaries, specifying delegation when an application depends on it, and matching verification effort to the change rather than automatically repeating broad tests. The guide also distinguishes routine work that can proceed from material decisions that need user input.

This supports a small router, explicit task ownership, proportional evidence, and continued work inside already authorized scope. It does not establish behavior for every model or runtime, and example prompts in the guide are not security enforcement.

Eric Provencher's [post on skill files and agent instructions](https://x.com/pvncher/status/2095991462416490862) argues that accumulated skills, overlapping descriptions, and elaborate recipes can make discovery and execution worse as model behavior changes. It recommends short descriptions with concrete task boundaries, progressive disclosure for conditional workflows, periodic removal of instructions that no longer earn their context cost, and completion boundaries that match the user's intended stopping point.

That post is practitioner guidance, not an evaluation result. This refactor adopts its testable design ideas—precise discovery, conditional loading, and fewer simultaneous obligations—without treating model-specific observations, popularity signals, or prescriptive size limits as proof.

## Source-to-governance mapping

The two sources above remain direct references for [collection governance](collection-governance.md) and [agent instruction governance](agent-instructions.md). They motivate the following design choices; the workflows specify how to test them. Reading these sources is optional during an ordinary governance run, not a mandatory network preflight.

| Source and section | Source claim | Governance application and limit |
|---|---|---|
| OpenAI guide, “Instruction following” | Accessible skill and repository instructions can create conflicts or premature stopping; identify the exact instruction behind a pause. | Quote the implicated rule, its owner and scope. Distinguish an explicit requirement from the agent's interpretation. Do not invent a host-independent precedence order. |
| Provencher post, “Skill files” | Descriptions compete in shared discovery context; overbroad triggers and elaborate recipes can be counterproductive. | Evaluate a named collection's exposed descriptions together, including rejection cases. A file on disk is not proof it was exposed; character totals are not token counts or measured session cost. |
| Provencher post, “AGENTS.md” | Always-on preparation can be disproportionate to a small task; contextual references remain useful. | Separate broadly applicable constraints from conditional procedures. Preserve required repository checks and operational knowledge when relocating rules. |
| Both sources, initiative / decision boundaries / persistence | Ambiguous ask-first and stopping rules can interrupt intended completion. | Clarify the authorized workflow and its completion evidence; retain explicit approvals for consequential actions. Model initiative is not a grant of user permission. |
| OpenAI guide, “Testing and verification”; Provencher post, “AGENTS.md” | Verification can exceed what a small change needs. | Test the affected behavior and preserve target-required checks; broaden only for a new change, failure or unresolved risk. Do not convert this into “never test.” |
| Provencher post, cross-model discussion; OpenAI model-specific guidance | Instructions affect models differently. | Keep portable constraints separate from demonstrated host/model adjustments; measure with the named consumer before claiming transfer or improvement. |

The official guide was re-fetched on 2026-09-22 and matched the earlier captured body. The post was re-read from its complete previously captured text; its live content was not re-fetched for this extension. These are provenance observations, not proof of later source freshness or of a universal model behavior.

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