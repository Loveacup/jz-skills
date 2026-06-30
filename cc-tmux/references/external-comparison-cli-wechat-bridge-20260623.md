# 外部对比：CLI-WeChat-Bridge → cc-tmux 可迁移项

> 2026-06-23 · 对比对象：`UNLINEARITY/CLI-WeChat-Bridge` v0.9.0 · cc-tmux v1.13.2
> 对比结论：cc-tmux 的 hook 架构更成熟（--settings 注入 + marker 文件 vs TCP server），
> 但 WeChat Bridge 有三项技术值得纳入 cc-tmux 未来版本。

## 架构差异速览

| 维度 | cc-tmux (v1.13.2) | CLI-WeChat-Bridge (v0.9.0) |
|------|:---:|:---:|
| Hook 注入 | `--settings` 会话级 | TCP server + settings.json 写入 |
| 状态感知 | marker 文件 + watcher 探针 | TCP 事件 + PTY stdout 解析 |
| 进程控制 | tmux pane（保留 TUI） | node-pty 子进程（全程序化） |
| 测试覆盖 | 86/86 | 少量单元测试 |

**结论：不搬 PTY/TCP server 方案**——cc-tmux 的 marker 文件模型更简洁，tmux 保留用户可见 TUI 是核心价值。

---

## 可迁移项 ①：Transcript 尾随读取 thinking

**现状**：cc-tmux 靠 `capture-pane` + spinner 解析（✻/✳/✶）感知 thinking，从屏幕抓非结构化数据。

**WeChat Bridge 做法**：每 800ms 轮询 transcript JSONL 文件（路径从 SessionStart hook 的 `transcript_path` 获取），解析新写入的 JSON lines：

```
type: "assistant" → message.content[] → block.type === "thinking" → block.thinking
```

**迁移方案**：
1. SessionStart hook 记录 `transcript_path` 到状态文件
2. cc-watcher 或新增探针定期 `tail` transcript 文件
3. 提取 thinking 文本 → 写入 `/tmp/cc-thinking-<s>` → Hermes 被动读
4. 优势：结构化、准确、不受 TUI 渲染时机影响

**优先级**：中（提升 thinking 感知质量，非硬需求）

---

## 可迁移项 ②：PostCompact 会话恢复

**现状**：cc-tmux 未处理 Claude Code compact 后的 session 状态漂移（旧 transcript 删除、resume conversation ID 失效）。

**WeChat Bridge 做法**：
- SessionStart hook 识别 `source="compact"` + 新旧 `transcript_path` 变化
- 自动更新 `resumeConversationId`、`transcriptPath`
- PostCompact hook 确认 compaction 完成
- 若 resume ID 失效 → 抛 `isClaudeInvalidResumeError` → 自动摘除失效 session → 以新 session 继续

**迁移方案**：
1. `settings.runtime.json` 增加 PostCompact hook
2. SessionStart hook 检测 `source=compact` 时写 `cc-compacted-<s>` 标记
3. cc-finish 检测到 compacted → 更新 resume ID 缓存
4. cc-start 启动前验证 transcript 文件存在性，不存在则走 fresh start

**优先级**：高（防止 compact 后 cc-start --resume 失败）

---

## 可迁移项 ③：Workspace trust 预检

**现状**：cc-tmux 的 Phase 1 处理 Dialog 1（Enter）和 Dialog 2（bypass permissions），但未处理 Claude Code 首次进入目录时的 "Quick safety check: do you trust this folder?" 提示。

**WeChat Bridge 做法**：启动前直接写 `~/.claude.json`：
```json
{
  "projects": {
    "/absolute/path/to/cwd": {
      "hasTrustDialogAccepted": true
    }
  }
}
```

**迁移方案**：
1. cc-start.sh 启动前检查 `~/.claude.json` 中当前 `cwd` 的 `hasTrustDialogAccepted`
2. 若缺失 → 写入（原子 rename，防竞态）
3. 消除一个潜在的 TUI 卡点，无需额外 dialog 步骤

**优先级**：低（首进目录才触发一次，但消除总是好的）
