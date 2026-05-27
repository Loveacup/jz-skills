---
name: agent-registry
description: "Use when managing the AI agent fleet — capability discovery, agent registration, heartbeat monitoring, dynamic team composition, and talent pool management for 吏部 registry operations. Based on agentregistry (agentregistry-dev/agentregistry, 245⭐, protocol-agnostic MCP+A2A+ACP) and mq9 (robustmq/mq9, 7⭐, agent-native registry+mailbox) patterns. Do NOT use for Kanban task assignment (use kanban-orchestrator) or for profile configuration (use hermes config)."
version: 1.0.0
author: Hermes Agent (based on agentregistry-dev/agentregistry + robustmq/mq9)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [libu, registry, discovery, agents, talent, capability]
    related_skills: [kanban-orchestrator, a2a-protocol, three-provinces-constitution]
---

# Agent Registry — 吏部 Agent 注册与能力发现

> Based on agentregistry (245⭐, protocol-agnostic A2A+MCP+ACP) and mq9 (agent-native registry with persistent mailboxes). Adapted for 三省六部 agent fleet management and dynamic capability discovery.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I know all 15 profiles, I don't need a registry" | Profiles change models, add tools, go offline. Hardcoded assumptions break silently. Registry provides LIVENESS — only running agents appear |
| "Kanban already handles agent assignment" | Kanban assigns by profile name. Registry enables assignment by CAPABILITY: "find me an agent that can do code review" → discovers engineer OR jiangzuojian depending on who's online |
| "A registry is over-engineering for 15 agents" | The fleet grows over time (profiles + external contractors + specialist agents). Start with registry now so agent discovery scales linearly, not combinatorially |
| "I'll just ping each agent to check if it's alive" | 15 agents × heartbeat every 30s = complexity. Registry auto-expires stale registrations — dead agents disappear from discovery automatically |

## When to Use

- Registering new agent profiles or external specialist agents
- Discovering which agents are online and their current capabilities
- Dynamic team composition: "assemble a team for this task from available agents"
- Talent pool management: tracking external experts (将作监, agency-agents-zh style)
- Health monitoring: detecting agents that went offline or changed capabilities

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Agent Registry                      │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Register  │  │ Discover │  │ Heartbeat/Expire │  │
│  │ capabilities│ │ by capability│ │ auto-cleanup    │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                      │
│  Protocols: A2A + MCP + ACP (protocol-agnostic)      │
│  Transport: HTTP + gRPC + message queues             │
└──────────────────────────────────────────────────────┘
         │                │                │
    ┌────▼────┐    ┌──────▼──────┐    ┌───▼───┐
    │ engineer│    │   auditor   │    │jiangzuo│
    │ (online)│    │  (online)   │    │(offline)│
    └─────────┘    └─────────────┘    └───────┘
```

## Core Capabilities

### 1. Capability Registration

Each agent registers with its capabilities when starting:

```yaml
# engineer registers
POST /agents/register
{
  "name": "兵部 Engineer",
  "profile": "engineer",
  "capabilities": [
    "code-implementation",
    "code-review-response",
    "architecture-refactoring",
    "test-writing"
  ],
  "protocols": ["A2A", "MCP"],
  "endpoints": {
    "a2a": "http://localhost:48006/a2a",
    "mcp": "http://localhost:48006/mcp"
  },
  "models": ["claude-sonnet-4", "deepseek-v4-flash"],
  "tools": ["terminal", "write_file", "patch", "delegate_task"],
  "ttl": 60  # heartbeat every 60s
}
```

### 2. Capability Discovery

```bash
# "Find me all agents that can do code review"
hermes registry discover --capability code-review

# Output:
# engineer (online, claude-sonnet-4): code-review-response
# tester (online, deepseek-v4-flash): code-review, security-audit
# jiangzuojian (offline): code-review (last seen: 2h ago)

# "Find agents that speak A2A protocol"
hermes registry discover --protocol A2A --status online
```

### 3. Dynamic Team Composition

```bash
# Auto-assemble team for a task
hermes registry assemble-team \
  --task "Implement rate limiter with security review" \
  --required "code-implementation, code-review, security-audit"

# Output:
# Team assembled:
#   engineer (code-implementation) — online
#   tester (code-review + security-audit) — online
#   Coverage: 3/3 required, 2/2 agents
```

### 4. Talent Pool Management (吏部核心)

吏部 manages two tiers:

**Tier 1: Standing Department Agents** (15 profiles)
- Always registered, heartbeat-monitored
- Capability declarations in profile config

**Tier 2: External Talent Pool** (将作监-style specialists)
- On-demand registration
- Scored by: expertise domain, success rate, cost profile
- Gated hiring pipeline (from Nexus Hyper Agent Team pattern)

```bash
# Register external specialist
hermes registry talent add \
  --name "solidity-expert" \
  --capabilities "smart-contract, security-audit, formal-verification" \
  --score 4.7 \
  --cost 0.50  # $0.50 per task

# Query talent pool
hermes registry talent list --domain blockchain
```

### 5. Health Monitoring

```bash
# Check fleet health
hermes registry health

# Output:
# ✅ engineer: online (heartbeat: 3s ago, 99.7% uptime)
# ✅ planner: online (heartbeat: 12s ago, 98.1% uptime)
# ⚠️ jiangzuojian: offline (last seen: 2h 14m ago)
# ❌ budget: never registered
#
# Summary: 12/15 online, 1 degraded, 1 missing
```

## Quick Start

```bash
# Install agentregistry
npm install -g @agentregistry/cli

# Start registry server
arctl serve --port 48050

# Register agents
hermes registry register --profile engineer
hermes registry register --profile planner
hermes registry register --all  # register all 15 profiles

# Discover
hermes registry discover --capability code-implementation
```

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [agentregistry](https://github.com/agentregistry-dev/agentregistry) | 245 | - | Protocol-agnostic, MCP server, web UI |
| [mq9](https://github.com/robustmq/mq9) | 7 | - | Agent-native registry + persistent mailbox |
| [Starfire-AgentTeam](https://github.com/ZhanlinCui/Starfire-AgentTeam) | - | - | Org hierarchy, cross-framework support |

## Common Pitfalls

- **Registry as single point of failure**: If the registry goes down, agent discovery fails. Run with redundancy or fallback to static config.
- **Stale registrations**: Agents crash without de-registering. Set TTL + heartbeat to auto-expire stale entries.
- **Capability drift**: Agent capabilities change when models switch. Re-register on model change or config update.

---

## ✅ Verification Checklist (RUN AFTER REGISTRY SETUP)

- [ ] Are all 15 standing profiles registered with capabilities?
- [ ] Does discovery return correct results (`hermes registry discover --capability security-audit`)?
- [ ] Do heartbeats auto-expire stale registrations (kill an agent, wait 2×TTL)?
- [ ] Can I assemble a team for a multi-capability task?
- [ ] Is the talent pool gated (external specialists require scoring before registration)?

**If any box is unchecked, go back.**
