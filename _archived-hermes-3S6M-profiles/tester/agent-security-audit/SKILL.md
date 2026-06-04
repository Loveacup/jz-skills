---
name: agent-security-audit
description: "Use when auditing AI agent code for security vulnerabilities — prompt injection detection, confused-deputy attacks, MCP config auditing, tool-chain exfiltration, and OWASP Agentic Top 10 compliance for 刑部 security review. Based on agent-audit (HeadyZhang/agent-audit, 172⭐, 49 rules, 94.6% recall) and prompt-guard (seojoonkim/prompt-guard, 152⭐, 840+ patterns) patterns. Do NOT use for general code linting (use code-review-toolkit) or for non-AI application security scanning."
version: 1.0.0
author: Hermes Agent (based on HeadyZhang/agent-audit + seojoonkim/prompt-guard)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [xingbu, security, audit, prompt-injection, owasp, mcp, static-analysis]
    related_skills: [code-review-toolkit, kanban-gate, three-provinces-constitution]
---

# Agent Security Audit — 刑部 AI Agent 安全审计

> Based on agent-audit (HeadyZhang/agent-audit, Python, 172⭐, 49 OWASP rules) and prompt-guard (seojoonkim/prompt-guard, Python, 152⭐, 840+ injection patterns). Adapted for 三省六部 agent code review.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is just a config change, no security risk" | MCP server configs are the #1 attack surface. A single `command: "sh -c ..."` in an MCP manifest gives arbitrary code execution |
| "Prompt injection only affects chatbots, not our internal agents" | 三省六部 agents consume untrusted input from Kanban task bodies, GitHub issues, web search results, and user messages — all injection vectors |
| "I'll review security after the feature ships" | Agent vulnerabilities compound: a confused-deputy attack in one agent can cascade through the entire Kanban chain |
| "Static analysis is enough, I don't need the runtime patterns" | prompt-guard's 840+ patterns catch live attacks regex alone misses — obfuscation (Base64/homoglyphs/ROT13) must be decoded first |

## When to Use

- PR review for any agent that accepts external input (Kanban bodies, web content, user messages)
- Auditing MCP server configurations before deployment
- Security review of new agent profiles or SOUL.md changes
- Pre-commit gate for agent code changes
- Incident response: tracing how a prompt injection propagated through a Kanban chain

## OWASP Agentic Top 10 Coverage

Agent-audit maps 49 rules to all 10 OWASP categories:

| OWASP # | Category | Rules | Example Detection |
|---------|----------|-------|-------------------|
| ASI-01 | Prompt Injection | AGENT-001..010 | User input concatenated into system prompt |
| ASI-02 | Insecure Tool Use | AGENT-011..020 | `exec()`/`subprocess` with untrusted input |
| ASI-03 | MCP Misconfiguration | AGENT-021..030 | MCP server `command` with shell interpolation |
| ASI-04 | Data Leakage | AGENT-031..035 | Agent logging secrets to disk |
| ASI-05 | Goal Manipulation | AGENT-036..040 | System prompt overrides from external sources |
| ASI-06 | Tool Chain Abuse | AGENT-041..045 | Chained tool calls exfiltrating data |
| ASI-07 | Memory Poisoning | AGENT-046..047 | `.agentrc` / memory injection |
| ASI-08 | Output Handling | AGENT-048 | Unsanitized agent output to downstream systems |
| ASI-09 | Supply Chain | AGENT-049 | Malicious MCP server from untrusted source |
| ASI-10 | Agent Impersonation | AGENT-050 | Agent spoofing another profile |

## Quick Start

### Install agent-audit

```bash
pip install agent-audit
```

### Scan an agent profile

```bash
# Scan a specific profile's config + MCP servers
agent-audit scan ~/.hermes/profiles/engineer/ \
  --output json \
  --severity high,critical

# Scan with OWASP mapping
agent-audit scan ~/.hermes/profiles/regent/ \
  --rules owasp-top-10 \
  --format markdown > audit-report.md
```

### Runtime Guard (prompt-guard pattern)

```bash
# Install
pip install prompt-guard

# Guard mode: intercept before agent processes input
echo "user message with potential injection" | prompt-guard check --threshold MEDIUM

# Audit mode: scan historical agent conversations
prompt-guard audit ~/.hermes/profiles/regent/sessions/ --output jsonl
```

## Audit Checklist for 三省六部 Profiles

For each profile under review, verify:

### Config Audit
```bash
# Check for MCP servers with shell commands
grep -r "command:" ~/.hermes/profiles/$PROFILE/mcp_servers/ | grep -E '(sh|bash|zsh)'

# Check for hardcoded credentials
grep -rE '(api_key|token|secret|password)\s*[:=]\s*[^\s"]{8,}' ~/.hermes/profiles/$PROFILE/
```

### SOUL.md Audit
```bash
# Check for dangerous instructions
grep -E '(exec|eval|subprocess|os\.system)' ~/.hermes/profiles/$PROFILE/SOUL.md

# Check for tool escalation paths
grep -E '(sudo|root|admin|privilege)' ~/.hermes/profiles/$PROFILE/SOUL.md
```

### Kanban Body Injection Surface
```bash
# Kanban task bodies are user-controlled — audit how agents consume them
grep -r "HERMES_KANBAN_BODY\|task_body\|kanban body" ~/.hermes/profiles/$PROFILE/
```

## Severity Classification

| Severity | Example | Action |
|----------|---------|--------|
| **CRITICAL** | `exec()` on untrusted MCP input | Block merge, immediate fix |
| **HIGH** | Prompt injected via Kanban body | Block merge, fix before deploy |
| **MEDIUM** | Missing output sanitization | Create tracking issue |
| **LOW** | Informational logging of tool args | Note in audit report |

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [agent-audit](https://github.com/HeadyZhang/agent-audit) | 172 | MIT | 49 OWASP rules, 94.6% recall, taint analysis |
| [prompt-guard](https://github.com/seojoonkim/prompt-guard) | 152 | MIT | 840+ patterns, 10 languages, semantic detection |
| [AgentShield](https://github.com/AdityaBelhekar/AgentShield) | 2 | MIT | Runtime guard: goal drift, tool abuse, memory poisoning |

## Common Pitfalls

- **False positives on config values**: `api_key: $ENV_VAR` is not a hardcoded credential. Use taint analysis to trace to env vars.
- **MCP tool descriptions as injection surface**: Tool descriptions are displayed to the agent and can inject instructions. Audit them too.
- **Cross-agent trust assumptions**: Agent A trusts Agent B's output. If B is compromised, A is too. Always validate inter-agent messages.

---

## ✅ Verification Checklist (RUN AFTER SECURITY AUDIT)

- [ ] Did I scan all profiles that accept external input (not just the one being changed)?
- [ ] Did I check MCP server configs for shell command injection?
- [ ] Did I audit Kanban body consumption paths for prompt injection?
- [ ] Did I classify all findings by OWASP ASI category AND severity?
- [ ] Did I create blocking issues for CRITICAL/HIGH findings?
- [ ] Did I run both static (agent-audit) AND runtime pattern (prompt-guard) checks?

**If any box is unchecked, go back.**
