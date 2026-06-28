# SROF v1.0 — Independent Audit Report

> **Auditor**: CC (independent reviewer, adversarial stance)
> **Subject**: `skill-runtime-orchestration-framework-v1` (a.k.a. `/tmp/skill-orchestration-design-output.md`), 808 lines
> **Baseline for diff**: v0.1 (`/tmp/skill-orchestration-design.md`)
> **Date**: 2026-06-28

---

## Executive Summary

**Verdict: CONDITIONAL PASS.**

The *conceptual core* is sound and a genuine improvement over v0.1. The four load-bearing ideas — (1) two nested lifecycles (provisioning ⊃ execution), (2) sensor/actuator/engine triad, (3) `fail` vs `block` defined as *authority-to-clear*, (4) state-file-as-cache with re-verify-on-entry — are correct, well-motivated, and resolve real v0.1 defects. If the question is "is the *model* right?", the answer is yes.

But the document **cannot be implemented as written**. The gap is not in the philosophy; it is in the contract surface the doc itself promised to specify carefully (§1.3 explicitly names "the contract surface between engine and sensors/actuators" as the thing the rest of the doc *must* nail — and it doesn't). Two issues block the central `gate → actuate → verify` loop, and the single normative reference implementation (`setup.sh --auto`, §8.2) contradicts its own spec on four counts and is unsafe to run. The headline cross-session-resume feature (`BLOCKED_ON_INPUT`) is never persisted, so it can't actually resume.

None of this invalidates the architecture. All of it must be fixed before code. Hence **CONDITIONAL PASS**: ship the model, do not ship the contract/reference sections until the P0/P1 list below is closed.

**Severity tally**: 2 × P0 · 6 × P1 · 10 × P2 · 5 × P3.

---

## What v1.0 gets right (for fairness / to protect during revision)

- **The two-lifecycle separation** (§1.1, §2) is the correct decomposition and the doc's best contribution. v0.1's `READY→ACTIVE→READY` really was an execution loop smuggled into a provisioning machine; §10.1 diagnoses this honestly.
- **`fail` vs `block` = who may clear it** (§6.2) is the right razor and makes the verdict machine-actionable. The new `authority` field (§6.4) is a clean encoding.
- **Exit-code ⟂ verdict** (§6.3) is the correct insight (gate *health* vs gate *answer*). The irony is that the reference gates then violate it (see P2-6).
- **State-file-as-cache, re-verify-on-entry** (§3.5) kills the stale-READY class of bug — directionally correct (though oversold; see P2-3).
- **"Split state by lifetime, not scope"** (§7 D-1) — the "never put a lock in `.state/`" rule is exactly right and worth keeping as a headline.
- Resolving all five open questions instead of offering a menu matches the stated working preference and is the right call.

---

## Findings by Severity

### P0 — Blockers (core loop not implementable as written)

---

**P0-1 · The verify gate cannot observe the actuator's result. The central loop's third step is unimplementable.**

*Location*: §3.1 (`verify: exit_code:0`, `verify: json_path:.registered==true`), §6.4 (envelope), §6.5 (verify taxonomy), §8.2 lines 690–691.

*Problem*: The whole framework is "gate (when) → actuate (run) → gate (verify)" (§3.1 line 150). A gate is defined as a **pure function `world_state → {verdict, evidence}`** (§6.1) invoked as a *separate process* with a single primitive arg (§6.4 envelope has **no input channel** for the actuator's stdout/exit code). But `exit_code:0` and `json_path:.registered==true` are verifications *of the actuator's output*, which a freshly-spawned pure gate cannot see. §8.2 proves it: line 690 runs the actuator via `bash -c "$(...run...)"`; line 691 immediately spawns `gate-verify exit_code:0` as a new process — by then the actuator's `$?` is gone, captured nowhere, passed to nothing. The gate has nothing to verify.

It gets worse: the *same target means two different things* in the two paths. Interactive (§3.3) — the LLM ran the actuator and observed exit 0 itself, so `exit_code:0` is an *engine self-check*, not a gate call (and arguably brushes against §4.1 "the LLM must never assert a world-fact it did not obtain from a script"). Headless (§8.2) — it's a real `gate-verify` subprocess that structurally cannot know the exit code. And `json_path:.registered==true` is worse still: to "verify" a registration, a separate gate would have to *re-run the register call* (a remote write — harmful) or read output it was never handed.

*Why it matters*: `verify` is on **every step** in **both** paths. If the third leg of the core triad has no defined input contract, nothing downstream (`PROVISIONING → PROVISIONED`, memoization, `BROKEN` detection) has a sound foundation.

*Fix*:
1. Add an explicit input contract to the gate envelope for output-dependent verifies — e.g. the actuator writes its captured stdout+exit to a known path (`$SROF_RUN_RESULT`), and `gate-verify` reads *that*, not the live world. This keeps the gate pure (it observes a file) without re-executing the actuator.
2. Split the verify vocabulary into two explicit classes and say so in §6.5: **(a) re-query verifies** that are self-contained idempotent observations (`command_exists`, `http_ok`, `agent-reach skill --status → json_path`), and **(b) last-result verifies** (`exit_code`, `json_path` on the just-produced output) that consume `$SROF_RUN_RESULT`. Forbid using class (b) where re-execution would mutate state; prefer an idempotent class-(a) status query (e.g. verify registration via a `--status` read, never via re-`--register`).
3. In §8.2, replace `GATE gate-verify exit_code:0` after line 690 with an actual capture (`rc=$?`) feeding the contract above.

---

**P0-2 · The only normative reference runner (`setup.sh --auto`, §8.2) contradicts the spec on four counts and is unsafe. The "engine vs script" principle is violated without reconciliation.**

*Location*: §1.2 ("Scripts are its sensors and actuators. **Nothing else.**"), §3.4, §8.2 (whole), against §3.1/§3.3 (prerequisites), §4.3/§5.4 (retries), §6.3 (broken-gate default), §5.5/§3.5 (state schema + memoization).

*Root cause*: §1.2 asserts scripts are *only* sensors and actuators. But `setup.sh --auto` is neither — it is an **orchestrator/engine**: it sequences, applies `when`, decides skips, decides parking, decides state transitions. The doc never carves this out or acknowledges that, in headless mode, a *script inherits the engine's duties* — and therefore must replicate prerequisite enforcement, retry policy, block/danger handling, and safe-default-on-broken-gate. §8.2 does **none** of these:

- **(a) Prerequisites silently skipped.** §3.1/§3.3 define a prerequisite phase (`block/fail → halt`); §3.2's `setup.lock.json` even carries `prerequisites` (line 204). §8.2 starts at `steps` (line 674) and **never reads `.prerequisites`**. Headless provisioning runs steps with preconditions unchecked.
- **(b) Retry policy dropped.** Manifest declares `on_failure.max_retries: 2` (policy, per §4.3); lock.json carries it (line 210); the state machine says `PROVISIONING → BROKEN` happens *after* `max_retries` (§5.4). §8.2 line 691–692 goes to `BROKEN` on the **first** verify failure. Either headless ignores declared policy, or — if you "fix" it by hard-coding the retry loop into the script — you re-bake policy into code, the exact thing §4.3 forbids.
- **(c) Unsafe default on a broken gate — directly contradicts §6.3.** §6.3 mandates: exit≠0 ⇒ gate is broken ⇒ *do not assume pass*, safe default is treat-unknown-as-block. §8.2's `GATE()` does `local.sh 2>/dev/null || central.sh`, then `[ "$(... | jq -r .verdict)" = pass ]`. A broken gate (exit 1, empty/garbage stdout — including the `unknown target → exit 1` path of the very reference gate, §6.7 line 589) yields a non-`pass` string → the `when`-check treats it as "not satisfied" → **proceeds to run the actuator**. Broken gate ⇒ proceed. That is precisely the unsafe default §6.3 forbids, and §8.2 has *no* `block`/danger handling and *no* prerequisite halt to catch it.
- **(d) State write defeats memoization and contradicts the schema.** §5.5 schema requires per-step `steps{...memoized,last_verify...}`; §3.5's "skip memoized expensive actions" depends on it. §8.2 line 698–699 writes only `{skill, state:"PROVISIONED"}` — **no `steps` map**. Next entry reads this, finds nothing memoized, and must re-run everything (re-`npm install`, re-`register`). Headless-written state structurally breaks the framework's central anti-staleness mechanism.

*Why it matters*: This is the *only* concrete runner in the document. As written it skips preconditions, ignores declared retry policy, proceeds on broken gates, and erases the memoization the cache model depends on. A cron job running it is unsafe.

*Fix*:
1. Add an explicit subsection: **"Headless `setup.sh` is a degraded-mode engine substitute"** and enumerate the engine duties it MUST replicate: prerequisite phase, retry-to-`max_retries` (reading the threshold from lock.json — policy stays data), `block`/non-`pass`-on-broken-gate → halt with safe default, and full §5.5 state write including the `steps` memoization map.
2. Fix `GATE()` brokenness handling: distinguish "local gate absent" (then fall back to central) from "local gate exited non-zero" (a *broken gate* → halt, never fall through). Use `[ -x local ]` to decide fallback, not exit code.
3. Default any non-`pass`/non-`fail` verdict (including empty output) to **halt**, never proceed.
4. Read and enforce `.prerequisites` before the step loop.

---

### P1 — Must fix

---

**P1-1 · `when` idempotency is inverted/contradictory, and the `*_missing:` gate targets it uses don't exist in the vocabulary.**

*Location*: §3.1 line 156/161 (`when: command_missing:agent-reach`, `env_missing:AGENT_REACH_API_KEY`), §3.3 step 2a ("pass → record skipped"), §6.5/§6.7 (gate vocabulary).

*Problem*: Two coupled bugs.
- **Inverted semantics.** §3.3 says: `when` gate `pass` → *skip* the step ("already satisfied"). The field is named `when` (= condition to *run*) and valued `command_missing:agent-reach` (= "agent-reach is missing"). On a fresh machine agent-reach *is* missing → if `command_missing` passes, §3.3 **skips the install** — backwards. The only way §3.3 is self-consistent is if `command_missing:X` is defined to *pass when X is present* ("the missing-check passes = not missing"), which is the opposite of how `command_exists` works and is nowhere stated. The comment "skip if already satisfied" reveals the author conflated "`when` = run-condition" with "`when` = already-done-condition."
- **Targets unimplemented.** Even setting semantics aside, `command_missing:` / `env_missing:` are **not in §6.5's taxonomy or §6.7's `case`** (only the positive `command_exists`/`env_exists` exist). So `gate-check command_missing:agent-reach` hits §6.7's `*)` default → `block`+exit 1. In §8.2 that means the step is never skipped → `npm install -g` re-runs **every** invocation. And `register-skill` (§3.1 line 176) has **no `when` at all** → it re-runs every time too (a remote write, every cron tick).

*Why it matters*: Breaks the framework's own principle #3 "idempotent by design." A motivating step (remote registration) re-fires on every run. The interactive LLM can paper over the muddle by "interpreting," but the normative pseudocode (§3.3) and the headless runner are provably wrong.

*Fix*: Pick one convention and implement it. Recommended: keep gate vocabulary **positive only** (`command_exists`, `env_exists`), redefine `when` as "the precondition that must hold for the step to be *needed*," and make the rule **`when` fails (precondition absent) → run; `when` passes → skip**. Rewrite §3.1 to `when: command_exists:agent-reach` and §3.3 step 2a to "pass → skip; fail → run." Give every state-mutating step (esp. `register-skill`) a `when`.

---

**P1-2 · `secret: true` is promised but the only injection mechanism leaks the secret into the transcript.**

*Location*: §3.1 lines 162–168 (`secret: true # never echo to transcript/state`, `$SROF_INPUT`), §3.3 line 229 ("inject as `$SROF_INPUT`"), §5.5 line 458.

*Problem*: The doc correctly keeps secrets out of the *state file*. But the *injection path* is "the LLM obtains the value and injects it as `$SROF_INPUT`" into an actuator like `printf '...%s' "$SROF_INPUT" >> env`. The only way the LLM injects a value into a subprocess is by *emitting it* — either interpolated into the command string it writes (→ in the transcript) or exported into the env (→ visible in `/proc/<pid>/environ`, `ps e`). Both violate the stated `secret: true # never echo to transcript`. There is no described out-of-band channel from "LLM holds secret" to "actuator consumes secret" that bypasses the LLM's own output stream.

*Why it matters*: This is the **motivating feature** (`帮我配小红书` / API keys). A design that promises secret-safety and then routes every secret through the model's transcript is worse than one that doesn't promise it.

*Fix*: Specify a secure channel that the LLM never sees the value of. E.g.: for `source_order: [vault, env, human]`, the *human/vault* writes the secret to a transient fd or `umask 077` temp file path that the LLM only ever references *by path*; the actuator reads `$SROF_INPUT_FILE`, never `$SROF_INPUT`. The LLM orchestrates (knows *that* a secret is needed and *where* it will land) but never holds the plaintext. Document this as the canonical `secret:true` path and forbid value-interpolation.

---

**P1-3 · `BLOCKED_ON_INPUT` is never persisted, so the cross-session resume it exists for cannot happen.**

*Location*: §3.4 line 256 ("the next interactive session sees `need: configure-key` … and resumes"), §5.1 (BLOCKED_ON_INPUT as a first-class state), §8.2 lines 685–688.

*Problem*: §8.2 *prints* `{"state":"BLOCKED_ON_INPUT","need":...}` to stdout and `exit 20` — it never writes it to `.state/provisioning.json` (the only durable write, line 698, happens solely on full success). Cron discards/► emails stdout. The interactive path (§3.3) never enters `BLOCKED_ON_INPUT` at all — the LLM just asks in-band. So the state is: never durably recorded by *either* path. "The next interactive session sees `need: configure-key`" requires reading durable state that was never written.

*Why it matters*: Self-describing parking is sold as the key enabler of "safe to attempt setup from cron" (§3.4) and the `帮我配 XXX` resume loop (Appendix A). The mechanism doesn't close the loop.

*Fix*: On hitting a non-auto step, headless must **persist** `state: BLOCKED_ON_INPUT` + `need` + `fix` + `since` to `.state/provisioning.json` *before* exiting 20. Define that on entry the engine/`skill_view` reads this and surfaces it. (Also reconcile: should interactive transition through BLOCKED_ON_INPUT too, or is it headless-only? State diagram §5.1 implies a real shared state; say which.)

---

**P1-4 · `setup.lock.json` is a second source of truth with no drift detection.**

*Location*: §3.2, §3.4, §11 step 4 ("or have the LLM emit it once, committed").

*Problem*: Interactive parses YAML; headless parses `setup.lock.json`. The doc offers no build system (skills are plain dirs) and explicitly allows the lock to be **LLM-emitted-once and committed** — the least reproducible option. Nothing guarantees `setup.lock.json` matches `setup.yaml`. The `version` field can stay `"1.0"` while steps change. Editing the YAML and forgetting to regenerate the lock → interactive and headless silently execute *different* provisioning. (§3.2's own example is already lossy/divergent — see P2-8.)

*Why it matters*: Two sources of truth with no reconciliation is a classic latent-bug factory; here it splits behavior across the exact two execution modes that are hardest to test together.

*Fix*: (1) Make the lock a pure derived artifact with a checksum of the source: store `source_sha256` of `setup.yaml` in the lock; headless refuses to run (or warns loudly) if `sha256(setup.yaml) != lock.source_sha256`. (2) Specify *who* generates it and add a conformance check to the skill-authoring lint (P… see Next Steps). (3) Drop "LLM emits it once" as anything but an emergency path.

---

**P1-5 · There is no declared home for execution-plane policy thresholds — but §4.3 forbids putting them in scripts.**

*Location*: §4.3 ("Never hard-code the policy number into the script"), §6.5 (`gate-counter sessions_active`, execution-plane), §9.1 ("Move the *limit* into `setup.yaml`/skill config").

*Problem*: `setup.yaml` is the **provisioning** manifest (§3.1); its only policy knob is `on_failure.max_retries` (a setup-retry limit). But the counter family is largely **execution-plane** (`sessions_active`, danger thresholds). §4.3 insists those limits must live in config, not code — yet the framework defines *no execution-plane config file*. §9.1 tells cc-tmux to "move the limit into setup.yaml/skill config," but setup.yaml is the wrong lifecycle and "skill config" is undefined.

*Why it matters*: cc-tmux is the first migration target and its real policy (session caps, kill rules) is execution-time. The framework's central "measure in script, set limit in config, apply in LLM" rule (§4.3) has nowhere to put the execution-time limit.

*Fix*: Introduce an explicit execution-plane policy surface (e.g. `policy.yaml` or a `policy:` block read by the engine, parallel to `setup.yaml`) and state that gate-counter thresholds for the execution plane live there. Update §9.1 to point at it.

---

**P1-6 · The nesting invariant ("can't be RUNNING and BROKEN at once") is single-process, but the doc explicitly supports concurrent sessions; and `exec.lock` granularity is per-skill, over-serializing concurrent skills.**

*Location*: §5.3 ("You cannot be RUNNING and BROKEN simultaneously — the nesting forbids it"), §3.6 (explicit cron + interactive concurrency), §2.1 / §5.5 (`$XDG_RUNTIME_DIR/srof/<skill>/exec.lock`).

*Problem*:
- Provisioning state is **shared per-skill** (one `provisioning.json`); execution is per-session. With concurrent sessions (which §3.6 explicitly enables), Session A can be `RUNNING` while Session B enters, re-verifies, and computes `BROKEN`. B's `BROKEN` doesn't (and can't easily) tear down A's in-flight action in another process. So `RUNNING` and `BROKEN` **do** coexist across sessions. The invariant holds only within one process.
- `exec.lock` is keyed **per-skill** (`srof/<skill>/exec.lock`). For a multi-session skill like cc-tmux — whose entire purpose is many concurrent panes/sessions — a per-skill lock serializes *all* concurrent use to one action at a time. The lock should usually be per-*resource* (per pane/target), as §6.7's `lock_free:NAME` actually allows (`srof/${name}.lock`), but §2.1/§5.5 fix it at per-skill.

*Why it matters*: The concurrency model and the nesting invariant are stated as if single-process; the rest of the doc (and the first migration target) is multi-session. They contradict.

*Fix*: (1) Scope the nesting invariant explicitly to a single execution context, and define cross-session BROKEN semantics (A keeps its lock and finishes/aborts; B parks; provisioning regression is observed at *each* session's entry). (2) Make execution lock granularity a manifest choice (`lock_scope: skill | resource:<key>`), defaulting cc-tmux to per-resource.

---

### P2 — Should fix

**P2-1 · Crash-without-reboot wedges locks; "ephemeral ⇒ crash-safe" is overstated.** (§3.6 `trap 'rmdir' EXIT`, §2.1/§5.5, claims at lines 116/284/456/607.) `trap … EXIT` does **not** fire on `SIGKILL`/power loss. "Released on crash too" is only true at *reboot* (tmp cleared). Between reboots, a SIGKILL'd provisioning/exec process leaves `provision.lock`/`exec.lock` held → skill wedged — the exact deadlock the design claims to prevent. *Fix*: write owner PID into the lock dir; on contended acquire, check liveness (`kill -0`) and reclaim if dead. mkdir-atomicity alone is insufficient for crash-safety.

**P2-2 · State writes aren't atomic, despite the claim.** (§4.4 "writes `provisioning.json` atomically"; §8.2 line 698 uses plain `>`.) `>` truncates-then-writes → torn reads / empty file on crash. Interactive re-verify (§8.3) reads the file **without** taking `provision.lock` → read/during/write race. *Fix*: write to `.tmp` + `mv` (atomic rename on POSIX); document that readers may read lock-free *because* writes are atomic-rename.

**P2-3 · "Self-healing" only heals *absence*, not *invalidity*.** (§3.5, §10 item 5.) Cheap re-verify is `env_exists:KEY` (present?) not "key works." An expired-but-present API key passes every cheap gate → stays `PROVISIONED` → fails at actual use. Only the expensive `ping` catches it, and §3.5 says skip expensive checks. *Fix*: allow a verify to be marked re-runnable-and-cheap-enough for validity (a cheap authenticated probe), or add a TTL that forces a periodic deep re-verify. Stop claiming it self-heals revoked credentials when it only detects missing ones.

**P2-4 · `vault` is undefined.** (§3.1 `source_order: [vault, env, human]`, §3.4, §9.2.) The secret-store leg — load-bearing for headless seeding and the agent-reach story — has no interface, command, or contract. Consequence: headless can't seed secrets, so agent-reach (input+confirm steps) can **never** fully provision from cron; it always parks at `configure-key`. The "safe to attempt from cron" claim (§3.4) doesn't hold for the motivating skill. *Fix*: define the vault contract (a command returning a secret by key, exit-coded) or delete `vault` and say headless requires env-seeded secrets.

**P2-5 · The safety-critical gates have no reference implementation.** (§8.1 lists `gate-danger.sh`, `gate-verify.sh`, `gate-counter.sh`; only `gate-check.sh` §6.7 is shown.) `gate-danger` is the *only* family that emits `block` — the entire safety model rests on it — and ships zero reference code. Given P0-1, the absence of a `gate-verify` reference is also where the verify-input gap hides. *Fix*: provide reference `gate-danger.sh` and `gate-verify.sh` to the §6.4 envelope; they'll surface the missing contracts.

**P2-6 · The reference gate conflates "broken (exit 1)" with "`block` verdict" — the exact thing §6.3 forbids.** (§6.7 lines 577, 589: `emit block human …; exit 1`.) §6.3 says exit≠0 ⇒ verdict untrustworthy. Emitting a meaningful `block` *and* exit 1 is self-contradictory: respect it or ignore it? *Fix*: choose — either "can't determine" → exit 1 with verdict irrelevant (recommended for `version_gte` read-failure and unknown-target), or "determined it's unsafe" → exit 0 + `block`. Never both.

**P2-7 · `cheap: true` is used but never defined.** (§3.5 "a fast `ping` if declared `cheap: true`" vs §3.1 schema, which has no `cheap` field.) Re-verify-on-entry depends on knowing which verifies are cheap; the field is absent from the manifest. *Fix*: add `cheap: bool` to the step/verify schema in §3.1.

**P2-8 · `setup.lock.json` projection rules are unspecified and the example is internally lossy.** (§3.2: `install-cli` has run+when+verify; `configure-key` has only id/kind/verify — no run/when — yet §8.2 reads `.run`/`.when` for every step.) What gets projected vs dropped is undefined, and the example would break §8.2 for an input step that ever became auto. *Fix*: specify the projection as total (all fields the runner reads) and regenerate the example.

**P2-9 · The headless exit-code taxonomy (20/21/22) has no specified consumer.** (§3.4, §8.2.) Plain cron has no supervisor to map exit 20 → "surface to human"; the resume loop's driver is unnamed. *Fix*: name the consumer (the supervising orchestrator / `skill_view` on next entry) and define the exit-code → action mapping in one table.

**P2-10 · Retry-counter persistence is unspecified.** (§4.3 `gate-counter retries:install-cli`.) Where the count lives, who increments it, and how a *pure* gate reads a count that the engine produced is undefined. If the LLM both increments and reads-via-gate, the "fact" is circular (engine fabricating its own sensor input). *Fix*: state that the actuator-runner increments a counter in ephemeral `runtime.json`, and `gate-counter` reads *that file* (pure observation of persisted state).

---

### P3 — Nice to have

**P3-1 · Length/redundancy.** 808 lines is *acceptable* for the scope — do **not** split. But the one principle is restated ~6× (§0, §1.2, §1.3, §4.1, §6.1, §7, §10) and §0/§7/§10 overlap heavily. Trim ~15–20% of restatement; keep the single canonical statement in §1.2 and cross-reference it.

**P3-2 · Drafting bug in staleness triggers.** §3.5 line 270 lists "(a) … and (c) …" — **(b) is missing**, implying a dropped trigger (a time-based TTL would fit, and would also address P2-3). Restore or renumber.

**P3-3 · Minor losses vs v0.1.** v0.1's optional-prerequisite semantics (`required: false → setup creates it`, v0.1 §2 for `settings.json`) has no v1.0 equivalent — v1.0 prerequisites are pass/fail gates with no "absent-but-creatable" path. Also v0.1's per-step human `name:` labels dropped (cosmetic). Re-add the "optional/creatable prerequisite" path.

**P3-4 · A dead scenario in §5.3.** "If a re-verify flips `PROVISIONED → BROKEN` while a task is mid-flight" — but re-verify only runs *on entry* (§3.5), never mid-action within one process. Either the scenario can't occur (remove it) or there's an intended mid-flight re-verify mechanism that's unspecified (add it). (Cross-session, the real version of this is P1-6.)

**P3-5 · `version_gte` runs `$cmd --version` with no timeout** (§6.7 line 576) — can hang, and for arbitrary `$cmd` is not guaranteed side-effect-free, lightly straining the purity claim. Add a timeout; note the caveat.

---

## Focus-Area Q&A (direct answers)

1. **Does the script/LLM division actually hold?** In the *interactive* path, yes (it's genuinely LLM-driven). In the *headless* path, **no** — `setup.sh --auto` is a script acting as an engine (sequencing, policy, transitions) while §1.2 says scripts are "sensors and actuators, nothing else." The doc never reconciles this. → **P0-2**, **P1-5** (policy with no home), **P1-1** (script applying skip policy on an unimplemented predicate).

2. **Is the gate interface pure enough? Any mutating gate?** The *reference* gates (§6.7) are observation-only — purity holds *there*. But the interface is **under-pure in the wrong direction**: `verify` gates need the actuator's output and there's no input channel, so an "honest" implementation would have to **re-execute** (e.g. re-`register`) — a *mutation* smuggled into a verify. → **P0-1**. Also §6.7 conflates broken/`block` (**P2-6**).

3. **Are the state machines correct? Can PROVISIONED/RUNNING coexist with BROKEN?** Single-process: the nesting is coherent and the invariant holds. **Multi-session (which the doc explicitly supports): no** — `RUNNING` (session A) and `BROKEN` (session B's view of shared provisioning state) coexist. → **P1-6**. Plus a dead mid-flight scenario (**P3-4**).

4. **Is BLOCKED_ON_INPUT implementable in headless cron? Does self-describe work?** Parking + exit 20 is implementable; **the self-describe does not close the loop** because the blocked state is printed to stdout, never persisted, so "the next session resumes" can't read it. And for the motivating skill, headless can't get *past* the first input step at all without a defined `vault`. → **P1-3**, **P2-4**, **P2-9**.

5. **Race conditions in lock/atomic ops? mkdir is atomic — what about jq reads?** `mkdir` mutex is correct *for liveness only*; it is **not crash-safe** under SIGKILL (**P2-1**). The **state file** is the real race: non-atomic `>` writes (**P2-2**) + lock-free reads during writes → torn reads. The jq *reads* in §8.2 are within the provision lock; the *interactive re-verify read* (§8.3) is not. → **P2-1**, **P2-2**.

6. **Is `setup.lock.json` generation actually build-time? Who/when?** **Under-specified.** No skill build system exists; the doc falls back to "LLM emits once, committed," with no drift detection vs `setup.yaml`. → **P1-4**, **P2-8**.

7. **Does the cc-tmux migration make sense? What breaks?** Partially. The lock-stays-ephemeral split is right. But (a) cc-tmux's real policy is *execution-plane* with no declared home (**P1-5**); (b) per-skill `exec.lock` over-serializes cc-tmux's inherently concurrent sessions (**P1-6**); (c) cc-tmux's durable provisioning state is near-empty (just `command_exists:claude/tmux`, cheaply re-verified anyway), so the migration adds bookkeeping for little gain (minor).

8. **Missing error cases? Gate exits 1 (broken) during PROVISIONING?** This is a real hole. §8.2 treats a broken `when`-gate as "not satisfied → **proceed**" (unsafe), has **no** prerequisite phase, **no** `block` handling, and **no** retry-before-BROKEN — directly contradicting §6.3's "never assume pass." → **P0-2(c)**, **P2-6**.

9. **Is 808 lines too long? Split?** No — length is justified by scope; **don't split**. Trim ~15–20% of restated principle and the §0/§7/§10 overlap. → **P3-1**.

10. **Did v1.0 lose anything vs v0.1?** Net improvement, small losses: optional-creatable prerequisites (`required:false`), per-step `name:` labels (**P3-3**), and crisper problem-statement framing. Nothing architecturally important was lost; v1.0's gains (two lifecycles, `fail`/`block` authority, cache+BROKEN, BLOCKED_ON_INPUT, resolved decisions) clearly dominate. The one *regression in rigor*: v0.1 was honestly a discussion doc; v1.0 presents broken reference code (§8.2) with the confidence of a spec — a stale-confidence risk worth a banner until P0-2 is fixed.

---

## Recommended fix order (P0/P1 only)

1. **P0-1 + P2-5** together: define the verify-gate input contract (`$SROF_RUN_RESULT`), split re-query vs last-result verifies, and write the `gate-verify.sh`/`gate-danger.sh` references — the missing references *are* where the contract gaps live.
2. **P0-2**: rewrite §8.2 as an explicit "degraded-mode engine" that replicates prerequisites, retry-to-policy, safe-default-on-broken-gate, and the full §5.5 state write; fix `GATE()` to branch on `[ -x local ]` not exit code.
3. **P1-1**: pick the positive-only gate vocabulary, redefine `when` (fail→run, pass→skip), give every mutating step a `when`.
4. **P1-2**: specify the no-plaintext-through-the-LLM secret channel (`$SROF_INPUT_FILE`).
5. **P1-3**: persist `BLOCKED_ON_INPUT` (+need/fix) to `provisioning.json` before exit 20; define who reads it on resume.
6. **P1-4**: add `source_sha256` to the lock + a refuse/warn-on-drift check; name the generator.
7. **P1-5**: add the execution-plane policy surface; repoint §9.1.
8. **P1-6**: scope the nesting invariant to one execution context; make lock granularity (`lock_scope`) a manifest choice.

Once 1–8 are closed and a `gate-check`/`gate-verify` conformance test (§11 step 1) passes against the §6.4 envelope, this moves from CONDITIONAL PASS to PASS.

---

*Audit complete. Architecture: sound. Contract surface and the single reference implementation: not yet buildable. Fix the eight items above before any code.*
