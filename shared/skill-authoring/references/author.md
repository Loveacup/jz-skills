# Author a skill

Use for a new skill or a change to its trigger, instructions, or bundled behavior. A wording-only correction follows the inline path in `SKILL.md`; it does not need this workflow.

## Decide what belongs here

A skill earns its place when a recurring task benefits from guidance the agent would otherwise have to rediscover: a tool interface, domain-specific procedure, output contract, or important failure mode. Put project-wide invariants in the owning project instructions, facts in the appropriate data source, and one-off task details in the request. Do not create a second skill for a capability an existing one can own.

Inspect the target and its relevant callers or resources. Resolve genuine ambiguity from those sources before asking the user. For new work, make the inputs, consumer-visible result, intended trigger, and important failure/authorization boundary explicit. Scale the explanation to the task; do not manufacture a design document for a small edit.

Preserve explicit inclusions, exclusions, and permissions in the generated skill. Do not add an audience mode, convenience exception, fallback action, or default that weakens the requested contract. Missing information should lead to an appropriate input question, omission, or uncertainty marker—not unfinished instructions or invented facts.

## Make discovery precise

The name and description are the skill's discovery interface. They must let the agent choose it without reading the body.

- Name the task the skill performs, not every domain it touches. Describe the deliverable or operation in ordinary language.
- Include a nearby non-trigger when it prevents a demonstrated collision. A skill about writing skills should not activate merely because the user wants to use one.
- Do not fill the description with the workflow, a tool inventory, synonyms, urgency, or instructions to always load it.
- Check the target runtime's actual frontmatter requirements. Preserve established metadata when updating; do not invent a license, source, dependency, or supported platform.

For example, `Use for all database work` competes with unrelated skills. `Prepare and verify PostgreSQL schema migrations; not for ordinary queries` identifies a concrete task and an adjacent exclusion. The example illustrates a distinction, not required wording.

## Give the agent the missing information

Write the common execution path and result contract. Supply details that change decisions: input interpretation, precedence, tool arguments, output shape, error handling, and the conditions for asking or stopping. Trust the agent to carry out ordinary connective steps rather than prescribing an itinerary of trivial actions.

Organize multiple modes as a task router. Put environment-specific setup, rare recovery, research, and long examples behind references whose load conditions are stated at the link. A reference should resolve the next decision, not send the agent through another mandatory index. Keep each live rule in one owner and link to it where needed.

Use tools and models the environment actually exposes. If a capability is required but unavailable, say what part is blocked; do not invent a fallback that returns a success-shaped result. Shared skills separate portable behavior from conditional runtime adapters. Do not import another runtime's dispatcher, memory store, or service merely to make instructions reusable.

## Add assets only when they carry behavior

| Material | When it earns a place |
|---|---|
| Example | An ambiguous format, precedence rule, or task boundary is clearer with a concrete input and result |
| Template | Consumers genuinely require a stable output structure; label it mandatory only for that contract |
| Script | Deterministic validation, parsing, transformation, or a tool operation is more reliable as executable code |
| Reference | Only a subset of tasks need the information and its load condition can be stated |

Do not copy the same requirement into a warning, table, template, and closing checklist for salience. Use a stronger safeguard only for a demonstrated bypass or safety boundary. When an executable boundary is needed, a prompt reminder is not a substitute for enforcement.

If changing scripts or structured examples, preserve their language semantics. Test the uncertain behavior through the actual entrypoint in a disposable setting. Do not add permanent tests that merely assert your wording or file layout.

## Check and deliver

Exercise the task paths affected by the change. A new trigger needs relevant selection and non-selection cases; a workflow needs a realistic result; a script needs observed execution. For a straightforward content-only skill, use a representative request and inspect its result directly. Read [Evaluate](evaluate.md) for a nontrivial evaluation design, a diagnosed failure, or independent review. There is no universal scenario quota or score threshold.

Compare the finished skill with the original request, including any exceptions or defaults you introduced. Confirm that resources resolve and the instructions produce the requested artifact. A draft is complete when the user requested a draft; it is not permission to deploy or publish. Crossing those planes uses [Release](release.md) only when it is part of the authorized task.
