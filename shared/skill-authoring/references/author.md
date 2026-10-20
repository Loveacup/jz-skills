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

## Organize around use

Keep the common direction at the entrypoint. Put specialist depth, rare recovery and host-specific bindings behind links that explain when the material helps. Keep jointly required constraints near the operation that needs them; scattering them across files can cause omissions.

Examples clarify a genuinely ambiguous decision. Templates help when consumers require a stable shape. Scripts earn their place for deterministic work or enforced boundaries. References carry knowledge that only some tasks need. None is a required accessory, and a split that still eagerly loads everything does not reduce context.

## Keep the skill traceable

Every skill carries a core-requirements document and a change history, inside the skill so they travel with it (conventionally `references/core-requirements.md` and `CHANGELOG.md` or `references/changelog.md`). The requirements list, with stable IDs, what the skill must keep delivering: trigger boundary, consumer-visible result, boundaries it must not cross, non-goals. Extract them from actual behavior and stated needs; an entry earns its place only if losing it would be an observable regression. A dozen is typical. This is not a plan or PRD.

New skill: write the requirements from the agreed inputs, result, trigger and boundaries before the body is finished. Existing skill: read them before changing behavior; if absent, extract them first as the baseline. Each behavior change ends with a change-history entry stating what it improved, preserved and how that was confirmed, citing the IDs touched, and with the requirements updated where one was added, narrowed or retired. Retiring one is a user decision.

## Try the work and refine

Use a representative request and inspect the actual result: can another agent discover and use the skill, retrieve missing information, adapt to the inputs and satisfy the user's requirements? Run a bundled interface when its behavior is part of the change. For a narrow edit, verify only the affected path plus project-required checks.

Consult [Evaluate](evaluate.md) when a failure, a comparison claim or a consequential risk needs deeper evidence. Match the finished artifact against the request, especially any exceptions or defaults introduced. Deliver the requested draft or change; application and publication are separate actions under [Release](release.md).
