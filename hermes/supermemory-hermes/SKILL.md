---
name: supermemory-hermes
description: "Set up, configure, and manage Supermemory as Hermes Agent's external memory provider. Covers SDK setup, API key config, provider switching, container_tag isolation for multi-profile deployments, metadata taxonomy, cross-pool wrapper usage, LRU cache layer, and the multi-profile cabinet memory sharing model. Load when the user mentions Supermemory, memory setup, provider switching, cross-pool queries, or multi-profile memory architecture. Do NOT load for local `memory` tool operations (those are L1, independent of Supermemory)."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [supermemory, memory, migration, multi-profile, cabinet, governance]
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
├── Hitting errors or need daily ops guide?
│   └── → §Common Pitfalls (top 5) then `references/supermemory-six-rules.md`（2026-05-29 太子实测六条）
├── Dashboard shows documents but no memories/connections?
│   └── → §Knowledge Graph Disconnect (verify with SDK first!)
├── Dashboard shows a second pool / suspected cross-profile contamination?
│   └── → §Dual-Pool Recurrence Triage + `references/dual-pool-recurrence-runbook.md`
└── Full architecture design?
    └── → Obsidian: `20-Areas/10_AI实践/Hermes/10_制度/Supermemory多profile记忆架构设计_v2.0.md`
```

---

## Architecture

| Layer | What | Scope | Provider |
|-------|------|-------|----------|
| L1 | Local `memory` tool | Single session/profile | Built-in (always on) |
| L2 | Semantic long-term memory | Cross-session/profile | **Supermemory** (Hindsight retired) |

Three+ `container_tag` pools with physical isolation. The known pools:

```
hermes            → default (小黄) — private
hermes-cabinet    → regent + 14 multi-agent — shared institutional
sm_project_cli    → pi (Windows 7800x3d) — jz-skills project config
```

Additional pools may exist. Check `container_tag` in `supermemory.json`, search Supermemory for unknown tags, or ask the user for the full pool inventory. Do NOT assert "only two pools" — this was wrong in v1.0.

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

> ⚠️ **ACTIVATION GATE**: All channels are subject to `cross_pool_read` in `supermemory.json`. When set to `false` (current default), cross-pool queries are blocked regardless of channel config. The "ON" status above means channel is *configured*, not necessarily *active*. Check `supermemory.json → search_policy → cross_pool_read` to confirm.

```bash
# Query with cross-pool
~/.hermes/hermes-agent/venv/bin/python3 \
  ~/.hermes/scripts/supermemory_crosspool.py default "ADR 决策"

# Check channel stats
~/.hermes/hermes-agent/venv/bin/python3 \
  ~/.hermes/scripts/supermemory_crosspool.py archivist --stats
```

Audit log: `~/.hermes/logs/crosspool_audit.log`

### 🔑 Cross-Pool Config Format (supermemory.json)

The wrapper reads `search_policy` as a **dict** with `cross_pool_read` as an **array of channel objects**. Getting this wrong is the #1 cause of cross-pool failures.

**Correct format:**

```json
{
    "profiles": {
        "default": {
            "container_tag": "hermes",
            "search_policy": {
                "mode": "department",
                "default_top_k": 8,
                "cross_pool_read": [
                    {
                        "container_tag": "hermes-cabinet",
                        "mode": "readonly",
                        "max_top_k": 5,
                        "filter": {"visibility": "cabinet-shared"},
                        "rate_limit": {"per_minute": 6, "per_day": 500},
                        "require_explicit_intent": true
                    },
                    {
                        "container_tag": "sm_project_cli",
                        "mode": "readonly",
                        "max_top_k": 5,
                        "filter": {},
                        "rate_limit": {"per_minute": 10, "per_day": 500},
                        "require_explicit_intent": false
                    }
                ]
            }
        }
    }
}
```

**🚨 FORMAT TRAPS:**
- `search_policy` MUST be a dict — if it's a string (`"department"`), the script crashes with `AttributeError: 'str' object has no attribute 'get'`
- `cross_pool_read` MUST be an array — not `true`/`false` boolean. Boolean values are silently treated as empty list (no channels).
- `rate_limit` is a nested object with `per_minute` and `per_day` keys, not flat fields.
- Each channel entry REQUIRES `container_tag` (string). All other fields have defaults.
- `filter` restricts to specific metadata values (e.g. `{"visibility": "cabinet-shared"}`). Empty `{}` = no filter.
- `require_explicit_intent: true` gates the channel on `CROSS_POOL_INTENT_KEYWORDS` (see script source). Set `false` for project-config pools that should always be searched.

**Verification after config change:**
```bash
~/.hermes/hermes-agent/venv/bin/python3 \
  ~/.hermes/scripts/supermemory_crosspool.py default --stats
```
Should show `cross_pool_channels: N` (not 0) and list target containers.

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

## Knowledge Graph Disconnect (Dashboard ≠ SDK)

**Symptom**: Dashboard shows X documents but 0 memories and 0 connections, yet `supermemory_search` via SDK returns valid results with populated `memory` fields.

**Root cause**: Supermemory has two data planes:
- **Search index** — populated during document processing (embedding → indexing). What SDK `search.memories()` queries.
- **Knowledge Graph** — built as a separate step after indexing. What Dashboard's graph view displays. Nodes = memories, edges = connections.

A container can have a working search index but a broken/unbuilt knowledge graph. This is a **Supermemory backend issue** — not a Hermes config problem.

**Diagnosis workflow**:
1. Verify with SDK first: `client.search.memories(q="test", container_tag="<tag>", search_mode="hybrid")`
2. Check profile: `client.profile(container_tag="<tag>")` → static + dynamic counts
3. If SDK works but Dashboard shows 0 memories: **backend graph processing failure**
4. Contact <email redacted> with: affected container_tag, SDK search proof (works), Dashboard screenshot (broken)
5. Do NOT re-create the container or change Hermes config — the data is there, just not graph-linked

**Verified 2026-06-03**: hermes pool has functioning search (5 results, static=8, dynamic=50) but Dashboard graph shows only documents. hermes-cabinet pool is fully healthy in both planes.

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

## Dual-Pool Recurrence Triage

When the user reports “双池” again, first classify the symptom before changing config:

- **Name-variant split**: `hermes-cabinet` vs `hermes_cabinet` → suspect tag sanitization or stale code path.
- **Routing/isolation split**: `hermes` vs `hermes-cabinet` → suspect profile map drift, profile-local `supermemory.json`, or an unrestarted Gateway/Event Bridge.

For the current cabinet deployment, expected routing is `default/cron-worker → hermes` and `regent + multi-agent profiles → hermes-cabinet`. Always verify both planes: real-home `~/.hermes/supermemory.json` for daemon/Event Bridge behavior and `~/.hermes/profiles/<profile>/supermemory.json` for provider/profile behavior. Historical Dashboard containers are not proof of a live regression; check recent writes and loaded-provider results. Detailed runbook: `references/dual-pool-recurrence-runbook.md`.

---

## Common Pitfalls (Top 11)

1. **SDK not installed** → `python3 -m pip install supermemory` in venv
2. **Provider switch needs restart** → `hermes gateway restart`
3. **Cross-pool OR queries don't exist** → make two calls + merge
4. **API key has no pool permissions** → access control in wrapper, not key
5. **A2A mode doesn't load MemoryProvider** → use API Server for memory ops
6. **Assuming only two pools exist** → additional pools like `sm_project_cli` (pi) may be live. Discover with `client.search.memories(q="test", container_tag="<candidate>")` — if it returns without error, the pool exists even if empty.
7. **`search_policy` is a string, not a dict** → the crosspool wrapper calls `.get('cross_pool_read')` on `search_policy`. If `search_policy` is `"department"` (string), it crashes. See §Cross-Pool Config Format for the correct dict structure.
9. **Config file location confusion** → The Hermes Supermemory plugin reads ONLY from `$HERMES_HOME/supermemory.json` (for default profile: `~/.hermes/supermemory.json`). Profile-level files at `~/.hermes/profiles/<name>/supermemory.json` are **silently ignored** by the plugin. If both files exist, only the root one matters. Always verify which file the plugin is actually reading before troubleshooting.
10. **Dashboard graph ≠ SDK search** → The Dashboard's "Memories" and "Connections" counts come from the Knowledge Graph — a separate backend processing step from the flat search index. A container can return valid search results via SDK (`search.memories()`) while the Dashboard shows zero memories/connections because the graph-building step failed or is incomplete. **Always verify with SDK before trusting the Dashboard.** If SDK search works but Dashboard shows nothing, the issue is backend graph processing, not data loss.
11. **Hermes writes documents, not memories** → `supermemory_store` and `sync_turn` both call `client.documents.add()`, never a direct memory insert. Memories are derived by the Supermemory backend pipeline from documents. If the Dashboard shows documents but no memories, the pipeline is processing documents into the search index but failing at the knowledge-graph stage.

Full list: `references/common-pitfalls.md`

---

## References

| File | When to read |
|------|-------------|
| `references/supermemory-six-rules.md` | **Daily ops & quick diagnostics** — 太子 live-ops findings: tools vs SDK, pool isolation, supermemory.json trap, false negatives, Dynamic Dreaming failures, daily commands |
| `references/supermemory-troubleshooting.md` | **Diagnosing outages & drafting support emails** — log grep patterns, API health check script, support email template (bilingual), timeline construction, common pitfalls |
| `references/dual-pool-recurrence-runbook.md` | **Dual-pool recurrence triage** — distinguish sanitization name-variant splits from `hermes`/`hermes-cabinet` routing isolation issues; verify both config planes and loaded-provider behavior |
| `references/hindsight-migration-guide.md` | Historical: Hindsight → Supermemory migration procedure |
| `references/common-pitfalls.md` | Complete pitfalls list (16 items) |
| `references/phase-2-3-changelog.md` | What changed in Phase 2/3 implementation |

Obsidian vault: `20-Areas/10_AI实践/Hermes/10_制度/Supermemory多profile记忆架构设计_v2.0.md`

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I check whether this is a SETUP task (needs onboarding checklist §) or a USAGE task (needs SDK/cross-pool §)?
- [ ] If cross-pool: did I use `supermemory_crosspool.py`, not raw SDK with AND-semantics `containerTags`?
- [ ] If onboarding a new profile: did I follow all 5 steps in the 30-minute checklist?
- [ ] If cache question: did I mention TTL (1h), invalidation (write-through), and offline fallback?
- [ ] Did I point to `references/` for deep dives (migration guide, full pitfalls, changelog) instead of bloating the response?

**If any box is unchecked, go back.**
