# CC 可靠性 = 用法问题（WRR v6 实战校正）

## 用户纠正

Alex 明确纠正：**“CC 可靠；如果不可靠，大概率是用法出问题。”**

不要把一次/几次 zero-output、timeout、思考循环归纳成“CC 不可靠”。正确反应是诊断调用方式。

## 失败模式（2026-06-29 WRR v6）

- 一次性塞 5 个大型任务包（runtime/env/loader/registry/CLI）→ CC 900s ACTIVE/THINKING，零产物。
- `send-keys` 多行/长中文指令 → CC 队列化，出现 `Press up to edit queued messages`。
- `--effort high/xhigh` 用在实现任务上 → 增加过度思考概率。
- 产物路径未强约束 → capture-pane 只能看到片段，难以判断是否完成。

## 正确诊断顺序

1. **任务是否太大？** 拆成单任务包（≤3 文件/包、≤10 行任务描述）。
2. **输入是否太复杂？** 把上下文写到 `/tmp/task.md`，只发一行：“按 /tmp/task.md 执行。直接动手。”
3. **session 是否干净？** 旧 persisted-output / stale session 先清理。
4. **effort 是否过高？** 实现/文件操作默认 `medium`；审计推理才考虑 high。
5. **是否有明确产物路径？** 要求完整报告或变更说明写到 `/tmp/<name>.md`。

## 稳定调用模板

```bash
cat >/tmp/cc-task-foo.md <<'EOF'
只做 T1：写 file_a.py + tests/test_a.py。
不改其它文件。写完运行 pytest tests/test_a.py -v。
产出报告到 /tmp/cc-output-foo.md。
EOF

tmux new-session -d -s cc-foo -c /path/repo "claude --model claude-opus-4-8 --effort medium"
sleep 5
tmux send-keys -t cc-foo "按 /tmp/cc-task-foo.md 执行。直接动手。" Enter
```

## Codex 的位置

Codex exec 可以作为并行跑腿或兜底执行器，尤其适合机械拆分后的单任务包；但这不是“CC 不可靠”的证据。Hermes 仍需 review diff 和真实测试输出。