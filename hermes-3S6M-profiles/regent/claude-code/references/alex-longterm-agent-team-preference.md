# Alex preference: long-lived Claude Code + early agent teams

Session learning captured from a Hermes Telegram workflow.

## User preference

- Default Claude Code orchestration should use a long-lived tmux interactive session, not a fresh `claude -p` process, unless the user explicitly says the task is one-shot.
- When judging whether to use Claude Code's agent team/subagents, err strongly toward using a team: any modest complexity warrants it.
- Do not ask every time. Decide proactively.

## Practical threshold

Use a Claude Code agent team when the task has any of these signals:

- multiple files or directories
- multiple steps: inspect → modify → test → summarize
- uncertain root cause / debugging
- design or implementation tradeoffs
- tests, validation, or reviewer role needed
- codebase orientation before editing
- Hermes/agent workflow changes where separate reader/reviewer/tester roles help

Skip the team only for obviously single-point work:

- read one file or explain one small snippet
- run one command
- change one line/config value
- answer a simple factual question already visible in context

## Tested pattern

Long-lived session name used successfully:

```bash
tmux new-session -d -s hermes-claude-longterm -x 140 -y 40
tmux send-keys -t hermes-claude-longterm 'cd /Users/alexcai/.hermes/hermes-agent && claude' Enter
```

Monitoring:

```bash
tmux capture-pane -t hermes-claude-longterm -p -S -120
```

Agent team connectivity test prompt that worked:

```text
Agent team 连通性测试：请启动/调用两个只读子 agent（如果 Claude Code 支持）：A 只判断当前项目类型，B 只判断测试框架。禁止修改文件、禁止运行会改变状态的命令。最后用中文汇总每个子 agent 的一句话结论。
```

Observed result: Claude Code reported `2 Explore agents finished`, with separate read-only subagents returning project type and test framework findings.

## Pitfalls

- When sending text into the Claude Code TUI via tmux, make sure the prompt is actually submitted. If capture shows the text sitting at the `❯` line with no response, send `Enter` again and recapture. Avoid leaving accidental draft text in the prompt line before reporting completion.
- If the TUI is stuck on a startup/status spinner such as `Discombobulating…` for repeated captures with no tool calls or prompt, interrupt with `Ctrl+C` and rerun the bounded task in `claude -p` print mode. Preserve the same workdir, explicit permissions/read-only constraints, and `--max-turns`; verify the generated output artifact afterwards.
