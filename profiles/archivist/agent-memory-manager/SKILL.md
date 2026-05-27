---
name: agent-memory-manager
description: "Use when managing cross-session AI agent memory — persistent fact storage with temporal decay, knowledge graph consolidation, deduplication, and multi-agent recall for 史馆 archiving. Based on ICM (rtk-ai/icm, 221⭐, Rust binary, MCP native) and mnem (Uranid/mnem, 119⭐, Git-versioned) patterns. Do NOT use for session-scoped working memory (use default Hermes memory) or for real-time conversation context (use session_search)."
version: 1.0.0
author: Hermes Agent (based on rtk-ai/icm + Uranid/mnem)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [shiguan, memory, archivist, knowledge-graph, long-term, mcp]
    related_skills: [obsidian, qmd, three-provinces-constitution]
---

# Agent Memory Manager — 史馆长期记忆管理

> Based on ICM (rtk-ai/icm, Rust, 221⭐) and mnem (Uranid/mnem, Rust, 119⭐). Adapted for 三省六部 multi-agent archiving with temporal decay and knowledge graph consolidation.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "Memory is already handled by Hermes built-in memory" | Built-in MEMORY is for boot-critical facts (<2KB). Cross-session knowledge, decisions, and reasoning chains need a dedicated memory layer |
| "I'll just write important facts to Obsidian" | Obsidian is static documentation. Agent memory needs retrieval (FTS5+vector), temporal decay (forgetting unimportant things), and knowledge graph traversal |
| "The agent remembers enough from the current conversation" | Long-running 三省六部 chains span 10+ sessions. Without persistent memory, each session starts cold — wasting turns on re-discovery |
| "Vector search alone is fine for retrieval" | Pure vector search misses structural relationships (entity→decision→outcome chains). Hybrid FTS5+vector+graph achieves 98% multi-agent recall (ICM benchmark) |

## When to Use

- Archiving Kanban task decisions and reasoning chains across sessions
- Consolidating facts extracted from multi-agent conversations
- Detecting and resolving conflicting facts (Conflict Resolution per MemoryAgentBench ICLR'26)
- Building a knowledge graph of entities, decisions, and their relationships
- Implementing temporal decay: critical memories persist, low-importance ones fade

## Architecture

```
Agent Sessions ──→ Fact Extraction ──→ Dedup ──→ Storage
                       │                  │          │
                   LLM-based          Vector+FTS5   SQLite
                   or pattern-based   similarity    (local)
                       │                  │          │
                       └──── Knowledge Graph ───────┘
                                  │
                          Temporal Decay
                          (Ebbinghaus curve)
                                  │
                          Multi-Agent Recall
                          (98% accuracy)
```

## Core Capabilities

### 1. Fact Extraction & Storage

```bash
# Store a decision from a Kanban task
hermes memory store \
  --fact "尚书省 must be inserted after 门下封驳 in all multi-step chains" \
  --source "three-provinces-constitution v3.0" \
  --importance critical

# Query across all agent memories
hermes memory recall "尚书省 insertion rule"
```

### 2. Temporal Decay (ICM Pattern)

Facts decay by importance. Critical facts never fade; low-importance facts decay over time if not accessed.

| Importance | Half-life | Retention at 30d |
|-----------|-----------|-------------------|
| critical | ∞ | 100% |
| high | 90 days | 79% |
| medium | 30 days | 50% |
| low | 7 days | 5% |

### 3. Knowledge Graph Consolidation

```bash
# Auto-consolidate related facts
hermes memory consolidate --window 7d

# Example consolidation:
# Before: 3 separate facts about "kanban-gate plugin import fix"
# After:  1 consolidated knowledge node with 3 source references
```

### 4. Conflict Resolution (MemoryAgentBench CR)

When two agents produce conflicting facts:

```bash
hermes memory resolve \
  --fact-a "planner memory limit is 90 iterations" \
  --fact-b "planner memory limit is 120 iterations" \
  --strategy latest-authoritative

# Resolution strategies:
# - latest-authoritative: newest fact from authoritative source wins
# - majority-vote: fact with most confirmations wins
# - human-escalate: flag for regent review
```

### 5. Multi-Agent Recall

Agents query the shared memory with their profile context. Results are scoped to what that agent is authorized to see.

```bash
# engineer queries: gets implementation facts
hermes -p engineer memory recall "kanban_gate.py import fix"

# auditor queries: gets audit trail facts
hermes -p auditor memory recall "kanban_gate.py import fix"
```

## Quick Start

### Option A: ICM (Rust binary, MCP native, recommended)

```bash
# Install (single binary, zero dependencies)
curl -L https://github.com/rtk-ai/icm/releases/latest/download/icm-macos-arm64 -o /usr/local/bin/icm
chmod +x /usr/local/bin/icm

# Initialize
icm init --path ~/.hermes/memory/icm.db

# Register as MCP server
hermes mcp add icm --command icm --args "serve"
```

### Option B: mnem (Git-versioned, offline)

```bash
cargo install mnem
mnem init --path ~/.hermes/memory/mnem.db
```

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [ICM](https://github.com/rtk-ai/icm) | 221 | Apache 2.0 | Rust binary, MCP native, temporal decay, 17 tools |
| [mnem](https://github.com/Uranid/mnem) | 119 | Apache 2.0 | Git-versioned knowledge, BLAKE3 integrity, 6 benchmarks |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) | 302 | - | ICLR'26: AR/TTL/LRU/CR evaluation framework |

## Common Pitfalls

- **Memory pollution**: Low-quality facts from failed agent runs contaminate the knowledge base. Always verify extraction quality before storage.
- **Over-consolidation**: Consolidating too aggressively loses nuance. Set minimum fact count (≥3) before consolidation trigger.
- **Temporal decay misses**: Critical facts tagged as "high" instead of "critical" decay unintentionally. Audit importance tags monthly.

---

## ✅ Verification Checklist (RUN AFTER MEMORY SETUP)

- [ ] Is the memory backend running (`icm status` or `mnem status`)?
- [ ] Did I register the MCP server (`hermes mcp list` shows icm/mnem)?
- [ ] Did I define importance levels for stored facts (not all "medium")?
- [ ] Did I test cross-profile recall (query from ≥2 different agent profiles)?
- [ ] Did I set up a monthly consolidation + importance audit cron?

**If any box is unchecked, go back.**
