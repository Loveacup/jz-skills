---
name: supermemory-hermes
description: "Set up, configure, and manage Supermemory as Hermes Agent's external memory provider. Covers SDK setup, API key config, provider switching, container_tag isolation for multi-profile deployments, metadata taxonomy, cross-pool wrapper usage, LRU cache layer, and the 三省六部 cabinet memory sharing model. Load when the user mentions Supermemory, memory setup, provider switching, cross-pool queries, or multi-profile memory architecture. Do NOT load for local `memory` tool operations (those are L1, independent of Supermemory)."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [supermemory, memory, migration, multi-profile, cabinet, 三省六部, governance]
    related_skills: [cross-profile-api-bridge, hermes-agent]
---

# Supermemory for Hermes — Cabinet Memory Manual

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I know the SDK, I don't need this" | Hermes-specific wrapper (cross-pool, cache, metadata enforcement) is NOT in the SDK docs |
| "Just do a web search for Supermemory API" | Web results show generic SDK usage — NOT Hermes plugin internals, container_tag isolation, or cross-pool policy |
| "The user asked about memory, not Supermemory" | In this Hermes deployment, all L2 memory IS Supermemory. Hindsight is retired. |
| "300 lines? Skip the references section" | The four new features (onboarding, wrapper, cache, changelog) are documented here, not in the v2.0 design doc |

## 🔀 Decision Tree

```
User mentions Supermemory/memory/cabinet/cross-pool?
├── Setting up NEW profile with Supermemory?
│   └── → §New Profile Onboarding (30-min checklist)
├── Querying across pools (小黄 → cabinet)?
│   └── → §Cross-Pool Wrapper + §Cross-Pool Channels
├── Cache behavior / offline fallback questions?
│   └── → §Cache Layer
├── What changed in Phase 2/3?
│   └── → `references/phase-2-3-changelog.md`
├── Need SDK API reference?
│   └── → §Key SDK Methods
├── Hitting errors?
│   └── → §Common Pitfalls (top 5) then `references/common-pitfalls.md`
└── Full architecture design?
    └── → Obsidian: `20-Areas/10_AI实践/三省六部_Hermes/10_制度/Supermemory三省六部记忆架构设计_v2.0.md`
```

---

## Architecture

| Layer | What | Scope | Provider |
|-------|------|-------|----------|
| L1 | Local `memory` tool | Single session/profile | Built-in (always on) |
| L2 | Semantic long-term memory | Cross-session/profile | **Supermemory** (Hindsight retired) |

Two `container_tag` pools with physical isolation:

```
hermes            → default (小黄) — private
hermes-cabinet    → regent + 14 三省六部 — shared institutional
```

---

## Quick Setup

```bash
# 1. Install SDK
~/.hermes/hermes-agent/venv/bin/python3 -m pip install supermemory

# 2. Add API key
echo "SUPERMEMORY_API_KEY=sm_..." >> ~/.hermes/.env

# 3. Create config (~/.hermes/supermemory.json)
echo '{"container_tag":"hermes","auto_recall":true,"search_mode":"hybrid"}' > ~/.hermes/supermemory.json

# 4. Switch provider + restart
hermes config set memory.provider supermemory
hermes gateway restart
```

---

## New Profile Onboarding (30-Minute Checklist)

For adding a new profile to the `hermes-cabinet` pool:

- [ ] **1. Add API key**: `echo "SUPERMEMORY_API_KEY=sm_..." >> ~/.hermes/profiles/<name>/.env`
- [ ] **2. Create pool config**: Write `~/.hermes/profiles/<name>/supermemory.json` with `"container_tag": "hermes-cabinet"`
- [ ] **3. Switch provider**: `hermes --profile <name> config set memory.provider supermemory`
- [ ] **4. Set metadata defaults**: Ensure agent SOUL.md includes `department: <name>` for auto-tagging
- [ ] **5. Verify**: Call `hermes --profile <name> chat -q "test memory"` and check `supermemory_search` tool available

**PITFALL**: If profile has no gateway, verification is via API Server (`POST /v1/chat/completions`), not A2A. A2A subprocess mode doesn't load MemoryProvider tools (pitfall #10 in full list).

---

## Cross-Pool Wrapper

Standalone script at `~/.hermes/scripts/supermemory_crosspool.py`. Three channels configured:

| Channel | Path | Permissions | Default |
|---------|------|-------------|---------|
| X1 | default → cabinet | read-only, cabinet-shared, intent-gated, 6/min | ON |
| X3 | archivist → hermes | read-only, no filter, 30/min | ON |
| X4 | dispatcher → hermes | read-only, task_summary only, 4/min | ON |

```bash
# Query with cross-pool
~/.hermes/hermes-agent/venv/bin/python3 \
  ~/.hermes/scripts/supermemory_crosspool.py default "三省六部 ADR 决策"

# Check channel stats
~/.hermes/hermes-agent/venv/bin/python3 \
  ~/.hermes/scripts/supermemory_crosspool.py archivist --stats
```

Audit log: `~/.hermes/logs/crosspool_audit.log`

---

## Cache Layer

LRU cache in `plugins/memory/supermemory/__init__.py` (`_SearchCache` class):

| Parameter | Value |
|-----------|-------|
| Max entries | 200 |
| TTL | 1 hour |
| Eviction | LRU |
| Wrapped methods | `search_memories()`, `get_profile()` |
| Invalidation | Full flush on `add_memory()` or `forget_memory()` |
| Offline fallback | Serves stale cache + logs WARNING |

Target: hit rate ≥ 60%. Hit rate available via `~/.hermes/logs/errors.log` grep for "cache hit" patterns (future: metrics endpoint).

---

## Metadata Taxonomy

When writing cabinet memories:

| Field | Required | Values |
|-------|----------|--------|
| `department` | Yes | regent, shangshu, gongbu, engineer, planner, tester, reviewer, auditor, archivist, dispatcher, protocol, budget, registry, hanlinyuan, jiangzuojian |
| `type` | Yes | decision, troubleshoot, architecture, research, config, protocol_spec, postmortem, pattern, runbook, policy, budget_record, task_summary |
| `ttl` | Yes | permanent, long-term, short-term, ephemeral |
| `visibility` | Yes | department-only, cabinet-shared, regent-only, cross-department |

Enforcement is **client-side (wrapper)** — SDK does NOT enforce. Write without metadata → role confusion.

---

## Role Confusion Prevention

Five-layer defense: (1) Write constraint — wrapper auto-fills `department`, (2) Recall filtering — `search_policy`, (3) Prompt labeling — `[来源: gongbu]` headers, (4) Behavior — SOUL.md reference rules, (5) Post-audit — auditor sampling (deferred).

---

## Key SDK Methods

```python
from supermemory import Supermemory
client = Supermemory(api_key=key)

# Write
client.add(content="...", container_tag="hermes", metadata={...})

# Read
client.search.memories(q="query", container_tag="tag", limit=5)

# Delete
client.memories.forget(id="mem_xxx", container_tag="hermes")
```

**PITFALL**: `add()` and `search.memories()` take keyword-only args after positional. Always use named parameters.

---

## Common Pitfalls (Top 5)

1. **SDK not installed** → `python3 -m pip install supermemory` in venv
2. **Provider switch needs restart** → `hermes gateway restart`
3. **Cross-pool OR queries don't exist** → make two calls + merge
4. **API key has no pool permissions** → access control in wrapper, not key
5. **A2A mode doesn't load MemoryProvider** → use API Server for memory ops

Full list: `references/common-pitfalls.md`

---

## References

| File | When to read |
|------|-------------|
| `references/supermemory-cabinet-design-v1.1.md` | Full architecture design document |
| `references/hindsight-migration-guide.md` | Historical: Hindsight → Supermemory migration procedure |
| `references/common-pitfalls.md` | Complete pitfalls list (16 items) |
| `references/phase-2-3-changelog.md` | What changed in Phase 2/3 implementation |

Obsidian vault: `20-Areas/10_AI实践/三省六部_Hermes/10_制度/Supermemory三省六部记忆架构设计_v2.0.md`

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I check whether this is a SETUP task (needs onboarding checklist §) or a USAGE task (needs SDK/cross-pool §)?
- [ ] If cross-pool: did I use `supermemory_crosspool.py`, not raw SDK with AND-semantics `containerTags`?
- [ ] If onboarding a new profile: did I follow all 5 steps in the 30-minute checklist?
- [ ] If cache question: did I mention TTL (1h), invalidation (write-through), and offline fallback?
- [ ] Did I point to `references/` for deep dives (migration guide, full pitfalls, changelog) instead of bloating the response?

**If any box is unchecked, go back.**
