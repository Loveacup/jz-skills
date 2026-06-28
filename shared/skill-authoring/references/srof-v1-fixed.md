# Skill Runtime Orchestration Framework (SROF) — Design Document

> **Status**: Design v1.1 (supersedes v1.0; closes the independent audit's P0/P1)
> **Date**: 2026-06-28
> **Context**: First-principles redesign of skill orchestration for Hermes Agent, grounded in the Agent-Reach self-describing-setup pattern and the cc-tmux script-gate / LLM-decision split.
> **Relationship to v1.0**: v1.1 keeps v1.0's architecture intact (two nested lifecycles, sensor/actuator/engine triad, fail-vs-block-as-authority, state-file-as-cache + re-verify-on-entry) and fixes only the *contract surface* the audit found unbuildable. Both P0 blockers (the verify-gate input contract; the unsafe headless runner) and all six P1s are closed, plus folded P2-1/P2-2/P2-6 and P3-1. §12 is the finding→fix map.

---

## 0. 中文摘要(给 Alex 的逐决策结论)

v1.1 不动 v1.0 的骨架,只焊死审计指出的合同面。一句话:**v1.0 的模型对,合同没接上;v1.1 把合同接上了。**

唯一主原则(§1.2 为权威出处,全文只此一处完整陈述):**LLM 是编排引擎,脚本是它的传感器(gate)和执行器(actuator),没有别的。**

v1.1 的四个关键修复(其余见 §12):

1. **`$SROF_RUN_RESULT` 结果合同(闭 P0-1)**:verify 之所以不可实现,是因为新起的纯函数 gate 看不到刚跑完的 actuator 的输出。修法:所有 `run:` 一律经 `srof-run.sh` 执行,它把 actuator 的 stdout+exit **原子写入** `$SROF_RUN_RESULT`(已知路径)。verify 词表一分为二:**(a) 重查类**(`command_exists`/`http_ok`/`status_json`,幂等自洽,交 `gate-check`)与 **(b) 末次结果类**(`exit_code`/`result_json`,读 `$SROF_RUN_RESULT`,交 `gate-verify`)。**凡重跑会改世界的,禁用 (b);注册一律用 `--status` 读校验,绝不重新 `--register`。** 交互与 headless 两条路现在共用同一份合同。

2. **headless `setup.sh` 重写为"降级引擎"(闭 P0-2)**:它不再假装只是脚本,而是显式承担引擎职责——先跑前置闸(prereq),按 lock.json 里的 `max_retries`(策略仍是数据)重试,**坏闸即停**(任何非 `pass`/`fail` 裁决或 exit≠0 → HALT,绝不"当通过"),并写完整 §5.5 状态(含 `steps{}` memo)。"本地闸缺失"(`[ -x ]` 回退中央)与"本地闸跑挂"(坏闸 → 停)严格区分。

3. **`when` 语义纠偏 + 正向词表(闭 P1-1)**:删掉根本不存在的 `command_missing`/`env_missing`。`when` 读作"**已满足就跳过**":gate **PASS → SKIP**(已就绪),**FAIL → RUN**(未就绪)。每个写状态的步骤(尤其 `register-skill`)都补上 `when`。

4. **机密通道 `$SROF_INPUT_FILE`(闭 P1-2)**:机密明文**永不**过 LLM。人/vault 把机密写进 `umask 077` 临时文件,LLM 只引用**路径**,actuator 读文件。禁止把机密插值进命令串。这是 `secret: true` 的唯一正路。

还补齐:`BLOCKED_ON_INPUT` 落盘后才 `exit 20`(闭 P1-3,跨会话才真能 resume);`setup.lock.json` 带 `source_sha256` 防漂移、命名生成器 `srof-lock`(闭 P1-4);新增执行面策略文件 `policy.yaml`(闭 P1-5);嵌套不变式收窄到单执行上下文 + `lock_scope` 可选(闭 P1-6);PID 存活回收锁、`.tmp`+`mv` 原子写状态(闭 P2-1/P2-2);坏闸不再同时 `block`+exit≠0,改用 `unknown`+exit≠0(闭 P2-6)。

五道裁决(§7,结论不变):D-1 按生命周期切状态;D-2 YAML 无脚本解析(headless 读 jq-only 的 lock,**构建期** yq 生成);D-3 prompt 形式化为 `kind`;D-4 substrate 无关;D-5 库+本地覆盖。

以下为完整技术正文(沿用 v1.0 英文,保持与代码库与前作连续;未受修复影响的散文按原样保留)。

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

- **Sensors** = gates (`gate-check`, `gate-verify`, `gate-danger`, `gate-counter`). They *observe* the world (or a captured result file) and report a verdict. They never change the world.
- **Actuators** = the `run:` commands of setup steps and skill actions, executed through `srof-run` (§6.8). They *change* the world. They do not decide *whether* to.
- **Engine** = the LLM. It reads the declarative manifest, sequences steps, calls sensors and actuators, interprets ambiguity, talks to the human, and decides risk.

This is the single canonical statement of the principle. Everywhere else in SROF that "scripts observe / the LLM decides" appears, it is a *corollary of this sentence* and cross-references here rather than restating it. The one bounded exception is the headless `setup.sh` (§3.4), which is explicitly a **degraded-mode engine substitute** — a script that inherits the engine's sequencing duties because no LLM is in the loop.

### 1.3 What the principle immediately dissolves

The principle makes three of v0.1's hardest open questions evaporate before §7:

1. **The `yq` dependency (was D-2) disappears at runtime.** If the LLM is the interpreter of the manifest, then *no shipped runtime script parses the manifest*. Scripts receive only primitive targets like `command_exists:tmux`. The manifest's only readers are the human author (YAML is friendliest) and the LLM (reads YAML natively). The headless runner reads a JSON *lock* with `jq` only; the lock is produced **at authoring/build time** by `srof-lock` (§8.3), which may use `yq` — a build-time-only dependency that never ships in the runtime path.

2. **Substrate coupling (was D-4) disappears.** A sensor that takes a primitive string (plus, for last-result verifies, the path in `$SROF_RUN_RESULT`) and emits JSON on stdout has *zero* coupling to Hermes. iii workers, cron jobs, or any runtime call the identical gate binary. SROF is "a manifest convention + a portable gate/state library," not a Hermes subsystem.

3. **"Who handles the user prompt?" (was D-3) disappears.** Talking to a human is a *decision/prose* activity; by the principle it belongs wholly to the engine (LLM). The script for an interactive step stays pure and merely consumes the value the LLM *located* — and for secrets it consumes a file *path* it is handed, never the plaintext (§3.7). No script ever blocks on `read`.

What the principle does **not** dissolve is the *contract surface* between engine and sensors/actuators. v1.0 named this as the thing to specify and then under-specified it; v1.1 nails each piece: the gate I/O envelope (§6.4), **the actuator→verify result contract `$SROF_RUN_RESULT`** (§6.8), the secret channel `$SROF_INPUT_FILE` (§3.7), the state file (§5.5), and the rule for placing a node on the hard plane vs the soft plane (§4.2).

---

## 2. Architecture: Two Nested Lifecycles

### 2.1 Revised component map

```
┌──────────────────────────── Skill Directory ────────────────────────────┐
│  SKILL.md                  frontmatter + body (always loaded)            │
│  setup.yaml                Provisioning manifest — LLM-facing (no runtime parser) │
│  setup.lock.json           Build-time JSON projection + source_sha256 (headless) │
│  policy.yaml               EXECUTION-plane policy — engine-facing (NEW, §3.8)     │
│  scripts/                                                                  │
│    ├─ gate-check.sh        precondition + re-query sensor                  │
│    ├─ gate-verify.sh       last-result sensor (reads $SROF_RUN_RESULT)     │
│    ├─ gate-danger.sh       safety sensor (the only emitter of `block`)     │
│    ├─ gate-counter.sh      measurement sensor (reads runtime.json)         │
│    ├─ srof-run.sh          actuator-runner: runs `run:`, writes result     │
│    ├─ setup.sh             headless degraded-mode engine (--auto only)     │
│    └─ <skill actions>.sh   the skill's real work (actuators)              │
│  references/               progressive-disclosure detail                  │
│  .state/                   DURABLE provisioning state (gitignored)         │
│    └─ provisioning.json    cache of completed actions + parked-input state │
└───────────────────────────────────────────────────────────────────────────┘

Ephemeral, OUTSIDE the skill dir (must not survive a crash):
  $XDG_RUNTIME_DIR/srof/<skill>/   or   /tmp/srof/<skill>/
    ├─ provision.lock/          atomic lock dir; holds owner.pid (liveness reclaim)
    ├─ exec.lock  (or  <resource>.lock)   per lock_scope (§3.8, P1-6)
    ├─ result.json              $SROF_RUN_RESULT — captured stdout-path + exit_code
    ├─ <step>.out / <step>.err  captured actuator streams
    ├─ secret.XXXXXX            umask-077 secret file ($SROF_INPUT_FILE, §3.7)
    └─ runtime.json             execution sub-state + retry counters + sessions_active

Build/authoring time only (never shipped in the runtime path):
  srof-lock                     setup.yaml → setup.lock.json (+ source_sha256), uses yq

  ┌──────────────── Engine (LLM) — the orchestrator ─────────────┐
  │  reads setup.yaml · sequences · interprets · talks to human  │
  │  calls sensors (gates) and actuators (srof-run) · decides risk │
  └───────────────────────────────────────────────────────────────┘
```

Two things moved relative to v0.1 and both are deliberate (see §7, D-1):

- **Durable** provisioning state stays skill-local in `.state/` — it travels with the skill and must persist. It now also holds the **parked** `BLOCKED_ON_INPUT` record so a later session can resume (§5.5, P1-3).
- **Ephemeral** execution state (locks, result file, secret file) lives in a runtime dir that the OS clears on reboot. **A lock in a persistent `.state/` would turn a crash into a permanent deadlock.** That is the single most important storage decision in the whole framework.

### 2.2 The two planes

| | **Provisioning plane** | **Execution plane** |
|---|---|---|
| Owns | `setup.yaml`, `setup.lock.json`, `setup.sh --auto`, `.state/provisioning.json`, `srof-lock` | `policy.yaml`, skill actions, `runtime/` lock(s), `result.json` |
| Sensors | `gate-check` (preconditions) | `gate-verify` (last-result), `gate-danger`, `gate-counter`; `gate-check` re-query verifies |
| Actuator-runner | `srof-run` | `srof-run` |
| Outer state machine | §5.1 | — |
| Inner state machine | — | §5.2 |
| Policy home | `setup.yaml` `on_failure.*` (provisioning-only) | `policy.yaml` (caps, kill rules, `lock_scope`) — P1-5 |
| Trigger | skill first use, or staleness/breakage | every gated action during a task |
| Terminal good state | `PROVISIONED` | `IDLE` (between actions) |

`gate-check` spans both planes because re-query verifies (class (a), §6.5) are the same kind of idempotent observation as preconditions; the actuator-runner `srof-run` is shared because both planes need the `$SROF_RUN_RESULT` contract.

The planes meet at exactly one point: **the execution plane only runs when the provisioning plane is in `PROVISIONED`.** If provisioning regresses (key revoked → `BROKEN`), the execution sub-machine is torn down (§5.3).

---

## 3. First-Run Setup Configuration  *(Focus Area #1)*

### 3.1 The manifest: `setup.yaml`

The manifest is **declarative and LLM-facing**. It describes *what readiness means* and *what steps establish it*, never *how to parse itself*. Changes from v1.0: positive-only gate vocabulary (P1-1); `when` on every state-mutating step; verify targets drawn from the split taxonomy (§6.5); `secret`/`cheap` fields surfaced per step; secrets consumed via `$SROF_INPUT_FILE` (§3.7). Execution-plane policy has moved to `policy.yaml` (§3.8).

```yaml
# setup.yaml — Provisioning manifest. Read by the LLM and the human. No runtime script parses this.
version: "1.1"
skill: agent-reach

# What must be true BEFORE provisioning can even start. Each is a gate target (§6.5).
prerequisites:
  - check: command_exists:node            # gate-check resolves this
    min: version_gte:node:18.0.0
  - check: command_exists:jq              # only hard dep of the headless path
  - check: env_exists:HOME

# Ordered, idempotent steps. Each step is: when-guard (skip?) → actuate (run) → verify.
# `when` reads as "skip WHEN this already holds": gate PASS → SKIP, FAIL → RUN. (P1-1)
steps:
  - id: install-cli
    kind: auto                            # no human needed → headless-safe
    when:   command_exists:agent-reach    # already present → skip the install (idempotency)
    cheap:  true                          # re-verifiable on entry without cost (§3.5, P2-7)
    run: |
      npm install -g @panniantong/agent-reach
    verify: command_exists:agent-reach    # class (a) re-query

  - id: configure-key
    kind: input                           # needs a human-supplied secret
    when:   env_exists:AGENT_REACH_API_KEY  # already configured → skip
    secret: true
    cheap:  true
    input:                                # the LLM LOCATES this; the actuator reads $SROF_INPUT_FILE
      label: "Agent-Reach API key"
      hint:  "Get one at https://agent-reach.dev/settings"
      env:   AGENT_REACH_API_KEY          # headless env-seed source (P2-4)
      key:   agent-reach/api_key          # headless vault key (if SROF_VAULT_GET set)
      source_order: [vault, env, human]   # try a secret store, then env, then ask
    run: |                                # NO secret interpolation; read the file by PATH (§3.7)
      umask 077; mkdir -p "$HOME/.agent-reach"
      { printf 'AGENT_REACH_API_KEY='; cat "$SROF_INPUT_FILE"; } >> "$HOME/.agent-reach/env"
    verify: status_json:'agent-reach config get api_key --json'::.set==true  # re-query, no leak

  - id: test-connection
    kind: auto
    cheap:  false                         # a network probe; skip on cheap-only re-verify
    run:    agent-reach ping
    verify: exit_code:0                   # class (b) last-result → reads $SROF_RUN_RESULT (§6.8)

  - id: register-skill
    kind: confirm                         # writes to a remote; require human OK once
    # skip if already registered — an IDEMPOTENT status read, never a re-register (P1-1, P0-1)
    when:   status_json:'agent-reach skill --status ./SKILL.md'::.registered==true
    confirm:
      prompt: "Register this skill with the agent-reach hub? (one-time, writes remote state)"
    run:    agent-reach skill --register ./SKILL.md
    # verify by RE-QUERYING status, NEVER by re-running --register (would mutate). (P0-1)
    verify: status_json:'agent-reach skill --status ./SKILL.md'::.registered==true

# Provisioning-plane policy ONLY (declarative). Execution policy lives in policy.yaml (§3.8).
on_failure:
  default: report_and_halt                # report_and_halt | retry | skip
  max_retries: 2                          # the THRESHOLD is policy → manifest data, never code
```

Step `kind` is the formalization of v0.1's ad-hoc `prompt:` field:

| `kind` | Human needed? | Headless behavior | Engine responsibility |
|---|---|---|---|
| `auto` | no | runs unattended | call actuator (via `srof-run`), then verify |
| `input` | yes (a value) | try vault/env seed; else → `BLOCKED_ON_INPUT`, persist + self-describe | locate value via `source_order`; land it in a umask-077 file; set `$SROF_INPUT_FILE` (§3.7) |
| `confirm` | yes (a yes/no) | → `BLOCKED_ON_INPUT` (no human to authorize) | get explicit human authorization before actuating |

### 3.2 `setup.lock.json` — the headless parse target (TOTAL projection + drift guard)

The *interactive* path never parses YAML (the LLM reads it). A *headless* `setup.sh --auto` (cron, iii worker) has no LLM and must execute deterministically. SROF ships a **denormalized JSON projection** of `setup.yaml`, produced at build time by `srof-lock` (§8.3). Two v1.1 fixes:

- **Drift guard (P1-4).** The lock carries `source_sha256` = `sha256(setup.yaml)`. The headless runner refuses to run if `sha256(setup.yaml) != lock.source_sha256` (§8.2), so editing the YAML and forgetting to regenerate cannot silently split interactive vs headless behavior.
- **Total projection (P2-8).** The lock contains **every field the runner reads** — `id, kind, when, run, verify, secret, cheap, input` per step, plus `prerequisites, on_failure, version, skill, source_sha256`. No field the runner needs is ever absent.

```json
{
  "skill": "agent-reach",
  "version": "1.1",
  "source_sha256": "9f2c…(sha256 of setup.yaml at generation time)",
  "prerequisites": [
    {"check": "command_exists:node", "min": "version_gte:node:18.0.0"},
    {"check": "command_exists:jq"},
    {"check": "env_exists:HOME"}
  ],
  "steps": [
    {"id":"install-cli","kind":"auto","when":"command_exists:agent-reach",
     "run":"npm install -g @panniantong/agent-reach","verify":"command_exists:agent-reach",
     "secret":false,"cheap":true,"input":null},
    {"id":"configure-key","kind":"input","when":"env_exists:AGENT_REACH_API_KEY",
     "run":"umask 077; mkdir -p \"$HOME/.agent-reach\"; { printf 'AGENT_REACH_API_KEY='; cat \"$SROF_INPUT_FILE\"; } >> \"$HOME/.agent-reach/env\"",
     "verify":"status_json:'agent-reach config get api_key --json'::.set==true",
     "secret":true,"cheap":true,
     "input":{"env":"AGENT_REACH_API_KEY","key":"agent-reach/api_key","source_order":["vault","env","human"]}},
    {"id":"test-connection","kind":"auto","when":null,
     "run":"agent-reach ping","verify":"exit_code:0","secret":false,"cheap":false,"input":null},
    {"id":"register-skill","kind":"confirm",
     "when":"status_json:'agent-reach skill --status ./SKILL.md'::.registered==true",
     "run":"agent-reach skill --register ./SKILL.md",
     "verify":"status_json:'agent-reach skill --status ./SKILL.md'::.registered==true",
     "secret":false,"cheap":true,"input":null}
  ],
  "on_failure": {"default":"report_and_halt","max_retries":2}
}
```

The only tool that ever parses this is `jq`. This is the clean resolution of the format debate (§7, D-2): **YAML for humans and the LLM; a generated, checksummed JSON lock for the dependency-light headless runner.**

### 3.3 Orchestration — the interactive path (LLM-driven)

This is the normal path and it is *pure LLM orchestration*. There is no master `setup.sh` doing sequencing; the LLM is the sequencer. It executes every `run:` **through `srof-run`** so that the `$SROF_RUN_RESULT` contract (§6.8) holds identically to headless — which is what makes a `verify` mean the same thing in both paths (closing the P0-1 asymmetry).

```
On skill entry, if provisioning is not PROVISIONED (or a re-verify failed, §3.5):
  1. PREREQUISITE PHASE. For each prerequisite p: call gate-check p.check
        pass → continue
        fail → halt, report exactly what's missing, stop
        block / unknown (exit≠0) → halt (safe default §6.3 — never assume pass)
  2. For each step s in order:
        a. if s.when present: call gate-check s.when            # P1-1
              PASS (already satisfied) → record skipped, continue
              FAIL → fall through and run
              block / unknown (exit≠0) → halt (safe default §6.3)
        b. switch s.kind:
              auto    → (nothing to gather)
              input   → locate value via s.input.source_order; for secret:true, write it to a
                        umask-077 file and set $SROF_INPUT_FILE to its PATH — never hold the
                        plaintext in the conversation (§3.7). If the human defers, persist
                        BLOCKED_ON_INPUT(need=s.id) to .state and stop (resumable).
              confirm → ask for explicit authorization; no → persist BLOCKED_ON_INPUT / halt
        c. run s.run THROUGH srof-run  → writes $SROF_RUN_RESULT (§6.8)            [ACTUATOR]
        d. verify-dispatch s.verify (§6.5):
              exit_code:* | result_json:*  → gate-verify (reads $SROF_RUN_RESULT)  [class (b)]
              everything else              → gate-check  (re-observes the world)   [class (a)]
              pass → memoize step in provisioning.json (steps{} map, §5.5)
              fail → apply on_failure (retry ≤ max_retries, else halt; §4.3)
              block / unknown (exit≠0) → halt (safe default §6.3)
  3. All steps verified → write state PROVISIONED (full §5.5 schema incl. steps{}).
```

Every line maps onto §1.2: gates are sensors, `srof-run` is the actuator-runner, the switch/decide/retry logic is the engine. Crucially, the engine never *asserts* "exit was 0" from its own belief (the §4.1 anti-hallucination clause): the exit code is read from `$SROF_RUN_RESULT` by `gate-verify`, a script.

### 3.4 Orchestration — the headless path (`setup.sh --auto` = degraded-mode engine)

**`setup.sh --auto` is not "just a script."** With no LLM in the loop, it is a **degraded-mode engine substitute**: it inherits the engine's sequencing duties and therefore MUST replicate them. This is the one bounded relaxation of §1.2, and it is bounded to this single file. The duties it must replicate (each was missing in v1.0 — P0-2):

- **(a) Prerequisite phase.** Read `.prerequisites`; `fail` → BROKEN(need), `block`/`unknown` → halt. (v1.0 skipped this entirely.)
- **(b) Retry-to-policy.** Read `max_retries` from `setup.lock.json` (policy stays *data*); retry a `fail`ing verify up to that threshold; only then → BROKEN. (v1.0 went BROKEN on the first failure.)
- **(c) Safe default on a broken gate.** Any verdict that is not `pass`/`fail`, OR any gate exit≠0, → HALT. Distinguish **"local gate absent"** (`[ -x local ]` false → fall back to central) from **"local gate exited non-zero"** (broken → halt, never fall through). (v1.0 treated a broken gate as "not satisfied → proceed".)
- **(d) Full §5.5 state write.** On success, write the complete `steps{}` memoization map, not just `{state}`. (v1.0 erased memoization, forcing a full re-install/re-register every entry.)

Plus the v1.1 contract work: it executes via `srof-run` (so `$SROF_RUN_RESULT` is populated for last-result verifies), it persists `BLOCKED_ON_INPUT` *before* `exit 20` (P1-3), it checks `source_sha256` first (P1-4), and it uses PID-liveness lock reclaim + atomic state writes (P2-1/P2-2). The reference implementation is §8.2.

The critical behavior v0.1/v1.0 lacked: **a headless setup that hits an `input`/`confirm` step it cannot satisfy from vault/env does not fail — it persists `BLOCKED_ON_INPUT` and self-describes the missing piece** (`need`, `fix`, `since`) to `.state/provisioning.json`, then `exit 20`. A supervising orchestrator (or the next interactive session via `skill_view`, §8.4) reads that durable record, surfaces "帮我配 agent-reach 的 key" to the human, and resumes. This is what makes setup safe to attempt from a cron job — and, unlike v1.0, the resume can actually happen because the state is durable, not just printed to stdout.

### 3.5 Idempotency & staleness: the state file is a *cache*, not a *proof*

v0.1's `setup.sh` early-exits when `provisioning.json` says `state: READY`. That blindly trusts a stale file: if the API key was revoked yesterday, the skill is broken but still claims READY.

First-principles correction:

> **`provisioning.json` records that an *expensive action* completed. It does NOT assert that the skill currently works. Whether it works is re-established by the (cheap) verify gates on each entry.**

So on entry to a PROVISIONED skill, the engine:
- **skips** expensive *actions* it has memoized (don't re-`npm install`, don't re-`register`),
- **re-runs** cheap *verifications* — those marked `cheap: true` (§3.1, P2-7): `command_exists`, `env_exists`, a fast idempotent `status_json`.

If a re-verify fails → transition `PROVISIONED → BROKEN` (§5.1) and re-provision only the broken step. Staleness also triggers on **(a)** manifest `version` change, **(b)** a verify's optional TTL elapsing (a periodic *deep* re-verify, which alone catches an expired-but-present credential — cheap gates only detect *absence*, not *invalidity*; see §12 note on P2-3), and **(c)** explicit reset.

### 3.6 Concurrency: provisioning needs its own crash-safe lock

With both cron and interactive sessions potentially touching one skill, two provisioning runs can race (double `npm install -g`, half-written env file). Provisioning acquires an **atomic** provisioning lock before mutating, and — fixing v1.0's overstated "ephemeral ⇒ crash-safe" (P2-1) — it reclaims a lock whose owner is dead:

```bash
LOCK="$XDG_RUNTIME_DIR/srof/agent-reach/provision.lock"
acquire() {
  if mkdir "$LOCK" 2>/dev/null; then echo $$ > "$LOCK/owner.pid"; return 0; fi
  owner="$(cat "$LOCK/owner.pid" 2>/dev/null)"
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then return 1; fi  # alive → really held
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null && { echo $$ > "$LOCK/owner.pid"; return 0; }  # dead → reclaim
  return 1
}
acquire || { echo '{"state":"PROVISIONING","reason":"another live run holds the lock"}'; exit 21; }
trap 'rm -rf "$LOCK"' EXIT          # released on clean exit; SIGKILL handled by the reclaim path above
```

`mkdir` is atomic on POSIX, so this is a correct mutex with no extra dependency. The lock lives in the *ephemeral* runtime dir, not `.state/`. `trap … EXIT` covers clean exits; it does **not** fire on SIGKILL/power loss, which is exactly why the PID-liveness reclaim exists — without it, a SIGKILL'd run wedges the skill until reboot.

### 3.7 Secret handling: the `$SROF_INPUT_FILE` channel (P1-2)

`secret: true` promises a secret never reaches the transcript or state. v1.0's `$SROF_INPUT` broke that promise: the only way an LLM injects a *value* into a subprocess is to emit it (into the command string → transcript, or into the env → `/proc/<pid>/environ`). v1.1 routes the *value* around the LLM entirely:

> **Canonical `secret: true` path.** The secret's *holder* (a vault command, an env var, or the human) writes the plaintext to a `umask 077` temp file. The engine learns only the **path**, exported as `$SROF_INPUT_FILE`. The actuator reads the file by path. The LLM orchestrates (it knows *that* a secret is needed and *where* it will land) but never holds, emits, or interpolates the plaintext.

- **Forbidden**: `run: ... "$SROF_INPUT"` value-interpolation, or exporting the secret as a value into the actuator's env. `$SROF_INPUT` is removed.
- **Required**: actuators for secret steps read `"$SROF_INPUT_FILE"` and write only to the secret's real destination. They MUST NOT echo the secret to stdout — `srof-run` captures stdout into `$SROF_RUN_RESULT.*`, so an echoed secret would land in a result file.
- **Verify without leak**: confirm the secret arrived via a re-query that reveals presence, not value — e.g. `status_json:'agent-reach config get api_key --json'::.set==true`.
- **Headless seeding** (so cron can sometimes get past an `input` step, P2-4): `setup.sh` tries, in `source_order` minus `human`: the step's `env` var, then a configured read-only fetch command `$SROF_VAULT_GET <key>`. Either is written to a umask-077 file → `$SROF_INPUT_FILE`. If neither yields a value, it parks in `BLOCKED_ON_INPUT`. (`vault` = whatever command `$SROF_VAULT_GET` names; if unset, headless requires env-seeded secrets.)

### 3.8 Execution-plane policy: `policy.yaml` (P1-5)

§4.3 forbids hard-coding policy numbers into scripts, but `setup.yaml` is the **provisioning** manifest — its only knob is `on_failure.max_retries` (a setup-retry limit). Execution-plane limits (`sessions_active` caps, kill rules) had no home in v1.0. v1.1 adds a sibling manifest read by the engine (never by `setup.sh`):

```yaml
# policy.yaml — EXECUTION-plane policy. Read by the engine. Provisioning policy stays in
# setup.yaml; this governs the inner (execution) loop ONLY. (P1-5)
version: "1.0"
skill: cc-tmux
execution:
  lock_scope: resource:pane        # P1-6: per-resource lock (NOT per-skill) — default for cc-tmux
  limits:
    sessions_active: 4             # engine compares gate-counter sessions_active to this cap
  danger:
    kill_pane:
      authority: human             # gate-danger emits block; only a human clears it
      never: [self, orchestrator]  # patterns gate-danger always blocks
```

The rule "the script *measures*, the manifest *sets the limit*, the LLM *applies* it" (§4.3) now has a concrete home for **execution-plane** limits: `gate-counter` reports `sessions_active`; the engine compares it to `policy.yaml`'s `limits.sessions_active`; the engine acts.

---

## 4. Script / LLM Division of Labor  *(Focus Area #2)*

### 4.1 The invariant

> **Scripts emit *facts* and *verdicts*. The LLM emits *decisions* and *prose*.** (Corollary of §1.2.)
> A script must never encode policy. The LLM must never assert a world-fact it did not obtain from a script (or tool).

The second clause is the anti-hallucination guard: the agent may not *claim* "tmux is installed", "the lock is free", or "the actuator exited 0" from its own belief — only by quoting a gate's verdict (the exit code itself is read from `$SROF_RUN_RESULT` by `gate-verify`, never asserted by the LLM). This matters acutely for a destructive-action gate, where a hallucinated "looks safe" is how you kill the wrong session.

### 4.2 A falsifiable test for placing a node

For any orchestration node X, ask: *is X's answer a deterministic function of observable world state (or the captured run-result) with one correct value?*

- **Yes → it is a fact → put it in a script (sensor).** ("Is port 8080 free?", "Did the last run exit 0?", "How many retries so far?")
- **No → it requires weighing ambiguity, intent, or risk tolerance → keep it in the LLM (engine).** ("Should we retry or abort?", "Is force-killing that session acceptable?", "Did the user really mean *this* platform?")

This test is mechanical; it removes the guesswork from "should this be a script or a prompt?".

### 4.3 The dangerous middle: the threshold rule

The hard case is a fact with a *policy threshold* baked in — e.g. "give up after 3 retries." Naively this looks like one node, but it is two:

> **The script *measures*; the manifest *sets the limit*; the LLM *applies* it.**
> Never hard-code the policy number into the script.

```
gate-counter retries:install-cli      →  {"verdict":"pass","evidence":{"count":3}}   # FACT
setup.yaml: on_failure.max_retries: 2          (provisioning-plane policy → data)     # POLICY
policy.yaml: execution.limits.sessions_active  (execution-plane policy → data)        # POLICY
LLM: 3 > 2  → stop retrying, halt, report                                            # DECISION
```

This is why cc-tmux's `gate-counter.sh` *counts* but does not *decide* — the limit is configuration (in `setup.yaml` for provisioning retries, in `policy.yaml` for execution limits, §3.8), the comparison is the engine's. Bake the `2` into the script and you can no longer change policy without editing code, and two skills can't share the counter.

### 4.4 Responsibility table (revised)

| Concern | Hard plane (script / sensor) | Soft plane (LLM / engine) |
|---|---|---|
| **Can it run?** (preconditions) | `gate-check` returns pass/fail/block | reads the verdict; decides to remediate or halt |
| **What to do & in what order** | — | sequences steps from the manifest |
| **Gather human input/secret** | actuator reads `$SROF_INPUT_FILE` (path only) | conducts the conversation; lands the secret in a umask-077 file (§3.7) |
| **Run the actuator + capture result** | `srof-run` runs `run:`, writes `$SROF_RUN_RESULT` | decides *whether* to run it |
| **Did it work?** | `gate-verify` (last-result) / `gate-check` (re-query) | interprets a genuinely ambiguous result; decides retry |
| **Is it safe to proceed?** | `gate-danger` matches patterns → `block` | risk-assesses; obtains human authority to clear a `block` |
| **How many times tried?** | `gate-counter` reads the count from `runtime.json` (fact) | compares to manifest/policy limit and acts |
| **Persist state** | writes `provisioning.json` via `.tmp`+`mv` (atomic) | decides *when* a transition is warranted |
| **Acquire a lock** | atomic `mkdir` + PID-liveness reclaim (actuator) | decides whether contending for the lock is worth it |

### 4.5 Worked example — a gated destructive setup action

`register-skill` writes remote state; suppose a variant must first *delete* a stale remote registration.

```
1. LLM intends: re-register (delete old, write new).
2. gate-danger remote_delete:agent-reach-hub
      → {"verdict":"block","authority":"human","reason":"irreversible remote delete"}   [FACT]
3. LLM may NOT self-clear a block. It surfaces the reason and asks the human.            [DECISION]
4. Human authorizes.  LLM records authorization, proceeds.                                [DECISION]
5. srof-run: agent-reach skill --reregister  → writes $SROF_RUN_RESULT                    [ACTUATOR]
6. gate-verify-dispatch status_json:'… --status'::.registered==true → pass (re-query)     [FACT]
7. LLM marks step done.                                                                   [DECISION]
```

Note the clean separation: the script *detected* danger and *refused to pass*; only the human (authority) could clear it; the LLM never overrode the verdict, only carried the authorization. And the verify is a re-query of `--status`, never a re-`--register` (which would re-mutate remote state — the P0-1 hazard).

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
        │   │   PROVISIONING  │  needs human input ┌──────────────────┐
        │   │ (running steps) ├───────────────────►│ BLOCKED_ON_INPUT │
        │   └────────┬────────┘◄───────────────────┤ (PERSISTED +     │
        │            │     value/confirm supplied   │  self-describes) │
        │            │ all verify pass              └──────────────────┘
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
| `UNPROVISIONED` | No state file, or it is stale (version changed / TTL / explicit reset). |
| `PROVISIONING` | Steps executing; provisioning lock held. |
| `BLOCKED_ON_INPUT` | A step needs a human value/confirm. **Now persisted** to `.state/provisioning.json` with `need`/`fix`/`since` (P1-3) so a later session resumes. Headless always persists here; interactive persists only if the human defers. |
| `PROVISIONED` | All steps verified. The only state in which the skill may execute. |
| `BROKEN` | A previously-passing verify now fails (revoked key, deleted file), or a prerequisite/gate is broken. Re-provision the broken step only. |

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
| `RUNNING` | Gates passed; actuator executing; lock held (per `lock_scope`) | a `pass` from every gate | LLM judged the action worth doing |
| `HALTED` | A gate returned `block`; awaiting human authority or abort | `block` verdict | LLM/human decides clear-vs-abort |

### 5.3 Nesting and teardown — scoped to a single execution context (P1-6)

- The execution sub-machine is **instantiated on entry to `PROVISIONED` and destroyed on exit**, *within one execution context (one session/process).* If a re-verify flips `PROVISIONED → BROKEN` at that context's next entry, its current action is halted, the lock released, and control returns to the provisioning plane. **Within one context you cannot be `RUNNING` and `BROKEN` simultaneously — the nesting forbids it.**
- **Cross-session semantics (the honest multi-process truth).** Provisioning state is shared per-skill; execution is per-session. So while session A is `RUNNING`, session B can enter, re-verify, and compute `BROKEN`. That is allowed and well-defined: **A keeps its lock and finishes or aborts its in-flight action; B parks (does not start a new action against broken provisioning); the provisioning regression is observed independently at *each* session's next entry.** The "no `RUNNING`+`BROKEN`" invariant is therefore explicitly *intra-context*, not global. B never reaches into A's process to tear down A's action.
- `BLOCKED_ON_INPUT` is *provisioning-scoped* and durable; `HALTED` is *execution-scoped* and ephemeral. Keeping them distinct means a blocked setup ("need a key") and a halted action ("refusing to kill that pane") are reported, stored, and resumed by different mechanisms.

### 5.4 Transition table — who enforces / who decides

| Transition | Enforced by (script = hard fact) | Decided by (LLM = soft) |
|---|---|---|
| `UNPROVISIONED → PROVISIONING` | provisioning lock acquired (`mkdir`+PID reclaim) | engine chooses to provision now vs defer |
| `PROVISIONING → BLOCKED_ON_INPUT` | step `kind∈{input,confirm}` ∧ value/authorization absent ∧ record persisted | — (mechanical, then engine sources the value) |
| `BLOCKED_ON_INPUT → PROVISIONING` | persisted record read; value/confirm now present | engine (or human) supplied it |
| `PROVISIONING → PROVISIONED` | every `verify` returns pass | engine judged steps complete |
| `PROVISIONING → BROKEN` | a step fails after `max_retries` (policy from manifest), or a gate is broken | engine applied the retry policy (§4.3) |
| `PROVISIONED → BROKEN` | an on-entry re-verify fails | — (mechanical); engine then re-provisions |
| `BROKEN → PROVISIONING` | — | engine/human chooses to repair |
| `* → UNPROVISIONED` | manifest version changed / TTL / explicit reset | human or build process |
| `IDLE → GATING → RUNNING` | every gate returns pass | engine chose the action |
| `GATING → IDLE` | a gate returns fail (precondition unmet) | engine decides remediate-or-drop |
| `RUNNING/GATING → HALTED` | a gate returns block (or a broken gate → safe default) | — (binding); engine reports |
| `HALTED → RUNNING` | human authority recorded | human authorized; engine carries it |
| `RUNNING → IDLE` | actuator exited 0 (verify pass) | engine judged the task done |

### 5.5 State persistence schema

**Durable** — `.state/provisioning.json` (skill-local, gitignored). Records memoized actions + last verdicts; it is a cache (§3.5), not a proof. Written atomically via `.tmp`+`mv` (P2-2), so lock-free readers (the interactive re-verify) never see a torn file.

```json
{
  "skill": "agent-reach",
  "manifest_version": "1.1",
  "state": "PROVISIONED",
  "state_since": "2026-06-28T06:00:00Z",
  "steps": {
    "install-cli":    {"status":"done","memoized":true,"last_verify":"pass","at":"2026-06-28T06:00:01Z"},
    "configure-key":  {"status":"done","memoized":true,"last_verify":"pass","at":"2026-06-28T06:00:02Z"},
    "test-connection":{"status":"done","memoized":true,"last_verify":"pass","at":"2026-06-28T06:00:03Z"},
    "register-skill": {"status":"done","memoized":true,"last_verify":"pass","at":"2026-06-28T06:00:04Z"}
  },
  "run_count": 3
}
```

**Durable, parked** — same file, while waiting on a human (P1-3). This is the record `skill_view` reads on the next entry to resume:

```json
{
  "skill": "agent-reach",
  "manifest_version": "1.1",
  "state": "BLOCKED_ON_INPUT",
  "need": "configure-key",
  "fix": "run interactively or seed AGENT_REACH_API_KEY / SROF_VAULT_GET, then re-enter",
  "since": "2026-06-28T06:00:02Z",
  "steps": { "install-cli": {"status":"done","memoized":true,"last_verify":"pass","at":"…"} }
}
```

**Ephemeral** — `$XDG_RUNTIME_DIR/srof/<skill>/runtime.json` (+ `result.json`, `provision.lock/`, `exec.lock` or per-resource locks, secret files). Holds the execution sub-state, retry counters (read by `gate-counter`, P2-10), and lock ownership. Wiped on reboot by design.

```json
{
  "sessions_active": 2,
  "retries": { "install-cli": 1 },
  "exec": { "lock_scope": "resource:pane", "held": ["pane:%3"] }
}
```

> Secrets are **never** written to either file. `input` values with `secret: true` go only to their real destination via `$SROF_INPUT_FILE` (§3.7); state stores `{"status":"done"}`, never the value.

---

## 6. Gate Script Interface  *(Focus Area #4)*

### 6.1 A gate is a pure function

> A gate is a **pure, side-effect-free function** invoked as a separate process: `(target [, $SROF_RUN_RESULT]) → {verdict, evidence}`.
> It *observes* the world, or a captured result *file*; it never *mutates*. Installing, acquiring a lock, running an actuator, writing a file — those are **actuators**, not gates.

Purity is what makes gates safe to call repeatedly, in any order, in dry-run, and from any runtime. It is also what makes SROF substrate-agnostic (§7, D-4). The one subtlety v1.1 resolves: a *last-result* verify needs to see the actuator's output. It stays pure by reading the **already-captured** result file (`$SROF_RUN_RESULT`, §6.8) — it never re-executes the actuator. (v1.0's gap forced an "honest" verify to re-run the command — e.g. re-`register` — smuggling a mutation into a gate; §6.8 closes that.)

### 6.2 Verdict semantics: `pass` / `fail` / `block` — and the `unknown` signal

v0.1 listed three verdicts but never said what separates `fail` from `block`. The distinction is the whole point, and it is about **authority to clear**:

| Verdict | Meaning | Who may clear it | Engine's obligation |
|---|---|---|---|
| `pass` | Precondition satisfied / action permitted | — | proceed |
| `fail` | Precondition **not** met, but expected & fixable | **the agent** | may remediate (install, configure) and re-gate |
| `block` | Hard safety stop (danger pattern, irreversible op, exclusive lock held) | **only a human** | must NOT auto-remediate; surface reason; get explicit authorization |
| `unknown` | The gate **could not determine** an answer (always paired with exit≠0) | n/a | treat as broken; **safe default = halt** (§6.3) — never "assume pass" |

`pass`/`fail`/`block` are the three *world-verdicts* (statements about the world). `unknown` is not a world-verdict; it is the could-not-determine signal, and it is the only verdict that co-occurs with a non-zero exit. This is the v1.1 fix for P2-6: a gate that cannot determine an answer emits `unknown`+exit≠0, **never** a meaningful `block`+exit≠0. `block` remains exclusively a *determined* "this is unsafe" with exit 0. The "only `gate-danger` emits `block`" rule (§6.5) is unaffected — `unknown` is an error signal any gate may raise.

### 6.3 Exit code vs verdict — gate *health* vs gate *answer*

> **Exit code reports whether the gate could determine an answer. The JSON verdict reports the answer.** They are independent.

```
exit 0  +  verdict pass|fail|block   → the gate worked; trust the verdict
exit ≠0 (verdict "unknown")          → the gate is BROKEN / could-not-determine
```

> **Engine safe default (binding):** a broken gate — exit≠0, or any verdict that is not `pass`/`fail` — is treated as **block ⇒ HALT**. Never proceed on a gate you could not trust. This is what lets the framework distinguish "the check says no" (`fail`/`block`, exit 0 → respect it) from "the check itself is broken" (exit≠0 → halt), and it is enforced in both paths (interactive §3.3 step 1/2a/2d; headless §8.2 `GATE()`).

### 6.4 The JSON envelope

Single line of JSON to stdout. stderr is for human/debug logs and is never parsed.

```jsonc
{
  "gate":     "check|verify|danger|counter",   // which sensor family
  "target":   "command_exists:tmux",            // the primitive arg, echoed
  "verdict":  "pass|fail|block|unknown",        // unknown ⟺ exit≠0 (§6.2/§6.3)
  "authority":"agent|human|none",               // who may clear a non-pass (see §6.2)
  "reason":   "human-readable explanation",
  "evidence": { "count": 3, "found": "/usr/bin/tmux" }  // optional structured facts
}
```

**Input channel (NEW, P0-1).** Gates take their primitive `target` as `argv[1]`. *Last-result* verifies (`exit_code`, `result_json`) additionally read **one environment input**: `$SROF_RUN_RESULT`, a path to the JSON the actuator-runner wrote (§6.8). No other input channel exists; gates never read the live actuator process. `authority` makes fail/block explicit: a `fail` carries `authority:agent`, a `block` carries `authority:human`, `pass`/`unknown` carry `none`.

### 6.5 Namespaced targets, the taxonomy, and the verify split

Targets are `namespace:argument[:argument]`, parsed by trivial prefix-strip (no parser dependency). The **verify vocabulary is split into two classes** (P0-1), and the class determines which family evaluates it:

- **Class (a) — re-query verifies**: self-contained idempotent observations of the *world*. Evaluated by **`gate-check`** (the same observation as a precondition). Safe to use as a `when` guard. `command_exists`, `env_exists`, `file_exists`, `version_gte`, `port_free`, `lock_free`, `http_ok`, `status_json`.
- **Class (b) — last-result verifies**: observations of the *just-produced output*. Evaluated by **`gate-verify`**, which reads `$SROF_RUN_RESULT`. `exit_code`, `result_json`. **Forbidden where re-execution would mutate state** — never put a mutating command behind a verify; verify a registration with a class-(a) `status_json` read, never by re-running `--register`.

Verify-dispatch (used by both paths): `exit_code:* | result_json:*` → `gate-verify`; everything else → `gate-check`.

| Sensor | Family | Typical targets | Verdict bias |
|---|---|---|---|
| `gate-check.sh` | preconditions + class-(a) re-query verifies | `command_exists:X`, `env_exists:X`, `file_exists:X`, `port_free:N`, `version_gte:X:V`, `lock_free:NAME`, `http_ok:URL`, `status_json:CMD::.k==v` | pass / **fail** |
| `gate-verify.sh` | class-(b) last-result verifies | `exit_code:N`, `result_json:.k==v` (read `$SROF_RUN_RESULT`) | pass / **fail** |
| `gate-danger.sh` | safety | `remote_delete:X`, `kill_pane:self`, `rm_rf:PATH`, `force_push:branch` | pass / **block** |
| `gate-counter.sh` | measurement | `retries:STEP`, `sessions_active`, `age_seconds:FILE` | always **pass** + `evidence.count` |

Rules of thumb encoded above: `gate-danger` is the *only* family that emits `block`; `gate-counter` never emits a non-pass for a *known* target (it reports a number; the engine judges it — §4.3). Any family may emit `unknown`+exit≠0 when it genuinely cannot determine an answer.

### 6.6 Library + local override resolution

> Universal primitives live in a **central library**; skill-specific gates live **local** and shadow central ones by name. Resolution branches on *presence* (`[ -x ]`), never on exit code (P0-2c).

```
resolve gate-check:
  1. $SKILL_DIR/scripts/gate-check.sh     # skill-specific override IF EXECUTABLE
  2. $SROF_LIB/gate-check.sh              # central shared library (default)
```

- **Central** (`$SROF_LIB`): `command_exists`, `env_exists`, `file_exists`, `version_gte`, `port_free`, `lock_free`, `http_ok`, `status_json` — generic, identical everywhere, shared by Hermes and iii alike.
- **Local** (`$SKILL_DIR/scripts`): danger patterns are inherently skill-specific (cc-tmux's "never kill the orchestrator pane" is meaningless to another skill), so they belong with the skill and shadow any central namesake.

A local gate that is *absent* falls back to central. A local gate that is *present but exits non-zero* is a **broken gate** → halt; it must never silently fall through to central (that would let a buggy local gate be bypassed). This presence-vs-exit distinction is the heart of the P0-2c fix.

### 6.7 Reference implementation — `gate-check.sh`

```bash
#!/usr/bin/env bash
# gate-check.sh — precondition + class-(a) re-query sensor. PURE: observes the world, never mutates.
# Usage:  gate-check.sh <namespace:arg[:arg]>
# Stdout: one line of JSON (§6.4). Exit 0 = determined; exit 1 = could-not-determine (verdict "unknown").
set -uo pipefail
TARGET="${1:-}"

emit() {  # emit <verdict> <authority> <reason> [evidence-json]
  local ev="${4:-}"; [ -n "$ev" ] || ev='{}'
  printf '{"gate":"check","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "$ev"
}

case "$TARGET" in
  command_exists:*)
    cmd="${TARGET#command_exists:}"
    if path="$(command -v "$cmd" 2>/dev/null)"; then emit pass none "command '$cmd' found" "{\"found\":\"$path\"}"
    else emit fail agent "command '$cmd' not found"; fi ;;          # agent may install → fail, not block

  env_exists:*)
    var="${TARGET#env_exists:}"
    if [ -n "${!var:-}" ]; then emit pass none "env '$var' set"
    else emit fail agent "env '$var' not set"; fi ;;

  file_exists:*)
    f="${TARGET#file_exists:}"
    if [ -f "$f" ]; then emit pass none "file exists" "{\"path\":\"$f\"}"
    else emit fail agent "file '$f' not found"; fi ;;

  version_gte:*)                                                    # version_gte:node:18.0.0
    rest="${TARGET#version_gte:}"; cmd="${rest%%:*}"; want="${rest#*:}"
    if ! have="$(timeout 5 "$cmd" --version 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)+' | head -1)" || [ -z "$have" ]; then
      emit unknown none "cannot read version of '$cmd'"; exit 1; fi # could-not-determine → unknown+exit1 (P2-6)
    lowest="$(printf '%s\n%s\n' "$want" "$have" | sort -V | head -1)"
    if [ "$lowest" = "$want" ]; then emit pass none "$cmd $have >= $want" "{\"have\":\"$have\"}"
    else emit fail agent "$cmd $have < $want" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  port_free:*)
    p="${TARGET#port_free:}"
    if command -v lsof >/dev/null 2>&1; then
      if lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then emit fail agent "port $p in use"
      else emit pass none "port $p free"; fi
    else emit unknown none "lsof unavailable; cannot determine port $p"; exit 1; fi ;;

  http_ok:*)                                                        # idempotent GET health check
    url="${TARGET#http_ok:}"
    if curl -fsS --max-time 10 -o /dev/null "$url" 2>/dev/null; then emit pass none "GET $url ok"
    else emit fail agent "GET $url not ok"; fi ;;

  status_json:*)                                                    # status_json:CMD::.path==value  (CMD MUST be read-only)
    rest="${TARGET#status_json:}"; cmd="${rest%%::*}"; cond="${rest#*::}"
    path="${cond%%==*}"; want="${cond#*==}"
    if ! out="$(eval "$cmd" 2>/dev/null)"; then emit unknown none "status cmd failed: $cmd"; exit 1; fi
    if ! have="$(jq -r "$path" <<<"$out" 2>/dev/null)"; then emit unknown none "jq parse failed on status output"; exit 1; fi
    if [ "$have" = "$want" ]; then emit pass none "$path == $want" "{\"have\":\"$have\"}"
    else emit fail agent "$path is '$have', want '$want'" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  lock_free:*)
    name="${TARGET#lock_free:}"; lock="${XDG_RUNTIME_DIR:-/tmp}/srof/${name}.lock"
    if [ -d "$lock" ]; then emit block human "lock '$name' held by another session"  # determined → block+exit0 (OK per §6.3)
    else emit pass none "lock '$name' free"; fi ;;                  # NOTE: observe only — acquiring is an actuator

  *)
    emit unknown none "unknown check target"; exit 1 ;;             # unknown → can't determine → unknown+exit1 (P2-6)
esac
```

Two P2-6 corrections vs v1.0: the `version_gte` read-failure and the unknown-target default now emit **`unknown`+exit 1** (could-not-determine), not the self-contradictory `block`+exit 1. `lock_free:held` stays `block`+exit 0 — that is a *determined* answer, which §6.3 permits.

### 6.8 The actuator→verify result contract: `$SROF_RUN_RESULT` + `srof-run.sh`  (P0-1)

The central loop is `when → run → verify`. A freshly-spawned pure gate cannot see a sibling actuator's exit code or stdout — so v1.0's `verify: exit_code:0` had nothing to read. v1.1 adds an explicit, file-based contract:

> **Every `run:` executes through `srof-run`, which captures the actuator's stdout, stderr, and exit code, and writes a small JSON descriptor to the known path `$SROF_RUN_RESULT` (atomically). A class-(b) `gate-verify` reads *that file* — never the live world, never a re-execution.**

`$SROF_RUN_RESULT` descriptor:

```json
{ "exit_code": 0, "stdout_path": "/run/srof/agent-reach/test-connection.out",
  "stderr_path": "/run/srof/agent-reach/test-connection.err", "step": "test-connection" }
```

```bash
#!/usr/bin/env bash
# srof-run.sh — the actuator-runner. Executes one step's `run:` and writes the captured result
# to $SROF_RUN_RESULT so gate-verify can read it (the §6.8 contract). It is an ACTUATOR (it
# mutates the world); its only "decision" is the mechanical capture. Used by BOTH paths so a
# `verify` means the same thing interactively and headless (closes the P0-1 asymmetry).
# Usage:  SROF_RUN_RESULT=<path> [SROF_INPUT_FILE=<path>] srof-run.sh <step-id> -c '<run-script>'
#    or:  ... srof-run.sh <step-id>   <<<'<run-script>'
set -uo pipefail                       # NOT -e: we WANT to capture a non-zero exit, not die on it
STEP="${1:?step id}"; shift
if [ "${1:-}" = "-c" ]; then SCRIPT="${2:?run script}"; else SCRIPT="$(cat)"; fi

: "${SROF_RUN_RESULT:?set SROF_RUN_RESULT}"
RUNDIR="$(dirname "$SROF_RUN_RESULT")"; mkdir -p "$RUNDIR"
OUT="$RUNDIR/$STEP.out"; ERR="$RUNDIR/$STEP.err"

# Execute. $SROF_INPUT_FILE (if any) is already a PATH in the env; the secret value is never
# passed as an argument or interpolated (§3.7). stdout/stderr are captured to files — actuators
# for secret steps MUST NOT echo the secret, or it would land in $STEP.out.
bash -c "$SCRIPT" >"$OUT" 2>"$ERR"
rc=$?

# Atomic write (.tmp + mv, P2-2).
tmp="$SROF_RUN_RESULT.tmp.$$"
jq -n --argjson ec "$rc" --arg op "$OUT" --arg ep "$ERR" --arg st "$STEP" \
  '{exit_code:$ec, stdout_path:$op, stderr_path:$ep, step:$st}' > "$tmp"
mv -f "$tmp" "$SROF_RUN_RESULT"
exit "$rc"
```

### 6.9 Reference implementation — `gate-verify.sh` (class (b), reads `$SROF_RUN_RESULT`)

```bash
#!/usr/bin/env bash
# gate-verify.sh — class-(b) last-result sensor. PURE: reads the captured result file written by
# srof-run (§6.8); NEVER re-executes the actuator. Class-(a) re-query verifies are handled by
# gate-check, not here (§6.5).
# Usage:  SROF_RUN_RESULT=<path> gate-verify.sh <exit_code:N | result_json:.path==value>
# Stdout: one JSON line (§6.4). Exit 0 = determined; exit 1 = could-not-determine ("unknown").
set -uo pipefail
TARGET="${1:-}"

emit() { local ev="${4:-}"; [ -n "$ev" ] || ev='{}'
  printf '{"gate":"verify","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "$ev"; }

need_result() {                          # last-result verify requires the descriptor
  if [ -z "${SROF_RUN_RESULT:-}" ] || [ ! -f "${SROF_RUN_RESULT:-}" ]; then
    emit unknown none "last-result verify but \$SROF_RUN_RESULT missing"; exit 1; fi
}

case "$TARGET" in
  exit_code:*)
    need_result
    want="${TARGET#exit_code:}"
    have="$(jq -r '.exit_code // empty' "$SROF_RUN_RESULT" 2>/dev/null)"
    [ -n "$have" ] || { emit unknown none "no exit_code in result"; exit 1; }
    if [ "$have" = "$want" ]; then emit pass none "exit $have == $want" "{\"have\":$have}"
    else emit fail agent "exit $have != $want" "{\"have\":$have,\"want\":$want}"; fi ;;

  result_json:*)                         # result_json:.path==value  (on the captured stdout)
    need_result
    expr="${TARGET#result_json:}"; path="${expr%%==*}"; want="${expr#*==}"
    out="$(jq -r '.stdout_path // empty' "$SROF_RUN_RESULT" 2>/dev/null)"
    [ -f "$out" ] || { emit unknown none "captured stdout missing"; exit 1; }
    if ! have="$(jq -r "$path" "$out" 2>/dev/null)"; then emit unknown none "jq parse failed on captured stdout"; exit 1; fi
    if [ "$have" = "$want" ]; then emit pass none "$path == $want" "{\"have\":\"$have\"}"
    else emit fail agent "$path is '$have', want '$want'" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  *)
    emit unknown none "unknown verify target (class-a re-query? route to gate-check, §6.5)"; exit 1 ;;
esac
```

### 6.10 Reference implementation — `gate-danger.sh` (the only emitter of `block`)

```bash
#!/usr/bin/env bash
# gate-danger.sh — safety sensor. PURE: CLASSIFIES an intended action; never runs it.
# The ONLY family that emits `block`; `block` ⇒ authority:human (only a human may clear, §6.2).
# Skill-specific danger patterns live LOCAL and shadow any central namesake (§6.6).
# Usage:  gate-danger.sh <namespace:arg[:arg]>
# Stdout: one JSON line (§6.4). Exit 0 = classified; exit 1 = could-not-classify ("unknown").
set -uo pipefail
TARGET="${1:-}"

emit() { local ev="${4:-}"; [ -n "$ev" ] || ev='{}'
  printf '{"gate":"danger","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "$ev"; }

case "$TARGET" in
  remote_delete:*)
    what="${TARGET#remote_delete:}"
    emit block human "irreversible remote delete of '$what'" "{\"resource\":\"$what\"}" ;;

  rm_rf:*)
    path="${TARGET#rm_rf:}"
    emit block human "recursive delete of '$path'" "{\"path\":\"$path\"}" ;;

  force_push:*)
    br="${TARGET#force_push:}"
    emit block human "force-push to '$br' rewrites history" "{\"branch\":\"$br\"}" ;;

  kill_pane:*)                           # skill-specific: never kill self / the orchestrator pane
    tgt="${TARGET#kill_pane:}"
    if [ "$tgt" = "self" ] || [ "$tgt" = "orchestrator" ] || [ "$tgt" = "${SROF_ORCHESTRATOR_PANE:-}" ]; then
      emit block human "refusing to kill the orchestrator pane" "{\"pane\":\"$tgt\"}"
    else
      emit pass none "killing pane '$tgt' is permitted" "{\"pane\":\"$tgt\"}"   # determined-safe → pass+exit0
    fi ;;

  *)
    emit unknown none "unknown danger target — cannot classify"; exit 1 ;;       # engine safe default: treat as block
esac
```

Note: a *classified-safe* action emits `pass`+exit 0; a *classified-dangerous* one emits `block`+exit 0; only a target it cannot classify emits `unknown`+exit 1, which the engine's safe default (§6.3) treats as a halt. There is never a `block`+exit≠0 (P2-6).

### 6.11 Reference implementation — `gate-counter.sh` (reads `runtime.json`)

```bash
#!/usr/bin/env bash
# gate-counter.sh — measurement sensor. PURE: reports a number; never judges it. The engine
# compares evidence.count to a manifest/policy limit (§4.3). Counts live in the EPHEMERAL
# runtime.json, written by the actuator-runner/engine, so the gate only OBSERVES persisted
# state — it never fabricates its own input (P2-10).
# Usage:  [SROF_RUNTIME_JSON=<path>] [SROF_SKILL=<name>] gate-counter.sh <retries:STEP|sessions_active|age_seconds:FILE>
set -uo pipefail
TARGET="${1:-}"
RUNTIME="${SROF_RUNTIME_JSON:-${XDG_RUNTIME_DIR:-/tmp}/srof/${SROF_SKILL:-_}/runtime.json}"

emit()  { printf '{"gate":"counter","target":"%s","verdict":"pass","authority":"none","reason":"%s","evidence":{"count":%s}}\n' "$TARGET" "$1" "$2"; }
unkn()  { printf '{"gate":"counter","target":"%s","verdict":"unknown","authority":"none","reason":"%s","evidence":{}}\n' "$TARGET" "$1"; exit 1; }
get()   { [ -f "$RUNTIME" ] && jq -r "$1 // 0" "$RUNTIME" 2>/dev/null || echo 0; }

case "$TARGET" in
  retries:*)        step="${TARGET#retries:}"; emit "retry count for '$step'" "$(get ".retries.\"$step\"")" ;;
  sessions_active)  emit "active sessions" "$(get '.sessions_active')" ;;
  age_seconds:*)
    f="${TARGET#age_seconds:}"
    if [ -f "$f" ]; then now=$(date +%s); m=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)
      [ -n "$m" ] && emit "age of $f" "$((now-m))" || unkn "cannot stat $f"
    else emit "file absent" "-1"; fi ;;
  *)                unkn "unknown counter target" ;;
esac
```

A *known* counter target always yields `pass` + a number (the engine judges it). Only a target the counter cannot read yields `unknown`+exit 1 — consistent with every other family (§6.2), and not a violation of "counter never emits non-pass," which is about *judging*, not about could-not-determine.

### 6.12 The purity rule and the lock exception

`lock_free` *observes* whether a lock is held; it must not *acquire* it. Acquisition is a state change → an actuator, and it must be **atomic** (`mkdir`/`flock`, §3.6) *and crash-safe* (PID-liveness reclaim, P2-1). Keeping observation (gate) and acquisition (actuator) separate is what lets the engine *check then decide then act*, and what keeps every gate replay-safe. `srof-run` is likewise an actuator, not a gate, even though it produces the file a gate later reads — it *mutates* (runs the command), so it can never be a gate. Any gate that mutates is a bug.

---

## 7. Resolved Decisions  *(was: Open Questions D-1…D-5)*

These are decided, not offered as a menu. Each gives the forces, the verdict, and the consequence.

### D-1 — State storage: **split by lifetime, not by scope**

- **Forces.** Provisioning state must persist and travel with the skill. Locks must *not* persist — a lock surviving a crash is a permanent deadlock. v0.1 framed this as "local vs central," which is the wrong axis.
- **Decision.** Durable provisioning state → **skill-local `.state/provisioning.json`** (gitignored, co-located, now also holding the parked `BLOCKED_ON_INPUT` record, P1-3). Ephemeral execution state + locks + result/secret files → **`$XDG_RUNTIME_DIR/srof/<skill>/`** (OS-cleared on reboot; PID-liveness reclaim for crash-between-reboots, P2-1). A central audit index (`~/.hermes/state/`) is **derived by scanning, never authoritative.**
- **Consequence.** A crash mid-action cannot wedge the skill; provisioning (and parked input) survive reboots; auditing is possible without a second source of truth. The one rule to remember: *never put a lock in `.state/`.*

### D-2 — Manifest format: **YAML, parsed by no runtime script**

- **Forces.** A runtime-parsed YAML needs `yq`; JSON is dependency-light but author-hostile; frontmatter embedding bloats the always-loaded SKILL.md.
- **Decision.** Manifest is **YAML, LLM-facing**; *no runtime script parses it* (§1.3). The headless runner parses a build-time **`setup.lock.json`** projection with `jq` only; that lock is generated by `srof-lock` (§8.3), which may use `yq` **at authoring time only**. The lock carries `source_sha256` and the runner refuses on drift (P1-4). Frontmatter embedding rejected — multi-platform auth manifests are long and would violate progressive disclosure.
- **Consequence.** Zero new *runtime* dependency; humans get readable YAML; headless gets deterministic, checksummed JSON; SKILL.md stays lean.

### D-3 — Prompt handling: **hybrid, formalized as step `kind`**

- **Forces.** Some steps are fully automatable; some need a secret; some need a yes/no for an irreversible action.
- **Decision.** Each step declares `kind: auto | input | confirm` (§3.1). Scripts stay pure; secrets flow via `$SROF_INPUT_FILE` (path only, §3.7), never through the LLM; the human conversation is 100% the LLM's; headless parks `input/confirm` it cannot seed in a **persisted** `BLOCKED_ON_INPUT` (§3.4/§5.5).
- **Consequence.** Setup is headless-safe *and* interactively rich, from one manifest. Direct corollary of the §4.1 invariant (talking to humans is a decision → LLM).

### D-4 — iii / substrate: **agnostic by construction**

- **Forces.** Hermes and iii workers both provision skills; duplicating the mechanism invites drift.
- **Decision.** Because gates are pure, primitive-in (+ `$SROF_RUN_RESULT` for class-(b) verifies) / JSON-out, and Hermes-free, **iii and Hermes call the identical gate binaries** via a shared `$SROF_LIB`. SROF is "manifest convention + portable gate/state library." Hermes contributes only *policy* (its `skill_view` decides *when* to provision).
- **Consequence.** One gate library, two+ runtimes, no adapter layer.

### D-5 — Gate reusability: **library + local override, split by universality**

- **Forces.** `command_exists` is universal; danger patterns are skill-specific. Forcing either fully-central or fully-local is wrong.
- **Decision.** Universal primitives in **central `$SROF_LIB`**; skill-specific gates **local**, shadowing central by name; resolution local → central by *presence* (`[ -x ]`), not exit code (§6.6, P0-2c).
- **Consequence.** No re-implementing `command_exists` per skill; danger logic stays with the skill that understands it; a broken local gate halts rather than being silently bypassed.

---

## 8. Reference Implementation

### 8.1 File tree of a SROF skill

```
agent-reach/
├── SKILL.md                 # frontmatter declares setup_manifest + policy
├── setup.yaml               # LLM-facing provisioning manifest (§3.1)
├── setup.lock.json          # build-time JSON projection + source_sha256 (§3.2)
├── policy.yaml              # execution-plane policy (§3.8)
├── scripts/
│   ├── srof-run.sh          # actuator-runner; writes $SROF_RUN_RESULT (§6.8)
│   ├── setup.sh             # headless degraded-mode engine (--auto, §8.2)
│   ├── gate-danger.sh       # skill-specific safety (local override, §6.10)
│   └── <actions>.sh         # the skill's real work
├── .state/                  # gitignored, durable
│   └── provisioning.json    # cache of completed actions + parked input (§5.5)
└── references/

$SROF_LIB/                   # shared, one copy for Hermes + iii
├── gate-check.sh            # universal precondition + re-query primitives (§6.7)
├── gate-verify.sh           # last-result verifies (§6.9)
├── gate-counter.sh          # measurement (§6.11)
└── srof-run.sh              # actuator-runner (may also live central)

(authoring/build time, not shipped in the runtime path)
└── srof-lock                # setup.yaml → setup.lock.json (+ source_sha256), uses yq (§8.3)
```

### 8.2 `setup.sh --auto` — the degraded-mode engine (rewritten, closes P0-2)

```bash
#!/usr/bin/env bash
# setup.sh --auto — HEADLESS provisioning runner = DEGRADED-MODE ENGINE SUBSTITUTE (§3.4).
# With no LLM in the loop, this script inherits the engine's duties: prerequisite phase,
# retry-to-policy, safe-default-on-broken-gate, persisted BLOCKED_ON_INPUT, and the full
# §5.5 state write. §1.2's "scripts are only sensors/actuators" is relaxed HERE BY
# CONSTRUCTION and bounded to this one file.
set -uo pipefail

[ "${1:-}" = "--auto" ] || { echo '{"error":"headless-only; interactive setup is LLM-driven (§3.3)"}'; exit 2; }

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"; SKILL="$(basename "$SKILL_DIR")"
YAML="$SKILL_DIR/setup.yaml"; LOCK_JSON="$SKILL_DIR/setup.lock.json"; STATE="$SKILL_DIR/.state/provisioning.json"
RUNROOT="${XDG_RUNTIME_DIR:-/tmp}/srof/$SKILL"
export SROF_RUN_RESULT="$RUNROOT/result.json" SROF_RUNTIME_JSON="$RUNROOT/runtime.json" SROF_SKILL="$SKILL"
: "${SROF_LIB:?set SROF_LIB}"
mkdir -p "$RUNROOT" "$SKILL_DIR/.state"

sha256() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" 2>/dev/null | awk '{print $1}'; }
now()     { date -u +%FT%TZ; }
write_state() { local tmp="$STATE.tmp.$$"; printf '%s\n' "$1" > "$tmp"; mv -f "$tmp" "$STATE"; }   # atomic (P2-2)

# ---------- P1-4: refuse on lock/source drift ----------
if [ -f "$YAML" ]; then
  want="$(jq -r '.source_sha256 // empty' "$LOCK_JSON")"; have="$(sha256 "$YAML")"
  if [ -n "$want" ] && [ "$have" != "$want" ]; then
    write_state "$(jq -n --arg s "$SKILL" '{skill:$s,state:"BROKEN",reason:"setup.lock.json stale vs setup.yaml",fix:"regenerate with srof-lock"}')"
    echo '{"state":"BROKEN","reason":"lock drift; run srof-lock"}'; exit 23
  fi
fi

# ---------- P2-1: crash-safe provisioning lock (mkdir + PID-liveness reclaim) ----------
LOCK="$RUNROOT/provision.lock"
acquire() {
  if mkdir "$LOCK" 2>/dev/null; then echo $$ > "$LOCK/owner.pid"; return 0; fi
  local owner; owner="$(cat "$LOCK/owner.pid" 2>/dev/null)"
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then return 1; fi      # alive → really held
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null && { echo $$ > "$LOCK/owner.pid"; return 0; }  # dead → reclaim
  return 1
}
acquire || { echo '{"state":"PROVISIONING","reason":"another live run holds the lock"}'; exit 21; }
trap 'rm -rf "$LOCK"' EXIT

# ---------- gate caller: local→central by PRESENCE, BROKEN-aware (P0-2c) ----------
# echoes verdict; returns 0 if gate determined (exit 0), 3 if gate BROKEN (exit≠0 / non-pass/fail/block).
GATE() {  # GATE <family> <target>
  local fam="$1" tgt="$2" g out rc v
  if [ -x "$SKILL_DIR/scripts/$fam.sh" ]; then g="$SKILL_DIR/scripts/$fam.sh"; else g="$SROF_LIB/$fam.sh"; fi
  out="$("$g" "$tgt")"; rc=$?
  if [ "$rc" -ne 0 ]; then echo unknown; return 3; fi                         # broken gate (exit≠0)
  v="$(jq -r '.verdict' <<<"$out" 2>/dev/null)"
  case "$v" in pass|fail|block) echo "$v"; return 0 ;; *) echo unknown; return 3 ;; esac
}
verify_dispatch() {  # route by class (§6.5)
  case "$1" in exit_code:*|result_json:*) GATE gate-verify "$1" ;; *) GATE gate-check "$1" ;; esac
}
halt_broken() {
  write_state "$(jq -n --arg s "$SKILL" --arg r "$1" '{skill:$s,state:"BROKEN",reason:$r}')"
  printf '{"state":"BROKEN","reason":"%s"}\n' "$1"; exit 22
}
park_blocked() {  # PERSIST before exit 20 (P1-3)
  local id="$1" fix="$2" ts; ts="$(now)"
  write_state "$(jq -n --arg s "$SKILL" --arg id "$id" --arg fix "$fix" --arg ts "$ts" \
    '{skill:$s,state:"BLOCKED_ON_INPUT",need:$id,fix:$fix,since:$ts}')"
  printf '{"state":"BLOCKED_ON_INPUT","need":"%s","fix":"%s","since":"%s"}\n' "$id" "$fix" "$ts"; exit 20
}
# headless secret seeding: env → vault → (else fail). Writes umask-077 file, echoes its PATH (§3.7, P2-4).
seed_secret() {  # seed_secret <step-json> ; echoes path on success, returns 1 otherwise
  local sj="$1" envvar key f val
  envvar="$(jq -r '.input.env // empty' <<<"$sj")"; key="$(jq -r '.input.key // .id' <<<"$sj")"
  f="$(umask 077; mktemp "$RUNROOT/secret.XXXXXX")"
  if [ -n "$envvar" ] && [ -n "${!envvar:-}" ]; then printf '%s' "${!envvar}" > "$f"; echo "$f"; return 0; fi
  if [ -n "${SROF_VAULT_GET:-}" ] && val="$("$SROF_VAULT_GET" "$key" 2>/dev/null)" && [ -n "$val" ]; then
    printf '%s' "$val" > "$f"; echo "$f"; return 0; fi
  rm -f "$f"; return 1
}

# ---------- (a) PREREQUISITE PHASE (P0-2a) ----------
for i in $(seq 0 $(( $(jq '.prerequisites|length' "$LOCK_JSON") - 1 ))); do
  chk="$(jq -r ".prerequisites[$i].check" "$LOCK_JSON")"
  v="$(GATE gate-check "$chk")" || halt_broken "prerequisite gate broken: $chk"
  case "$v" in
    pass) : ;;
    fail) write_state "$(jq -n --arg s "$SKILL" --arg n "$chk" '{skill:$s,state:"BROKEN",reason:("prerequisite unmet: "+$n)}')"
          printf '{"state":"BROKEN","need":"%s","reason":"prerequisite unmet"}\n' "$chk"; exit 22 ;;
    *)    halt_broken "prerequisite blocked/undeterminable: $chk" ;;
  esac
done

# ---------- (b)(c) STEP LOOP with retry-to-policy + safe defaults ----------
MAXR="$(jq -r '.on_failure.max_retries // 0' "$LOCK_JSON")"     # threshold from DATA (P0-2b, §4.3)
declare -a DONE
for i in $(seq 0 $(( $(jq '.steps|length' "$LOCK_JSON") - 1 ))); do
  step="$(jq -c ".steps[$i]" "$LOCK_JSON")"
  id="$(jq -r '.id' <<<"$step")"; kind="$(jq -r '.kind' <<<"$step")"
  when="$(jq -r '.when // empty' <<<"$step")"; verify="$(jq -r '.verify // empty' <<<"$step")"
  run="$(jq -r '.run // empty' <<<"$step")"

  # idempotency guard: when PASS → skip, FAIL → run, broken → halt (P1-1 + P0-2c)
  if [ -n "$when" ]; then
    wv="$(GATE gate-check "$when")" || halt_broken "when-gate broken on '$id': $when"
    if [ "$wv" = pass ]; then DONE+=("$id"); continue; fi
  fi

  # headless cannot satisfy human steps it can't seed → PERSIST + park (P1-3)
  case "$kind" in
    auto) : ;;
    input)
      if seeded="$(seed_secret "$step")"; then export SROF_INPUT_FILE="$seeded"
      else park_blocked "$id" "run interactively, or seed env/SROF_VAULT_GET, then re-enter"; fi ;;
    confirm) park_blocked "$id" "needs human authorization; run interactively" ;;
    *) halt_broken "unknown kind '$kind' on step '$id'" ;;
  esac

  # actuate + verify, retry a FAIL up to MAXR; broken/block → halt (safe default §6.3)
  attempt=0
  while :; do
    "$SKILL_DIR/scripts/srof-run.sh" "$id" -c "$run"           # writes $SROF_RUN_RESULT (§6.8)
    if [ -z "$verify" ]; then break; fi
    vv="$(verify_dispatch "$verify")" || vv=unknown
    case "$vv" in
      pass) break ;;
      fail)
        attempt=$((attempt+1))
        rtmp="$SROF_RUNTIME_JSON.tmp.$$"
        jq -n --arg id "$id" --argjson n "$attempt" '{retries:{($id):$n}}' > "$rtmp" 2>/dev/null && mv -f "$rtmp" "$SROF_RUNTIME_JSON" 2>/dev/null || true
        [ "$attempt" -gt "$MAXR" ] && halt_broken "step '$id' failed verify after $MAXR retries" ;;
      *) halt_broken "verify broken/blocked on '$id': $verify ($vv)" ;;     # unknown|block → halt
    esac
  done
  DONE+=("$id"); unset SROF_INPUT_FILE
done

# ---------- (d) FULL §5.5 STATE WRITE incl. steps{} memoization map (P0-2d) ----------
steps_obj='{}'; ts="$(now)"
for sid in "${DONE[@]}"; do
  steps_obj="$(jq -c --arg id "$sid" --arg at "$ts" \
    '. + {($id):{status:"done",memoized:true,last_verify:"pass",at:$at}}' <<<"$steps_obj")"
done
prev="$(jq -r '.run_count // 0' "$STATE" 2>/dev/null || echo 0)"
write_state "$(jq -n --arg s "$SKILL" --arg v "$(jq -r .version "$LOCK_JSON")" --arg ts "$ts" \
  --argjson steps "$steps_obj" --argjson rc "$((prev+1))" \
  '{skill:$s,manifest_version:$v,state:"PROVISIONED",state_since:$ts,steps:$steps,run_count:$rc}')"
echo '{"state":"PROVISIONED"}'
```

What changed vs v1.0's §8.2, point by point: **(a)** a real prerequisite phase precedes the step loop; **(b)** `max_retries` is read from the lock and a `fail` is retried to that threshold before BROKEN; **(c)** `GATE()` branches on `[ -x local ]` (presence) not exit code, and *any* broken gate (exit≠0 / non-pass-fail-block) → `halt_broken`, while a broken `when`/`verify` halts instead of proceeding; **(d)** success writes the full `steps{}` memoization map. Plus drift refusal, persisted `BLOCKED_ON_INPUT`, PID-reclaim locking, atomic writes, the `$SROF_RUN_RESULT` contract via `srof-run`, and `$SROF_INPUT_FILE` secret seeding.

### 8.3 `srof-lock` — the lock generator (authoring/build time, names the generator for P1-4)

```bash
#!/usr/bin/env bash
# srof-lock — AUTHORING/BUILD-TIME generator (NOT a runtime component). Projects setup.yaml into
# the dependency-light setup.lock.json the headless runner reads, stamping source_sha256 for drift
# detection (P1-4) and projecting EVERY field the runner reads (total projection, P2-8). Uses yq at
# BUILD time only; the shipped runtime still parses JSON with jq alone (D-2 preserved).
# Invoked by: skill-authoring's publish/lint step (or `make lock`). The LLM-emits-once path is an
# EMERGENCY fallback only — prefer this deterministic generator.
set -euo pipefail
YAML="${1:-setup.yaml}"; OUT="${2:-setup.lock.json}"
command -v yq >/dev/null || { echo "srof-lock needs yq (build-time only)"; exit 1; }
SHA="$(shasum -a 256 "$YAML" 2>/dev/null | awk '{print $1}' || sha256sum "$YAML" | awk '{print $1}')"
SHA="$SHA" yq -o=json '
  {
    "skill": .skill, "version": .version, "source_sha256": env(SHA),
    "prerequisites": (.prerequisites // []),
    "steps": [ .steps[] | {
        "id": .id, "kind": .kind, "when": (.when // null), "run": (.run // null),
        "verify": (.verify // null), "secret": (.secret // false), "cheap": (.cheap // false),
        "input": (.input // null)
    } ],
    "on_failure": (.on_failure // {"default":"report_and_halt","max_retries":0})
  }' "$YAML" > "$OUT.tmp" && mv -f "$OUT.tmp" "$OUT"
echo "wrote $OUT (source_sha256=$SHA)"
```

### 8.4 `SKILL.md` frontmatter integration + `skill_view` load logic

```yaml
---
name: agent-reach
description: "Use when researching/searching the web across 13 platforms…"
type: routine
version: 1.1.0
setup_needed: true              # existing flag — now load-bearing
setup_manifest: setup.yaml      # where readiness is defined
setup_lock: setup.lock.json     # headless parse target (checksummed, §3.2)
policy_manifest: policy.yaml     # execution-plane policy (§3.8) — optional
srof_lib: ${SROF_LIB}           # shared gate library location
required_commands: [jq]         # only the headless path's hard runtime dep
---
```

Engine load logic — the consumer of the persisted state and the exit-code taxonomy (replaces v0.1's blind early-exit; names the resume reader, P1-3/P2-9):

```
on skill_view(skill):
  if not skill.setup_needed: proceed
  elif skill.has_manifest():
     read .state/provisioning.json:
        state == BLOCKED_ON_INPUT → surface need/fix to the human ("帮我配 <need>"), resume from there
        state == BROKEN           → re-provision only the broken step
        state == PROVISIONED      → re-verify cheap gates (cache, not proof, §3.5):
                                       all pass → proceed
                                       any fail → mark BROKEN, re-provision broken step
        else (UNPROVISIONED)      → run provisioning
                                       interactive → LLM-driven §3.3
                                       headless    → setup.sh --auto §8.2, then map exit:
                                          0  → PROVISIONED
                                          20 → BLOCKED_ON_INPUT (read need/fix, surface to human)
                                          21 → another run in progress (back off, retry later)
                                          22 → BROKEN (report reason)
                                          23 → lock drift (run srof-lock, then retry)
  else:                             # legacy skill, no manifest
     warn("requires setup but no setup.yaml — agent will improvise")
```

The exit-code taxonomy (20/21/22/23) now has a named consumer — `skill_view` on the next entry, and any supervising orchestrator — with a single mapping table (P2-9).

---

## 9. Migration Path & Backward Compatibility

### 9.1 cc-tmux (already has the gate pattern)

| Current cc-tmux | SROF v1.1 migration |
|---|---|
| `gate-verify.sh`, `gate-danger.sh`, `gate-counter.sh` | Keep, but conform to §6: each emits `verdict`+`authority`, uses `unknown`+exit≠0 for could-not-determine (never `block`+exit≠0), and `gate-counter` reads its count from `runtime.json` (§6.11). `gate-verify` becomes class-(b) only (last-result); re-query checks move to `gate-check`. |
| `gate-counter.sh` hard-codes limits | Move the *limit* into **`policy.yaml`** `execution.limits` (NOT `setup.yaml` — execution plane, P1-5); counter keeps only the *count* (§4.3). |
| session caps / kill rules | Declare in `policy.yaml` (`limits.sessions_active`, `danger.kill_pane`). The engine compares `gate-counter sessions_active` to the cap; `gate-danger kill_pane:self` → `block`. |
| `.state/` in `/tmp` | Split: durable bits → skill-local `.state/`; the session **lock** stays in the ephemeral runtime dir (correct — must be ephemeral, §3.6, D-1), now with PID-reclaim. |
| one lock for everything | Set `policy.yaml: execution.lock_scope: resource:pane` (P1-6) so concurrent panes don't serialize on a single per-skill lock. |
| `cc-start.sh` does lock + session setup | Extract pre-flight precondition checks into `setup.yaml` steps (`kind: auto`); keep lock acquisition as an actuator. |
| implicit setup | Add a small `setup.yaml`: prerequisites `command_exists:claude`, `command_exists:tmux`. |

### 9.2 agent-reach (the motivating case)

The §3.1 manifest *is* the agent-reach migration: per-platform login becomes `kind: input` steps with `source_order: [vault, env, human]`, secrets flowing via `$SROF_INPUT_FILE` (§3.7), so "帮我配小红书" maps to the `BLOCKED_ON_INPUT → input` flow — and because the parked state is now persisted (P1-3), a cron attempt that parks can be resumed by the next interactive session. Headless can fully provision *only* the steps it can seed from env/vault; an `input` step with no seed parks (honest: cron cannot invent a human's API key). Zero API fees preserved — every `run:` is an existing CLI call; gates are pure local observations (the `status_json` verifies use read-only `--status`/`config get`, not paid endpoints).

### 9.3 Backward compatibility

Skills **without** `setup.yaml` are untouched: the engine sees no manifest and falls back to "warn + improvise" exactly as today. SROF is strictly opt-in; adoption is per-skill and incremental. `policy.yaml` is optional — a skill with no execution-plane limits omits it and the engine applies no caps.

---

## 10. Honest Delta — what carried over, what v1.1 changes

**Kept from v1.0 (the architecture the audit affirmed):** two nested lifecycles (provisioning ⊃ execution); `fail` vs `block` = authority-to-clear; exit-code ⟂ verdict; state-file-as-cache + re-verify-on-entry; "split state by lifetime, not scope"; resolving all five decisions instead of offering a menu; the sensor/actuator/engine triad (§1.2).

**Changed in v1.1 (contract-surface fixes the audit required):**
1. **Verify can now observe the actuator** via the `$SROF_RUN_RESULT` file contract + the `srof-run` actuator-runner, used by both paths; verify vocabulary split into re-query (class a, `gate-check`) and last-result (class b, `gate-verify`); mutating re-verifies forbidden (P0-1).
2. **`setup.sh --auto` rewritten as an explicit degraded-mode engine** with prerequisites, retry-to-policy, safe-default-on-broken-gate, and full `steps{}` state write (P0-2).
3. **`when` semantics fixed and vocabulary made positive-only** — `command_missing`/`env_missing` deleted; `when` PASS→skip, FAIL→run; every mutating step (incl. `register-skill`) has a `when` (P1-1).
4. **Secret channel `$SROF_INPUT_FILE`** — plaintext never transits the LLM; value-interpolation forbidden (P1-2).
5. **`BLOCKED_ON_INPUT` persisted** before `exit 20`, with a named resume reader (`skill_view`) and exit-code taxonomy (P1-3/P2-9).
6. **`setup.lock.json` gains `source_sha256`** + refuse-on-drift; `srof-lock` named as the generator; total projection; LLM-emit demoted to emergency (P1-4/P2-8).
7. **`policy.yaml`** introduced for execution-plane limits; `setup.yaml` stays provisioning-only (P1-5).
8. **Nesting invariant scoped to one execution context**; cross-session BROKEN semantics defined; `lock_scope: skill | resource:<key>` made a manifest choice (P1-6).
9. **Folded correctness fixes**: PID-liveness lock reclaim (P2-1); atomic `.tmp`+`mv` state writes (P2-2); `unknown`+exit≠0 instead of `block`+exit≠0 for broken gates (P2-6); `cheap` field defined (P2-7); counter persistence in `runtime.json` (P2-10); headless secret seeding so cron isn't always blocked (P2-4, partial).
10. **De-duplicated** the one principle to a single canonical statement (§1.2) with cross-references, trimming the ~6× restatement (P3-1).

**Stale-confidence banner retired.** v1.0's reference code (§8.2) was broken-but-confident; v1.1's reference code is written to the contracts it depends on, and the `$SROF_RUN_RESULT` thread is traced end-to-end (manifest §3.1 → lock §3.2 → contract §6.8 → gates §6.9 → both runners §3.3/§8.2).

---

## 11. Next Steps

1. **Prototype the contract, not the skill.** Implement `$SROF_LIB/{gate-check,gate-verify,gate-counter,srof-run}.sh` to the §6 envelope; write a conformance test: each target → expected verdict + exit code, including the broken-gate (`unknown`+exit 1) and last-result (`exit_code`/`result_json` via a seeded `$SROF_RUN_RESULT`) cases.
2. **Migrate cc-tmux first** (it already has gates) — proves the library/override split (§6.6), the lock-stays-ephemeral rule (D-1), `policy.yaml` (§3.8), and `lock_scope: resource:pane` (P1-6).
3. **Then agent-reach** — proves `kind: input` + `$SROF_INPUT_FILE` + persisted `BLOCKED_ON_INPUT` + `source_order` end to end ("帮我配小红书").
4. **Wire `srof-lock` into skill-authoring** publish/lint, with a drift check (`sha256(setup.yaml) == lock.source_sha256`) as a CI assertion (P1-4).
5. **Update the `skill-authoring` skill** with the SROF section: manifest schema, the gate contract, the `$SROF_RUN_RESULT`/`$SROF_INPUT_FILE` contracts, and the §4.2 placement test.
6. **Wire Hermes `skill_view`** to the §8.4 load logic (read persisted state; re-verify cheap gates; map headless exit codes).

---

## 12. Changes from v1.0 (audit closure)

| Finding | Severity | Fix in v1.1 | Section(s) touched |
|---|---|---|---|
| P0-1 verify gate cannot observe actuator result | P0 | `$SROF_RUN_RESULT` file contract; `srof-run` actuator-runner (both paths); verify split into class-(a) re-query (`gate-check`) / class-(b) last-result (`gate-verify`); mutating re-verifies forbidden | §1.3, §3.1, §3.3, §6.4, §6.5, §6.8, §6.9, §8.2 |
| P0-2 headless `setup.sh` contradicts spec / unsafe | P0 | Rewritten as degraded-mode engine: prerequisite phase, retry-to-`max_retries` from data, safe-default-on-broken-gate (`[ -x ]` presence vs exit≠0), full `steps{}` state write | §3.4, §8.2 |
| P1-1 `when` inverted + `*_missing` targets unimplemented | P1 | Positive-only vocabulary; `when` PASS→skip / FAIL→run; `when` on every mutating step incl. `register-skill` | §3.1, §3.3, §6.5, §6.7, §8.2 |
| P1-2 secret leaks through the LLM transcript | P1 | `$SROF_INPUT_FILE` path-only channel; value-interpolation forbidden; canonical `secret:true` path | §3.1, §3.7, §4.4, §6.8 |
| P1-3 `BLOCKED_ON_INPUT` never persisted | P1 | Persist `need`/`fix`/`since` to `.state` before `exit 20`; `skill_view` reads on resume; interactive persists on defer | §3.4, §5.1, §5.5, §8.2, §8.4 |
| P1-4 `setup.lock.json` drift, no detection | P1 | `source_sha256` + refuse-on-drift; `srof-lock` generator named; total projection; LLM-emit → emergency only | §3.2, §8.2, §8.3 |
| P1-5 execution-plane policy has no home | P1 | `policy.yaml` execution-plane surface; `setup.yaml` provisioning-only; cc-tmux repointed | §2.2, §3.8, §4.3, §9.1 |
| P1-6 nesting invariant single-process; per-skill lock over-serializes | P1 | Invariant scoped to one execution context; cross-session BROKEN defined; `lock_scope: skill\|resource:<key>` | §3.8, §5.3, §9.1 |
| P2-1 crash-without-reboot wedges locks | P2 (folded) | Owner PID in lock dir; `kill -0` liveness reclaim | §3.6, §8.2 |
| P2-2 state writes not atomic | P2 (folded) | `.tmp`+`mv` atomic rename; lock-free reads safe | §4.4, §5.5, §6.8, §8.2 |
| P2-6 reference gate emits `block`+exit≠0 | P2 (folded) | `unknown`+exit≠0 for could-not-determine; `block` only with exit 0 | §6.2, §6.3, §6.7, §6.9, §6.10, §6.11 |
| P3-1 principle restated ~6× | P3 (folded) | Single canonical statement in §1.2; others cross-reference | §0, §1.2, §1.3, §4.1, §6.1, §7, §10 |
| P2-4 `vault` undefined (partial) | P2 (consistency) | Headless seed: env → `$SROF_VAULT_GET <key>` → park; vault = the configured fetch command | §3.7, §8.2 |
| P2-7 `cheap:` used, never defined | P2 (consistency) | `cheap: bool` added to step schema; drives cheap re-verify on entry | §3.1, §3.5 |
| P2-8 lock projection lossy/unspecified | P2 (consistency) | Total projection (all runner-read fields); example regenerated | §3.2, §8.3 |
| P2-9 exit-code taxonomy has no consumer | P2 (consistency) | `skill_view` named as consumer; single exit→action table | §8.4 |
| P2-10 retry-counter persistence unspecified | P2 (consistency) | Runner increments `runtime.json.retries`; `gate-counter` reads that file (pure) | §5.5, §6.11, §8.2 |

*Not addressed in v1.1 (out of the P0/P1 mandate, flagged for a later pass):* P2-3 (cheap re-verify detects absence, not invalidity — partially mitigated by the optional verify TTL noted in §3.5), and the cosmetic P3-3 losses (optional-creatable prerequisites, per-step human `name:` labels).

---

## Appendix A — Agent-Reach Pattern Analysis (retained)

> "Agent 读了 SKILL.md 之后自己知道该调什么。需要登录的平台（小红书、Twitter、Reddit），告诉 Agent「帮我配 XXX」即可解锁。"

Mapped to SROF:
1. **Self-describing setup** → the `setup.yaml` manifest *is* the self-description; the LLM reads it directly.
2. **Conversational unlock** ("帮我配 XXX") → user intent maps to a `kind: input` step; headless surfaces it as the **persisted** `BLOCKED_ON_INPUT.need`, which `skill_view` reads on the next entry (P1-3).
3. **Platform-specific auth** → `source_order: [vault, env, human]` per step handles differing flows; the secret flows by path via `$SROF_INPUT_FILE`, never through the transcript (§3.7).
4. **Zero API fees** → every `run:` is an existing CLI call; gates are pure local observations, and verifies re-query read-only `--status`/`config get`, never paid or mutating endpoints.

## Appendix B — Glossary

| Term | Meaning |
|---|---|
| **Gate / sensor** | Pure function observing world state (or `$SROF_RUN_RESULT`) → verdict. Never mutates. (§6.1) |
| **Actuator** | A command that changes the world (`run:`, lock acquire), run through `srof-run`. Decides nothing. |
| **`srof-run`** | The actuator-runner; executes `run:` and writes the captured result to `$SROF_RUN_RESULT`. (§6.8) |
| **Engine** | The LLM: sequences, interprets, converses, decides risk. The headless `setup.sh` is a bounded degraded-mode substitute. |
| **Provisioning** | Outer lifecycle: "can this skill run at all?" Persistent, rare, idempotent. |
| **Execution** | Inner lifecycle: "may this action run now?" Ephemeral, frequent. Policy in `policy.yaml`. |
| **`$SROF_RUN_RESULT`** | Path to the JSON descriptor (`exit_code`, `stdout_path`) of the just-run actuator; read by class-(b) verifies. (§6.8) |
| **`$SROF_INPUT_FILE`** | Path to a umask-077 file holding a secret value; actuators read it; the LLM never sees the value. (§3.7) |
| **`pass/fail/block`** | World-verdicts; `fail` = agent may clear, `block` = only a human may. `unknown` = could-not-determine (exit≠0). (§6.2) |
| **`when` (guard)** | "Skip when this already holds": gate PASS → SKIP, FAIL → RUN. Positive-only targets. (§3.1, P1-1) |
| **`BLOCKED_ON_INPUT`** | Provisioning parked awaiting a human value/confirm; **persisted** + self-describing; resumable. (§5.1, P1-3) |
| **`BROKEN`** | A previously-passing verify now fails; re-provision the broken step. (§5.1) |
| **State file = cache** | Records completed actions, not current health; re-verified on entry. (§3.5) |
| **`lock_scope`** | `skill` or `resource:<key>`; per-resource avoids over-serializing concurrent sessions. (§3.8, P1-6) |

---

*SROF v1.1 — first-principles redesign, audit-closure revision. Produced by Hermes Agent (小黄) + CC, 2026-06-28. Supersedes v1.0; closes the independent audit's 2×P0 and 6×P1.*
