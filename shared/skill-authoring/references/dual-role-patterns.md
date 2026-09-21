# Independent Behavior Review Pattern

Use this pattern when a skill change alters a high-impact behavior contract, when producer bias could hide a defect, or when conflicting evidence needs an independent judgment. Do not use it as mandatory ceremony for small wording or historical edits.

## Independence contract

The producer and judge must be different contexts. For high-impact work, use a fresh agent and give it the original acceptance contract, the current artifact, and direct evidence—not the producer's conclusion.

The review does not authorize publication, deployment, deletion, or runtime mutation. It evaluates the candidate or evidence package only.

## Risk routing

| Change | Review |
|---|---|
| wording/reference-only, no behavior change | focused self-check and link/mirror evidence |
| trigger, workflow, output, or tool-selection behavior | fresh context when invocation or instruction-following is the uncertainty |
| security boundary, destructive action, publication/deployment policy, runtime/orchestration behavior | fresh independent reviewer required before acceptance |

If high-impact behavior cannot be exercised safely, the reviewer audits the exact artifact and evidence in isolation and returns `BLOCKED` for the unexercised claim. Unrelated downstream work may continue only if it does not rely on that claim.

## Review packet

Provide:

- original request and falsifiable acceptance items;
- exact changed files or candidate artifact;
- source/canonical/runtime relation;
- risk tier and named consumer/target;
- scenarios and command/output evidence already observed;
- explicit non-goals and actions not authorized;
- known failures, uncertainties, and unresolved contradictions.

Do not hide failed evidence or replace the original acceptance contract with a success-oriented summary.

## Two lenses

The same independent reviewer may perform two explicit passes, or separate reviewers may own them when stronger independence is required.

### Contract lens

Determine whether the skill:

- fires for the intended task and stays out of unrelated tasks;
- states a consumer-visible result and meaningful failure conditions;
- keeps common-path instructions separate from conditional depth;
- preserves source/privacy/safety boundaries;
- distinguishes preparation, canonical application, runtime deployment, publication, and retirement;
- avoids unsupported claims and redundant ceremony.

### Adversarial lens

Try to falsify the changed contract:

- follow the most plausible shortcut an agent might take;
- test ambiguous precedence and boundary conditions;
- check whether a dry run or local edit could be mistaken for publication/deployment;
- check whether a named target could broaden into all profiles/platforms;
- check whether unavailable evidence is mislabeled as success;
- check whether a correct existing rule was rewritten to compensate for an execution lapse.

Choose scenarios from the actual change. Do not manufacture a fixed count or numerical score.

## Verdict contract

Return one verdict per acceptance item:

- **PASS** — direct, reachable evidence shows the item is true;
- **FAIL** — direct evidence shows the item is false;
- **BLOCKED** — required evidence is unavailable or unsafe to obtain in the current scope.

Each verdict includes an evidence anchor such as a file/line, diff hunk, command exit/output, or agent artifact. A general impression, self-reported score, line position, or file length is not evidence of behavior.

Then report:

- defects that must be fixed before acceptance;
- non-blocking improvements that are actually supported by evidence;
- external writes or runtime actions not authorized/performed;
- the smallest changed-path scenario needed after remediation.

## Revision loop

1. Fix only the contract implicated by a `FAIL` or evidence-backed finding.
2. Repeat the affected scenario after the edit.
3. Obtain a new independent verdict for remediated high-impact behavior.
4. Stop after acceptance or escalate the precise unresolved decision; do not loop by adding more rules.

Reuse prior evidence for unaffected behavior. Repeat broader checks only when a new edit, failure, or unresolved risk invalidates them.
