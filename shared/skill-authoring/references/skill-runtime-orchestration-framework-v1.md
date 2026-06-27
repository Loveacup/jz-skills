# Skill Runtime Orchestration Framework (SROF) — Design Document

> **Status**: Design v1.0 (supersedes Draft v0.1)
> **Date**: 2026-06-27
> **Context**: First-principles redesign of skill orchestration for Hermes Agent, grounded in the Agent-Reach self-describing-setup pattern and the cc-tmux script-gate / LLM-decision split.
> **Relationship to v0.1**: This is a *redesign*, not a revision. v0.1 conflated two lifecycles and left five decisions open; v1.0 separates the lifecycles and resolves all five. Section 10 records the honest delta.

---

## 0. 中文摘要(给 Alex 的逐决策结论)

v0.1 有两处"补丁味",v1.0 从第一性原理重构:

1. **一条主原则统领全局**:**LLM 是编排引擎,脚本是它的传感器(gate)和执行器(action)。** 这条原则一旦确立,v0.1 里纠结的 `yq` 依赖、iii substrate 耦合、用户 prompt 归谁管,全部自动溶解——脚本永远只收原始字符串参数、只吐 JSON,清单(manifest)只给 LLM 和人读,**没有任何脚本需要解析 YAML**。

2. **两个嵌套生命周期**取代 v0.1 的扁平状态机:
   - 外层 **Provisioning**(开通):罕见、持久、幂等。回答"这个技能在本环境**能不能用**"。
   - 内层 **Execution**(执行):每次调用、易失、高频。回答"**此刻这个动作**准不准跑"。

3. 补上 v0.1 缺的三处要害:
   - `BLOCKED_ON_INPUT` 态:headless/cron 下需要人给 API key 时有地方"停泊"并自描述,而不是失败。
   - `fail` vs `block` 的真正区别 = **谁有权清除闸门**:`fail` agent 自己能修;`block` 只有人能放行。
   - **状态文件是"已完成昂贵动作"的缓存,不是"技能可用"的证明**;每次进入用廉价 gate 重新 verify,杜绝 stale-READY 类 bug。

五道裁决(详见 §7,此处只给结论):
- **D-1 状态存哪**:按**生命周期**而非作用域切分。持久 provisioning 状态 → 技能本地 `.state/`;易失锁/运行态 → `/tmp`(崩溃后必须自动消失,否则死锁)。中央审计视图**派生扫描得到,不作为真相源**。
- **D-2 清单格式**:YAML,但**没有脚本解析它**(LLM 即解释器),依赖问题消失。headless 路径解析的是构建期产出的 `setup.lock.json`(只用 `jq`)。
- **D-3 prompt 归谁**:混合,形式化为 step `kind: auto|input|confirm`。脚本保持纯粹,人机对话 100% 归 LLM。
- **D-4 iii/substrate**:天然 substrate 无关——gate 是纯函数、原始参数进 JSON 出、零 Hermes 耦合,任何 runtime 共用同一份 gate 库。
- **D-5 gate 复用**:库 + 本地覆盖。通用原语(`command_exists` 等)进中央库;技能专属危险模式留本地并按名遮蔽。

以下为完整技术正文(沿用 v0.1 英文,保持与代码库与前作连续)。

---

## 1. First Principles

### 1.1 The two questions a skill must answer

Before any skill does its job, two — and exactly two — orthogonal questions must be answered. v0.1's central mistake was answering them with one mechanism.

| | **Provisioning** ("can it run *at all*?") | **Gating** ("may *this action* run *now*?") |
|---|---|---|
| Scope | Per-environment (machine/profile) | Per-action (live world state) |
| Lifetime | Persistent across sessions | Ephemeral; cleared when the action ends |
| Frequency | Rare (once per env, or on breakage) | Constant (every gated action) |
| Example | "Is `agent-reach` installed? Is the API key set? Is XHS logged in?" | "Is another session holding the tmux lock? Is this command destructive?" |
| Idempotent? | Yes — re-running is cheap and safe | N/A — it observes, it doesn't change state |
| On failure | Remediate (install, configure) and re-check | Halt the action; do not 'fix' the world to force a pass |

These are **two nested control loops at different timescales**, not a single linear path. The rest of this document is organized around that separation:

- The **Provisioning plane** is Focus Area #1 (first-run setup) and owns the *outer* state machine.
- The **Execution plane** is Focus Areas #2 + #4 (division of labor + gate interface) and owns the *inner* state machine.
- Focus Area #3 (the state machine) is the explicit nesting of the two.

### 1.2 The one principle that resolves everything

> **The LLM is the orchestration engine. Scripts are its sensors and actuators. Nothing else.**

- **Sensors** = gates (`gate-check`, `gate-verify`, `gate-danger`, `gate-counter`). They *observe* the world and report a verdict. They never change it.
- **Actuators** = the `run:` commands of setup steps and skill actions. They *change* the world. They do not decide *whether* to.
- **Engine** = the LLM. It reads the declarative manifest, sequences steps, calls sensors and actuators, interprets ambiguity, talks to the human, and decides risk.

Everything in SROF is a corollary of this one sentence.

### 1.3 What the principle immediately dissolves

The principle is worth stating because it makes three of v0.1's hardest open questions evaporate before we even reach §7:

1. **The `yq` dependency (was D-2) disappears.** If the LLM is the interpreter of the manifest, then *no script ever parses the manifest*. Scripts receive only primitive targets like `command_exists:tmux`. The manifest's only readers are the human author (YAML is friendliest) and the LLM (reads YAML natively). There is nothing left to need `yq`. v0.1's `setup.sh` tried to be a YAML interpreter in bash — we simply delete that responsibility.

2. **Substrate coupling (was D-4) disappears.** A sensor that takes a primitive string and emits JSON on stdout has *zero* coupling to Hermes. iii workers, cron jobs, or any runtime call the identical gate binary. SROF is "a manifest convention + a portable gate/state library," not a Hermes subsystem.

3. **"Who handles the user prompt?" (was D-3) disappears.** Talking to a human is a *decision/prose* activity; by the principle it belongs wholly to the engine (LLM). The script for an interactive step stays pure and merely consumes the value the LLM injects. No script ever blocks on `read`.

What the principle does **not** dissolve — and what the rest of the doc must specify carefully — is the *contract surface* between engine and sensors/actuators: the gate I/O format (§6), the state file (§5.5), and the rules for placing a node on the hard plane vs the soft plane (§4).

---

## 2. Architecture: Two Nested Lifecycles

### 2.1 Revised component map

```
┌──────────────────────────── Skill Directory ────────────────────────────┐
│  SKILL.md                  frontmatter + body (always loaded)            │
│  setup.yaml                Provisioning manifest — LLM-facing (no parser) │
│  setup.lock.json           Build-time JSON projection — headless-facing   │
│  scripts/                                                                  │
│    ├─ gate-check.sh        precondition sensor   (setup-time)             │
│    ├─ gate-verify.sh       post-action sensor    ("did it work?")         │
│    ├─ gate-danger.sh       safety sensor         (emits block-class)       │
│    ├─ gate-counter.sh      measurement sensor    (counts; manifest judges) │
│    ├─ setup.sh             headless actuator-runner (--auto path only)     │
│    └─ <skill actions>.sh   the skill's real work (actuators)              │
│  references/               progressive-disclosure detail                  │
│  .state/                   DURABLE provisioning state (gitignored)         │
│    └─ provisioning.json    cache of completed expensive actions           │
└───────────────────────────────────────────────────────────────────────────┘

Ephemeral, OUTSIDE the skill dir (must not survive a crash):
  $XDG_RUNTIME_DIR/srof/<skill>/   or   /tmp/srof/<skill>/
    ├─ exec.lock                atomic lock (mkdir/flock) for the running action
    └─ runtime.json             current execution sub-state

  ┌──────────────── Engine (LLM) — the orchestrator ─────────────┐
  │  reads setup.yaml · sequences · interprets · talks to human  │
  │  calls sensors (gates) and actuators (run:) · decides risk    │
  └───────────────────────────────────────────────────────────────┘
```

Two things moved relative to v0.1 and both are deliberate (see §7, D-1):

- **Durable** provisioning state stays skill-local in `.state/` — it travels with the skill and must persist.
- **Ephemeral** execution state (locks!) lives in a runtime dir that the OS clears on reboot. **A lock in a persistent `.state/` would turn a crash into a permanent deadlock.** That is the single most important storage decision in the whole framework.

### 2.2 The two planes

| | **Provisioning plane** | **Execution plane** |
|---|---|---|
| Owns | `setup.yaml`, `setup.sh --auto`, `gate-check`, `.state/provisioning.json` | skill actions, `gate-verify/danger/counter`, `runtime/` lock |
| Outer state machine | §5.1 | — |
| Inner state machine | — | §5.2 |
| Trigger | skill first use, or staleness/breakage | every gated action during a task |
| Terminal good state | `PROVISIONED` | `IDLE` (between actions) |

The planes meet at exactly one point: **the execution plane only runs when the provisioning plane is in `PROVISIONED`.** If provisioning regresses (key revoked → `BROKEN`), the execution sub-machine is torn down (§5.3).

---

## 3. First-Run Setup Configuration  *(Focus Area #1)*

### 3.1 The manifest: `setup.yaml`

The manifest is **declarative and LLM-facing**. It describes *what readiness means* and *what steps establish it*, never *how to parse itself*. Changes from v0.1: every step gains a `kind` (auto/input/confirm) so headless mode knows what it can and cannot do unattended; verify targets are namespaced gate calls (§6.5).

```yaml
# setup.yaml — Provisioning manifest. Read by the LLM and the human. No script parses this.
version: "1.0"
skill: agent-reach

# What must be true BEFORE provisioning can even start. Each is a gate target (§6.5).
prerequisites:
  - check: command_exists:node            # gate-check resolves this
    min: version_gte:node:18.0.0
  - check: command_exists:jq              # only hard dep of the headless path
  - check: env_exists:HOME

# Ordered, idempotent steps. Each step is: gate (when) → actuate (run) → gate (verify).
steps:
  - id: install-cli
    kind: auto                            # no human needed → headless-safe
    when:   command_missing:agent-reach   # skip if already satisfied (idempotency)
    run: |
      npm install -g @panniantong/agent-reach
    verify: command_exists:agent-reach

  - id: configure-key
    kind: input                           # needs a human-supplied secret
    when:   env_missing:AGENT_REACH_API_KEY
    input:                                # the LLM obtains this; the script consumes $SROF_INPUT
      label: "Agent-Reach API key"
      hint:  "Get one at https://agent-reach.dev/settings"
      secret: true                        # never echo to transcript/state
      source_order: [vault, env, human]   # try a secret store, then env, then ask
    run: |
      umask 077; printf 'AGENT_REACH_API_KEY=%s\n' "$SROF_INPUT" >> "$HOME/.agent-reach/env"
    verify: env_exists:AGENT_REACH_API_KEY

  - id: test-connection
    kind: auto
    run:    agent-reach ping
    verify: exit_code:0

  - id: register-skill
    kind: confirm                         # writes to a remote; require human OK once
    confirm:
      prompt: "Register this skill with the agent-reach hub? (one-time, writes remote state)"
    run:    agent-reach skill --register ./SKILL.md
    verify: json_path:.registered==true

# Policy lives HERE (declarative), measurement lives in the script (§4.3).
on_failure:
  default: report_and_halt                # report_and_halt | retry | skip
  max_retries: 2                          # the THRESHOLD is policy → manifest
```

Step `kind` is the formalization of v0.1's ad-hoc `prompt:` field:

| `kind` | Human needed? | Headless behavior | Engine responsibility |
|---|---|---|---|
| `auto` | no | runs unattended | call actuator, then verify |
| `input` | yes (a value) | → `BLOCKED_ON_INPUT`, self-describe what it needs | obtain value via `source_order`, inject as `$SROF_INPUT` |
| `confirm` | yes (a yes/no) | → `BLOCKED_ON_INPUT` | get explicit human authorization before actuating |

### 3.2 `setup.lock.json` — the headless parse target

The *interactive* path never parses YAML (the LLM reads it). But a *headless* `setup.sh --auto` (cron, iii worker) has no LLM in the loop and must execute deterministically. Rather than reintroduce a YAML parser, SROF ships a **denormalized JSON projection** of `setup.yaml`, produced at skill build/publish time (or, in a pinch, by the LLM once and committed):

```json
{
  "skill": "agent-reach", "version": "1.0",
  "prerequisites": [{"check": "command_exists:node", "min": "version_gte:node:18.0.0"}],
  "steps": [
    {"id":"install-cli","kind":"auto","when":"command_missing:agent-reach",
     "run":"npm install -g @panniantong/agent-reach","verify":"command_exists:agent-reach"},
    {"id":"configure-key","kind":"input","verify":"env_exists:AGENT_REACH_API_KEY"}
  ],
  "on_failure": {"default":"report_and_halt","max_retries":2}
}
```

The only tool that ever parses this is `jq`, which is already this user's near-universal dependency. This is the clean resolution of the format debate (§7, D-2): **YAML for humans and the LLM; a generated JSON lock for the dependency-light headless runner.**

### 3.3 Orchestration — the interactive path (LLM-driven)

This is the normal path and it is *pure LLM orchestration*. There is no master `setup.sh` doing sequencing; the LLM is the sequencer.

```
On skill entry, if provisioning is not PROVISIONED:
  1. For each prerequisite p:  call gate-check p
        block/fail → halt, report exactly what's missing, stop.
  2. For each step s in order:
        a. if s.when present:  call gate-check s.when
              pass (already satisfied) → record skipped, continue
        b. switch s.kind:
              auto    → (nothing to gather)
              input   → obtain value via s.input.source_order; inject as $SROF_INPUT
              confirm → ask the human for explicit authorization; no → halt
        c. run s.run (the actuator)
        d. call gate-verify s.verify
              pass → mark step done in provisioning.json (memoize the action)
              fail → apply on_failure (retry ≤ max_retries, else halt; see §4.3)
  3. All steps verified → write state PROVISIONED.
```

Every line above maps cleanly onto §1.2: gates are sensors, `run` is an actuator, the switch/decide/retry logic is the engine. Nothing here needs a YAML parser.

### 3.4 Orchestration — the headless path (`setup.sh --auto`)

For cron/iii where no human is present:

```bash
setup.sh --auto:
  load setup.lock.json (jq)
  for each step:
    if when satisfied → skip
    if kind != auto AND required input not already available (vault/env):
        emit  {"state":"BLOCKED_ON_INPUT","need":"<step.id>","reason":"...","fix":"<hint>"}
        exit 20            # distinct code: not an error, a self-described pause
    run; verify
  on all-pass → write PROVISIONED
```

The critical behavior v0.1 lacked: **a headless setup that hits an `input`/`confirm` step does not fail — it *parks* in `BLOCKED_ON_INPUT` and self-describes the missing piece** (exit 20). A supervising orchestrator (or the next interactive session) sees `need: configure-key`, surfaces "帮我配 agent-reach 的 key" to the human, and resumes. This is what makes setup safe to attempt from a cron job.

### 3.5 Idempotency & staleness: the state file is a *cache*, not a *proof*

v0.1's `setup.sh` early-exits when `provisioning.json` says `state: READY`. That blindly trusts a stale file: if the API key was revoked yesterday, the skill is broken but still claims READY.

First-principles correction:

> **`provisioning.json` records that an *expensive action* completed. It does NOT assert that the skill currently works. Whether it works is re-established by the (cheap) verify gates on each entry.**

So on entry to a PROVISIONED skill, the engine:
- **skips** expensive *actions* it has memoized (don't re-`npm install`, don't re-`register`),
- **re-runs** cheap *verifications* (`command_exists`, `env_exists`, a fast `ping` if declared `cheap: true`).

If a re-verify fails → transition `PROVISIONED → BROKEN` (§5.1) and re-provision only the broken step. This converts a class of silent "stale READY" failures into a self-healing re-check. Staleness also triggers on **(a)** manifest `version` change and **(c)** explicit reset.

### 3.6 Concurrency: provisioning needs its own lock

With both cron and interactive sessions potentially touching one skill, two provisioning runs can race (double `npm install -g`, half-written env file). Provisioning therefore acquires an **atomic** provisioning lock before mutating:

```bash
LOCK="$XDG_RUNTIME_DIR/srof/agent-reach/provision.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo '{"state":"PROVISIONING","reason":"another run holds the lock"}'; exit 21
fi
trap 'rmdir "$LOCK"' EXIT          # released on crash too — ephemeral by design
```

`mkdir` is atomic on POSIX filesystems, so this is a correct mutex with no extra dependency. The lock lives in the *ephemeral* runtime dir, not `.state/`, so a crash mid-install cannot wedge the skill permanently.

---

## 4. Script / LLM Division of Labor  *(Focus Area #2)*

### 4.1 The invariant

> **Scripts emit *facts* and *verdicts*. The LLM emits *decisions* and *prose*.**
> A script must never encode policy. The LLM must never assert a world-fact it did not obtain from a script (or tool).

The second clause is the anti-hallucination guard: the agent may not *claim* "tmux is installed" or "the lock is free" from its own belief — only by quoting a gate's verdict. This matters acutely for a destructive-action gate, where a hallucinated "looks safe" is how you kill the wrong session.

### 4.2 A falsifiable test for placing a node

For any orchestration node X, ask: *is X's answer a deterministic function of observable world state with one correct value?*

- **Yes → it is a fact → put it in a script (sensor).** ("Is port 8080 free?", "Did `ping` exit 0?", "How many retries so far?")
- **No → it requires weighing ambiguity, intent, or risk tolerance → keep it in the LLM (engine).** ("Should we retry or abort?", "Is force-killing that session acceptable?", "Did the user really mean *this* platform?")

This test is mechanical; it removes the guesswork from "should this be a script or a prompt?".

### 4.3 The dangerous middle: the threshold rule

The hard case is a fact with a *policy threshold* baked in — e.g. "give up after 3 retries." Naively this looks like one node, but it is two:

> **The script *measures*; the manifest *sets the limit*; the LLM *applies* it.**
> Never hard-code the policy number into the script.

```
gate-counter retries:install-cli      →  {"verdict":"pass","evidence":{"count":3}}   # FACT
setup.yaml: on_failure.max_retries: 2                                                 # POLICY
LLM: 3 > 2  → stop retrying, halt, report                                            # DECISION
```

This is why cc-tmux's `gate-counter.sh` *counts* but does not *decide* — the limit is configuration, the comparison is the engine's. Bake the `2` into the script and you can no longer change policy without editing code, and two skills can't share the counter.

### 4.4 Responsibility table (revised)

| Concern | Hard plane (script / sensor) | Soft plane (LLM / engine) |
|---|---|---|
| **Can it run?** (preconditions) | `gate-check` returns pass/fail/block | reads the verdict; decides to remediate or halt |
| **What to do & in what order** | — | sequences steps from the manifest |
| **Gather human input/secret** | consumes `$SROF_INPUT` (pure) | conducts the conversation; sources the secret |
| **Did it work?** | `gate-verify` runs the check, parses output | interprets a genuinely ambiguous result; decides retry |
| **Is it safe to proceed?** | `gate-danger` matches patterns → `block` | risk-assesses; obtains human authority to clear a `block` |
| **How many times tried?** | `gate-counter` counts (fact) | compares to manifest limit (policy) and acts |
| **Persist state** | writes `provisioning.json` atomically | decides *when* a transition is warranted |
| **Acquire a lock** | atomic `mkdir`/`flock` (actuator) | decides whether contending for the lock is worth it |

### 4.5 Worked example — a gated destructive setup action

`register-skill` writes remote state; suppose a variant must first *delete* a stale remote registration.

```
1. LLM intends: re-register (delete old, write new).
2. gate-danger remote_delete:agent-reach-hub
      → {"verdict":"block","authority":"human","reason":"irreversible remote delete"}   [FACT]
3. LLM may NOT self-clear a block. It surfaces the reason and asks the human.            [DECISION]
4. Human authorizes.  LLM records authorization, proceeds.                                [DECISION]
5. run: agent-reach skill --reregister                                                    [ACTUATOR]
6. gate-verify json_path:.registered==true → pass                                         [FACT]
7. LLM marks step done.                                                                   [DECISION]
```

Note the clean separation: the script *detected* danger and *refused to pass*; only the human (authority) could clear it; the LLM never overrode the verdict, only carried the authorization.

---

## 5. State Machine  *(Focus Area #3)*

Two machines, nested. The inner one exists only inside the outer's `PROVISIONED` state.

### 5.1 Outer: the Provisioning lifecycle

```
                 reset / version-bump / staleness
        ┌──────────────────────────────────────────────┐
        │                                                ▼
        │                                       ┌─────────────────┐
        │                  start provisioning   │  UNPROVISIONED  │
        │            ┌──────────────────────────┤ (no/stale state)│
        │            ▼                           └─────────────────┘
        │   ┌─────────────────┐
        │   │   PROVISIONING  │  needs human input (headless) ┌──────────────────┐
        │   │ (running steps) ├──────────────────────────────►│ BLOCKED_ON_INPUT │
        │   └────────┬────────┘◄──────────────────────────────┤ (self-describes  │
        │            │           human supplies value/confirm └──────────────────┘
        │            │ all verify pass
        │            ▼
        │   ┌─────────────────┐   re-verify fails on entry   ┌──────────────────┐
        └───┤   PROVISIONED   ├─────────────────────────────►│      BROKEN      │
            │ (skill usable)  │◄─────────────────────────────┤ (was OK, now not)│
            └─────────────────┘   re-provision broken step   └──────────────────┘
                     │
                     │  enter execution plane (§5.2)
                     ▼
              [inner sub-machine]
```

| State | Meaning |
|---|---|
| `UNPROVISIONED` | No state file, or it is stale (version changed / explicit reset). |
| `PROVISIONING` | Steps executing; provisioning lock held. |
| `BLOCKED_ON_INPUT` | **(new)** A step needs a human value/confirm; headless runs park here and self-describe (`need`, `fix`). |
| `PROVISIONED` | All steps verified. The only state in which the skill may execute. |
| `BROKEN` | **(new, ≠ generic ERROR)** A previously-passing verify now fails (revoked key, deleted file). Re-provision the broken step only. |

### 5.2 Inner: the Execution sub-machine (only within `PROVISIONED`)

```
        ┌───────┐  action requested   ┌────────┐ gates pass ┌─────────┐
        │ IDLE  ├────────────────────►│ GATING ├───────────►│ RUNNING │
        │       │◄────────────────────┤        │            │         │
        └───────┘   gate fail (no-op) └───┬────┘            └────┬────┘
            ▲                              │ gate → block         │ done
            │                              ▼                      │
            │                         ┌─────────┐                 │
            └─────────────────────────┤ HALTED  │◄────────────────┘
              human clears / abort     │ (block) │  fatal action error
                                       └─────────┘
```

| State | Meaning | Enforced by | Decided by |
|---|---|---|---|
| `IDLE` | Provisioned, between actions | state = PROVISIONED | LLM picks next action |
| `GATING` | Evaluating gates for the pending action | gates run | LLM chose to attempt the action |
| `RUNNING` | Gates passed; actuator executing; `exec.lock` held | a `pass` from every gate | LLM judged the action worth doing |
| `HALTED` | A gate returned `block`; awaiting human authority or abort | `block` verdict | LLM/human decides clear-vs-abort |

### 5.3 Nesting and teardown

- The execution sub-machine is **instantiated on entry to `PROVISIONED` and destroyed on exit.** If a re-verify flips `PROVISIONED → BROKEN` while a task is mid-flight, the current action is halted, `exec.lock` released, and control returns to the provisioning plane. You cannot be `RUNNING` and `BROKEN` simultaneously — the nesting forbids it.
- `BLOCKED_ON_INPUT` is *provisioning-scoped*; `HALTED` is *execution-scoped*. v0.1's single `ERROR` blurred these. Keeping them distinct means a blocked setup ("need a key") and a halted action ("refusing to kill that pane") are reported, stored, and resumed by different mechanisms.

### 5.4 Transition table — who enforces / who decides

| Transition | Enforced by (script = hard fact) | Decided by (LLM = soft) |
|---|---|---|
| `UNPROVISIONED → PROVISIONING` | provisioning lock acquired (`mkdir`) | engine chooses to provision now vs defer |
| `PROVISIONING → BLOCKED_ON_INPUT` | step `kind∈{input,confirm}` ∧ value absent | — (mechanical, then engine sources the value) |
| `BLOCKED_ON_INPUT → PROVISIONING` | value/confirm now present | engine (or human) supplied it |
| `PROVISIONING → PROVISIONED` | every `verify` gate returns pass | engine judged steps complete |
| `PROVISIONING → BROKEN` | a step fails after `max_retries` (policy from manifest) | engine applied the retry policy (§4.3) |
| `PROVISIONED → BROKEN` | an on-entry re-verify gate fails | — (mechanical); engine then re-provisions |
| `BROKEN → PROVISIONING` | — | engine/human chooses to repair |
| `* → UNPROVISIONED` | manifest version changed / explicit reset | human or build process |
| `IDLE → GATING → RUNNING` | every gate returns pass | engine chose the action |
| `GATING → IDLE` | a gate returns fail (precondition unmet) | engine decides remediate-or-drop |
| `RUNNING/GATING → HALTED` | a gate returns block | — (block is binding); engine reports |
| `HALTED → RUNNING` | human authority recorded | human authorized; engine carries it |
| `RUNNING → IDLE` | actuator exited 0 (verify pass) | engine judged the task done |

### 5.5 State persistence schema

**Durable** — `.state/provisioning.json` (skill-local, gitignored). Records memoized actions + last verdicts; it is a cache (§3.5), not a proof.

```json
{
  "skill": "agent-reach",
  "manifest_version": "1.0",
  "state": "PROVISIONED",
  "state_since": "2026-06-27T06:00:00Z",
  "steps": {
    "install-cli":   {"status":"done","memoized":true,"last_verify":"pass","at":"..."},
    "configure-key": {"status":"done","memoized":true,"last_verify":"pass","at":"..."},
    "register-skill":{"status":"done","memoized":true,"last_verify":"pass","at":"..."}
  },
  "run_count": 3
}
```

**Ephemeral** — `$XDG_RUNTIME_DIR/srof/<skill>/runtime.json` (+ `exec.lock`, `provision.lock`). Holds the execution sub-state and lock ownership. Wiped on reboot by design — a lock that outlives its process is a deadlock, never a feature.

> Secrets are **never** written to either file. `input` values with `secret: true` go only to their real destination (e.g. `~/.agent-reach/env`, `umask 077`); state stores `{"status":"done"}`, not the value.

---

## 6. Gate Script Interface  *(Focus Area #4)*

### 6.1 A gate is a pure function

> A gate is a **pure, side-effect-free function** `world_state → {verdict, evidence}`.
> It *observes*; it never *mutates*. Installing, acquiring a lock, writing a file — those are **actuators**, not gates.

Purity is what makes gates safe to call repeatedly, in any order, in dry-run, and from any runtime. It is also what makes SROF substrate-agnostic (§7, D-4): a pure stdin/args → stdout/JSON function has nothing Hermes-specific to couple to.

### 6.2 Verdict semantics: `pass` / `fail` / `block` — the missing definition

v0.1 listed three verdicts but never said what separates `fail` from `block`. The distinction is the whole point, and it is about **authority to clear**:

| Verdict | Meaning | Who may clear it | Engine's obligation |
|---|---|---|---|
| `pass` | Precondition satisfied / action permitted | — | proceed |
| `fail` | Precondition **not** met, but expected & fixable | **the agent** | may remediate (install, configure) and re-gate |
| `block` | Hard safety stop (danger pattern, irreversible op, exclusive lock held) | **only a human** | must NOT auto-remediate; surface reason; get explicit authorization |

`fail` is *not* an error — it is a negative-but-actionable fact ("CLI missing"). `block` is a refusal the agent is forbidden to override on its own. Encoding "who can clear it" as the dividing line makes the verdict machine-actionable rather than advisory.

### 6.3 Exit code vs verdict — gate *health* vs gate *answer*

> **Exit code reports whether the gate could determine an answer. The JSON verdict reports the answer.** They are independent.

```
exit 0  +  verdict pass/fail/block   → the gate worked; trust the verdict
exit ≠0                              → the gate is BROKEN / could not determine
```

This decoupling (correctly anticipated in v0.1) is essential: it lets the engine distinguish **"the check says no"** (`block`, exit 0 → respect it) from **"the check itself is broken"** (exit 1 → investigate/escalate; crucially, do **not** assume pass). Conflating them — e.g. `exit 1` for "fail" — would make a broken gate indistinguishable from a negative result, and the safe default (treat-unknown-as-block) impossible to express.

### 6.4 The JSON envelope

Single line of JSON to stdout. stderr is for human/debug logs and is never parsed.

```jsonc
{
  "gate":     "check|verify|danger|counter",   // which sensor family
  "target":   "command_exists:tmux",            // the primitive arg, echoed
  "verdict":  "pass|fail|block",
  "authority":"agent|human|none",               // who may clear a non-pass (see §6.2)
  "reason":   "human-readable explanation",
  "evidence": { "count": 3, "found": "/usr/bin/tmux" }  // optional structured facts
}
```

`authority` is new vs v0.1 and makes the fail/block semantics explicit: a `fail` carries `authority:agent` (agent may clear), a `block` carries `authority:human`.

### 6.5 Namespaced targets & the gate taxonomy

Targets are `namespace:argument[:argument]`, parsed by trivial prefix-strip (no parser dependency). The taxonomy maps onto cc-tmux's existing scripts:

| Sensor | Family | Typical targets | Verdict bias |
|---|---|---|---|
| `gate-check.sh` | preconditions (setup-time) | `command_exists:X`, `env_exists:X`, `file_exists:X`, `port_free:N`, `version_gte:X:V`, `lock_free:NAME` | pass / **fail** |
| `gate-verify.sh` | post-action ("did it work?") | `exit_code:0`, `json_path:.k==v`, `http_ok:URL` | pass / **fail** |
| `gate-danger.sh` | safety | `remote_delete:X`, `kill_pane:self`, `rm_rf:PATH`, `force_push:branch` | pass / **block** |
| `gate-counter.sh` | measurement | `retries:STEP`, `sessions_active`, `age_seconds:FILE` | always **pass** + `evidence.count` |

Rule of thumb encoded above: `gate-danger` is the *only* family that emits `block`; `gate-counter` *never* emits a non-pass (it reports a number, the engine judges it — §4.3).

### 6.6 Library + local override resolution

> Universal primitives live in a **central library**; skill-specific gates live **local** and shadow central ones by name.

```
resolve gate-check:
  1. $SKILL_DIR/scripts/gate-check.sh     # skill-specific override, if present
  2. $SROF_LIB/gate-check.sh              # central shared library (default)
```

- **Central** (`$SROF_LIB`): `command_exists`, `env_exists`, `file_exists`, `version_gte`, `port_free`, `lock_free` — generic, identical everywhere, shared by Hermes and iii alike.
- **Local** (`$SKILL_DIR/scripts`): danger patterns are inherently skill-specific (cc-tmux's "never kill the orchestrator pane" is meaningless to another skill), so they belong with the skill and shadow any central namesake.

This is ordinary stdlib + project override — no novelty, which is the point.

### 6.7 Reference implementation — `gate-check.sh` (revised)

```bash
#!/usr/bin/env bash
# gate-check.sh — precondition sensor. PURE: observes, never mutates.
# Usage: gate-check.sh <namespace:arg[:arg]>
# Stdout: one line of JSON. Exit 0 = determined; exit 1 = could-not-determine.
set -euo pipefail

TARGET="${1:-}"

emit() { # verdict authority reason [evidence-json]
  printf '{"gate":"check","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "${4:-{}}"
}

case "$TARGET" in
  command_exists:*)
    cmd="${TARGET#command_exists:}"
    if path="$(command -v "$cmd" 2>/dev/null)"; then
      emit pass none "command '$cmd' found" "{\"found\":\"$path\"}"
    else
      emit fail agent "command '$cmd' not found"      # agent may install → fail, not block
    fi ;;

  env_exists:*)
    var="${TARGET#env_exists:}"
    if [ -n "${!var:-}" ]; then emit pass none "env '$var' set"
    else emit fail agent "env '$var' not set"; fi ;;

  file_exists:*)
    f="${TARGET#file_exists:}"
    if [ -f "$f" ]; then emit pass none "file exists" "{\"path\":\"$f\"}"
    else emit fail agent "file '$f' not found"; fi ;;

  version_gte:*)                                       # version_gte:node:18.0.0
    rest="${TARGET#version_gte:}"; cmd="${rest%%:*}"; want="${rest#*:}"
    if ! have="$("$cmd" --version 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)+' | head -1)"; then
      emit block human "cannot read version of '$cmd'"; exit 1   # could-not-determine
    fi
    lowest="$(printf '%s\n%s\n' "$want" "$have" | sort -V | head -1)"
    if [ "$lowest" = "$want" ]; then emit pass none "$cmd $have >= $want" "{\"have\":\"$have\"}"
    else emit fail agent "$cmd $have < $want" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  lock_free:*)
    name="${TARGET#lock_free:}"; lock="${XDG_RUNTIME_DIR:-/tmp}/srof/${name}.lock"
    if [ -d "$lock" ]; then emit block human "lock '$name' held by another session"
    else emit pass none "lock '$name' free"; fi ;;     # NOTE: observe only — acquiring is an actuator

  *)
    emit block human "unknown check target"; exit 1 ;; # unknown → can't determine → exit 1
esac
```

### 6.8 The purity rule and the lock exception

`lock_free` *observes* whether a lock is held; it must not *acquire* it. Acquisition is a state change → an actuator, and it must be **atomic** (`mkdir`/`flock`, §3.6) to be correct under concurrency. Keeping observation (gate) and acquisition (actuator) separate is what lets the engine *check then decide then act*, and what keeps every gate replay-safe. Any gate that mutates is a bug.

---

## 7. Resolved Decisions  *(was: Open Questions D-1…D-5)*

These are decided, not offered as a menu. Each gives the forces, the verdict, and the consequence.

### D-1 — State storage: **split by lifetime, not by scope**

- **Forces.** Provisioning state must persist and travel with the skill. Locks must *not* persist — a lock surviving a crash is a permanent deadlock. v0.1 framed this as "local vs central," which is the wrong axis.
- **Decision.** Durable provisioning state → **skill-local `.state/provisioning.json`** (gitignored, co-located, no global coupling). Ephemeral execution state + locks → **`$XDG_RUNTIME_DIR/srof/<skill>/`** (OS-cleared on reboot). A central audit index (`~/.hermes/state/`) is **derived by scanning, never authoritative.**
- **Consequence.** A crash mid-action cannot wedge the skill; provisioning survives reboots; auditing is possible without a second source of truth. The one rule to remember: *never put a lock in `.state/`.*

### D-2 — Manifest format: **YAML, parsed by no one but the LLM**

- **Forces.** A script-parsed YAML needs `yq`; JSON is dependency-light but author-hostile; frontmatter embedding bloats the always-loaded SKILL.md.
- **Decision.** Manifest is **YAML, LLM-facing**; *no script parses it* (§1.3). The headless runner parses a build-time **`setup.lock.json`** projection with `jq` only. Frontmatter embedding rejected — multi-platform auth manifests are long and would violate progressive disclosure.
- **Consequence.** Zero new dependency; humans get readable YAML; headless gets deterministic JSON; SKILL.md stays lean.

### D-3 — Prompt handling: **hybrid, formalized as step `kind`**

- **Forces.** Some steps are fully automatable; some need a secret; some need a yes/no for an irreversible action.
- **Decision.** Each step declares `kind: auto | input | confirm` (§3.1). Scripts stay pure (`$SROF_INPUT`); the human conversation is 100% the LLM's; headless parks `input/confirm` in `BLOCKED_ON_INPUT`.
- **Consequence.** Setup is headless-safe *and* interactively rich, from one manifest. Direct corollary of the §4.1 invariant (talking to humans is a decision → LLM).

### D-4 — iii / substrate: **agnostic by construction**

- **Forces.** Hermes and iii workers both provision skills; duplicating the mechanism invites drift.
- **Decision.** Because gates are pure, primitive-in/JSON-out, and Hermes-free, **iii and Hermes call the identical gate binaries** via a shared `$SROF_LIB`. SROF is "manifest convention + portable gate/state library." Hermes contributes only *policy* (its skill_view decides *when* to provision).
- **Consequence.** One gate library, two+ runtimes, no adapter layer.

### D-5 — Gate reusability: **library + local override, split by universality**

- **Forces.** `command_exists` is universal; danger patterns are skill-specific. Forcing either fully-central or fully-local is wrong.
- **Decision.** Universal primitives in **central `$SROF_LIB`**; skill-specific gates **local**, shadowing central by name; resolution local → central (§6.6).
- **Consequence.** No re-implementing `command_exists` per skill; danger logic stays with the skill that understands it.

---

## 8. Reference Implementation

### 8.1 File tree of a SROF skill

```
agent-reach/
├── SKILL.md                 # frontmatter declares setup_manifest
├── setup.yaml               # LLM-facing manifest (§3.1)
├── setup.lock.json          # build-time JSON projection (§3.2)
├── scripts/
│   ├── setup.sh             # headless --auto runner (§3.4)
│   ├── gate-danger.sh       # skill-specific safety (local override)
│   └── <actions>.sh         # the skill's real work
├── .state/                  # gitignored, durable
│   └── provisioning.json    # cache of completed actions (§5.5)
└── references/

$SROF_LIB/                   # shared, one copy for Hermes + iii
├── gate-check.sh            # universal precondition primitives (§6.7)
├── gate-verify.sh
└── gate-counter.sh
```

### 8.2 `setup.sh --auto` skeleton (headless path)

```bash
#!/usr/bin/env bash
# setup.sh — headless provisioning runner. Interactive setup is LLM-driven, not this.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/srof/$(basename "$SKILL_DIR")/provision.lock"
mkdir -p "$(dirname "$LOCK")"
mkdir "$LOCK" 2>/dev/null || { echo '{"state":"PROVISIONING","reason":"locked"}'; exit 21; }
trap 'rmdir "$LOCK"' EXIT

LOCK_JSON="$SKILL_DIR/setup.lock.json"
GATE() { "$SKILL_DIR/scripts/${1}.sh" "$2" 2>/dev/null || \
         "${SROF_LIB:?set SROF_LIB}/${1}.sh" "$2"; }   # local → central (§6.6)

steps_len=$(jq '.steps|length' "$LOCK_JSON")
for i in $(seq 0 $((steps_len-1))); do
  step=$(jq -c ".steps[$i]" "$LOCK_JSON")
  id=$(jq -r '.id'   <<<"$step"); kind=$(jq -r '.kind'   <<<"$step")
  when=$(jq -r '.when//empty' <<<"$step")
  verify=$(jq -r '.verify//empty' <<<"$step")

  # idempotency: skip if `when` already satisfied
  if [ -n "$when" ] && [ "$(GATE gate-check "$when" | jq -r .verdict)" = pass ]; then continue; fi

  # headless cannot satisfy human-input steps → park & self-describe
  if [ "$kind" != auto ]; then
    printf '{"state":"BLOCKED_ON_INPUT","need":"%s","fix":"run interactively to supply input"}\n' "$id"
    exit 20
  fi

  bash -c "$(jq -r '.run' <<<"$step")"                 # actuator
  if [ -n "$verify" ] && [ "$(GATE gate-verify "$verify" | jq -r .verdict)" != pass ]; then
    printf '{"state":"BROKEN","step":"%s","reason":"verify failed"}\n' "$id"; exit 22
  fi
done

# write durable cache (NOT a proof of health — re-verified on each entry, §3.5)
mkdir -p "$SKILL_DIR/.state"
jq -n --arg s "$(basename "$SKILL_DIR")" \
  '{skill:$s,state:"PROVISIONED"}' > "$SKILL_DIR/.state/provisioning.json"
echo '{"state":"PROVISIONED"}'
```

### 8.3 `SKILL.md` frontmatter integration

```yaml
---
name: agent-reach
description: "Use when researching/searching the web across 13 platforms…"
type: routine
version: 1.0.0
setup_needed: true              # existing flag — now load-bearing
setup_manifest: setup.yaml      # NEW: where readiness is defined
srof_lib: ${SROF_LIB}           # NEW: shared gate library location
required_commands: [jq]         # only the headless path's hard dep
---
```

Engine load logic (replaces v0.1's blind early-exit):

```
on skill_view(skill):
  if not skill.setup_needed: proceed
  elif skill.has_manifest():
     reverify cheap gates           # state file is a cache, not a proof (§3.5)
     if PROVISIONED and gates pass: proceed
     else: run provisioning (interactive: LLM-driven §3.3 | headless: setup.sh --auto §3.4)
  else:                             # legacy skill, no manifest
     warn("requires setup but no setup.yaml — agent will improvise")
```

---

## 9. Migration Path & Backward Compatibility

### 9.1 cc-tmux (already has the gate pattern)

| Current cc-tmux | SROF migration |
|---|---|
| `gate-verify.sh`, `gate-danger.sh`, `gate-counter.sh` | Keep verbatim — they already match §6's families. Just ensure each emits the `verdict`+`authority`+exit-code contract. |
| `gate-counter.sh` hard-codes limits | Move the *limit* into `setup.yaml`/skill config; counter keeps only the *count* (§4.3). |
| `.state/` in `/tmp` | Split: durable bits → skill-local `.state/`; the session **lock** stays in `/tmp` (correct — it must be ephemeral, §3.6, D-1). |
| `cc-start.sh` does lock + session setup | Extract pre-flight precondition checks into `setup.yaml` steps (`kind: auto`); keep lock acquisition as an actuator. |
| implicit setup | Add a small `setup.yaml`: prerequisite `command_exists:claude`, `command_exists:tmux`. |

### 9.2 agent-reach (the motivating case)

The §3.1 manifest *is* the agent-reach migration: per-platform login becomes `kind: input` steps with `source_order: [vault, env, human]`, so "帮我配小红书" maps to the `BLOCKED_ON_INPUT → input` flow. Zero API fees preserved — every `run:` is an existing CLI call.

### 9.3 Backward compatibility

Skills **without** `setup.yaml` are untouched: the engine sees no manifest and falls back to "warn + improvise" exactly as today. SROF is strictly opt-in; adoption is per-skill and incremental.

---

## 10. Honest Delta — what v0.1 got right, what v1.0 changes

**Kept from v0.1 (it was right):**
- "Scripts enforce, LLM decides"; file-based state; idempotent `when`; per-step `verify`; gitignored `.state/`; the exit-code-independent-of-verdict insight; the agent-reach self-describing-setup framing.

**Changed (first-principles corrections):**
1. **One flat state machine → two nested lifecycles** (provisioning ⊃ execution). v0.1's `READY→ACTIVE→READY` was an execution loop smuggled into a provisioning machine.
2. **`setup.sh` as YAML interpreter → deleted.** The LLM is the interpreter; scripts take primitives. Kills the `yq` dependency entirely.
3. **Added `BLOCKED_ON_INPUT`.** Headless/cron setup now parks and self-describes instead of failing — essential for this user's cron/iii workloads.
4. **Defined `fail` vs `block`** = authority-to-clear (agent vs human). v0.1 listed them without distinguishing them; added the `authority` JSON field.
5. **State file reframed as a *cache*, not a *proof*.** Re-verify cheap gates on entry → self-heals stale-READY; added `BROKEN`.
6. **Concurrency made explicit** (atomic provisioning lock). v0.1 ignored two sessions racing.
7. **All five open questions resolved** (§7), per the "decide, don't offer a menu" preference.

---

## 11. Next Steps

1. **Prototype the contract, not the skill.** Implement `$SROF_LIB/gate-check.sh` + `gate-verify.sh` to the §6 envelope; write a 6-line conformance test (each target → expected verdict + exit code).
2. **Migrate cc-tmux first** (it already has gates) — proves the library/override split (§6.6) and the lock-stays-ephemeral rule (D-1).
3. **Then agent-reach** — proves `kind: input` + `BLOCKED_ON_INPUT` + `source_order` end to end ("帮我配小红书").
4. **Add the `setup.lock.json` generator** to the skill build step (or have the LLM emit it once, committed).
5. **Update the `skill-authoring` skill** with the SROF section: manifest schema, gate contract, the §4.2 placement test.
6. **Wire Hermes `skill_view`** to the §8.3 load logic (re-verify, not blind early-exit).

---

## Appendix A — Agent-Reach Pattern Analysis (retained)

> "Agent 读了 SKILL.md 之后自己知道该调什么。需要登录的平台（小红书、Twitter、Reddit），告诉 Agent「帮我配 XXX」即可解锁。"

Mapped to SROF:
1. **Self-describing setup** → the `setup.yaml` manifest *is* the self-description; the LLM reads it directly.
2. **Conversational unlock** ("帮我配 XXX") → user intent maps to a `kind: input` step; headless surfaces it as `BLOCKED_ON_INPUT.need`.
3. **Platform-specific auth** → `source_order: [vault, env, human]` per step handles differing flows.
4. **Zero API fees** → every `run:` is an existing CLI call; gates are pure local observations.

## Appendix B — Glossary

| Term | Meaning |
|---|---|
| **Gate / sensor** | Pure function observing world state → verdict. Never mutates. (§6.1) |
| **Actuator** | A command that changes the world (`run:`, lock acquire). Decides nothing. |
| **Engine** | The LLM: sequences, interprets, converses, decides risk. |
| **Provisioning** | Outer lifecycle: "can this skill run at all?" Persistent, rare, idempotent. |
| **Execution** | Inner lifecycle: "may this action run now?" Ephemeral, frequent. |
| **`pass/fail/block`** | Verdicts; `fail` = agent may clear, `block` = only a human may. (§6.2) |
| **`BLOCKED_ON_INPUT`** | Provisioning parked awaiting a human value/confirm; self-describes. (§5.1) |
| **`BROKEN`** | A previously-passing verify now fails; re-provision the broken step. (§5.1) |
| **State file = cache** | Records completed actions, not current health; re-verified on entry. (§3.5) |

---

*SROF v1.0 — first-principles redesign. Produced by Hermes Agent (小黄) + CC, 2026-06-27. Supersedes v0.1.*
