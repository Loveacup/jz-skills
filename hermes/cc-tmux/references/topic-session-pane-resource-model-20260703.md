# Topic-Session-Pane Resource Model — 2026-07-03

## Trigger

During cc-tmux design discussion, the user clarified:

- Same Hermes topic reusing the previous CC/tmux session is reasonable.
- `/clear` may be used to clean context before reuse.
- Same topic may use a second CC for collaboration if the design is explicit and safe.
- Codex should plan, CC should execute, OMP should audit for this class of cc-tmux documentation/design work.

OMP independently audited the design and found `concern`-level issues, all verified by Hermes against source:

1. `hooks/cc-status-writer.sh` keys status files by `CC_TMUX_SESSION`; multiple Claude panes inside one tmux session would overwrite each other’s `cc-status`, heartbeat, turn-done, and output state.
2. `cc-topic-map.sh` is currently 1 topic → 1 session; a fork/new session overwrites mapping unless schema evolves.
3. `cc-route.sh` targets one session; it has no same-topic multi-worker routing semantics yet.

## Final decision

Use **Topic continuity + Session isolation + Pane presentation**:

| Layer | Meaning | Rule |
|---|---|---|
| Hermes topic | User-visible continuity unit | owns primary worker and children |
| Primary tmux session | Default CC worker for a topic | sequential same-topic work reuses it when safe |
| Child tmux session | Same-topic collaborative CC | used for parallel/reviewer/auditor roles |
| Pane/window | Display/scratch/observer only | not a worker identity |

Recommended resource shape:

```text
topic:<id>
  primary: hermes-cc-...main...
  children:
    - hermes-cc-...reviewer...
    - hermes-cc-...auditor...
```

## Reuse / fork / clear policy

| Scenario | Action |
|---|---|
| Same topic, same scope, primary IDLE/COMPLETED, heartbeat fresh, not poisoned | reuse primary |
| Same topic but context is too heavy/dirty | `/clear` then reuse primary |
| Same topic needs a second CC in parallel | fork child tmux session |
| Primary busy and message is continuation/redirect for current task | route/queue to primary |
| Primary busy and user wants parallel review/audit/subtask | fork child session |
| Repo/worktree/branch/write-scope/danger-class changes | fork |
| State is stale/resurrected/uncertain | do not reuse; classify suspected |
| User asks for fresh/isolate/new attempt | fork |

`/clear` is **reuse hygiene**, not a fork and not a new worker identity.

## Why not same-session panes/windows for second CC?

Do not run two managed CC workers inside the same tmux session today.

Reason: current state authority files are keyed by `CC_TMUX_SESSION`:

- `/tmp/cc-status-<session>.json`
- `/tmp/cc-heartbeat-<session>`
- `/tmp/cc-turn-done-<session>`
- `/tmp/cc-output-<session>/`

Two CC panes in one tmux session would collide on these files and confuse `cc-route`, `cc-monitor`, `cc-wait-decision`, and `cc-finish`.

Pane/window may still be used for observer/log/scratch duties, but not as lifecycle authority.

## Topic-map evolution

Current implemented schema is 1:1:

```json
{"topic_id": {"session": "hermes-cc-...", "at": "..."}}
```

Target minimal schema:

```json
{
  "topic_id": {
    "primary": {"session": "hermes-cc-...main...", "role": "primary", "at": "..."},
    "children": [
      {"session": "hermes-cc-...reviewer...", "role": "reviewer", "fork_reason": "parallel_review", "at": "..."}
    ]
  }
}
```

This registry is ownership/routing metadata only. Do **not** rebuild a lifecycle event bus in topic-map; hook/status files remain state authority.

## Documentation-library workflow lesson

For cc-tmux OB technical documentation restructuring, use the chain:

1. Codex planning-only: inventory, classify authority/history/audit/duplicates, produce execution package.
2. CC via cc-tmux executes bounded file edits/moves inside the OB project directory.
3. OMP audits authority alignment and link/navigation correctness.
4. Hermes verifies frontmatter, wikilinks, stale claims, qmd refresh, and Obsidian sync state.

Keep root project docs minimal (`README.md`, `AGENTS.md`), authorities in `10_cc-tmux核心/`, collaboration theory/incidents in `20_Agent协作/`, audit snapshots in `30_审计/`, and related speculative projects in `40_相关项目/`.
