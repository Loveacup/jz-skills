# WRR Artifact Slice Implementation Lessons（S0–S4）

## Durable invariants

1. **Capability ≠ attempted ≠ executed ≠ validated evidence**
   - Detecting a local WRR route only establishes capability.
   - A provider call establishes attempted/executed state.
   - Only Validator/Adjudicator output may establish validated evidence.

2. **ClaimBundle precedes research in every ready mode**
   - `sparse` / `condensed` / `full` must all derive the same class of deterministic, video-only ClaimBundle before research planning.
   - Standard draft assembly reuses the precomputed artifact; it must not rebuild, clear or fabricate it.
   - Audience/comment/danmaku claims carry `support_scope=audience_signal`, not factual support.
   - Reject placeholder evidence and evidence-free insights recursively.

3. **Semantic identity excludes display identity**
   - Stable claim/insight UIDs derive from normalized content and canonical evidence locations.
   - Semantic hashes exclude display IDs and normalize record order.
   - Audit records must also strip display-local IDs before semantic hashing.

4. **ResearchPlan references claims; executable queries remain searchable**
   - `plan.claims` stores `claim_uid`, risk and verification policy, not duplicated claim prose.
   - `query.query` may contain bounded executable search text; forbidding all query text makes WRR execution impossible.
   - Normalize claim order by UID and fail closed on duplicate UIDs.

5. **Provider seam is one-shot**
   - Engine calls `provider.execute(plan)` exactly once.
   - Engine owns no retry, Exa/Brave selection, shelling or fallback loop; WRR owns routing and retry diagnostics.
   - No injected provider returns explicit unavailable state without pretending execution.

6. **Fixture and archive replay are plan-bound**
   - Freeze fixture content at provider construction, not first execution.
   - Bind fixture/archive to the expected `plan_semantic_hash`.
   - Archived provider replays only `RawResearchRun`; a validated ResearchBundle loader is a distinct component.

7. **WRR adapter output remains raw until S5 validation**
   - The Engine accepts an injected `ResearchProvider`; it does not become a general web-search client.
   - Each query reaches the adapter with its routing mode already declared. The adapter must not choose Exa/Brave, shell out or implement an Engine-side retry loop.
   - Adapter candidates are allowlisted, bounded and labeled `validation_status=untrusted`; snippets are discovery metadata, never quotes or validated evidence.
   - Main orchestration requires an explicit canonical EvidenceBundle semantic hash. Legacy results-dict or `/tmp/*_fact_checks.json` transports are marked `legacy_untrusted`, do not call the provider and cannot claim execution.
   - Store `ResearchPlan` and `RawResearchRun` as peer/private artifacts. Never copy raw candidates into report sections, fact checks, ClaimBundle or Markdown before Validator/Adjudicator.

8. **Research planning binds the final ClaimBundle, not an intermediate one**
   - In a multi-stage report path, draft assembly may replace or refine `report["claim_bundle"]` after `analyze_video()` returns.
   - Call research orchestration only after the final `draft_with_qa.claim_bundle` has been assigned to the report.
   - A direct unit test of `orchestrate_research()` is insufficient. Add an integration regression that deliberately makes the assembled ClaimBundle hash differ from the initial hash, then assert `research_plan.claim_bundle_hash == final_report.claim_bundle_semantic_hash`.
   - Also assert provider call count remains exactly one and a raw-candidate sentinel never reaches Markdown, sections, fact checks or the final ClaimBundle.

9. **Slice acceptance must distinguish current-slice regressions from future-slice partial work**
   - Run focused tests for the current slice first, then the full suite.
   - If full-suite failure comes from an already-present but unfinished future-slice file, report both results; do not misattribute it to the current slice and do not call the overall pipeline green.
   - Before acting on a newly appearing untracked file, correlate active sessions/background tasks, file mtime and scoped diff. A late async writer can land artifacts after the orchestrator has moved on.
   - Never start a second writer on the same files. Freeze the current workspace, inspect the partial artifact, and continue from its existing RED/implementation state.

10. **Async execution failure requires source-of-truth verification**
   - A timed-out delegated writer is failure, not implicit completion.
   - Inspect actual target-file existence, scoped git diff and symbols before deciding whether partial work is reusable.
   - If no scoped production/test artifacts exist, take over from the existing RED/task package rather than repeating the whole research/design phase.

## Review discipline

- Test green is insufficient: compare the implementation against the artifact ownership contract.
- Treat raw WRR candidates and snippets as untrusted discovery metadata; they cannot enter report projection before Validator/Adjudicator.
- When a reviewer says “claim requests duplicate prose,” distinguish `plan.claims` from executable `queries`; reject fixes that would make queries non-executable while still enforcing UID-only claim requests.
