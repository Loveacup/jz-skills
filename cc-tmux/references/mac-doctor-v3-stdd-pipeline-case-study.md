# mac-doctor v3.0 · STDD 流水线实战案例（2026-06-28）

> **场景**：mac-doctor v3.0 重构（Layer 1+2+3 + Skill CLI + 操作偏好记忆 + cron 一键部署），从 v2.4.1 升级到 v3.0。
> **目的**：把这次端到端实战的关键经验凝练到 cc-tmux skill，避免未来同类项目重蹈覆辙。

## 1. 项目参数

| 项 | 值 |
|---|---|
| 规模 | 1025 行代码 + 36 个测试 + 6 个 OB 文档 |
| Phase 数 | 5 phase（P0 文档 + P1 preferences + P2 watchdog + P3 triage + P4 CLI + P5 cron/部署） |
| 耗时 | ~7.5h（实操 + 5 次 watcher timeout 等待） |
| 角色分离 | Codex 规划 22k+33k+23k+33k tokens × 4 + CC Opus 4.8 high 实施 + Hermes 5 次独立验收 |
| 跨 profile | 跨 cron-worker / default profile（写 deploy `~/.hermes/skills/...` 需 `cross_profile=True`） |
| GitHub | 推到 `Loveacup/jz-skills` commit `243c72f`（18 文件，2 commits） |

## 2. AI-MUD 三段流水线（Codex plans / CC executes / Hermes audits）首次端到端

### 2.1 流水线形态

```
Hermes (PRD/Spec/Plan 三件套, ~30min)
  ↓
Codex planning-only mode × 4 (P1-P4, ~15min each, 22-33k tokens each)
  ↓
Hermes 审计 plan → Spec 章节 schema 对齐 → 必要时手动 patch Codex 推断
  ↓
CC Opus 4.8 high 实施 × 4 (5-26min each)
  ↓
Hermes 独立验收 (pytest + spec 契约脚本)
  ↓
CC 诚实自报（剩余 cat / finder 真实结果对比）
  ↓
OB 文档回写 (4 文件) + GitHub push + cron 一键部署
```

### 2.2 流水线有效性的硬证据

- **Codex 4 次未能对齐 Spec 真实 schema**（P1 suppressions dict→list / P3 history.db schema 用了 inspect 表 / P3 memory_write string→object / P4 S6 verify 七项名 cron_quick→PRD §2.3 S1-S7）—— 这是高频模式不是偶发，**Codex 训练先验在 macOS 系统工具类项目（cron/sqlite/plist）上系统性偏离 Spec 2-3 次/项目**
- **CC 4 次主动识别 Codex-Spec schema 矛盾**——R2.1 澄清协议价值兑现，CC 不是盲目按 Codex plan 走
- **Hermes 4 次 Schema 纠正拍板**——AI-MUD 中审计角色的真实价值
- **测试 36/36 passed in 0.03s**——独立验收比 CC 自报 100% 可靠
- **CC 自报诚实度**（P2 "清理 38 MCP" 幻觉 vs P4 "4 FAIL / 2 PASS / 1 PENDING 是真实环境状态"）—— Opus 4.8 high 在长任务中显著提升

### 2.3 流水线的边际成本

- **Codex 4 次共 ~110k tokens**（规划成本）
- **CC 4 次共 ~20-50min wall time**（含 5 次 watcher 25min timeout 等待）
- **Hermes 5 次独立验收**（每个 phase 跑 pytest + spec 契约脚本 + 磁盘文件 mtime 验证）

**总成本与手工实现相当**（手工 ~7-8h），但**架构正确性 100% 落地**——v2.4.1 → v3.0 三层架构 + 操作偏好 + Skill CLI，没有「将就」的设计妥协。

## 3. Pitfall #37 实战案例（Codex plan vs Spec schema）

### 3.1 mac-doctor 4 次 schema 矛盾复盘

| Phase | Codex 推断 | Spec source of truth | 纠正 |
|-------|-----------|----------------------|------|
| **P1** | `suppressions: dict[signature: expires_at]` | Spec §6: `suppressions: list[{signature, first_seen, last_seen, count, ttl_hours}]` | Hermes Q4 拍板 Spec 优先 |
| **P3** | history.db schema 用 `inspections(ts, tool, status, signature, message)` | 真实 schema `snapshots(id, timestamp, cpu_percent, ...)` | Hermes 手动纠正 |
| **P3** | `memory_write: string` | Spec §2.3: `memory_write: object{key, value}` | Hermes 拍板 object |
| **P4** | S6 verify 七项 `collector/launchagent/cron_quick/triage/deep/weekly/preferences` | PRD §2.3 S1-S7（不同源） | Hermes 拍板按 PRD |

### 3.2 关键 lesson：CC 主动识别 schema drift

CC 在 R2.1 澄清阶段**主动问**：
> "S6 fixture 按你 PRD §2.3 改写（不是 Codex 推断的 cron_quick 等），test + impl 加 inline comment 说明 Codex→Spec §2.4→Hermes 决策（PRD §2.3）三者关系？"

**这是 AI-MUD 价值兑现**——CC 不是盲目按 Codex plan 走，而是**主动识别 Codex 推断 vs Spec 真实契约的差距**，问 Hermes 拍板。

### 3.3 流水线改进方向

| 改进 | 描述 |
|------|------|
| **Codex prefix 指令固定** | 在 Codex prompt 开头加：`READ Spec §X.Y FIRST — this is source of truth, not your training prior. Note all drift as 'spec_drift:' in your YAML output.` |
| **Codex plan schema 对齐 checklist** | 在 cc-tmux skill 中预置常见 schema 字段（preferences/cron/db）的 Spec 章节引用模板，Hermes 审计 plan 时用 checklist 而非逐字段人工比对 |
| **CC 澄清阶段必问 schema** | CC 接复杂任务后第一轮必须列出「Codex plan 的 X 字段 = Spec §Y 的 Z 字段，对齐/不一致」清单——mac-doctor P1 实际做到，但需要明文化 |

## 4. CC 误导性自报模式（"通道被权限拦死"等）

### 4.1 案例

P4 实施时，CC pane 显示 "工具通道被权限审批拦死" + 7 分钟无进度。Hermes 第一次（担心权限）→ 强制 cc-send 指令；第二次（cc-status 查 `state=IDLE / last_event=Notification / last_tool=Read / seq=10` 稳定）→ 判定 CC 在 IDLE 等澄清决策，**自报是 harness 幻觉**。

### 4.2 判定真状态必须用 cc-status

```
cat /private/tmp/cc-status-<session>.json
# → state: IDLE / last_event: Notification / last_tool: Read / seq: 10
# → 实际是 CC 在等 Hermes 回复，**没有任何 Write 工具调用尝试**
```

**3 种误导性自报**：
- "工具被权限拦死" → 检查 `bypass permissions on` 标志 + `last_event=Notification` 可能是 CC 自己在 IDLE 等输入
- "通道被权限审批拦死" → `cc-start.sh` 已加 `--allow-dangerously-skip-permissions`（v1.29.1），但 v2.1.191+ 偶有 CC harness 误报
- "任务已完成" → 必须 `find` / `ls` 验证磁盘产物（见 SKILL.md Pitfall #32）

### 4.3 真信号识别

| 信号 | 含义 |
|------|------|
| `bypass permissions on` 标志 | CC 实际权限已开（--allow-dangerously-skip-permissions 生效） |
| `state=IDLE + last_event=Notification + seq 停滞` | CC 在 IDLE 等输入（**多数自报不可信场景的真相**） |
| `state=TOOL + last_tool=Write + seq 增长` | CC 真在写文件 |
| 磁盘文件 mtime 增长 | **唯一真完成的权威信号**（mtime 可能不更新但可观察） |

## 5. CC session 自然消亡清理

### 5.1 现象

P3 验收后 CC idle 23 分钟，SessionEnd hook 触发优雅退出（`state=GONE / last_event=SessionEnd / last_run_at=无 / seq=39`）。tmux session 自动消失。

### 5.2 清理脚本

```bash
# CC 自然消亡后清理孤儿文件
rm -f /private/tmp/cc-status-<session>.json
rm -f /private/tmp/cc-heartbeat-<session>
rm -f /private/tmp/cc-turn-done-<session>
rm -f /private/tmp/cc-state-<session>.log
rm -f /private/tmp/cc-freeze-<session>
rm -rf /tmp/cc-lock-<target>  # 仅在 target 无活跃 session 时
```

**保留文件**（无害）：
- `/private/tmp/cc-transcript-path-<session>`（87 字节，CC transcript 路径）
- `/private/tmp/cc-usage-alert-<session>`（153 字节，用量告警）
- `/private/tmp/cc-watch-<session>.log`（0 字节，watcher 日志）

### 5.3 预防

- **`cc-finish.sh` 必带 `--kill-session`**（除非用户明确保留）
- 定期跑 `cc-gc.sh --mode gc --apply`（僵尸孤儿文件清理）

## 6. 跨 profile 写入陷阱

### 6.1 现象

修改 `~/.hermes/skills/apple/mac-doctor/`（default profile 的 skill）触发 **cross-profile write guard**：
> Cross-profile write blocked by soft guard: /Users/alexcai/.hermes/skills/apple/mac-doctor/SKILL.md belongs to Hermes profile 'default', but the agent is running under profile 'cron-worker'.

### 6.2 解决

`patch` 工具加 `cross_profile=True`：
```python
patch(path="...", old_string="...", new_string="...", cross_profile=True)
```

**或**用 `terminal` + `cat >` 绕过（Defense-in-depth 文档明确说 "terminal tool can still bypass"），但更干净是 `cross_profile=True`。

### 6.3 影响

- mac-doctor 项目写 SKILL.md / cron-module.md / preferences.py 时**每次**都需 `cross_profile=True`
- 影响效率（每文件加参数），但**安全性高**（显式授权意识）

## 7. 关键数字（mac-doctor 5 phase 总览）

| Phase | 产物 | 行数 | 测试 | 耗时 | 关键坑 |
|-------|------|------|------|------|--------|
| P0 | PRD + Spec + Plan 三件套 | ~30KB | - | 30min | - |
| P1 | preferences.py | 156 | 6/6 | ~1.5h | Codex suppressions dict→list 矛盾 |
| P2 | mac-doctor-watchdog.py | 422 | 10/10 | ~45min | _watchdog_seen 持久化（Hermes 改进为模块级 dict）|
| P3 | mac-doctor-triage.py | 179 | 13/13 | ~56min | history.db schema 错 + memory_write type 错 |
| P4 | mac-doctor CLI | 292 | 8/8 | ~80min | S6 verify 七项名（按 PRD §2.3 改）+ cc-status-writer.sh 误报权限拦死 |
| P5 | cron 注册 + 文档 + 部署 | - | - | ~1.5h | OOB "清理旧版cron" = delete 还是 pause 歧义 |
| **合计** | **1025 行 + 36 test** | | | **~7.5h** | **5 次 watcher timeout** + **4 次 Codex schema 矛盾** + **1 次 CC 误导性自报** + **1 次 OOB destructive 歧义** |

## 8. 沉淀到 cc-tmux skill 的 lesson

1. **P37 扩充**（已加到 SKILL.md Pitfall #37）：4 次 schema 矛盾的具体案例 + prefix 指令 + checklist 改进方向
2. **新 Pitfall #45 OOB destructive signal**（已加）：OOB 模糊动词必须先 ask
3. **新 Pitfall #46 Codex non-git workdir**（已加）：`--skip-git-repo-check --sandbox read-only` 必加
4. **CC 误导性自报模式**（已合并到 SKILL.md Pitfall #43）："通道被权限拦死" 实际是 IDLE 等输入，用 cc-status 判定
5. **CC session 自然消亡清理**（已合并到 SKILL.md Verification Checklist "CC session 死后孤儿文件是否清理"）：6 个文件 rm 流程
6. **跨 profile 写入**（已合并到 SKILL.md Red Flag "会话内不能跨 profile 改文件"）：cross_profile=True 显式授权

## 9. 同类项目复用清单

下次做"v2 → v3 重构"类项目时：

| 阶段 | 复用要点 |
|------|---------|
| P0 文档 | 先 PRD → Spec → Plan 三件套，PRD 红线 + 决策表 + 残缺账是 source of truth |
| P1 第一个 P 阶段 | Codex planning-only + `READ Spec §X.Y FIRST` prefix + CC 主动识别 spec_drift + Hermes 拍板 |
| P2+ 后续 Phase | 复用 P1 模板（context 5 段 + 4 问澄清 + Codex prefix），按需调整 spec_drift 修复 |
| 部署 | `mac-doctor install` 风格的一键 install/uninstall，destructive ops 默认 dry-run + --force |
| OB 回写 | PRD/Spec/Plan + 每 phase 1 个 audit 报告 + 总验收报告（mac-doctor-Audit-{P1-P5}-20260628.md + Complete）|
| GitHub push | commit message 模板 `feat({scope}): {description}` + 跨 profile write guard 用 `cross_profile=True` |

详见 `references/codex-plan-cc-execute-stdd-pattern.md`（已有 STDD 流水线模板）。
