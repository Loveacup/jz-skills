# Map Renderer Contract Slice Review — native renderer completion gate

Use this when a CC/Codex slice claims a renderer-facing map contract is implemented. The key audit question is whether the browser truly renders the new contract or merely adapts it into an old UI.

## Pattern

For map/UI contract slices, split acceptance into three layers:

1. **Contract connected** — server/engine emits the new payload (`map_view.version == 3`, `mode == mud_grid`, `nodes/edges/legend/viewport` present).
2. **Renderer native** — frontend main path directly consumes the new payload and exposes a new DOM/SVG contract.
3. **Visual/readability acceptable** — browser smoke shows the map metaphor is legible.

Do not collapse these. A slice can pass layer 1 while failing layer 2.

## Red flag: adapter masquerading as native renderer

This is not native completion:

```text
mud_map_view@3 → _v3ToStageView() → renderSceneStage()
```

It may be a useful compatibility bridge, but it still renders the old stage metaphor. Treat it as an explicit risk/partial pass, not as done.

## Codex → CC → Hermes recipe

### Codex planning prompt shape

Use read-only planning. Ask Codex for:

- minimum implementation slice;
- exact files to modify;
- RED-first tests;
- DOM/SVG contract markers;
- CC forbidden changes;
- unit + browser smoke commands;
- risks and acceptance gates.

For non-git workdirs include `--skip-git-repo-check --sandbox read-only`.

### CC execution boundaries

For a frontend renderer-only slice, bound CC to files like:

```text
static/map_renderer.js
static/style.css
tests/test_map_renderer_contract.py
tests/test_map_renderer_acceptance.py
```

Forbid backend/schema/fixture/Obsidian/qmd/theme redesign unless explicitly approved.

### Hermes audit checklist

After CC turn-done, Hermes must re-run:

```bash
python -m unittest tests.test_map_renderer_contract -v
python -m unittest tests.test_map_renderer_acceptance -v
python -m unittest discover tests -v
python -m py_compile server.py engine.py world.py predictor.py map_engine.py map_space.py map_layout.py map_visibility.py llm_telemetry.py
```

Then run a live app smoke:

- WebSocket first scene has `map_view.version == 3`, `mode == mud_grid`, focus node correct.
- Browser DOM contains `.mud-map-v3`.
- Browser DOM does not contain `.scene-stage` for the v3 main map.
- `.mud-node` count > 1 and `.mud-edge` count > 0.
- hidden edges/nodes are absent.
- `.mud-legend-layer` exists.
- screenshot/vision check: no obvious overlap, text clipping, or center-through-node edges.

Example DOM probe:

```js
(() => {
  const svg = document.querySelector('svg.mud-map-v3');
  const nodes = [...document.querySelectorAll('.mud-node')];
  const edges = [...document.querySelectorAll('.mud-edge')];
  return {
    hasMudMap: !!svg,
    mapVersion: svg?.dataset.mapViewVersion,
    mapMode: svg?.dataset.mapMode,
    focusNode: svg?.dataset.focusNode,
    sceneStageCount: document.querySelectorAll('.scene-stage').length,
    nodeCount: nodes.length,
    edgeCount: edges.length,
    hasHiddenEdge: !!document.querySelector('[data-edge-id="blacksmith_east_secret_tunnel"]'),
    legend: !!document.querySelector('.mud-legend-layer')
  };
})()
```

Accept native renderer only when:

```text
hasMudMap=true
mapVersion="3"
sceneStageCount=0
nodeCount>1
edgeCount>0
hasHiddenEdge=false
legend=true
```

## Reporting language

Be precise:

- “backend contract connected” means payload/schema/tests pass.
- “native renderer complete” means the frontend no longer routes v3 through the old adapter and browser DOM proves the new renderer path.
- “visual pass” requires screenshot/vision inspection beyond unit tests.

If only layer 1 passed, say so. Do not tell the user the map renderer is done.