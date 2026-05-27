---
name: agent-cost-manager
description: "Use when tracking or controlling AI agent API spending — hard budget enforcement with circuit breaking, per-agent/per-task cost attribution, multi-model pricing (2,600+ models), cost optimization recommendations, and spending forecasts for 户部 budget management. Based on AgentBudget (sahiljagtap08/agentbudget, 101⭐, Apache 2.0, 'ulimit for AI agents') and AgentCost (agentcostin/agentcost, 6⭐, 2,610+ models). Do NOT use for general infrastructure cost tracking (use costly-oss) or for provider-native usage dashboards."
version: 1.0.0
author: Hermes Agent (based on sahiljagtap08/agentbudget + agentcostin/agentcost)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hubu, budget, cost, finance, api-spending, optimization]
    related_skills: [infra-monitoring, agent-observability, three-provinces-constitution]
---

# Agent Cost Manager — 户部 API 成本管控

> Based on AgentBudget (101⭐, Apache 2.0, "ulimit for AI agents") and AgentCost (2,610+ models pricing). Adapted for 三省六部 multi-agent cost management with hard budget enforcement.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll check costs at the end of the month" | Multi-agent chains can burn $50+ in a single runaway session. AgentBudget's circuit breaker stops this in real-time, not post-mortem |
| "The provider dashboard shows costs, that's enough" | Provider dashboards don't show per-agent, per-task, per-Kanban-card attribution. You need to know WHICH agent burned the budget |
| "Budget limits stifle agent creativity" | Without hard limits, a single recursive agent loop (planner→reviewer→planner→reviewer...) can silently consume $200+ before anyone notices the idle loop |
| "I can estimate costs from token counts" | Prompt caching, reasoning tokens, and tool call overhead make token-based estimates inaccurate. Real-time pricing tables with cache-tier awareness are essential |

## When to Use

- Setting per-agent budget limits for 15 三省六部 profiles
- Tracking cost per Kanban task chain (planner→engineer→auditor = ?)
- Detecting cost anomalies: "why did yesterday's spend spike 3x?"
- Optimizing model selection: "would switching engineer from claude-opus to haiku save 40% with acceptable quality?"
- Forecasting monthly spend based on task volume trends

## Architecture

```
Agent SDK calls ──→ AgentBudget wrapper ──→ Provider API
                         │
                    Real-time cost calc
                    (pricing table: 2,600+ models)
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         Track cost  Check budget  Circuit break
         per task    remaining     (stop if over)
              │          │          │
              └──────────┼──────────┘
                         ▼
                 户部 Dashboard
                 (per-agent, per-task, per-model)
```

## Core Capabilities

### 1. Hard Budget Enforcement

```python
from agentbudget import AgentBudget

# Initialize with per-session budget
session = AgentBudget.init(budget=5.00)  # $5 hard limit

# Wrap any LLM client
client = AgentBudget.wrap_client(openai_client, session)

# After $5 is spent, ALL calls raise BudgetExceededError
response = client.chat.completions.create(...)  # auto-tracked
```

### 2. Per-Agent Cost Attribution

```bash
# Tag costs by agent profile and Kanban task
hermes budget track \
  --profile engineer \
  --task t_abc123 \
  --model claude-sonnet-4 \
  --tokens-in 1200 --tokens-out 800

# Query: "Which agent cost the most this week?"
hermes budget query --group-by profile --window 7d
```

### 3. Multi-Model Pricing

AgentCost maintains a vendored database of 2,610+ models across 40+ providers:

| Provider | Models | Pricing Tiers |
|----------|--------|---------------|
| OpenAI | 45+ | GPT-4o, o3, o4-mini, reasoning tiers |
| Anthropic | 12+ | Opus, Sonnet, Haiku, prompt caching |
| Google | 30+ | Gemini, Vertex AI tiers |
| DeepSeek | 8+ | V3, R1, caching tiers |
| OpenRouter | 200+ | Aggregated pricing |

### 4. Cost Optimization

```bash
# Analyze: can we save by switching models?
hermes budget optimize --profile engineer --window 30d

# Output:
# Current: claude-opus-4 @ $15/M input → $120/month
# Recommendation: claude-sonnet-4 @ $3/M input → $24/month (80% savings)
# Quality impact: estimated ∆ ≤ 5% on code generation tasks
```

### 5. Anomaly Detection

```bash
# Detect cost spikes
hermes budget anomaly-detect --window 24h --threshold 3x

# Example alert:
# ⚠️ ANOMALY: engineer cost $18.47 in last hour
#    Baseline median: $2.10/hour (7d avg)
#    Spike factor: 8.8x
#    Top task: t_def456 (12,000 tokens, model: claude-opus-4)
```

## Quick Start

```bash
pip install agentbudget
```

```python
# Add to regent config
hermes config set budget.enabled true
hermes config set budget.default_limit 10.00  # $10 per session
hermes config set budget.per_profile.engineer 3.00  # engineer max $3/session
hermes config set budget.alert_threshold 0.80  # alert at 80% of budget
```

## Budget Allocation Template (三省六部)

| Profile | Daily Budget | Rationale |
|---------|-------------|-----------|
| regent | $5.00 | Orchestration + oversight |
| planner | $2.00 | Plan generation, kimi-k2.6 |
| reviewer | $1.00 | Gate review, deepseek-v4-flash |
| engineer | $3.00 | Code implementation, claude-sonnet-4 |
| gongbu | $1.00 | Infrastructure checks |
| budget | $0.50 | Cost queries (this agent!) |
| protocol | $1.00 | Document rendering |
| tester | $1.50 | Security scanning + audit |
| **Total/day** | **$15.00** | ~$450/month |

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [AgentBudget](https://github.com/sahiljagtap08/agentbudget) | 101 | Apache 2.0 | Hard circuit breaker, Python/Go/TS |
| [AgentCost](https://github.com/agentcostin/agentcost) | 6 | - | 2,610+ models, optimization recs |
| [NullSpend](https://github.com/NullSpend/nullspend) | 3 | Apache 2.0 | FinOps + Stripe margin tracking |

## Common Pitfalls

- **Budget too tight**: Agents blocked mid-task leave partial state. Set budget at 120% of estimated cost to allow retries.
- **Cache-tier unawareness**: Prompt caching can reduce costs 10x. Models with caching enabled should have lower effective rates.
- **Tool call costs untracked**: web_search, browser, and delegate_task also consume tokens. Track ALL API calls, not just LLM completions.

---

## ✅ Verification Checklist (RUN AFTER BUDGET SETUP)

- [ ] Did I set per-profile budget limits (not just a global limit)?
- [ ] Did I verify the circuit breaker works (intentionally exceed a small budget)?
- [ ] Can I query cost by agent profile AND by Kanban task ID?
- [ ] Did I set alert thresholds (80% warning, 95% critical)?
- [ ] Did I review the optimization recommendations for model switching?

**If any box is unchecked, go back.**
