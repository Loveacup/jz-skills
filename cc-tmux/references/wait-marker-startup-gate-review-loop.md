# wait-marker startup gate review loop（2026-06-30）

## 场景

另一个 topic 使用 cc-tmux 时，`tmux send-keys ... Enter` 后文本停在 CC 输入框，CC 未进入 THINKING/TOOL；随后 `cc-wait-marker.sh` 等一个未启动任务直到 900s timeout。

## 持久结论

这不是“CC 不可靠”，而是提交确认链路缺失。修复应优先落在脚本硬约束，而不是只写使用提醒。

## 实现规则

`cc-wait-marker.sh` 等 marker 前必须执行 startup gate：

- 无新 marker + `IDLE` → `exit 4` fail-fast
- 输入框 residual → 默认 `exit 4`，**不要自动 Enter**
- queued-message banner → `exit 4`
- residual 自动提交只能显式 opt-in：`CC_WAIT_AUTO_SUBMIT_RESIDUAL=1`
- 真 running / fresh hook running 才进入 wait loop

## 为什么默认不能自动 Enter

Codex 审查指出：自动 Enter 可能误提交旧输入框残留，造成重复/错误任务执行。默认策略必须保守：fail-fast，让 Hermes/用户清理或重发。

## 必测用例

- clean IDLE + no marker → exit 4, fast
- residual input default → exit 4, no `send-keys Enter`
- residual opt-in → exactly one Enter, then still fail-fast if not started
- residual line containing `Write/Edit/Tool` → still residual, not running
- old tool scrollback + empty prompt → IDLE/fail-fast, not running
- queued-message banner → exit 4, no Enter
- true running pane → gate passes, timeout path remains exit 1 if no marker

## Review gate lesson

For cc-tmux script changes, Codex review should check not only code behavior but also:

- docs/test counts match `tests/run-tests.sh` output
- newly referenced `references/*.md` files exist in repo, not only runtime skill dir
- `git diff --check` is clean

Do not push after a “code PASS” if docs counts or reference links are stale; those are blockers for this skill because AGENTS/SKILL are operational inputs for future agents.
