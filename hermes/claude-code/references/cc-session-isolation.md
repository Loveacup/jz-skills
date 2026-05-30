# CC Session Isolation — Complete Investigation

> **2026-05-30** — Root cause traced from "daemon singleton" theory to verified "session sharing" mechanism.
> **Resolution:** Multi-Agent Coordination Protocol + per-agent independent workdirs.

## Investigation Timeline

### Phase 1: Symptom Discovery

Multiple Hermes agents sending `send-keys` to same CC tmux session → commands interleave, tasks corrupted.

Initial theory: CC is a global singleton daemon. Killing the process + rebuilding tmux should fix it.

### Phase 2: Daemon Theory Disproven

```bash
# 1. Agent A runs task in tmux session
tmux send-keys -t cc-session 'claude --dangerously-skip-permissions' Enter

# 2. Kill ALL CC processes
pkill -f claude

# 3. Rebuild tmux + restart CC
tmux new-session -d -s cc-fresh
tmux send-keys -t cc-fresh 'cd /new/project && claude' Enter

# 4. Result: CC RESUMES OLD SESSION — daemon kill didn't help
# State persisted in ~/.claude/
```

### Phase 3: Root Cause Identified (Web Research)

Searched Exa + Brave for CC CLI references, GitHub Issues:

- **CC Official Docs**: "If you resume the same session in two terminals without forking, messages from both interleave into one transcript."
- **Session storage**: `~/.claude/projects/<project-hash>/<session-id>.jsonl`
- **`--session-id <uuid>`**: Works reliably in **print mode**, unreliable in interactive mode (Issue #44607 — CLI generates own internal UUID)
- **`--fork-session`**: Creates new session from existing, preserving history but diverging

### Phase 4: Systematic Testing (2026-05-30)

| Test | Configuration | Result |
|------|-------------|--------|
| 1 | Single Agent Team (3 workers) | ✅ PASS — all workers dispatched, Fact-Forcing Gate handled |
| 2 | Different workdirs, simultaneous | ✅ PASS — no interference, 2s timestamp difference |
| 3 | Same workdir, sequential | ✅ PASS — shared session file, no message interleaving |
| 4 | Same workdir + `--continue` | ❌ THEORY — would conflict (two agents on same session) |

**Key finding from Test 3:** Even in same workdir, `claude` (not `--continue`) creates independent sessions that don't conflict when sequential.

## Verified Mechanisms

### Print Mode (`-p`)

```bash
# ✅ VERIFIED — two UUIDs produce two independent .jsonl files
claude -p "task" --session-id "11111111-1111-4111-8111-111111111111" --output-format json
claude -p "task" --session-id "22222222-2222-4222-8222-222222222222" --output-format json

# Result:
# ~/.claude/projects/<hash>/11111111-1111-4111-8111-111111111111.jsonl
# ~/.claude/projects/<hash>/22222222-2222-4222-8222-222222222222.jsonl
```

### Interactive Mode

- `--session-id` unreliable (Issue #44607)
- Isolation achieved via: **independent workdirs** + **no `--continue`** + **`--fork-session` for branching**

## Coordination Protocol (Deployed)

See SKILL.md `§ Multi-Agent Coordination Protocol`:

1. **Before any CC invocation**: scan all tmux sessions for `●` active tool calls
2. **If BUSY**: report to user, don't silently start new session
3. **Session naming**: `hermes-cc-{profile}-{ts}`
4. **Workdir isolation**: each agent uses independent workdir

## Related

- [Issue #44607](https://github.com/anthropics/claude-code/issues/44607) — `--session-id` inconsistency between modes
- [CC Sessions Docs](https://code.claude.com/docs/en/sessions) — session management
- [CC CLI Reference](https://code.claude.com/docs/en/cli-reference) — `--session-id`, `--fork-session`, `--resume`
- Obsidian: `00-Inbox/CC tmux 多Agent 会话隔离问题.md`
