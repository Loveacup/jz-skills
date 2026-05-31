# --teammate-mode tmux：官方文档验证

> 更新：2026-05-31 · 公网 grounding 验证

## 来源

官方文档：https://code.claude.com/docs/en/agent-teams

## 关键事实

- Agent teams 是实验性功能，需设 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 启用
- 两种显示模式：
  - **in-process**：所有 teammate 在主 terminal 运行，Shift+Down 切换
  - **split panes (tmux)**：每个 teammate 独立窗格，需要 tmux 或 iTerm2
- `--teammate-mode <mode>` 是 CLI flag，合法值：`auto`、`in-process`、`tmux`
- 全局配置：`~/.claude/settings.json` 设 `"teammateMode": "tmux"`
- 单 session override：`claude --teammate-mode in-process`
- 已知限制：session 恢复、任务协调、关闭行为
- Split-pane 不支持 VS Code 集成终端、Windows Terminal、Ghostty

## 与 SKILL.md 的关系

SKILL.md 写「`--teammate-mode` 或 tmux team workflow」——这个「或」是措辞歧义，不是 flag 语法错误。`--teammate-mode tmux` 是正确用法。

## CC 审计误报

本 session CC Agent Team 审计对 `--teammate-mode tmux` 标记为 P2「可能是内部 wrapper 参数」——经官方文档交叉验证，**此标记为误报**。今后 CC 审计对 CLI flag 质疑需公网 grounding 复核。
