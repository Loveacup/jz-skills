# Map Disabled Node Readability Pass

Use when a renderer-facing AI-MUD / Graph-MUD slice already has Engine-provided action affordances (for example `node.actions[]`) and the remaining problem is that disabled/unreachable nodes look like broken clickable nodes.

## Trigger

- Web/SVG renderer consumes `mud_map_view@3` or equivalent renderer contract.
- Clickability already comes from Engine output (`action.enabled`, `disabled_reason`).
- Disabled nodes are functionally non-clickable but visually ambiguous, inaccessible, or lack readable reason text.

## Boundary

This is a **readability/accessibility pass**, not a contract or Engine slice.

Allowed scope for the small pass:

- renderer output attributes (`aria-disabled`, `title`, `data-disabled-reason`)
- CSS selectors driven by existing contract fields (`data-action-enabled="false"`)
- renderer contract tests
- browser DOM/visual smoke

Do **not** change:

- Engine legality logic
- schema / fixture unless the existing fixture cannot express enabled + disabled nodes
- action contract shape
- movement validation
- v2/legacy renderer paths unless explicitly in scope

## RED-first test checklist

Add renderer tests before implementation:

1. Disabled node emits `data-action-enabled="false"`.
2. Disabled node keeps `data-disabled-reason` non-empty.
3. Disabled node emits `aria-disabled="true"`.
4. Disabled node exposes the reason through SVG `<title>` or `aria-label`.
5. Enabled node does **not** receive `aria-disabled="true"`.
6. Click/keyboard binding remains gated only by `el.dataset.actionEnabled === 'true'`.
7. No new legality inference from `node.state`, `edge.traversal_state`, `visibility_state`, DOM, CSS, or labels.
8. CSS has disabled selector such as `.mud-node[data-action-enabled="false"]`.
9. CSS has enabled selector such as `.mud-node[data-action-enabled="true"]`.

## Minimal implementation pattern

Keep the renderer source of truth as Engine-provided actions:

```js
const moveAction = (node.actions || []).find(a => a.type === 'move');
const actionEnabled = moveAction ? moveAction.enabled : false;
const disabledReason = moveAction ? (moveAction.disabled_reason || '') : 'unreachable';
```

Then add presentation-only fields:

```js
const ariaDisabled = actionEnabled ? '' : ' aria-disabled="true"';
const titleSvg = actionEnabled
  ? `<title>${mapEsc(label)}</title>`
  : `<title>${mapEsc(label)} · ${mapEsc(disabledReason)}</title>`;
```

CSS should make disabled nodes visibly inert but still readable:

```css
.mud-node[data-action-enabled="true"]{cursor:pointer}
.mud-node[data-action-enabled="false"]{cursor:not-allowed}
.mud-node[data-action-enabled="false"] .mud-node-body{opacity:.52;stroke-dasharray:4 3}
.mud-node[data-action-enabled="false"] .mud-node-label{fill:var(--text-dim)}
.mud-node[data-action-enabled="false"] .mud-node-state-label{fill:var(--muted)}
.mud-node[data-action-enabled="false"]:focus .mud-node-body{stroke:var(--muted);stroke-width:1.5}
```

## Verification

Run targeted and renderer contract tests, then do browser smoke:

```bash
python -m unittest tests.test_map_renderer_affordance -v
python -m unittest tests.test_map_renderer_contract tests.test_map_renderer_acceptance tests.test_map_renderer_affordance -v
python -m unittest discover -s tests -v
```

Browser DOM smoke should confirm:

- disabled nodes: `aria-disabled="true"`, `cursor:not-allowed`, `onclick=false`, `<title>` includes reason
- enabled nodes: no `aria-disabled`, `cursor:pointer`, `onclick=true`
- `.mud-map-v3` exists and `.scene-stage` is absent on v3 path
- no JS errors

视觉 smoke: disabled nodes should be obviously not clickable, still readable, and visually lower-priority than enabled/current nodes.

## Pitfall

Do not fix visual ambiguity by reintroducing frontend legality inference. The renderer may style `data-action-enabled` and display `disabled_reason`; it may not derive those values from state, edge, DOM, CSS, or labels.
