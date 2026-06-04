# Memory-Hub Integration Guide · 记忆回路集成指南

> How to connect any skill to the centralized CQI logging pipeline.
> 把任意技能接入集中式 CQI 日志回路的通用指南。
>
> Pipeline owner: `memory-hub` (Jz-Plugin v4.0, Phase 1.5). Methodology root: this skill (`skill-authoring`).
> 回路内核：`memory-hub`；方法学根基：本技能。

---

## Quick Decision: Mandatory vs Optional · 强制还是可选

| Scope · 范围 | Policy · 策略 |
|:---|:---|
| **skill-authoring 自身的操作** — 每个经本技能创作/审计/演进的技能 | 🔴 **Mandatory.** CC 会话结束必须吐 handoff，Hermes 三步链自动归集。 |
| **其他任意技能** | 🟡 **Optional — ask the user FIRST.** 未经明确许可，**绝不**给别的技能装这条管道。 |

**Ask-user-first protocol · 先问用户协议**：在为非 skill-authoring 的技能接入前，明确询问「是否要把 `<skill>` 接入 memory-hub CQI 日志回路？」，得到肯定答复才动手。理由：管道会改变该技能的会话收尾行为，属于跨技能副作用。

---

## 接入步骤 · How to Wire

技术细节（handoff 格式、字段、事件类型、Hermes 三步链）都由 **memory-hub 自己**维护，本文不再复制——以那边为唯一真相源：

1. **先加载 memory-hub skill**：`skill_view("memory-hub")`，其「§接入协议」有完整 handoff 格式 + Hermes 链说明。
2. 按 memory-hub 的「接入清单」逐项执行。
3. 完成后在该技能 CHANGELOG 记一条「接入 memory-hub CQI 回路」。

> ⚠️ CC 只产出 handoff 文件（`/tmp/cc-cqi-events-<session>.jsonl`），**永不**写 `status`、**不**直接调 memory-hub 脚本——校验、批量写入、provenance 全由 Hermes 侧 `mem_ingest.py` 经单写入口完成。

---

## Template: Wiring Checklist · 接入清单模板

把某技能接入 memory-hub 时逐项过：

- [ ] **若非 skill-authoring 自身** → 先问用户，得到明确许可。
- [ ] 加载 memory-hub，照其「§接入协议」执行（不要在本技能里重抄格式）。
- [ ] 在该技能 SKILL.md 加一节「CC 会话结束写 handoff」，内容引用 memory-hub 协议。
- [ ] 明确 CC 只吐 `issue`/`evolution`，**不写 status**。
- [ ] 列出该技能 issue 的常见 `implicated_rule` 取值（指向真实规则 id）。
- [ ] 确认 Hermes 侧三步链已挂上 CC session-end 触发；cron 兜底已配。
- [ ] 在该技能 CHANGELOG 记一条「接入 memory-hub CQI 回路」。

---

## Reference: Cron Fallback · cron 兜底

session-end 触发可能漏（CC 异常退出、检测抖动）。memory-hub 另设每 30 分钟 cron 兜底，仅跑后两步（两者幂等）：

```bash
*/30 * * * * cd ~/.hermes/skills/governance/memory-hub && \
  python3 scripts/cqi_runtime.py --quiet && python3 scripts/mem_merge.py --quiet
```

`--quiet`：空闲（无新 issue / 无可合并）时静默，不刷日志。

真相源永远是 memory-hub 的 `references/*.jsonl`（append-only）；Obsidian 审计文档、SQLite、qmd 等都只是派生索引，不可反向当真相。

---

## See Also · 参见

- `memory-hub` SKILL.md「§接入协议」— 完整 handoff 格式、Hermes 三步链、接入清单（**唯一真相源**）。
- `memory-hub` SKILL.md「§Schema 速览」— 字段硬/软校验、单写入口、Git 同步回路。
- `references/log-driven-cqi-mvp.md` — 为什么 Phase 1 必须 log-driven、手动闸门。
- `references/structured-cqi-log-memory.md` — append-only JSONL 作为真相源、派生索引的边界。
