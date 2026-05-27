---
name: specialist-engineer
description: "Use when deploying external specialist AI agents for complex engineering tasks — domain-expert hiring pipeline, adversarial code review, multi-model routing, and external contractor integration for 将作监 operations. Based on Nexus Hyper Agent Team (asiflow/claude-nexus-hyper-agent-team, 31 domain experts, 341-assertion test suite) and vibecosystem (vibeeval/vibecosystem, 321⭐, 136 agents, 260 skills) patterns. Do NOT use for in-house六部 engineering work (use engineer profile) or for simple single-file changes."
version: 1.0.0
author: Hermes Agent (based on asiflow/claude-nexus-hyper-agent-team + vibeeval/vibecosystem)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [jiangzuojian, specialist, external-contractor, expert-system, engineering]
    related_skills: [kanban-orchestrator, agent-registry, a2a-protocol]
---

# Specialist Engineer — 将作监外聘专家工程

> Based on Nexus Hyper Agent Team (31 domain experts, 341-assertion contract suite) and vibecosystem (321⭐, 136 agents, 260 skills, self-learning). Adapted for 三省六部 将作监 external specialist deployment and management.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "Engineer can handle this, no need for a specialist" | Generalist agents lack domain depth. A security audit by engineer misses OWASP ASI-02 violations that a security specialist catches in 30 seconds |
| "I'll just add a specialist prompt to the existing agent" | Specialist agents need isolated workspaces (Git worktrees), adversarial review (challenger gate), and trust calibration. Prompt hacking doesn't provide these |
| "Hiring a specialist agent is too complex for a one-off task" | The gated hiring pipeline (research→synthesis→validation→challenger→register→verify→probation→promote) ensures quality. One bad specialist can corrupt the codebase |
| "I can assess specialist quality by reading their output" | Output quality ≠ process quality. A specialist might produce correct code that introduces supply chain vulnerabilities. Adversarial review catches this |

## When to Use

- Complex multi-file refactoring requiring domain expertise (crypto, distributed systems, compiler internals)
- Security-critical code that needs adversary-minded review
- Cross-stack work (frontend + backend + infra) where no single agent has full coverage
- External contractor integration: hiring and managing specialist agents from the talent pool
- Code that will be deployed to production and needs 341-assertion contract validation

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              将作监 Specialist Hub                        │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Talent Scout  │  │  Recruiter   │  │ Challenger    │  │
│  │ detect gaps   │  │ gated hiring │  │ adversarial   │  │
│  │ 5-signal conf │  │ 8 phases     │  │ review gate   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  Specialist Pool:                                        │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐  │
│  │ security│ │ crypto  │ │ frontend │ │ distributed│  │
│  │ auditor │ │ engineer│ │ architect│ │ systems    │  │
│  └─────────┘ └─────────┘ └──────────┘ └────────────┘  │
│                                                         │
│  Validation: 341-assertion contract test suite          │
│  Trust: Bayesian per-agent trust ledger                  │
└─────────────────────────────────────────────────────────┘
```

## Core Capabilities

### 1. Gated Hiring Pipeline

When a coverage gap is detected, the talent scout + recruiter hire a new specialist:

```
Phase 1: Research    — Study the domain, identify required expertise
Phase 2: Synthesis   — Draft specialist prompt + toolset spec
Phase 3: Validation  — Run against known test cases (contract suite)
Phase 4: Challenger  — Adversarial agent tries to break the specialist
Phase 5: Register    — Atomic registration in agent-registry
Phase 6: Verify      — Post-hire smoke test on real task
Phase 7: Probation   — 5-task observation period with trust score
Phase 8: Promote     — Full specialist status, trust ledger active
```

### 2. Coverage Gap Detection

```bash
# 将作监 continuously monitors for capability gaps
hermes jiangzuojian detect-gaps

# Output:
# Gap detected: solidity-smart-contract (confidence: 0.87)
#   Signal 1: 3 recent tasks required Solidity knowledge
#   Signal 2: engineer failed 2/3 Solidity tasks
#   Signal 3: no registered specialist for Solidity
#   Signal 4: session-sentinel co-signed the gap
#   Signal 5: estimated cost of gap: $45/week in failed tasks
# 
# Recommendation: HIRE solidity-specialist
#   Estimated cost: $15/week
#   ROI: 3x (saves $45/week, costs $15/week)
```

### 3. Adversarial Review (Challenger Gate)

Before any specialist output is accepted, an adversarial agent reviews it:

```bash
hermes jiangzuojian challenger-review \
  --specialist crypto-engineer \
  --task "implement key derivation function" \
  --output /tmp/kdf-implementation.py

# Challenger tries to:
# 1. Inject edge cases that break the implementation
# 2. Find timing side-channels
# 3. Verify constant-time operations
# 4. Check for known-weak PRNG usage
# 5. Validate against NIST SP 800-132
```

### 4. Trust Ledger (Bayesian Calibration)

Every specialist has a trust score calibrated by task outcomes:

```yaml
specialist: solidity-expert
trust_ledger:
  total_tasks: 15
  successes: 13
  failures: 1
  challenger_overrides: 1
  
  trust_score: 0.87  # Bayesian posterior
  domain_scores:
    erc20: 0.95
    erc721: 0.91
    custom_contracts: 0.76  # weaker area
    security_audit: 0.98
  
  trend: improving (+0.03 per 5 tasks)
  last_incident: "2026-05-20: reentrancy vulnerability missed (caught by challenger)"
```

### 5. Multi-Model Routing

将作监 routes tasks to the optimal specialist + model combination:

```bash
hermes jiangzuojian route \
  --task "audit smart contract for reentrancy vulnerabilities" \
  --budget 2.00

# Router decision:
# Specialist: solidity-expert (trust: 0.98 on security_audit)
# Model: claude-opus-4 (reasoning_effort=high, cost: $1.50)
# Fallback: deepseek-v4-pro (if opus unavailable)
# Estimated: 3 tool calls, $1.80, 45s
```

## Specialist Roster (Example)

| Specialist | Domain | Trust | Model | Cost/task |
|-----------|--------|-------|-------|-----------|
| security-auditor | OWASP, injection, auth | 0.95 | claude-sonnet-4 | $0.80 |
| crypto-engineer | ECDSA, KDF, TLS | 0.88 | claude-opus-4 | $1.50 |
| distributed-systems | Raft, Paxos, CRDTs | 0.82 | deepseek-v4-pro | $0.60 |
| performance-profiler | CPU, memory, I/O | 0.91 | haiku | $0.15 |
| accessibility-expert | WCAG 2.2, ARIA | 0.94 | gemini-2.5-pro | $0.40 |

## Quick Start

```bash
# Initialize specialist hub
hermes jiangzuojian init

# Hire first specialist
hermes jiangzuojian hire \
  --domain "security-audit" \
  --from registry \
  --phases 8

# Run a task with specialist
hermes jiangzuojian execute \
  --task "audit ~/.hermes/profiles/regent/scripts/kanban_gate.py" \
  --specialist security-auditor
```

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [Nexus Hyper Agent Team](https://github.com/asiflow/claude-nexus-hyper-agent-team) | - | - | 31 experts, 341-assertion suite, gated hiring |
| [vibecosystem](https://github.com/vibeeval/vibecosystem) | 321 | - | 136 agents, 260 skills, self-learning |
| [specialist-agent](https://github.com/HerbertJulio/specialist-agent) | 10 | MIT | 27 agents, 7 framework packs |

## Integration with 三省六部

将作监 operates as a specialist augmentation layer:

```
Kanban chain: planner → reviewer → shangshu → [engineer, 将作监]
                                                    │
                                          ┌─────────┘
                                          ▼
                                    将作监 Specialist
                                    (external contractor)
                                          │
                                    ┌─────┴─────┐
                               challenger    trust ledger
                               review        calibration
```

将作监 differs from 兵部 (engineer):
- **兵部**: Standing department, generalist, always online
- **将作监**: External specialist, domain expert, hired on-demand

## Common Pitfalls

- **Specialist overload**: Hiring specialists for every task dilutes the trust ledger. Only hire when gap confidence > 0.75.
- **Challenger bypass**: "The code looks fine, skip adversarial review." NEVER. The challenger gate is the last defense.
- **Trust score blind spots**: A specialist with 0.95 trust might have 0.50 in a subdomain. Always check domain_scores, not just aggregate.

---

## ✅ Verification Checklist (RUN BEFORE DEPLOYING SPECIALIST OUTPUT)

- [ ] Did the specialist pass all 8 phases of the gated hiring pipeline?
- [ ] Did the challenger agent review the output (not just the hiring agent)?
- [ ] Did I check the specialist's trust score for the SPECIFIC domain (not aggregate)?
- [ ] Is the specialist working in an isolated workspace (Git worktree, not shared)?
- [ ] Did I log the task outcome to update the trust ledger?

**If any box is unchecked, go back.**
