# R4c real-review hardening notes — 2026-06-25

## When to use

Use this reference when maintaining cc-tmux after a real Claude Code review task, especially when touching dogfood reporting, tmux-based test harnesses, or finish-session residue handling.

## Context

A real read-only CC task reviewed commit `a0d4a4a` and produced `/tmp/cc-r4c-real-review-report.md`. The review validated the R4c control model but found several hardening issues worth preserving as recurring lessons.

## Durable lessons

### 1. Dogfood `exit_code==10` is not Stop-hook evidence

`cc-finish.sh` emits dogfood records for dangerous residue (`exit_code==10`) inside the residue hard gate, before completion audit can set `TURN_DONE_FRESH`.

Therefore a record like:

```json
{"residue_danger":true,"turn_done_missing":true,"exit_code":10}
```

means “dangerous residue aborted before completion audit,” not necessarily “Stop hook failed.” Report logic should exclude `exit_code==10` from `turn_done_missing` counts, or model the value as `n/a`.

Regression pattern: add a fixture with `exit_code=10` + `turn_done_missing=true` and assert the summary shows `危险残留: 1 次` but `turn-done 缺失: 0 次`.

### 2. tmux test harnesses must detach stdio

In captured-output environments (CI, Hermes terminal capture, agent tool sessions), `tmux new-session -d` may leave the tmux server/child inheriting stdout/stderr file descriptors. That can keep the parent process output pipe open and make otherwise-finished commands appear to hang.

For tests, prefer:

```bash
tmux new-session -d -s "$SESSION" -x 120 -y 20 "..." </dev/null >/dev/null 2>&1
```

Do not blindly rewrite redirects inside the quoted command payload; only detach the `tmux new-session` invocation itself. If the payload intentionally contains `2>/dev/null`, preserve it inside the quotes.

### 3. Residue clearing is not guaranteed

Claude TUI input is not always a normal shell readline buffer. `C-u`, `Escape+C-u`, and `C-a C-k` can fail to clear visible residue.

When `cc-finish.sh` reports residue and mechanical clear attempts fail:

- do **not** press Enter;
- report that residue remains and was not executed;
- preserve evidence via pane capture / dogfood;
- release locks only when safe;
- start a fresh session or ask the user before any destructive cleanup / kill.

### 4. Documentation wording matters

A review flagged “last_tool set-u 修复” as overclaiming. Prefer precise wording: “last_tool 插值规范化 + 回归测试” unless there is verified evidence of the exact shell expansion failure mode.

## Verification used in the session

- `tests/test-dogfood.sh`: 12/12
- `tests/test-monitor.sh`: 9/9
- `tests/test-monitor-freeze.sh`: 8/8
- Full suite: 21/21 files, 203/203 assertions
- Runtime/source parity checked by hash for SKILL.md, AGENTS.md, `cc-dogfood-report.sh`, and all test scripts.
