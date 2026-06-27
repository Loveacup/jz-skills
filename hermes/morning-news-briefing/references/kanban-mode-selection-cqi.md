# Kanban mode selection for morning-news CQI

Use when deciding how the morning-news pipeline should run through Hermes Kanban, especially after quality incidents or when cron should trigger Kanban.

## Evidence baseline from 2026-06-05 review

- Mode B / Swarm produced an acceptable morning-news artifact when repaired and pinned: 47 headline bullets, 8 deep-analysis blocks, S01–S50 source ledger, mobile + A4 PDFs, TTS MP3, and stable final-artifacts persistence.
- Five-mode Kanban smoke testing showed:
  - Single-task: PASS — best for atomic recovery.
  - Swarm: PASS/PARTIAL — graph creation works, but gateway auto-dispatch and synthesizer skill assignment need gates.
  - Orchestrator/manual dependency graph: PASS — cleanest multi-card result; fan-in dependencies worked.
  - Triage: PASS/PARTIAL — `decompose` creates real executable child cards and can be auto-claimed; not a dry-run.
  - Goal: PASS/PARTIAL — CLI accepts goal cards, but full judge loop needs isolated testing.

## Recommended mode combination

- **Primary production mode: Swarm.** Morning news is a deterministic, high-parallelism, gate-heavy pipeline: multi-lane search → verifier/auditor → publisher/synthesizer. This matches Swarm's fan-out/fan-in model.
- **CQI and targeted repair: Orchestrator/manual graph.** Use hand-written dependencies for CQI writeback, layout-only repairs, source-count fixes, mobile-only re-rendering, or any task where one output must not disturb another.
- **Recovery/archival: Single-task.** Use one-card tasks for re-rendering one PDF, regenerating TTS, persisting final artifacts to stable workspace, or re-running one lane.
- **Exploration only: Triage.** Use only for ambiguous new sections or experimental changes. Do not put daily production through `specify/decompose` because it reintroduces non-deterministic task graphs.
- **Long-running quality campaigns only: Goal.** Use for multi-day quality-improvement campaigns with explicit acceptance criteria, isolated board, and budget. Do not place daily news production on a judge loop.

## Hard gates before cron-triggered Swarm

1. Check all worker/auditor/publisher profiles: `model.default`, `fallback_providers`, and gateway status.
2. Ensure publisher/synthesizer cards use explicit, valid full-path skills. Immediately inspect created cards/logs for `Unknown skill(s)` or accidental skills such as `humanizer`.
3. Treat ready cards as live: gateway dispatchers may claim them immediately. If preflight cannot be guaranteed before creation, create blocked/todo cards first and promote only after gates pass.
4. Persist final user-facing artifacts to a stable workspace; do not rely on scratch Kanban workspaces.
5. Use the asset templates (`assets/mobile-template.html`, `assets/standard-template.html`) for accepted Swiss/IKB layout; `render-pdfs.py` is only a fallback unless it is verified to use those assets.

## Mechanical verification to include in CQI writeback

- Count headline bullets under `## 📰 今日要闻`.
- Count deep-analysis blocks using the exact `### 🔍 分析` prefix.
- Distinguish source ledger count (`S01–SNN` under 来源清单) from citation-marker count (`[sNN]` in body). Record both if they differ.
- Check layout sentinels in generated asset HTML: `#002FA7`, `cover-wrap`, `sec-timeline` present; old bronze `#b47a32` absent.
- Verify mobile/A4 PDF and TTS MP3 exist in stable final-artifacts directory with non-trivial sizes.

## CQI writeback pattern

When a CC/Hermes review produces a mode decision, append a concise section to `早新闻 CQI.md` with:

- mode combination conclusion,
- test evidence used,
- auditable rationale (premise → evidence → inference → conclusion, not hidden chain-of-thought),
- cross-mode hard gates,
- next mechanical tests.

Keep the full CC advisor report and machine verification JSON in a workspace and link their paths from the CQI note rather than pasting full logs into Telegram.
