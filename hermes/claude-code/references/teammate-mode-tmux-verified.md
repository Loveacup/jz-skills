# --teammate-mode tmux 官方文档验证

> 2026-05-31 公网 grounding 验证。来源：[code.claude.com/docs/en/agent-teams](https://code.claude.com/docs/en/agent-teams)

## 确认项

- `--teammate-mode` 是官方 CLI flag，非第三方 hack
- 支持 `auto` / `in-process` / `tmux` 三种值
- `tmux` = split-pane 模式，每个 teammate 独立窗格
- 也可在 `~/.claude/settings.json` 设 `"teammateMode": "tmux"` 全局生效
- Agent teams 是实验性功能，需 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Split-pane 需要 tmux 或 iTerm2
- 已知限制：session 断连、orphaned tmux session、VS Code/Win Terminal/Ghostty 不支持 split-pane

## 原 SKILL.md 中的措辞

`SKILL.md` § Non-Code Agent Team Reviews 写道：

> 2. 用 CC team/teammate 流程（`--teammate-mode` 或 tmux team workflow）

这个「或」容易引起歧义——让人以为 `--teammate-mode` 和 tmux 是两个独立机制。实际上 `--teammate-mode tmux` 就是正确的组合用法。

## 建议措辞

> 用 CC Agent Team（`--teammate-mode tmux`，官方 split-pane 模式）

## 延伸

上游 Claude Octopus MCP 含 **11 个工具**（非 5 个）：
- 8 工作流：discover / define / develop / deliver / embrace / debate / review / security
- 2 自省：list_skills / status
- 1 IDE：set_editor_context

Hermes 的 MCP bridge 配置仅暴露其中 5 个只读接口（cc / cc_reply / cc_timeline / cc_transcript / cc_report）。
