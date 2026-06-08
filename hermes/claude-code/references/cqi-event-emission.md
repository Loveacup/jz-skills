# §CQI 事件吐出（memory-hub 接入）— 完整规格

> 从 `SKILL.md ## §CQI 事件吐出` 下沉（v4.1.2 slim）。SKILL.md 只保留 type 铁律 + 本文件指针。

> CC 每轮任务结束时，把本轮发现的 **issue / evolution** 以 JSONL 追加写到 handoff 文件
> `/tmp/cc-cqi-events-<session>.jsonl`（`<session>` = 当前 CC session 名）。一行一条 JSON。
> 这是 fail-open 的旁路：写不写都不影响主任务交付，但写了能让 memory-hub 自动归集。

- **字段（对齐 live 6 硬字段 + payload）**：`type`（**只能 `issue` 或 `evolution`，禁自由发挥**）、`skill`（受影响技能名）、
  `source`（恒为 `"cc"`）、`evidence`（原话/trace 逐字，勿摘要）、`ts`（ISO-8601 带时区）；
  `id` 可省（归集时自动生成 `ISSUE-/EVO-<skill>-NNN`）。`payload` 可选：issue 填 `implicated_rule`/`change_type`；
  evolution 必填 `change_type`，可带 `validation_score`/`changelog_ref`。`session_id` 建议带上。
- **🔴 type 枚举强制映射（v4.1.2）** ：`type` 只有两个合法值——`issue` 和 `evolution`。**禁止**使用 `audit`/`fix`/`writeback`/`constraint`/`improvement` 或任何其他自造词。如果不确定用哪个，按下表映射：

  | 你想表达的含义 | 正确 type | 说明 |
  |:---|:---|:---|
  | 审计发现缺陷/规则未遵守 | `issue` | 发现问题是 issue，不是 audit |
  | 本轮做了修复/改进 | `evolution` | 实际改动是 evolution，不是 fix |
  | 回写了文件/内容 | `evolution` | writeback 是 evolution 的子类 |
  | 识别了新约束/前置条件 | `issue` | 约束发现是 issue |
  | 状态变更 | ✅ 不写 type | 状态机由 memory-hub 维护，CC 只吐事件 |

  **铁律**：`type` 只取 `issue` 或 `evolution`。写错 = memory-hub mem_ingest.py 校验拒收（degrade），事件永久丢失。
- **CC 自判事件类型**：
  - `issue` —— 发现某技能的规则缺陷 / 指令未遵循 / 反复踩同一坑（trigger 多为 `runtime_failure` 或 `user_correction`）。
  - `evolution` —— 本轮实际改进了某技能正文/脚本/版本（trigger 多为 `manual_review`，带 `change_type`）。
- **状态语义**：CC 只吐 `issue`/`evolution` 原始事件，**不写 status**；状态机（new→acknowledged…）由 memory-hub 侧 `cqi_runtime.py` 维护。
- **Hermes 侧触发（三步链，全异步 + fail-open）**：Hermes 检测到 CC session 结束（`❯` 提示符且无 `●` 持续 >2min，复用 Session GC 判据）时，
  在 `memory-hub/` 下依次调用，**任一步失败不阻断后续，也不阻断 Hermes 主任务**：
  1. `scripts/mem_ingest.py` —— 归集该 handoff 文件 → 校验 → 批量写入 shard → 删 handoff。
  2. `scripts/cqi_runtime.py` —— 拉本期 new issue，自动追加 status_event（new→acknowledged，by=cqi-auto）；幂等。
  3. `scripts/mem_merge.py` —— 将新 issue 合并进 Obsidian CQI 审计文档（waterline 去重，只追加）；幂等。
- **cron 兜底**：上述链以 CC session 结束为触发；另有每 30 分钟的 cron 跑 `cqi_runtime.py && mem_merge.py`，
  捕获漏触发的批次。两脚本均幂等（无 new issue 直接跳过、waterline 去重），重复跑无副作用。
