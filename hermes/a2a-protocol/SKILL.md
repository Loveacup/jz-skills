---
name: a2a-protocol
description: "Use when designing or implementing agent-to-agent communication in the 三省六部 system — A2A Protocol (Google→Linux Foundation, 23.4K⭐) integration for inter-agent task delegation, capability discovery, streaming artifacts, and cross-profile handoff. Based on a2aproject/A2A specification v1.0 and Python/JS SDKs. Do NOT use for intra-agent tool calling (use MCP) or for human-agent communication (use Telegram/gateway)."
version: 1.0.0
author: Hermes Agent (based on a2aproject/A2A + google-a2a/a2a-python)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [shangshu, a2a, protocol, inter-agent, delegation, discovery]
    related_skills: [kanban-orchestrator, kanban-worker, three-provinces-constitution]
---

# A2A Protocol — 尚书省 Agent 互通协议

> Based on A2A Protocol (a2aproject/A2A, 23.4K⭐, Google→Linux Foundation, Apache 2.0). Adapted for 三省六部 inter-agent communication.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "Kanban already handles inter-agent communication" | Kanban is task QUEUING — fire-and-forget card creation. A2A adds real-time capability discovery, streaming results, and structured handoffs that Kanban doesn't support |
| "A2A is for external agents, not our internal 三省六部 profiles" | A2A is equally valuable internally: planner discovers engineer's capabilities → delegates sub-task → streams progress back → receives structured artifact. Without A2A, this requires manual chain construction |
| "We don't need capability discovery — we know all 15 profiles" | Capability discovery means agents can adapt when profiles change models, add tools, or go offline. Hardcoded assumptions break silently |
| "The protocol is too complex for our use case" | A2A v1.0 core is simple: Agent Card (capability manifest) + Task (unit of work) + Message (communication). The advanced features (streaming, push notifications) are optional |

## When to Use

- Designing new inter-agent communication patterns beyond Kanban cards
- Implementing dynamic capability discovery: "which agent can handle JSON schema validation?"
- Streaming long-running task progress from one agent to another
- Building formal handoff protocols between profiles (planner→engineer artifact delivery)
- Integrating external AI agents into the 三省六部 system

## A2A Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    A2A Protocol                          │
│                                                         │
│  Agent Card          Task              Message          │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐      │
│  │ name     │    │ id       │    │ role         │      │
│  │ skills   │    │ status   │    │ parts[]      │      │
│  │ tools    │    │ artifact │    │ task_id      │      │
│  │ endpoint │    │ history  │    │ context_id   │      │
│  └──────────┘    └──────────┘    └──────────────┘      │
│                                                         │
│  Transport: JSON-RPC | HTTP+JSON/REST | gRPC            │
└─────────────────────────────────────────────────────────┘
```

## A2A in 三省六部 Context

### Current State (Kanban-only)

```
planner ──kanban_create──→ engineer (fire-and-forget)
planner ←──kanban poll─── engineer (polling, 60s delay)
```

### With A2A (real-time)

```
planner ──A2A discover──→ engineer (capability check)
planner ──A2A task.send──→ engineer (delegation)
planner ←──A2A stream──── engineer (real-time progress)
planner ←──A2A artifact── engineer (structured result)
```

## Core Concepts

### 1. Agent Card — Capability Manifest

Each 三省六部 profile exposes an A2A Agent Card:

```yaml
# ~/.hermes/profiles/engineer/a2a-card.yaml
name: "兵部 Engineer"
description: "Code implementation, architecture, refactoring"
url: "http://localhost:48006/a2a"
capabilities:
  streaming: true
  pushNotifications: false
skills:
  - id: "code-implementation"
    description: "Implement features from plan specifications"
  - id: "code-review-response"
    description: "Respond to code review findings"
defaultInputModes: ["text", "file"]
defaultOutputModes: ["text", "file"]
```

### 2. Task — Unit of Work

```python
# planner delegates to engineer via A2A
task = a2a_client.tasks.send(
    message={
        "role": "user",
        "parts": [{
            "type": "text",
            "text": "Implement rate limiter per plan-v3.md §3.2"
        }, {
            "type": "file",
            "file": {"uri": "file:///workspaces/plan-v3.md"}
        }]
    },
    context_id="kanban-t_abc123"  # links A2A task to Kanban card
)
```

### 3. Streaming Progress

```python
# engineer streams progress back to planner
for event in a2a_client.tasks.send_streaming(message):
    if event.kind == "status-update":
        print(f"Progress: {event.metadata['progress']}%")
    elif event.kind == "artifact-update":
        print(f"Artifact: {event.artifact.name}")
```

## Quick Start

### Install A2A Python SDK

```bash
pip install a2a-sdk
```

### Expose an Agent Card

```bash
# Generate capability manifest for a profile
hermes a2a generate-card --profile engineer --output ~/.hermes/profiles/engineer/a2a-card.yaml

# Serve as A2A endpoint
hermes a2a serve --profile engineer --port 48006
```

### Discover and Delegate

```python
from a2a.client import A2AClient

# Discover available agents
client = A2AClient()
agents = client.discover("http://localhost:48006")

# Delegate a task
task = client.send_task(
    agent_url=agents["engineer"]["url"],
    message="Implement rate limiter per specification",
    context_id="kanban-t_abc123"
)

# Stream results
for update in client.stream_task(task.id):
    print(update)
```

## Integration with 三省六部

### Phase 1: Capability Discovery (low risk)

All profiles publish Agent Cards. 尚书 uses them to validate assignments before creating Kanban cards.

```bash
# Before creating Kanban card, check engineer can handle the task
hermes a2a discover engineer | grep "code-implementation" && \
  hermes kanban create "Implement X" --assignee engineer
```

### Phase 2: Task Delegation (medium risk)

For simple tasks, replace kanban_create with A2A direct delegation. Kanban remains for complex multi-step chains.

### Phase 3: Full A2A-MCP Stack (future)

```
A2A: agent ↔ agent communication
MCP: agent ↔ tool communication
Kanban: task lifecycle + audit trail
```

## Reference: Upstream

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [A2A Protocol](https://github.com/a2aproject/A2A) | 23.4K | Apache 2.0 | Open standard, spec v1.0 |
| [a2a-python](https://github.com/google-a2a/a2a-python) | 1.8K | Apache 2.0 | Official Python SDK |
| [a2a-samples](https://github.com/a2aproject/a2a-samples) | 1.5K | Apache 2.0 | Examples: LangGraph, CrewAI, ADK |

## Common Pitfalls

- **Confusing A2A with MCP**: A2A = agent-to-agent, MCP = agent-to-tool. Don't use A2A for tool calling or MCP for agent delegation.
- **A2A vs Kanban overlap**: A2A tasks are ephemeral (in-memory). Kanban cards are durable (SQLite). Use A2A for real-time delegation within a session; use Kanban for cross-session durability.
- **Agent Card staleness**: Profiles change capabilities over time. Regenerate Agent Cards on config change or profile restart.

---

## ✅ Verification Checklist (RUN AFTER A2A SETUP)

- [ ] Did I generate Agent Cards for all profiles that participate in A2A?
- [ ] Can agents discover each other (`hermes a2a discover <profile>`)?
- [ ] Did I test a simple task delegation (planner→engineer, round-trip)?
- [ ] Did I verify streaming works for tasks >30 seconds?
- [ ] Did I document which communication patterns use A2A vs Kanban vs MCP?

**If any box is unchecked, go back.**
