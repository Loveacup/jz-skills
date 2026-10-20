# Changelog

Version entries describe changes, not proof that a runtime loaded or correctly used them. Deployment and publication require their own evidence. From v6.1.0 each entry states what it improved, what it preserved, and how that was confirmed, citing IDs from [core requirements](./core-requirements.md).

## v6.1.0 — 2026-10-20

Source: the OpenAI Developers article [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra), fetched 2026-10-20; it supersedes the earlier post capture as the cited source. Merged semantically onto v6.0.0 after a parallel v5.2.x line (branch `local-v5.2.1`, built on v5.1.1) was found to overlap with the v6 redesign; v6's structure wins, only the additive points below were carried over.

**Improved.** CR01: descriptions lead with the operation and trigger because consumers truncate them, with the article's migration example. CR03: shared skills are written for the task; model-compensating constraints belong in a host adapter or carry their reason. CR04: skills and instruction surfaces state what finished means; a review stop after a first draft is kept only where a material decision sits. CR09: ask-first rules classified by origin, with compensation for an earlier model converted to a scoped grant that states its safety basis (article's disposable-test-suite example); contextual pointers must name current documents; test encouragement written for an earlier model is narrowed to the required verifier. CR10 (new): every skill carries a core-requirements document and change history; revisions read the former first and update both; this skill's own [core requirements](./core-requirements.md) were extracted from v6.0.0 behavior. A "new model" audit routes to the existing collection and agent-instruction guides over named targets.

**Preserved.** CR02, CR05–CR08 and the whole v6.0.0 structure: question-driven references, no audit forms or quotas, separate planes, no authority by recency, blocked-not-passed semantics.

**Confirmed.** Internal links and anchors resolved by script; frontmatter parses at 6.1.0; `deploy/skill-drift-summary.sh` PASS. Earlier, the pre-merge agent-instructions text ran one offline scenario over a six-rule fixture `AGENTS.md` and produced the intended narrowings while keeping the push/apply boundary and required integration gate; the merged wording was not re-run. Runtime loading by a named consumer was not observed.

## v6.0.0 — 2026-10-16

Reoriented the entrypoint, authoring, evaluation, collection and instruction guides around expert knowledge, model judgment, targeted research and adaptable methods. Replaced universal audit forms and scenario itineraries with question-driven references; kept precise interfaces, user requirements, executable boundary checks and high-impact independent judgment. The description and reference paths remain stable. Import, release and privacy remain specialist resources; host-specific installation details belong in the local adapter, not the common entrypoint.

The research basis includes Anthropic's degrees-of-freedom guidance, [presentation granularity](https://arxiv.org/html/2605.31408), [SkillJuror](https://arxiv.org/html/2606.11543v1) and [model-aware skill alignment](https://arxiv.org/html/2605.30723). These support task-dependent design, not a universal brevity rule or a measured gain for this version. No new service, benchmark platform, fixed quota or publication permission is introduced.

## v5.3.0 candidate — 2026-10-16

This additive candidate was superseded by the directional redesign before canonical application or runtime deployment.

Added conditional value checks for capability versus workflow/preference skills, no-skill comparisons, held-out acceptance cases, variation and blinded qualitative comparisons. Discovery diagnosis distinguishes exposure, loading, guidance adoption and task success, including real catalog conditions when implicated. Efficiency uses observed execution costs only when relevant. No fixed quotas, new framework, mandatory benchmark suite, authorization changes or retirement permission; the wording-only fast path and existing safety gates are unchanged.

## v5.2.0 — 2026-10-13

Strengthened the existing agent-instruction workflow with decision-focused investigation, separate authority/state/priority questions, counterevidence handling, conditional actions and exit conditions, subtask routing, coverage questions instead of mandatory templates, and verified/authorized learning. Eager imports are not treated as progressive disclosure. Original host-resolution, trust, permission, generated-source, required-verifier and independent-review boundaries remain in place.

Extended changed-path evaluation to inspect actual instruction artifacts and distinguish preserved behavior from demonstrated improvement. Added non-normative provenance for the supplied visual method and official host documentation; their scope and extraction limits remain explicit. The description, routes and other authoring workflows are unchanged. This is a source revision, not a deployment, publication, or cross-host performance claim.

## v5.1.1 — 2026-09-22

Scoped collection comparisons to the requested claim instead of always enumerating every pair. Targeted reviews screen co-exposed descriptions for relevant competitors and handoffs; whole-collection audits still screen all named entries, including cross-domain catch-all triggers. Explicit exhaustive coverage remains supported. Report screened and untested scope without inferring runtime behavior, universal safety, or measured efficiency from pair counts.

Require direct before/after comparison of retained prohibitions and approval conditions when narrowing triggers. Preserve their wording unless revision of that constraint is itself authorized; domain-specific qualifiers must not silently weaken a broader restriction.

## v5.1.0 — 2026-09-22

Added scoped collection governance and agent instruction review/revision, including AGENTS.md and host equivalents. The new workflows distinguish exposed descriptions from installed files, real conflicts from complementary responsibilities, declared host precedence from filename assumptions, and generated entrypoints from their editable authority. Review does not authorize bulk changes or runtime management.

Both original articles remain directly cited in [Research notes](research-notes.md), with a source-to-governance mapping and model-specific evidence limits. Existing author/import/evaluate/release workflows and the wording-only path remain available. This entry describes the prepared content; it does not assert canonical application, deployment or publication.

## v5.0.0 — 2026-09-22

Rebuilt the family around a minimal task router, an inline wording-only path, and four workflows. Removed obsolete operational duplicates, v3 backup instructions, and unimplemented framework designs from the active payload after preserving them outside runtime discovery. This is a layout and workflow cutover, not an alias layer.

| Previous material | Current capability owner |
|---|---|
| Root authoring recipe; template/command and naming advice | [Author](author.md): discovery, instruction design, assets and output contracts |
| Dual-role, defect patterns, CQI diagnosis, clean-room and platform migration notes | [Evaluate](evaluate.md): failure diagnosis, capability inventory, behavioral evidence and independent judgment |
| Absorption, architecture-fit evaluation, profile-local import, provenance and runtime-drift guides | [Import](import.md): classified semantic merge and preservation of legitimate differences |
| Deployment, modify/push, rename/cleanup, compatibility and overlay safety | [Release](release.md): named actions, exact artifacts, execution boundaries, actual consumer evidence and retirement |
| SkillHub context/workflow, import/exposure and watchdog recovery | [SkillHub](skillhub.md): conditional local authority lookup and regeneration ownership |
| Desensitization variants | [Privacy](privacy.md): full intended artifact coverage and syntax-preserving transformation |
| Research, consolidation/slimming cases, CQI proposals and SROF drafts/audits | [Research notes](research-notes.md): attributable design lessons and explicit evidence limits; no new runtime framework |

Complete pre-cutover source material remains in repository history at commit `862dc7a1d96f12a539ba530a7ed3b97ad9978ed1`, under `shared/skill-authoring/`. The authorized local refactor audit retains full per-plane backups, including richer runtime-only material, hashes, a per-file disposition and validation evidence. Those private artifacts are not part of this distributable skill.

No fixed line ceiling, rule-position requirement, scorecard, or test quota is a quality gate. Legacy empirical numbers and deployment claims are historical statements, not current acceptance evidence.

## v4.1 — 2026-09-22

Replaced mandatory scorecards, line/test quotas, pushy discovery and implicit release with behavior contracts, risk-tier evidence, conditional SkillHub reads and distinct preparation/application/deployment/publication/retirement states. Preserved richer runtime material by semantic merge. The deeper reference collection had not yet been consolidated.

## Earlier recorded history

- **v3.1 — 2026-06-01:** Added log-driven CQI and staged orchestration proposals. These remain historical designs, not a requirement to install logging, cron, Kanban or another coordinator.
- **v3.0 — 2026-05-27:** Added failure classification, deployment-oriented review and research-derived refinement. Fixed reflection/score dimensions from that version are no longer active.
- **v2.0 — 2026-05-27:** Added decision trees, trigger examples and validation lists. Fixed example counts and list shapes are no longer active.
- **v1.0 — 2026-05-26:** Initial progressive-disclosure, rationalization, scorecard and deployment guidance.
