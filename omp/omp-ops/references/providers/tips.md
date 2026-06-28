# OMP Runtime Tips (`tips.txt`) — Verified Reference

Source: `@oh-my-pi/pi-coding-agent@16.2.3/src/modes/components/tips.txt`, `builtin-registry.ts`, release notes, and GitHub issues/PRs.

OMP shows random tips from its bundled `tips.txt` while idle. Some tips describe fully documented features; others point to **undocumented or hidden switches**. This reference catalogs every tip in v16.2.3, its real behavior, and caveats.

## Status legend

| Status | Meaning |
|---|---|
| ✅ verified/current | Tip is accurate in v16.2.3. |
| ⚠️ misleading | Command/feature exists, but the tip's wording is inaccurate or incomplete. |
| 🕵️ undocumented but real | Feature exists and works, but is not covered by official `docs/`. |
| ❌ removed/changed | Feature was removed or significantly changed; tip is stale. |

---

## Slash commands

| # | Tip | Status | Real behavior / caveat | Evidence |
|---|-----|--------|------------------------|----------|
| 1 | Send `.` instead of "keep going" | ✅ | Input `.` tells the agent to continue the previous task. Implemented in TUI input layer. | `tips.txt` v16.2.3 |
| 2 | `/btw` — ask a side question | ✅ | Ephemeral side-question panel; uses current context without writing to transcript. | PR #399, `builtin-registry.ts` |
| 3 | `/tan` — fork into background agent | ✅ | Run a full background agent on tangential work. | `builtin-registry.ts`, v16.0.3 notes |
| 4 | `/omfg` — complain about spaghetti code | ⚠️ | Exists, but it **forges a TTSR rule** from the complaint to stop recurring behavior, not just a vent. | `builtin-registry.ts`, v15.7.3 |
| 5 | `/force read` — pin next turn to a tool | ✅ | `/force <tool>` or `/force:<tool>` forces the next turn to use that tool. Tool must be active. | `builtin-registry.ts`, `agent-session-force-tool-choice.test.ts` |
| 6 | `/copy code` / `/copy cmd` | 🕵️ | `/copy` opens a copy selector; the `code`/`cmd` args are hinted in tips.txt but the exact routing is not clearly documented. Core `/copy` is confirmed. | PR #2076, `builtin-registry.ts` |
| 7 | `/shake` / `/shake images` | ✅ | `/shake` (or `/shake elide`) strips heavy tool results; `/shake images` drops only image blocks. | v15.7.3, `builtin-registry.ts` |
| 8 | `/collab` / `/join` | ✅ | E2E-encrypted live session sharing. `/collab view` gives read-only link. | README, `builtin-registry.ts` |
| 9 | `/usage reset` | ✅ | Redeem a saved Codex rate-limit reset for the active Codex account. | `builtin-registry.ts`, `handleUsageResetCommand` |
| 10 | `/advisor` | ✅ | Toggle a second model that reviews each turn. Since 16.2.3, supports multiple advisors via `WATCHDOG.yml` with full tool access; manage with `/advisor configure` TUI. | `docs/`, `builtin-registry.ts`, v16.2.3 notes |

### Usage notes

- `/force <tool>` fails if the tool is not in the current active set.
- `/usage reset` only works with Codex OAuth accounts; other providers are ignored.
- `/copy` on Linux prefers `wl-copy` / `xclip` / `xsel` over native clipboard so the selection survives process exit.

---

## Keyboard shortcuts

| # | Tip | Status | Real behavior / caveat | Evidence |
|---|-----|--------|------------------------|----------|
| 11 | `Ctrl+D` exits with draft saved | ❌ | `Ctrl+D` exits **only when the editor is empty**. Unsent drafts are **not** preserved; sent turns are always persisted. Use `/exit` or `Ctrl+C` twice to exit with editor content. | `docs/keybindings.md`, README |
| 12 | `Alt+P` (or `/switch`) switches provider | ⚠️ | `Alt+P` and `/switch` open the **temporary model switcher**, not a provider switcher. Provider changes require `/login`. | `docs/keybindings.md`, issue #2933 |
| 13 | `Ctrl+P` cycles role models smol → slow → ... | ✅ | Cycles forward through `cycleOrder` / default role order. | `docs/keybindings.md` |
| 14 | `Ctrl+R` searches prompt history | ✅ | Searches previously sent prompts for reuse. | `docs/keybindings.md` |
| 15 | `← ←` drills into a running/finished agent | ⚠️ | `← ←` navigates **up** from a subagent to its parent, not down into a subagent. Use Agent Hub (`Ctrl+S` / `Alt+Down`) to inspect subagents. | v16.0.3 release notes, v15.6.0 |

---

## Features, magic words, and env vars

| # | Tip | Status | Real behavior / caveat | Evidence |
|---|-----|--------|------------------------|----------|
| 16 | `omp stats` — model abuse stats | ✅ | Local web dashboard (default `http://localhost:3847`) showing per-model cost/latency/cache/error rates. | `@oh-my-pi/omp-stats`, PR #2841 |
| 17 | Task isolation → CoW worktrees | ✅ | `task` tool can run subagents in isolated CoW worktrees via `task.isolation.mode`. | `docs/tools/task.md`, PR #2626 |
| 18 | `completion(x...)`; ask clanker for batches | 🕵️ | `completion()` is a real one-shot eval helper. "Clanker" is not an official name — likely informal slang for the eval agent runner. | `completion-bridge.ts`, prelude docs |
| 19 | kitty/tmux/cmux/zellij/wezterm splits keep own session; `omp -c` resumes | ✅ | Pane IDs (`TMUX_PANE`, `KITTY_WINDOW_ID`, etc.) are used as session breadcrumbs. | `environment-variables.md`, PR #2400 |
| 20 | `ultrathink` — harder reasoning + rainbow glow | ✅ | Magic keyword injecting an `ultrathink-notice`; prose gets animated rainbow gradient. | `magic-keywords.ts`, PR #2506 |
| 21 | `orchestrate` — multi-phase parallel subagents + glow | ✅ | Magic keyword injecting an `orchestrate-notice`; teal→violet gradient. | v15.6.0 notes, `magic-keywords.ts` |
| 22 | `workflowz` — parallel subagents in eval + glow | ✅ | Magic keyword driving eval `agent()` fan-outs; optional isolation in v16.1.16+. | `magic-keywords.ts`, issue #3196 |
| 23 | `/login` again → load-balances same provider accounts | ✅ | Multiple credentials for the same provider are rotated automatically on rate-limit/usage exhaustion. | `docs/providers.md`, `auth-storage.ts` |
| 24 | `omp auth-broker serve` / `omp auth-gateway` | ✅ | Centralized remote credential vault + OpenAI-compatible proxy. | `docs/auth-broker-gateway.md` |
| 25 | `PI_DIALECT=glm\|kimi\|anthropic…` | 🕵️ | Forces an **owned in-band tool-call dialect**. Real but **not in `docs/environment-variables.md`**. `pi` dialect removed in v16.2.2. | `tips.txt`, release notes, issue #2759 |

### `PI_DIALECT` detail

`PI_DIALECT` selects the syntax OMP uses for **owned in-band tool calling** — useful when a model/gateway cannot parse native provider tool formats.

Known dialect values (v16.2.3, based on source/release notes):

- `glm`
- `hermes`
- `kimi`
- `xml`
- `anthropic`
- `deepseek`
- `harmony`
- `qwen3`
- `minimax` (added v16.0.5)
- `pi` / `pi-native` — **removed in v16.2.2**

Equivalent config-level controls:

- `PI_OWNED_TOOLS=1` or `PI_OWNED_TOOLS=<syntax>` — enable owned mode.
- `tools.format` in `config.yml` — choose `native` or a specific owned syntax.

Caveat: `PI_DIALECT` is undocumented in `docs/environment-variables.md`; prefer `tools.format` for stable, discoverable configuration.

---

## Known tip bugs

- **Ctrl+D wording** over-promises draft preservation.
- **Alt+P / `/switch` wording** incorrectly says "provider" instead of "model".
- **← ← wording** reverses navigation direction.
- **`PI_DIALECT=pi`** no longer works as of v16.2.2.

## See also

- `references/providers/models.md` — provider/model configuration and `tools.format`.
- `references/official/environment-variables.md` — documented env vars.
- `references/official/auth-broker-gateway.md` — broker/gateway setup.
