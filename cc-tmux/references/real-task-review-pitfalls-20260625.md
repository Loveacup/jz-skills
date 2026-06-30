# Real task review pitfalls (2026-06-25)

## When to use

Use this reference when running or interpreting a real cc-tmux task test, especially a readonly review that asks Claude Code to write a report artifact.

## Lessons from the real review test

A real readonly review of commit `a0d4a4a` exposed several workflow and implementation pitfalls that are broader than that one commit.

### 1. turn-done is not enough: verify the artifact

`cc-turn-done-<session>` only proves the Claude Code turn stopped. It does **not** prove the required report/file exists.

Required verification after turn-done:

```bash
stat /tmp/expected-report.md
# then read the file and verify it has the requested sections / evidence
```

If the artifact is missing, treat the task as **failed validation**, not PASS. Send a narrow follow-up asking CC to use already-collected evidence and write the specified file. Do not re-run the full task unless needed.

### 2. high-effort long thinking is a judgment point, not automatic C-c

`cc-monitor.sh` may report token freeze while the pane still shows a live thinking timer. If the timer continues increasing and the user preference is not to interrupt active thought, do not auto-`C-c`.

Correct handling:

1. Report the conflict: monitor warns freeze, pane timer still advances.
2. Check whether the output artifact already exists.
3. Ask or follow the user's standing preference before interrupting.
4. If the user says continue waiting, wait one more bounded round and re-check.

### 3. tmux test fixtures must redirect stdio

When a shell test creates tmux fixture sessions, use explicit stdio redirection:

```bash
tmux new-session -d -s "$SESS" -x 120 -y 20 "cmd" </dev/null >/dev/null 2>&1
```

Why: tmux server/child processes can inherit the caller's captured stdout/stderr file descriptors. In CI or Hermes tool-capture contexts this can hold the output pipe open and make the caller appear hung even after the test logic completed.

Apply this to test-only fixture sessions (`tests/test-*.sh`). Do not blindly change production session startup without reviewing TUI requirements.

### 4. dogfood `turn_done_missing` should avoid exit-10 false positives

A danger-residue hard gate (`cc-finish.sh` exit 10) can occur before the completion audit has set `TURN_DONE_FRESH`. If dogfood emits at that point and defaults `TURN_DONE_FRESH=false`, reports will count `turn_done_missing=true` even when the Stop hook is healthy.

Preferred fix shape:

- In `cc-dogfood-report.sh`, do not count `turn_done_missing` for records with `exit_code==10`; or
- In `cc-finish.sh`, encode the value as `n/a`/separate reason for early hard-gate records.

The important interpretation rule: danger residue and Stop-hook health are separate signals; do not let one inflate the other.

### 5. Be precise about what a code change actually fixed

Do not describe cosmetic shell interpolation changes as a proven runtime bug fix unless the pre-fix version demonstrably failed. For examples involving `$VAR` next to CJK punctuation, distinguish:

- a real `set -u` bug with a failing reproduction; vs
- a defensive style normalization to `${VAR}` plus a regression test.

Documentation should say exactly which one happened. Overclaiming a fix misleads later triage.

### 6. Clearing Claude TUI residual input may fail

`cc-finish.sh` can detect benign residual text in the prompt after completion. Mechanical clear attempts such as `C-u`, `Escape` + `C-u`, or `C-a` + `C-k` may not clear the Claude TUI input line in all states.

Rules:

- Never press Enter on residual text just to clear it.
- If mechanical clear fails, report the residue and leave the session alive unless the user confirms killing/restarting it.
- Treat clear-failure itself as a follow-up pitfall; do not hide it under a successful finish summary.
