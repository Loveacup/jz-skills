# Phase 2/3 Implementation Changelog

What changed since the v2.0 design document was written. Referenced from `supermemory-hermes` SKILL.md.

## Phase 2 — All Profiles + Cross-Pool (2026-05-29)

| Change | Detail |
|--------|--------|
| **14 profiles switched** | All multi-agent profiles configured with `memory.provider: supermemory`, `container_tag: hermes-cabinet`, per-profile `.env` with `SUPERMEMORY_API_KEY` |
| **Hindsight retired** | Physical data cleaned (6 paths deleted, ~1.5MB freed); schema docs kept for reference |
| **Cross-pool channels** | `~/.hermes/scripts/supermemory_crosspool.py` — standalone wrapper with rate limiting, intent detection, audit logging |
| **Channel X1** | `default → hermes-cabinet` (read-only, cabinet-shared only, 6/min limit, intent-gated) |
| **Channel X3** | `archivist → hermes` (read-only + soft-delete, 30/min, no intent gate) |
| **Channel X4** | `dispatcher → hermes` (read-only, task_summary only, 4/min) |

## Phase 3 — Cache + Cross-Pool (2026-05-29)

| Change | Detail |
|--------|--------|
| **LRU cache** | `_SearchCache` class added to `plugins/memory/supermemory/__init__.py` — 200 entries, 1h TTL, LRU eviction |
| **Cache scope** | Wraps `search_memories()` and `get_profile()` — first call API, repeat calls cache hit |
| **Write-through** | `add_memory()` and `forget_memory()` trigger full cache invalidation |
| **Offline fallback** | On API error, serves stale cache with `WARNING` log entry |
| **Metadata monitoring** | Deferred (insufficient write traffic to justify dashboard) |
| **Auditor drift detection** | Deferred (requires metadata monitoring baseline) |
