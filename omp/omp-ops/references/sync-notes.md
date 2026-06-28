# Sync Notes

## 2026-06-28

- Official OMP 16.2.2 adds the `tiny` model role for lightweight background
  tasks. Authored docs now mention `tiny` in `providers/models.md`,
  `architecture.md`, and `SKILL.md`.
- Official 16.2.2 also mentions a new `textVerbosity` setting in the
  changelog, but the current mirrored docs do not expose a dedicated settings
  section yet. Keep this as a follow-up until the official docs surface the
  configuration shape.

## 2026-06-28 — 16.2.3 update

- Official OMP 16.2.3 enables V2 streaming remote compaction by default
  for compatible models. New config keys: `compaction.remoteStreamingV2Enabled`,
  `compaction.v2RetainedMessageBudget`.
- Multi-advisor support via `WATCHDOG.yml`/`WATCHDOG.yaml` files, with
  per-advisor models, tool subsets, and instructions. Added `/advisor configure`
  TUI. Advisors now have full tool access (no longer read-only).
- New settings: `statusLine.compactThinkingLevel` (glyph render of thinking
  level), `edit.citationTags` (OpenAI citation-marker emission).
- Session titles are now mutable with auto-replan refreshes and idle recaps.
- Fixed 30+ bugs across compaction, reasoning, MCP SSE transport, SSH,
  OpenAI/Codex session rehydration, skill prompts as user turns, and more.
- Linux desktop notifications via D-Bus (`PI_NO_DESKTOP_NOTIFY=1` to disable).
- Catalog pricing and context window updates for several models.
- Reasoning capability disabled for multiple providers in catalog.
