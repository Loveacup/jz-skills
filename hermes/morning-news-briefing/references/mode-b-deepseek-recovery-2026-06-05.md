# Mode B DeepSeek Recovery — 2026-06-05

Use this reference when re-running Morning News in Interactive / Kanban Swarm mode with all worker agents pinned to DeepSeek v4 Pro.

## What happened

- User requested a full Mode B rerun and required all Kanban collaborative agents to use `deepseek-v4-pro`.
- All six profiles were updated before the swarm: `lane-zh`, `lane-en`, `lane-mixed`, `lane-tech`, `auditor`, `publisher`.
- Both `model.default` and `fallback_providers` were pinned to `deepseek-v4-pro`; gateways were restarted/kickstarted before dispatch.
- `lane-zh` hit DeepSeek content-risk filtering on Chinese conflict/news wording. Recovery was to reassign that lane to another already-pinned profile (`lane-en`) and continue; do not fall back to stale models such as Kimi.
- The first publisher completed into a scratch workspace that was garbage-collected. A stable follow-up publisher card regenerated the final artifacts into a persistent regent workspace.

## Repeatable checklist

1. Before creating the swarm, inspect/update every participating profile config:
   - `model.default = deepseek-v4-pro`
   - `fallback_providers = [deepseek-v4-pro]`
2. Restart or kickstart gateways for all six profiles, then run `hermes profile list`.
3. Create the Mode B swarm and dispatch.
4. Poll every 60–90s. Key transitions only: `blocked`, `failed`, `done`, high-risk drift.
5. If a lane hits DeepSeek `Content Exists Risk` repeatedly:
   - do **not** switch to an unapproved fallback model;
   - reassign to another profile that is already pinned to the requested model;
   - keep the lane scope but soften the specific wording if needed.
6. For final synthesis, avoid scratch-only delivery. Either:
   - create publisher with a stable `dir:<workspace>`; or
   - immediately copy/regenerate final artifacts into `~/.hermes/profiles/regent/workspaces/morning-news-{date}-modeb-<model>/final-artifacts/`.
7. Verify before reporting completion:
   - Markdown exists;
   - mobile + A4 PDF exist and each is >100KB;
   - PyMuPDF full-text extraction sees all sentinels;
   - `grep -E '一方面|另一方面|可能|或许|似乎'` returns zero;
   - TTS exists or the skip is explicitly annotated.

## Artifact quality bar from the successful rerun

- 50 今日要闻
- 8 深度分析
- 50 sources
- Mobile PDF and A4 PDF rendered with `scripts/render-pdfs.py`
- MP3 TTS generated through CosyVoice direct API after tool timeout

## Pitfalls

- `kanban_create --skill` may expect the skill's installed short name in some contexts, even where swarm worker strings use categorized paths. If a publisher card blocks with `Unknown skill(s)`, create a replacement card with the names shown by `hermes --profile publisher skills list`.
- Scratch workspaces can be cleaned after task completion. For user-facing deliverables, always persist to a stable workspace before final response.
- A model-level content-risk block is not a reason to silently change the model. Preserve the user's model constraint and recover via wording/reassignment within the pinned model pool.
