# Claude Code CLI 安装

> cc-tmux 所有脚本依赖 `claude` 在 PATH 中。本参考覆盖安装和验证。

## 安装

```bash
npm install -g @anthropic-ai/claude-code
```

## 验证

```bash
which claude && claude --version
# 预期: /opt/homebrew/bin/claude (macOS Apple Silicon)
#       2.1.190 (Claude Code) 或更新
```

## 常见问题

### `claude not found in PATH`

- 确认 npm global bin 在 PATH：`npm config get prefix` → 加 `/bin` 到 PATH
- macOS Homebrew 用户通常在 `/opt/homebrew/bin/`
- 如果刚安装，可能需要新开 terminal 或 `hash -r` 刷新 PATH cache

### 版本过旧

```bash
npm update -g @anthropic-ai/claude-code
```

## 前置依赖

- Node.js ≥ 18（cc-tmux v1.x 已验证 Node 24 兼容）
- npm ≥ 9
- tmux（macOS 自带，Linux 需 `apt install tmux`）
