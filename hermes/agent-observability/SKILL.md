---
name: agent-observability
description: "Use when setting up or debugging AI agent observability — distributed tracing across multi-agent chains, span-level cost attribution, real-time monitoring dashboards, and anomaly detection for 工部 infrastructure. Based on Laminar (lmnr-ai/lmnr, 2.9K⭐, YC S24) and Opik (comet-ml/opik, 18.6K⭐) patterns. Do NOT use for single-agent LLM call logging (use provider-native logging) or for non-agent infrastructure monitoring (use infra-health-check)."
version: 1.0.0
author: Hermes Agent (based on lmnr-ai/lmnr + comet-ml/opik)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [gongbu, observability, tracing, monitoring, multi-agent, opentelemetry]
    related_skills: [infra-health-check, infra-monitoring, kanban-orchestrator]
---

# Agent Observability — 工部多 Agent 可观测性

> Based on Laminar (lmnr-ai/lmnr, Rust+TypeScript, 2.9K⭐) and Opik (comet-ml/opik, 18.6K⭐) patterns. Adapted for 三省六部 multi-agent architecture.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "The agent returned a correct answer, so the pipeline is fine" | Correct output ≠ healthy pipeline. Hidden failures: tool call loops, credential exhaustion, silent fallback to weaker models |
| "I'll just grep the logs if something breaks" | Multi-agent chains produce 1000+ log lines per run. Structured tracing with span hierarchy is the only scalable approach |
| "OpenTelemetry is overkill for a few agents" | 三省六部 has 15 profiles running parallel chains. Without distributed tracing, debugging a single fan-out failure takes 20+ minutes manually |
| "I'll add observability later when there's a problem" | By the time you notice a problem, the trace data needed to diagnose it is already lost. Instrument FIRST |

## When to Use

- Setting up tracing for 三省六部 multi-agent Kanban chains
- Debugging "which agent broke?" in a fan-out pipeline
- Tracking per-agent/per-task API costs across 15 profiles
- Detecting silent failures (protocol violations, iteration budget exhaustion)
- Building real-time dashboards for gateway health + task throughput

## Architecture

```
Agent A (planner) ──span──→ Agent B (engineer) ──span──→ Agent C (auditor)
      │                         │                         │
      └─────── OpenTelemetry Collector ───────────────────┘
                         │
                   Laminar / Opik
                   (trace store + dashboard)
```

## Core Capabilities

### 1. Distributed Tracing

Each agent in a Kanban chain emits spans. Parent spans link to child spans via trace context propagation.

```bash
# Instrument a Kanban worker (one-line)
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
hermes -p engineer kanban run t_xxx  # spans auto-attached
```

### 2. Span-Level Cost Attribution

Every LLM call span carries:
- `hermes.profile` — which agent
- `hermes.task_id` — which Kanban card
- `hermes.model` — which model
- `hermes.tokens` — input/output tokens
- `hermes.cost_usd` — calculated cost

```bash
# Query: "Which task cost the most today?"
hermes observability query --metric cost --group-by task_id --window 24h
```

### 3. Anomaly Detection

Define signals in natural language. Laminar evaluates them on every trace:

```yaml
signals:
  - name: "iteration_budget_exhausted"
    description: "Agent ran out of tool-calling budget before completing"
    severity: high
  - name: "protocol_violation"
    description: "Worker exited without calling kanban_complete"
    severity: critical
  - name: "rate_limit_hit"
    description: "Provider returned 429 on any call in the chain"
    severity: medium
```

### 4. Real-Time Dashboard

```
┌─────────────────────────────────────────────┐
│  📊 三省六部 Health Dashboard                 │
│─────────────────────────────────────────────│
│  Active chains: 3                            │
│  Tasks/hour: 12  │  Avg latency: 4.2s        │
│  Cost today: $2.47  │  Cost this week: $18.30 │
│─────────────────────────────────────────────│
│  ⚠️ t_abc123: engineer → rate_limit (429)    │
│  ⚠️ t_def456: planner → budget exhausted      │
│  ✅ t_ghi789: auditor → done (3.2s)           │
└─────────────────────────────────────────────┘
```

## Quick Start

### Install Laminar (self-hosted, Rust binary)

```bash
# One-command deployment (Docker)
docker run -p 3870:3870 -p 4317:4317 \
  ghcr.io/lmnr-ai/lmnr:latest

# Or build from source
git clone https://github.com/lmnr-ai/lmnr
cd lmnr && cargo build --release
```

### Wire into Hermes

```bash
# Set OTel endpoint in regent config
hermes config set observability.otlp_endpoint "http://localhost:4317"
hermes config set observability.enabled true

# Verify
hermes observability status
```

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [Laminar](https://github.com/lmnr-ai/lmnr) | 2.9K | Apache 2.0 | Rust+OTel native, signals in NL, self-hosted |
| [Opik](https://github.com/comet-ml/opik) | 18.6K | Apache 2.0 | Full lifecycle: eval+test+monitor+optimize |
| [AgentWeave](https://github.com/arniesaha/agentweave) | - | MIT | Cross-agent delegation traces, PROV-O provenance |

## Common Pitfalls

- **OTel collector not running**: Spans are dropped silently. Always `hermes observability status` after setup.
- **Too many spans**: Each tool call = 1 span. High-frequency crons (1m/5m watchdog) can flood the collector. Set sampling rate for cron profiles.
- **Cost attribution drift**: When agents switch models mid-chain (fallback), cost calculation must use the ACTUAL model used, not the configured one.

---

## ✅ Verification Checklist (RUN AFTER SETUP)

- [ ] Is the OTel collector running and reachable (`nc -vz localhost 4317`)?
- [ ] Did I run `hermes observability status` to confirm spans are flowing?
- [ ] Did I define ≥3 signals for critical failure modes (budget exhaust, protocol violation, rate limit)?
- [ ] Did I set sampling rate for high-frequency cron profiles?
- [ ] Does the dashboard show traces from ≥2 different profiles?

**If any box is unchecked, go back.**
