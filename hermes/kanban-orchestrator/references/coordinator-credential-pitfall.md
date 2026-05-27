# Coordinator 子进程凭证隔离陷阱

## 症状
kanban-coordinator-poll.py 的子进程 `hermes -p regent chat ...` 持续 rc=1，
输出 `No Codex credentials stored` 或 `Stripped provider prefix... using for OpenAI Codex`。

## 根因
`-p <profile>` 加载 profile 的 config.yaml 后，其 `model.provider` **覆盖**
命令行 `--provider` 参数。regent profile 使用 `provider: openai-codex`（OAuth），
子进程即使传 `-m kimi-coding/kimi-k2.6 --provider kimi-coding`，
仍被强制走 openai-codex → OAuth token 不可用 → 崩溃。

## 修复
```python
# ❌ 错误：-p regent 覆盖 --provider
cmd = ["hermes", "-p", "regent", "chat", "-q", prompt,
       "-m", "kimi-coding/kimi-k2.6", "--provider", "kimi-coding"]

# ✅ 正确：去掉 -p，显式指定 provider+model
cmd = ["hermes", "chat", "-q", prompt,
       "--provider", "kimi-coding", "-m", "kimi-k2.6",
       "--skills", "kanban-orchestrator,hermes-agent"]
```

注意：
- 该脚本为 `no_agent=true` cron job，cron 的 model/provider 字段不生效
- kimi-k2.6 使用 API key 认证，不依赖 OAuth
- 去掉 `-p regent` 后 skills 需显式 `--skills` 加载
- `--quiet` 不是 hermes chat 的有效 flag，已移除

## 验证
```bash
cd ~/.hermes/profiles/regent
python3 scripts/kanban-coordinator-poll.py
# 有活跃任务 → 正常协调；无活跃任务 → 静默 exit 0
```
