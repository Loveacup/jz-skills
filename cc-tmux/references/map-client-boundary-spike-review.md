# Map Client Boundary / Replaceable Renderer Spike

Use this when a project claims “frontend is replaceable” or “renderer is not engine” and you need to turn that architecture rule into evidence.

## Trigger

- Renderer-facing contract exists (e.g. `mud_map_view@3`).
- Web/SVG renderer already consumes the contract.
- User stresses that frontend must be swappable and must not own semantics, layout, visibility, legality, state, or adjudication.

## Pattern

1. **Codex plans only**
   - Run Codex read-only.
   - Constrain it to schema/fixture/renderer/tests; explicitly forbid Obsidian/qmd and code edits.
   - Require fixed output: target, files, RED tests, minimal implementation, verification, risks, CC boundaries.

2. **CC executes a DOM-free probe**
   - Add a thin non-Web interpreter, not an Engine and not a real UI.
   - Input only the renderer-facing payload fields (`nodes`, `edges`, `viewport`, `legend`, `theme_id`, `color_mode`, `focus_node`).
   - Output a structured render model, not SVG/HTML: visible nodes, visible edges, node boxes, edge segments, legend usage, and action intents.

3. **Tests prove client-boundary invariants**
   - Hidden nodes/edges are excluded.
   - Topology/state/visibility are preserved.
   - Layout uses viewport + node layout from the payload.
   - Edge endpoints follow the same boundary/opposite-direction contract as the Web renderer.
   - Legend covers visible styles.
   - Theme changes do not alter topology/layout/state/actions.
   - Actions match the current Web contract, even if that contract later needs tightening.

4. **Hermes audits independently**
   - Re-run spike tests, renderer contract tests, and full tests.
   - Check persistent/event DB timestamps when relevant.
   - Verify the probe did not touch Engine/schema/fixture/Web renderer unless explicitly justified.
   - Update STDD residual status from “open validation” to “first-layer spike passed; real second client still pending”.

## Important pitfall

Do not conflate “client-boundary proof” with “business-rule fix.” In the AI-MUD spike, Web `bindMudMapV3Clicks()` exposed move actions for every visible non-current node, regardless of edge `traversal_state`. The DOM-free probe intentionally mirrored that rule to prove equivalence; fixing action legality belongs in a later **Action Affordance Contract** slice where the Engine emits explicit affordances and the renderer only displays/forwards them.

## Report checklist

- New/modified files.
- What contract semantics each test covers.
- Whether the probe conflicts with the current Web renderer contract.
- Exact verification commands and results.
- Residual risks / next slice.
