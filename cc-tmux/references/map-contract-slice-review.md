# Map Contract Slice Review Pattern

Use when a CC implementation slice changes a renderer-facing contract (map view, graph view, editor view, workflow canvas, etc.) and the user cares about semantic correctness and visible behavior.

## Pattern

1. **Codex plans only**: ask Codex for the minimal slice, RED tests, compatibility strategy, CC boundaries, verification commands, and explicit risks. For non-git project dirs, use `codex exec --skip-git-repo-check --sandbox read-only`.
2. **CC implements**: give CC the Codex plan plus an explicit forbidden list: no theme/aesthetic work, no schema changes to make tests easier, no docs/qmd/Obsidian unless requested.
3. **Hermes audits in layers**:
   - read CC report and key files;
   - rerun target tests and full tests;
   - run a runtime smoke that exercises the actual payload;
   - run a browser smoke when a frontend renderer is touched;
   - compare test pass with visible behavior.
4. **Separate verdict dimensions**. A slice may be a pass for the backend contract but a partial/fail for actual renderer capability. Say so instead of flattening everything to “done”.

## Acceptance wording

Use a table like:

| Dimension | Verdict |
|---|---|
| Engine emits new contract | ✅ |
| Payload carries new contract | ✅ |
| Compatibility preserved | ✅ |
| Tests pass | ✅ |
| Native renderer actually renders the new model | ⚠️ / ❌ |

## Common pitfall

Do not accept an adapter as a native renderer. Example: `mud_map_view@3 -> stage_view -> renderSceneStage()` may prove the payload is connected, but it does **not** prove the Graph-MUD grid renderer exists. Record this as “contract connected; native renderer pending”.

## Runtime smoke checklist

- WebSocket/API payload contains the new `version`, `mode`, focus field, and expected counts.
- Browser has no JS errors.
- UI visually shows the intended model; if it still shows the old metaphor through an adapter, mark frontend renderer as partial.
- No persistent side-effect DB/log was accidentally created unless intended.
