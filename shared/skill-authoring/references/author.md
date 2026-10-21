# Author a skill

Use this guide when designing or substantially improving a skill. Treat it as a set of design questions, not mandatory phases or headings.

## Find the useful contribution

What recurring work is the user trying to improve? What would a good result look like? What does the agent lack: specialist knowledge, access to a tool, a reliable technique, or a particular workflow or preference?

Start with the existing skill, relevant artifacts and actual usage. A useful skill supplies something the model cannot reliably infer from the request alone. Familiar connective reasoning can stay with the model. Project-wide invariants belong in the project's instruction owner; one task's temporary details belong in that task. Improve an existing capability rather than creating a competing owner.

For a capability claim, an observed difficulty is a stronger starting point than an imagined checklist. A preference skill can be valuable even when the model already knows how to perform every step: its contribution is fidelity to the user's intended work.

## Investigate what changes the design

Use available research and retrieval capabilities to close consequential gaps. Local files and implementations reveal how the target actually works; official documentation establishes interfaces; community experience suggests practical failure modes; empirical studies can challenge an attractive generalization. Choose sources for the question, not to satisfy a source quota.

Follow a claim back to usable evidence. Distinguish tested behavior, documented contracts, practitioner experience and your own inference. Consider a simpler alternative and credible counterevidence. Stop investigating when further information would not change the next useful decision; reopen the question when execution reveals a new problem.

Keep stable expertise in the skill and give a retrieval lead for changing facts. A helpful lead says what to look up and why it matters, without hardcoding an unavailable tool, a stale model version or another runtime's infrastructure. Missing capabilities should lead to an honest limitation or a supported alternative, not invented results.

## Make the skill discoverable

The name and description help the consumer choose before reading the body. Describe the actual operation and result in ordinary user language, and lead with the operation and the moment it applies: consumers that expose many skills shorten descriptions to fit, so the deciding clause must survive truncation. Include an adjacent exclusion when it resolves a real collision. Workflow summaries, synonym piles and urgency usually weaken that signal and make the agent load guidance that does not help the task.

For example, `Create and validate Postgres schema migrations. Use when working with databases, queries, models, or persistence` activates for any database work; `Create and validate Postgres schema migrations. Use when adding or changing a migration, or reviewing its rollout` names the operation and the moment it applies. The example illustrates a distinction, not required wording.

Check the target consumer's actual frontmatter contract and preserve established metadata. Examples, licenses and platform claims should reflect the artifact, not plausible defaults. Use [collection guidance](collection-governance.md) if discovery depends on competing entries or aliases.

## Give direction and usable knowledge

A useful body usually explains:

- the result worth pursuing and the inputs that matter;
- domain knowledge, interfaces or techniques the agent would otherwise have to rediscover;
- choices that affect quality, including when a suggested method is unsuitable;
- how to inspect the resulting artifact and recognize consequential failure;
- what finished looks like—the artifact, the checks that count and where to stop—so the agent neither stops at a first draft nor keeps exploring past the intended result.

This is a design lens, not a required template. Keep exact commands, parameters, schemas and output conventions where their precision is necessary. Elsewhere, explain the mechanism and let the agent choose the method. If a preferred approach fails, support diagnosis and another approach that preserves the goal and requirements rather than prescribing blind repetition or lowering acceptance criteria.

For example, a document-extraction skill can explain how to recognize a missing text layer and find an OCR route, while preserving page coverage and source fidelity. It need not prescribe one tool sequence for every document. A payment or migration interface, by contrast, may need an exact guarded operation; autonomy does not turn authorization or required checks into suggestions.

Write for the task, not for one model. A shared skill guides every contributor's agent, and those agents run different models. A constraint that exists only to compensate for one model's past behavior—acting without permission, skipping checks, stopping early—belongs in that host's adapter or carries its reason inline, so a model without that weakness is not overconstrained by it.

Choose engineering from the actual use. A one-off analysis may need only a direct script; a personal tool usually needs a clear working path, not multi-tenant infrastructure. Shared services need the protections justified by their real exposure and commitments, not every possible safeguard. In each setting, preserve required behavior, authorization and data integrity. Reuse project capabilities, standard-library or native platform features, and installed dependencies when they fit; introduce a new mechanism to close a concrete gap, not to reach the end of a mandatory search ladder.

An instruction earns its place by supplying useful knowledge or changing a consequential decision. For a safeguard, explain what it detects and what rejection, recovery or diagnosis accomplishes. Do not infer value or waste from names such as checksum, retry or compatibility layer. Inspect an existing protection before narrowing it; lack of an explanation is not evidence it is useless. Reduce the cause of repeated confirmation or overengineering in the owning rule rather than appending another ban. A larger change can be the simplest complete solution when required callers, state or tests must change together.

## Organize around use

Keep the common direction at the entrypoint. Put specialist depth, rare recovery and host-specific bindings behind links that explain when the material helps. Keep jointly required constraints near the operation that needs them; scattering them across files can cause omissions.

Examples clarify a genuinely ambiguous decision. Templates help when consumers require a stable shape. Scripts earn their place for deterministic work or enforced boundaries. References carry knowledge that only some tasks need. None is a required accessory, and a split that still eagerly loads everything does not reduce context.

## Keep the skill traceable

Keep the skill's important behavior and changes traceable in a form proportional to its size and maintenance needs. A small skill can state its trigger, result, boundaries and non-goals in the body, and record a meaningful change in an existing history or short note. Separate requirements files, stable IDs and a dedicated changelog are useful for complex or long-maintained families, not mandatory accessories or prerequisites for an ordinary edit. Preserve existing useful records; this guidance does not authorize deleting them or overriding a project's required records.

Before changing behavior, read the existing requirements where they live and compare with the actual skill. If no explicit baseline exists, identify what must survive as part of the edit; create another document only when it adds maintenance value. Record what improved, what stayed intact and how it was checked in the existing appropriate record, citing IDs when the skill uses them. Update requirements only when one was added, narrowed or retired. Removing a user-required capability needs the user's decision; traceability does not turn an agent-added suggestion into a binding requirement.

## Try the work and refine

Use a representative request and inspect the actual result: can another agent discover and use the skill, retrieve missing information, adapt to the inputs and satisfy the user's requirements? Run a bundled interface when its behavior is part of the change. For a narrow edit, verify only the affected path plus project-required checks.

Consult [Evaluate](evaluate.md) when a failure, a comparison claim or a consequential risk needs deeper evidence. Match the finished artifact against the request, especially any exceptions or defaults introduced. Deliver the requested draft or change; application and publication are separate actions under [Release](release.md).
