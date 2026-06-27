# CC Agent Team — Multi-Paper Research Pattern

> Proven 2026-06-05: 4 agents, 11 papers, 247-line briefing in one session.

## When to Use

- Need to research multiple papers/topics and synthesize findings
- Task requires searching web, fetching arxiv, reading blog posts across domains
- Output is a research briefing, feasibility report, or architecture recommendation

## Full Workflow

### 1. Prepare Context File

Write a detailed context file to `/tmp/cc-context-{task}.md` containing:

```markdown
## Background — what problem we're solving
## Current state — what we already know
## Papers to research — URLs (arxiv, blogs, etc.)
## Core questions — numbered list of what to answer
## Output format — briefing style, language, file path
## Constraints — budget, scope, language
## Discussion protocol — "this is research, not execution; brief me before editing anything"
```

Key: **describe coverage angles, not agent count.** E.g. "覆盖蒸馏/生命周期/减法/检索四个角度" — let CC decide how many agents to spawn.

### 2. Launch CC

```bash
tmux new-session -d -s hermes-cc-default-$(date +%Y%m%d) \
  send-keys "HOME=/Users/alexcai claude --model claude-opus-4-8 --effort max" Enter
```

Wait 5s for PTY init, verify `bypass permissions on`.

### 3. Deliver Task via File-Pass (Single Line)

```bash
tmux send-keys -t <s> "Read /tmp/cc-context-{task}.md。然后按里面说的做——先搜论文、再讨论、最后出简报。" Enter
```

**NEVER multi-line send-keys during research tasks** — CC will enter Flummoxing/Nucleating immediately and any queued text gets stuck.

### 4. Monitor with Patience

Research tasks at `max` effort will spend 3-5+ minutes in Flummoxing/Nucleating. This is NORMAL — CC is planning a complex multi-agent research strategy.

**Token growing** = thinking is active. Continue waiting.
**Token frozen >3min + "almost done"** = thinking loop. See recovery below.

### 5. Thinking Loop Recovery

When CC hits Flummoxing/Nucleating loop at "almost done" + token frozen >3min:

```bash
# Step 1: Ctrl+C to interrupt
tmux send-keys -t <s> C-c

# Step 2: Narrow to atomic task
tmux send-keys -t <s> "先只搜索并阅读 <paper1> 和 <paper2>。读完简短回复初步判断（5-10 bullet）。不要做架构设计。" Enter
```

After CC breaks through with the narrow task, chain the next step:

```bash
tmux send-keys -t <s> "分析不错。继续搜更多相关工作，然后内部讨论对齐后出完整简报。写简报..." Enter
```

### 6. Critical: Don't Send Commands During Thinking State

**SYMPTOM (2026-06-05):** CC is actively Nucleating (✻/✢/✳ spinning), you send `send-keys "指令" Enter`. Text appears at ❯ but is NOT processed — queued as "Press up to edit queued messages."

**FIX:** Ctrl+C to interrupt → send single-line command → Enter. The interrupt clears the queue and lets the new command through.

This is distinct from Pitfall #33 (multi-line sequential send-keys) — here a SINGLE line queues because CC's input processor is busy with the thinking state.

### 7. Track Agent Team Progress

```bash
tmux capture-pane -t <s> -p -S -30
```

Look for:
- Agent spawn: `Running N agents…`
- Per-agent: `├ <name> · N tool uses · Xk tokens`
- Completion: `│ ⎿ Done`
- Leader synthesis: `✻ Whirlpooling…` (writing briefing)

### 8. Disk-Verify Output

```bash
find /tmp -name "*.md" -newer /tmp/cc-marker -type f
ls -la <expected output path>
```

Don't trust the tmux task board alone — use `find -newer` (Core Rule #12).

### 9. Chain Research Rounds

After first round: `/clear` the CC session → send next research directive as single-line → continue. Don't kill the session between rounds — keep context for follow-up questions.

## Common Failure Modes

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Planning loop | "almost done" + token frozen >3min | Ctrl+C → narrow to 2 papers only |
| Send-keys queued during thinking | "Press up to edit queued messages" | Ctrl+C → single-line retry |
| Agent team stalled | `Waiting for N background agents` + token frozen | `ls` check disk → `send-keys "Agent N done."` if files exist |
| Late "almost done" churn | Token growing but "almost done" persists >5min | Genuine synthesis — let it finish. Only interrupt if token freezes |

## Tokens: Expected Budget

For a 4-agent, 10+ paper research task at max effort:
- Leader planning/fetching: 5-10k input tokens
- Agent research: 20-35k tokens per agent
- Leader synthesis: 25-30k tokens (writing 200+ line briefing)
- **Total: ~150k input tokens, ~5k output tokens**
