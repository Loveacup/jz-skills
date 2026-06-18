# memory-hub CQI 审计工作流

> Phase 1.5 完整闭环：CC handoff → mem_ingest → cqi_runtime → mem_merge → Obsidian 88-审计/ → 人工裁决 → 回写 status_event

## 管道全景

```
CC 执行结束 → /tmp/cc-cqi-events-*.jsonl (handoff)
    ↓
Hermes 三步链 (全异步, fail-open):
  1. mem_ingest.py  → 逐行校验 → 三 shard → 删 handoff
  2. cqi_runtime.py → new → acknowledged (幂等)
  3. mem_merge.py   → waterline 去重 → 追加到 88-审计/
    ↓
cron 兜底: 每 30 分钟 cqi_runtime && mem_merge (幂等)
    ↓
人工: 打开 88-审计/memory-hub CQI 持续审计.md
    → 逐条裁决 resolved/wontfix
    → mem_write --type status_event --status resolved --by human ...
    → 下次 mem_merge 自动更新状态
```

## Obsidian 文档映射

| 文档 | 位置 | 性质 | 更新方式 |
|------|------|------|----------|
| CQI 持续审计 | `88-审计/memory-hub CQI 持续审计.md` | 机器自动追加 + 人工裁决 | mem_merge 自动 |
| 首次审计 | `88-审计/memory-hub-v0.2.0-CQI首次审计_20260604.md` | 人工深度分析 | 历史归档 |
| 自动化接入方案 | `02-Plan&CQI/memory-hub-CC-CQI自动化接入方案_20260604.md` | 架构设计文档 | 手动 |
| 审计迭代说明 | `00-Inbox/自动日志-CQI-Skill审计与优化迭代说明_20260604.md` | 操作 SOP | 手动 |

## 裁决命令速查

```bash
cd ~/code/jz-skills/hermes/memory-hub

# 查看待裁决
python3 scripts/mem_read.py --skill X --status acknowledged

# 裁决 resolved
python3 scripts/mem_write.py --type status_event --skill X \
  --source audit --by human \
  --issue-id ISSUE-X-NNN --status resolved \
  --evidence "CQI审计: <理由>"

# 裁决 wontfix
python3 scripts/mem_write.py --type status_event --skill X \
  --source audit --by human \
  --issue-id ISSUE-X-NNN --status wontfix \
  --evidence "CQI审计: <理由>"

# 确认状态
python3 scripts/mem_read.py --skill X
```

## 注意事项

- 首次合并后，mem_merge 的 waterline 定在首次最大 ts，之后只拉增量
- 手动合并进持续审计文档的内容按 ISSUE-* id 去重，不会导致重复
- cqi_runtime 和 mem_merge 幂等，可任意多次运行
- cron 指向部署副本 `~/.hermes/skills/governance/memory-hub/`，与 repo 源共用 reference shard
