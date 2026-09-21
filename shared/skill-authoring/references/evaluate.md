# Evaluate a Skill

Load this workflow only to audit, refactor, diagnose, or verify a skill behavior that may have changed. Do not load it for the root workflow's wording-only path.

## Define the claim

Turn the request into observable acceptance items. Name the artifact under review, the consumer or interface involved, the behavior that should be visible, and the boundary that must remain unchanged. Do not use line count, checklist shape, a score, or the producer's confidence as a substitute for correctness.

Keep these claims distinct:

- **Artifact:** the intended files are complete, parseable, internally linked, and free of stale active instructions.
- **Discovery and route:** the skill is offered for an in-scope request and stays out of an out-of-scope request.
- **Interface:** frontmatter, bundled files, commands, or tool contracts are valid for the consumer that reads them.
- **Task behavior:** using the skill produces the requested result and respects its boundaries.
- **Runtime or release state:** a named consumer actually loaded the intended artifact. Byte identity alone proves only byte identity.

## Diagnose before rewriting

Use the observed trace or output to classify the failure:

- **Discovery failure:** the description or runtime exposure did not select the skill, or selected it for an unrelated task.
- **Omission:** the applicable instruction was available and unambiguous, but the result left it out. Reduce competing obligations or put the instruction at the decision point before adding another rule.
- **Confusion:** the available text supports competing interpretations or unclear precedence. Remove the ambiguity or duplicate owner.
- **Contract defect:** required behavior is absent, wrong, internally inconsistent, or impossible through the declared interface. Repair only the implicated contract.
- **Execution lapse:** the contract is adequate but this run did not follow it. Do not rewrite correct instructions merely to make the trace look explained.
- **Environment or capability failure:** the required consumer, tool, permission, dependency, or observation surface is unavailable or broken. Report that boundary; prose cannot supply the missing capability.

A single symptom can involve more than one class. Preserve contradictory evidence until the cause is resolved.

## Refactor without losing capability

When restructuring is requested, inventory the affected live rules, bundled behavior, incoming callers, and outgoing resources before changing the layout. Classify each item as current capability, conditional environment detail, historical evidence, or obsolete instruction. A document labelled “complete” or “deployed” does not establish either state.

Give each current capability one owner. Keep common decisions at the entrypoint; move conditional depth behind a link that states when it is needed. Consolidate duplicate procedures rather than adding a new facade that still loads all the old ones. Use [Author](author.md) for instruction-design decisions that the observed defect leaves unresolved.

Map retained capabilities to their replacement sections and preserve historical evidence outside active discovery when retirement is authorized. Exercise affected routes and callers before deleting the old paths; follow [Release](release.md) for that separately authorized cutover. A reference that exists is not enough if the actual consumer cannot find or serve it.

## Choose proportional evidence

Exercise the changed path and any boundary it can plausibly break:

| Change | Evidence that decides it |
|---|---|
| Description or ownership | Present representative in-scope and out-of-scope requests using only the skill name and description. Observe selection and rejection; do not expose the body to the router test. |
| Instructions or output contract | Run a realistic task with the candidate and inspect the produced artifact against the user's acceptance items. A model's statement that it complied is not evidence. |
| Bundled script, schema, or command interface | Parse or invoke the actual interface with meaningful input and observe its result and failure behavior. |
| Reference split, rename, or removal | Resolve affected links and exercise the route that loads the moved material. |
| Privacy-sensitive transformation | Apply the checks in [Privacy](privacy.md) to the exact crossing artifact, then repeat syntax- or behavior-sensitive checks affected by the transformation. |
| Runtime or release claim | Use the named consumer's real loading path and observe its behavior. Source/runtime hashes can support provenance but cannot replace consumer evidence. |

Reuse unaffected evidence. Broaden or repeat checks only after another edit, a failure, or an unresolved risk changes what the earlier evidence covered.

## Executable trust boundaries

Use this branch only when the skill wraps mutation, shell/tool execution, asynchronous agents, or state-driven cleanup. Derive adversarial cases from the actual boundary; a text-only draft does not need this matrix.

| Boundary present | Evidence required for its claim |
|---|---|
| Modes and required values | Exercise the real accepted mode strings, including namespaces. Reject semantically blank normalized values and empty members where content is required; non-empty containers alone are insufficient. |
| IDs, paths, and cleanup | Validate identifiers before interpolation and derive canonical state/output/cleanup paths from them. A mutable state file is not path authority. Probe traversal, absolute-path substitution, control characters, and forged state paths; unrelated victim files must survive. |
| Terminal and asynchronous outcomes | Separate progress events from terminal results. Only documented success with a proven real child exit code passes. Abort, error, truncation, unknown outcome, silence, timeout, or missing/invalid exit evidence cannot become success. |
| Negative fixtures | Establish that the valid fixture succeeds, change only the relevant fault, and observe its specific failure. Unrelated broken prerequisites are not evidence that a gate works. |
| Scope enforcement | Prove the executor actually confines the action. If it cannot enforce a claimed write scope, do not expose that capability as safe: isolate it or route it through a separately controlled executor before enabling it. A prompt restriction is not enforcement. |

Use private disposable roots and controlled test doubles for dangerous external effects; do not modify production manifests, permissions, processes, or global temporary names to build a test. Evidence from test doubles covers only the exercised boundary, not live integration. Keep disabled or unproven capabilities out of current templates and descriptions as well as the root; repair a real live exposure only under its authorized operational scope.

## Compare a genuine baseline when comparison matters

Use baseline-versus-candidate scenarios when a refactor claims to preserve behavior, improve routing, or correct an observed failure.

1. Freeze the exact baseline and candidate artifacts and record which one each run consumed.
2. Give both runs the same realistic request, supplied inputs, authorization, consumer interface, and material environment conditions. Do not rewrite the request to advertise the candidate's new wording.
3. Keep the runs independent of one another so candidate context cannot inherit baseline reasoning or output.
4. Judge each output directly against the same acceptance items. Compare the artifacts and boundary behavior, not style, verbosity, or self-reported scores.
5. Attribute differences only as far as the evidence permits. If the environment or consumer changed, the comparison does not isolate the skill change.

A baseline is unnecessary when there is no preservation or improvement claim; direct changed-path evidence is then clearer.

## Independent judgment for high-impact changes

A change to security boundaries, destructive actions, publication or deployment authority, credentials, or orchestration requires a judge who did not produce the candidate. Give the judge the original acceptance contract, exact candidate, observed evidence, non-goals, and known failures—not the producer's verdict.

Record independence on separate axes:

- **Context independence:** a fresh session without the producer's hidden rationale or conclusions.
- **Model independence:** a materially different model or provider. A fresh session of the same model supplies context independence only.

Use both when the governing project requires them or when model-specific instruction behavior is itself at issue. Otherwise state exactly which axis was obtained. If the required independent judge, real consumer, or safe execution capability is unavailable, the affected claim is `BLOCKED`; do not replace it with self-review or prompt language. Work that does not depend on the blocked claim may continue.

## Verdict and revision

Return `PASS`, `FAIL`, or `BLOCKED` for each acceptance item with a reachable file, diff, command output, runtime receipt, or reviewer artifact. Include the artifact and consumer that the evidence covers.

For a failure, change only the implicated owner, then repeat the smallest scenario invalidated by that edit. Re-run independent judgment after remediating high-impact behavior. Stop when the requested contract is demonstrated or report the exact missing evidence or decision.