# CC Bypass Permissions Dialog — Complete Fix Workflow

> Session: 2026-06-28 · CC v2.1.178 · macOS tmux
> Problem: `bypass permissions on` dialog blocks `tmux send-keys` input
> Fix: `--allow-dangerously-skip-permissions` startup flag

## Symptoms

- CC with `--effort max` shows persistent bottom banner: `⏵⏵ bypass permissions on (shift+tab to cycle) · ← for agents`
- `tmux send-keys` sends Down/Enter, Tab/Enter, Space/Enter, y/Enter, S-Tab/Enter — all ineffective
- Dialog persists, CC never consumes task input
- CC enters "Interrupted" state if Escape pressed

## Root Cause

Claude TUI's permission dialog uses **non-standard terminal input handling** (internal event loop). `tmux send-keys` sequences cannot map to its interaction logic.

## Fix Workflow

### Step 1: Test the flag in isolation

```bash
# Start a fresh tmux session for testing
tmux new-session -d -s test-bypass

# Start CC with the flag
tmux send-keys -t test-bypass 'claude --allow-dangerously-skip-permissions --model claude-sonnet-4-6 --effort high' Enter

# Wait 5s for initialization
sleep 5

# Send a simple test message
tmux send-keys -t test-bypass 'what is 2+2?' Enter

# Wait for response
sleep 10

# Capture output to verify
tmux capture-pane -t test-bypass -p -S -10 | tail -5
# Expected: "⏺ 四" or similar — CC consumed the input
```

### Step 2: Modify cc-start.sh

Add `--allow-dangerously-skip-permissions` to the CC launch command (around line 228):

```bash
# Before
claude --model "$model" --effort "$effort" ...

# After
claude --allow-dangerously-skip-permissions --model "$model" --effort "$effort" ...
```

### Step 3: Validate with real task

```bash
# Start CC via modified cc-start.sh
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-start.sh \
  --target "test-validation" \
  --effort max \
  --model claude-opus-4-8 \
  --task "test bypass permissions" \
  --ack-active

# Send a task that requires file write
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-send.sh \
  --session hermes-cc-default-test-validation-XXXX \
  --context /tmp/test-task.md

# Wait for turn-done marker
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-wait-marker.sh \
  --session hermes-cc-default-test-validation-XXXX \
  --after 0 --timeout 300

# Verify file was written
ls -la /tmp/test-output.md
```

### Step 4: Sync to source and push

```bash
# Find source directory (may differ from runtime)
find ~/code/jz-skills -type d -name "cc-tmux" 2>/dev/null
# → ~/code/jz-skills/hermes/cc-tmux

# Copy modified files
cp ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-start.sh \
   ~/code/jz-skills/hermes/cc-tmux/scripts/cc-start.sh

# Commit and push
cd ~/code/jz-skills
git add -A
git commit -m "fix(cc-tmux): add --allow-dangerously-skip-permissions to bypass tmux permission dialog

Problem: CC v2.1.178 with --effort max shows persistent bypass permission
banner that blocks tmux send-keys interaction.

Fix: Add --allow-dangerously-skip-permissions startup flag.
CC enters bypassPermissions mode directly without interactive confirmation.

Verification: CC normally consumes task input and writes files."
git push
```

### Step 5: Update reference documentation

Update `references/cc-bypass-permissions-dialog-issue.md` to mark as fixed and link to this workflow.

## Verification Checklist

- [ ] Test session shows `⏵⏵ bypass permissions on` (already on, not "press to enable")
- [ ] `tmux send-keys` input is consumed by CC (not shell)
- [ ] File write operations succeed (`Write` tool output shows path + size)
- [ ] turn-done marker appears after task completion
- [ ] cc-start.sh modified and committed
- [ ] Reference docs updated

## Notes

- **Max effort triggers dialog**: `--effort max` 100% triggers, `--effort high` 0% triggers (as of v2.1.178)
- **Banner remains visible**: Even with flag, banner still shows at bottom — but state is "on", not "waiting for confirmation"
- **Model compatibility**: Opus ✅ all efforts · Sonnet ❌ `--effort high` (use medium or omit)
- **Future CC versions**: If TUI framework changes, this workaround may need revision. Monitor `cc-bypass-permissions-dialog-issue.md`.
