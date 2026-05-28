# Common Pitfalls — Full Reference

Extended pitfalls list for Supermemory + Cabinet Memory architecture. The SKILL.md keeps top 5; see this file for the complete list.

## SDK / API

6. **Memory tool (L1) is not Supermemory**: The `memory` tool entries in the system prompt are stored locally, not in Supermemory. They persist regardless of provider setting.

7. **container_tag resolution**: `supermemory.json`'s `container_tag` field supports `{identity}` template variable, resolved at provider initialization. Raw string values are used as-is after sanitization (alphanumeric + underscore only).

8. **Token-sensitive strings in migration scripts**: When writing migration scripts that reference API keys, use string concatenation instead of f-strings.

9. **`client.search.memories()` requires keyword-only `q=` parameter**: `client.search.memories("query", container_tag="x")` → TypeError.

10. **A2A subprocess mode does NOT load MemoryProvider tools**: When a profile is invoked via A2A, the subprocess doesn't initialize MemoryProvider plugins. Use API Server mode for memory-dependent operations.

11. **Multi-profile setup requires per-profile `.env` + `supermemory.json`**: Each profile needs its own API key and config with the correct `container_tag`.

## Cross-Pool

12. **Cross-pool OR queries don't exist natively**: `containerTags: [A, B]` is AND, not OR. Use two separate calls + merge.

13. **API key has no pool-level permissions**: All access control via Hermes wrapper, not Supermemory API key.

14. **Metadata enforcement is client-side**: Supermemory SDK doesn't enforce metadata. Write without it = memory stored without identity → role confusion.

## Cache

15. **Cache invalidation is write-through (full flush)**: Any `add_memory` or `forget_memory` invalidates the entire cache. For high-frequency write scenarios, consider reducing `cache_ttl` instead.

16. **Stale cache on offline fallback**: If API is down and cache serves stale results, the agent won't know. Check `~/.hermes/logs/errors.log` for "serving stale cache" warnings.
