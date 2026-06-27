# Skill Runtime Orchestration Framework (SROF) — Design Document

> **Status**: Design Draft v0.1
> **Date**: 2026-06-27
> **Context**: Optimizing skill-authoring for Hermes Agent, inspired by Agent-Reach first-run config pattern and cc-tmux script/LLM division of labor.

---

## 1. Architecture Overview

### 1.1 Core Problem Statement

Current skill system has two gaps:

| Gap | Current State | Desired State |
|-----|--------------|---------------|
| **First-run setup** | `setup_needed: true` is declarative only. Agent sees flag but doesn't know steps, order, or verification. | Agent reads setup manifest → runs steps → verifies → persists state → proceeds |
| **Hard orchestration** | cc-tmux implements script-gate + LLM-decision ad-hoc. No reusable framework. | Any skill can adopt: scripts enforce gates, LLM makes decisions, clear interface |

### 1.2 Design Principles

1. **Scripts enforce, LLM decides** — Same as cc-tmux: "can/cannot" by code, "how" by LLM
2. **State is file-based, not memory** — Survives across sessions, auditable, zero dependencies
3. **Idempotent by design** — Setup can re-run; checks "already done?" before doing
4. **Progressive disclosure** — Setup manifest is small; heavy logic in `scripts/`
5. **Backward compatible** — Existing skills work unchanged; new framework is opt-in

### 1.3 Components

```
┌─────────────────────────────────────────────────────────────┐
│  Skill Directory                                            │
│  ├── SKILL.md          (frontmatter + body)                │
│  ├── scripts/                                                   │
│  │   ├── setup.sh      ← NEW: setup orchestrator           │
│  │   ├── gate-check.sh ← NEW: reusable gate pattern        │
│  │   ├── gate-verify.sh                                    │
│  │   ├── gate-danger.sh                                     │
│  │   └── ... (existing skill scripts)                       │
│  ├── setup.yaml        ← NEW: declarative setup manifest   │
│  ├── references/                                            │
│  └── .state/           ← NEW: runtime state (gitignored)   │
│       └── setup.json   (setup completion state)              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Hermes Agent Runtime                                       │
│  ├── skill_view() → loads SKILL.md                          │
│  ├── setup_needed? → check .state/setup.json                │
│  ├── If unconfigured: run scripts/setup.sh → verify         │
│  └── Then proceed with skill task                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Setup Manifest Schema (`setup.yaml`)

```yaml
# setup.yaml — Declarative first-run configuration
# Placed in skill root directory, alongside SKILL.md

version: "1.0"

# Prerequisites: what must exist BEFORE setup runs
prerequisites:
  commands:
    - name: node
      check: "node --version"
      min_version: "18.0.0"
    - name: tmux
      check: "tmux -V"
  env_vars:
    - name: HOME
      required: true
  files:
    - path: ~/.claude/settings.json
      required: false  # if missing, setup will create it

# Setup steps: ordered, idempotent
steps:
  - id: install-cli
    name: "Install CLI tool"
    when: "command_missing:agent-reach"
    run: |
      npm install -g @panniantong/agent-reach
    verify: "command_exists:agent-reach"
    
  - id: configure-env
    name: "Configure environment"
    when: "env_missing:AGENT_REACH_API_KEY"
    prompt: |
      Please provide your Agent-Reach API key.
      Get one at: https://agent-reach.dev/settings
    # ^ LLM presents this prompt to user; user's response feeds into next step
    run: |
      echo "AGENT_REACH_API_KEY=$USER_INPUT" >> ~/.agent-reach/env
    verify: "env_exists:AGENT_REACH_API_KEY"
    
  - id: test-connection
    name: "Test API connection"
    run: |
      agent-reach ping
    verify: "exit_code:0"
    
  - id: register-skill
    name: "Register skill with agent-reach"
    run: |
      agent-reach skill --register ./SKILL.md
    verify: "json_path:.registered == true"

# State persistence
state:
  file: .state/setup.json
  format: json
  
# Failure handling
on_failure:
  action: report_and_abort  # report_and_abort | retry | skip
  max_retries: 2
  ```

### 2.1 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| YAML not JSON | Human-readable; skill authors write it |
| `when` conditions | Idempotency: skip if already satisfied |
| `prompt` for user input | LLM handles the conversation; script just needs the result |
| `verify` per step | Each step must prove it worked |
| `.state/` directory | Gitignored runtime state; separate from skill source |

---

## 3. Gate Script Interface

Reusable pattern from cc-tmux, generalized:

### 3.1 Contract

```bash
# Gate scripts: standardized input/output
# 
# Input: Environment variables + arguments
#   $1 = check type (check|verify|danger)
#   $2 = target (what to check)
#   $CHECK_FILE = path to check definition (optional)
#
# Output: Structured JSON to stdout
#   {
#     "gate": "check|verify|danger",
#     "target": "...",
#     "result": "pass|fail|block",
#     "reason": "human-readable explanation",
#     "data": { ... }  # optional structured data
#   }
#
# Exit code: 0 = script ran correctly (result independent)
#            1 = script error (couldn't determine)
```

### 3.2 Example Gate Scripts

```bash
#!/bin/bash
# scripts/gate-check.sh — Check if prerequisites are satisfied

set -euo pipefail

TARGET="${1:-}"
CHECK_TYPE="${2:-check}"

result() {
  local status="$1" reason="$2"
  cat <<EOF
{"gate":"$CHECK_TYPE","target":"$TARGET","result":"$status","reason":"$reason"}
EOF
}

case "$TARGET" in
  command_exists:*)
    CMD="${TARGET#command_exists:}"
    if command -v "$CMD" >/dev/null 2>&1; then
      result "pass" "Command '$CMD' found"
    else
      result "fail" "Command '$CMD' not found"
    fi
    ;;
  env_exists:*)
    VAR="${TARGET#env_exists:}"
    if [ -n "${!VAR:-}" ]; then
      result "pass" "Environment variable '$VAR' is set"
    else
      result "fail" "Environment variable '$VAR' is not set"
    fi
    ;;
  file_exists:*)
    FILE="${TARGET#file_exists:}"
    if [ -f "$FILE" ]; then
      result "pass" "File '$FILE' exists"
    else
      result "fail" "File '$FILE' not found"
    fi
    ;;
  *)
    result "block" "Unknown check target: $TARGET"
    exit 1
    ;;
esac
```

### 3.3 LLM/Script Division of Labor

| Responsibility | Script (Hard) | LLM (Soft) |
|----------------|---------------|------------|
| **Can run?** | Check prerequisites, exit codes | N/A (script decides) |
| **What to do?** | N/A (LLM decides) | Read setup.yaml, plan steps, handle user prompts |
| **Did it work?** | Verify with commands, parse output | Interpret ambiguous results, decide retry |
| **Safe to proceed?** | Danger patterns, resource locks | Risk assessment, user confirmation |
| **State transition** | Write `.state/setup.json` | Decide when to transition |

### 3.4 Communication Channel

File-based state machine in `.state/setup.json`:

```json
{
  "skill": "agent-reach",
  "version": "1.0",
  "state": "READY",
  "state_since": "2026-06-27T06:00:00Z",
  "steps": {
    "install-cli": {"status": "completed", "completed_at": "..."},
    "configure-env": {"status": "completed", "completed_at": "..."},
    "test-connection": {"status": "completed", "completed_at": "..."}
  },
  "last_run": "2026-06-27T06:00:00Z",
  "run_count": 3
}
```

States: `UNCONFIGURED` → `SETUP_IN_PROGRESS` → `READY` → `ACTIVE` → `ERROR`

---

## 4. State Machine Specification

### 4.1 States and Transitions

```
                    ┌─────────────┐
         ┌─────────│ UNCONFIGURED │◄────────┐
         │ setup   │ (setup.yaml  │         │ reset
         │ needed  │  exists,     │         │
         │         │  .state missing│        │
         └────────►│ or stale)    │         │
                   └──────┬──────┘          │
                          │ run setup.sh   │
                          ▼                │
                   ┌─────────────┐          │
         ┌────────│ SETUP_IN_   │          │
         │ step   │ PROGRESS    │          │
         │ fail   │ (running    │◄─────────┘
         │        │  steps)     │
         └───────►└──────┬──────┘
                          │ all steps pass
                          ▼
                   ┌─────────────┐
                   │    READY    │◄────────┐
                   │ (setup done,│         │ skill
                   │  idle)      │         │ finishes
                   └──────┬──────┘         │
                          │ skill invoked  │
                          ▼                │
                   ┌─────────────┐        │
                   │   ACTIVE    │────────┘
                   │ (skill task │
                   │  running)   │
                   └─────────────┘
                          │
                          │ fatal error
                          ▼
                   ┌─────────────┐
                   │    ERROR    │◄────────┐
                   │ (setup or   │         │
                   │  skill fail)│         │
                   └─────────────┘         │
                                             │
                                             └──── manual fix
```

### 4.2 Who Decides vs Who Enforces

| Transition | Enforced By (Script) | Decided By (LLM) |
|------------|---------------------|------------------|
| UNCONFIGURED → SETUP_IN_PROGRESS | `setup.yaml` exists; `.state/setup.json` missing or stale | Agent decides to run setup now or defer |
| SETUP_IN_PROGRESS → READY | All `verify` checks pass | Agent decides step order (from `setup.yaml`); user may be prompted |
| SETUP_IN_PROGRESS → ERROR | Step fails after max retries | Agent decides retry/abort/skip strategy |
| READY → ACTIVE | `.state/setup.json` shows READY | Agent decides to invoke skill |
| ACTIVE → READY | Skill task completes (turn-done) | Agent decides when task is "done" |
| ERROR → UNCONFIGURED | Manual fix completed | User decides to retry |

---

## 5. Reference Implementation

### 5.1 Simplified Skill Adopting SROF

```
my-skill/
├── SKILL.md
├── setup.yaml          # ← NEW
├── scripts/
│   ├── setup.sh        # ← NEW: setup orchestrator
│   ├── gate-check.sh   # ← NEW: reusable gate
│   └── main.sh         # existing skill logic
├── .state/
│   └── setup.json      # ← NEW: runtime state (gitignored)
└── references/
    └── setup-guide.md
```

### 5.2 `scripts/setup.sh` (Setup Orchestrator)

```bash
#!/bin/bash
# scripts/setup.sh — Setup orchestrator for any skill
# Reads setup.yaml, runs steps, verifies, persists state

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETUP_YAML="$SKILL_DIR/setup.yaml"
STATE_DIR="$SKILL_DIR/.state"
STATE_FILE="$STATE_DIR/setup.json"

# Ensure state directory exists
mkdir -p "$STATE_DIR"

# Read setup.yaml (requires yq or python)
# ... parse steps ...

# Check if already configured
if [ -f "$STATE_FILE" ]; then
  STATE=$(cat "$STATE_FILE")
  CURRENT_STATE=$(echo "$STATE" | jq -r '.state // "UNCONFIGURED"')
  if [ "$CURRENT_STATE" == "READY" ]; then
    echo '{"result":"skip","reason":"Already configured"}'
    exit 0
  fi
fi

# Run steps in order
# ... for each step:
#   1. Check `when` condition (gate-check.sh)
#   2. If needed, run `run` command
#   3. Run `verify` check (gate-verify.sh)
#   4. Update state file

# Write final state
cat > "$STATE_FILE" <<EOF
{
  "skill": "$(basename "$SKILL_DIR")",
  "version": "1.0",
  "state": "READY",
  "state_since": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo '{"result":"success","reason":"Setup completed"}'
```

### 5.3 `SKILL.md` Frontmatter Integration

```yaml
---
name: my-skill
description: "Use when..."
type: routine
version: 1.0.0
setup_needed: true           # ← Existing flag, now meaningful
setup_manifest: setup.yaml   # ← NEW: points to setup definition
required_commands: [yq, jq]  # ← Existing, used by setup.sh
# ... rest of frontmatter
---
```

---

## 6. Migration Path for Existing Skills

### 6.1 cc-tmux Migration Example

cc-tmux already has the script-gate pattern. Migration would be:

| Current | Migration |
|---------|-----------|
| `setup_needed: false` (implicit) | Add `setup.yaml` for Claude CLI installation check |
| `scripts/gate-{verify,danger,counter}.sh` | Keep as-is; add `gate-check.sh` wrapper for setup.yaml |
| `.state/` in `/tmp` | Move to skill-local `.state/` or keep `/tmp` for ephemeral |
| `cc-start.sh` does lock/session setup | Extract "pre-flight check" into `setup.yaml` step |

### 6.2 Backward Compatibility

```
# In skill_view() loading logic:
if skill.setup_needed:
    if skill.has_setup_manifest():        # NEW
        run scripts/setup.sh              # NEW
    else:
        # LEGACY: just warn, agent figures it out
        warn("Skill requires setup but no setup.yaml found")
```

Skills without `setup.yaml` continue to work as before.

---

## 7. Open Questions (Need Alex's Decision)

### D-1: State Storage Location
- **Option A**: Per-skill `.state/` directory (local, gitignored)
- **Option B**: Centralized `~/.hermes/state/<skill-name>.json` (easier to audit, but cross-profile complexity)
- **Option C**: Both (local for skill-specific, central for cross-skill)

### D-2: Setup Manifest Format
- **Option A**: YAML (human-readable, needs `yq` dependency)
- **Option B**: JSON (machine-first, no extra dependency)
- **Option C**: Embedded in SKILL.md frontmatter (single file, but frontmatter bloat)

### D-3: LLM Prompt Handling in Setup
- **Option A**: Setup script prints prompt text → LLM reads and presents to user (current design)
- **Option B**: Setup script is pure script; LLM handles all user interaction separately
- **Option C**: Hybrid — script for automated steps, LLM for user-input steps

### D-4: iii Hub Integration
- **Option A**: SROF is Hermes-only; iii workers handle their own setup
- **Option B**: SROF is substrate-agnostic; iii workers can call same `gate-check.sh`
- **Option C**: iii has its own setup system; SROF is thin adapter

### D-5: Gate Script Reusability
- **Option A**: Each skill has its own `gate-check.sh` (current cc-tmux pattern)
- **Option B**: Centralized `~/.hermes/scripts/gate-check.sh` shared by all skills
- **Option C**: Both (local overrides central)

---

## 8. Appendix: Agent-Reach Pattern Analysis

From github.com/Panniantong/agent-reach:

> "Agent 读了 SKILL.md 之后自己知道该调什么。需要登录的平台（小红书、Twitter、Reddit），告诉 Agent「帮我配 XXX」即可解锁。"

Key insights for SROF:
1. **Self-describing setup**: The skill itself tells the agent what setup is needed
2. **Conversational unlock**: "帮我配 XXX" = user intent → agent maps to setup step
3. **Platform-specific handling**: Different platforms need different auth flows; setup.yaml `prompt` field handles this
4. **Zero API fees**: Setup uses existing CLI tools, not paid APIs

SROF adopts this by making setup.yaml the "self-describing" manifest, and letting LLM handle the conversational "帮我配 XXX" mapping.

---

## 9. Next Steps

1. **Alex decisions**: Resolve D-1 through D-5
2. **Prototype**: Implement `scripts/setup.sh` + `gate-check.sh` for one skill (e.g., agent-reach or cc-tmux)
3. **Test**: Verify idempotency, failure handling, state persistence
4. **Document**: Update skill-authoring skill with SROF guidelines
5. **Migrate**: Gradually add `setup.yaml` to existing skills

---

*Document produced by Hermes Agent (小黄) + CC design discussion, 2026-06-27*
