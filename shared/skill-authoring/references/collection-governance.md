# Govern a Named Skill Collection

Load this workflow only when the user explicitly asks to audit or revise a named set of skills, their descriptions, or their ownership boundaries. It is not a runtime dispatcher, a reason to scan every installed skill, or a preflight for ordinary coding. The collection may span consumers, but each consumer remains a separate observation surface.

This workflow governs preparation and an already authorized bounded revision. It does not itself authorize deleting or disabling a skill, changing runtime exposure, repointing an alias, editing a registry, deploying, or publishing. Those are named cross-plane actions under [release](release.md). Use [evaluate](evaluate.md) for evidence design, failure classification, and independent judgment.

## Freeze the collection and authority

Record before inspection:

- the user-named skills and consumers in scope, including the exact aliases or paths supplied;
- whether the request authorizes audit only, source revision, generated-output regeneration, or any separately named cross-plane action;
- the governing instructions for each editable source and the current owner of placement, exposure, generation, and skill content;
- paths and consumers deliberately out of scope;
- the acceptance boundary: which requests each skill should select, reject, or hand off.

Do not enlarge a named collection by recursively scanning a live skill tree. Add a discovered skill only when it is directly exposed beside the named skills and supplies evidence necessary to explain a collision; identify it as context, not as an authorized revision target.

When the collection is under local SkillHub governance, read only the target-specific rows and policies required by the [SkillHub adapter](skillhub.md). Do not infer authority from recency, version, path depth, richer prose, or which copy a consumer happens to expose. If no current instruction establishes the writable authority for a finding, mark that finding `BLOCKED` for revision while continuing independent audit work.

## Inventory exposure separately from availability

For every named consumer, use its actual list, describe, or discovery interface without invoking the skill body. Record one exposure row per consumer-visible entry:

| Field | Record |
|---|---|
| Consumer | Exact runtime, profile, or router observed. |
| Exposed identity | Name and route identifier exactly as exposed. |
| Exposed description | Exact text, with a location or captured interface receipt. |
| Claimed source | Path or provider reported by the consumer, if any. |
| Observation state | `OBSERVED`, `HYPOTHESIS`, or `BLOCKED`, with missing evidence. |

Separately inspect only the named disk candidates and directly implicated targets. Record the lexical path, entry type, resolved real path, existence and readability of `SKILL.md`, on-disk name and description, governing source, and whether the path is generated. Keep these claims distinct:

- an exposed description does not prove its claimed path exists or is readable;
- an available `SKILL.md` does not prove any consumer exposes or loads it;
- matching files do not prove matching descriptions at a consumer;
- a consumer receipt covers only that consumer and observation time.

A broken link, absent path, unreadable entry, malformed frontmatter, stale consumer description, and unexposed valid skill are different findings. Do not collapse them into “missing” or repair one by silently pointing elsewhere.

## Deduplicate bodies without erasing aliases

Resolve symlinks for each available candidate and group lexical paths that reach the same real path. Audit the shared body once, but retain every consumer and alias exposure row. An alias can have a distinct description, route name, host binding, or governing owner even when it resolves to the same body.

Do not merge entries merely because their bytes, names, or versions match. Distinct real paths may have different authorities or runtime-specific contracts. Conversely, do not report multiple independent implementations when several lexical paths resolve to one object. For every group, state both:

1. **Body identity:** the resolved object whose instructions were inspected.
2. **Exposure identity:** each consumer-visible name, description, and configured alias.

Preserve unresolved and broken aliases as their own availability findings. Repointing or removing an alias is a release action, not deduplication cleanup.

## Classify ownership before comparing text

Map each current capability and description clause to one of these evidence-backed roles:

- **Maintained owner:** the declared editable source for the portable capability.
- **Consumer projection:** a consumer-specific name or description derived from a maintained source.
- **Generated output:** an output whose declared source and generator, rather than the output file, own revision.
- **Runtime-owned overlay:** a narrow host-specific contract that is intentionally not portable.
- **Complementary skill:** a separate owner for a distinct phase, object, or action.
- **Duplicate or shadow:** a second claimant to the same task boundary without a justified distinct role.
- **Unknown authority:** no current governing instruction settles ownership.

Quote the instruction or policy that establishes the classification. When two current sources claim authority, preserve both claims and report an ownership conflict; do not choose the one that appears newer or more complete. Unknown authority blocks only the affected write, not findings whose evidence and owners are settled.

## Compare simultaneously exposed descriptions pairwise

Within each consumer, compare every unordered pair of named entries that can be offered to the same selector. Across consumers, compare a pair only to explain a stated cross-consumer difference; entries never offered together cannot collide in one router.

Use the exact exposed descriptions, not a summary of their bodies. Quote the clauses that establish the decision and classify the pair:

- **Conflicting trigger:** the same realistic request satisfies both descriptions and they claim incompatible ownership or next actions.
- **Generalist/specialist ambiguity:** both can own the request and the description does not state the condition that gives the specialist precedence.
- **Complementary workflow:** the skills own different phases or artifacts and their descriptions provide a usable handoff boundary.
- **Alias duplication:** multiple exposed identities reach the same body; any difference lies in exposure or routing, not implementation.
- **No material overlap:** shared vocabulary exists, but their positive and negative task boundaries remain distinguishable.
- **Blocked comparison:** a current exposed description or joint-selection surface could not be observed.

Shared nouns are not by themselves a collision, and different verbs are not by themselves separation. Decide from the requested outcome, object changed, action authority, and stopping point. Do not force one winner when two skills are complementary; make the handoff explicit only when observed requests show the boundary is unclear.

## Exercise description-only selection boundaries

For every skill whose discovery or ownership is implicated, derive boundary cases from its exposed description:

- a representative core request that should select it;
- a request near each disputed boundary that should still select it;
- a neighboring request that should not select it, to expose a false positive;
- an in-scope request likely to be missed by the current wording, to expose a false negative;
- for each conflicting pair, the same neutral request presented to both descriptions together;
- any explicit anti-trigger or handoff case promised by the description.

Use the actual consumer's selection interface when it can expose only names and descriptions while withholding skill bodies. Otherwise use an isolated selector with the captured names and descriptions and label the result as harness evidence, not consumer behavior. If body text, prior choices, or producer rationale leaks into the selection context, the result is confounded and does not decide discovery.

Record the exact request, description set, consumer or harness, selected and rejected entries, and expected boundary. A model's explanation or self-score is not the observation. Scenario count follows the actual disputed boundaries; there is no universal quota. Preserve per-runtime outcomes instead of averaging them into a universal routing claim.

Classify failures using [Evaluate](evaluate.md#diagnose-before-rewriting). A description collision is not proof that either body is defective, and an unavailable consumer cannot be repaired by rewriting prose.

## Produce actionable findings

Each finding must be independently decidable and contain:

| Field | Required content |
|---|---|
| Finding | Stable local identifier and concise defect or confirmed boundary. |
| Source evidence | Exact exposed description, instruction, path, or policy location; quote the decisive text. |
| Status | `OBSERVED`, `HYPOTHESIS`, or `BLOCKED`. Hypotheses are never revision authority. |
| Scope | Affected consumers, aliases, real-path group, and requests. |
| Ownership | Content owner, exposure owner, generator owner, or unresolved conflict. |
| Remedy | Smallest change that resolves the finding, or `no change` for a confirmed complementary boundary. |
| Capability destination | Exact maintained source and section that will own every retained rule. |
| Authorization | Audit-only, source revision authorized, or the exact missing cross-plane action. |
| Verification | Description-only cases or other changed-path evidence to repeat after revision. |

Also produce a capability map from every current useful constraint in the implicated text to its retained destination. This prevents shorter descriptions or consolidation from silently dropping security exclusions, verification requirements, consumer-specific conditions, or handoff boundaries. Length and token count do not decide whether a constraint is useful.

## Stage the minimum authorized revision

When source revision is explicitly authorized, prepare and review the smallest source-owned patch that addresses observed findings:

1. Edit only the implicated maintained owner. For generated entries, edit the declared source or generator input and regenerate through its designated mechanism; never hand-edit the output.
2. Prefer a precise positive trigger, concrete exclusions, and an explicit handoff over adding precedence prose to every skill.
3. Preserve useful constraints through the capability map. Move a rule only to a destination that the applicable workflow actually loads.
4. Preserve justified consumer-specific descriptions and runtime overlays. Do not normalize different runtimes unless their current owners and observed behavior establish one shared contract.
5. Stage source-content revisions separately from exposure, placement, registry, symlink, deployment, publication, or retirement changes.
6. Do not automatically delete, disable, rename, repoint, consolidate, or hide a skill. Propose the exact action and evidence separately; perform it only when that named target and action are authorized under [Release](release.md#resolve-authorization-by-named-action).

A prepared patch must identify the exact changed paths and the findings each hunk resolves. If authority is disputed, prepare alternatives or a bounded proposed delta, but do not write either claimant until the governing owner is settled.

## Re-evaluate and hand off cross-plane actions

After an edit, repeat only the description-only cases and links invalidated by that edit. For behavior beyond discovery, use the proportional scenarios in [Evaluate](evaluate.md#choose-proportional-evidence). Apply its independent-judgment branch after edits when the collection governs security, destructive actions, deployment, publication, credentials, or orchestration; review follows the candidate change rather than approving it in advance.

If the authorized outcome includes regeneration, exposure changes, deployment, repointing, publication, or retirement, hand the frozen reviewed artifact and exact action set to [Release](release.md). Keep `Prepared`, `Canonical applied`, `Runtime deployed`, `Published`, and `Retired` claims separate. No collection finding alone authorizes a cross-plane action.

Report changed and deliberately unchanged sources, retained runtime differences, per-consumer discovery evidence, unresolved ownership, and every blocked claim. The result is an audit and bounded revision record, not a permanent routing service or a new registry.

## Research basis and limits

The design rationale is summarized in [Research and Design Notes](research-notes.md#current-model-guidance). OpenAI's [Using GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra) motivates auditing accessible instruction conflicts and matching verification to the change. Eric Provencher's [post on skill files and agent instructions](https://x.com/pvncher/status/2095991462416490862) motivates concrete discovery boundaries, progressive disclosure, and removing obligations that no longer earn their context cost.

These sources are rationale, not commands, runtime evidence, or universal model behavior. They do not establish a fixed collection size, token budget, scenario count, winning description shape, or permission to alter any consumer.