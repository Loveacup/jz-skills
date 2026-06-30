# OOB 消息安全协议 · destructive 操作确认

> **场景**：CC 任务执行中，Hermes 收到用户 OOB（out-of-band）消息，可能是简短指令如「清理旧版cron」「重置状态」「对齐一下」。
> **风险**：OOB 字面意思与用户意图可能不一致——`清理/重置/对齐/同步/恢复` 等词在不同语境下意思不同。**destructive 操作的特征**：不可逆（无 undo）/影响范围大/可能触发级联。
> **目的**：把"OOB 模糊动词 → destructive 操作确认"这个高频陷阱固化为协议。

## 1. mac-doctor 对齐清理案例（2026-06-28 实发）

### 1.1 时序

```
T1: 用户 OOB: "清理旧版cron"
T2: Hermes 推断 = "pause"（保守/可恢复/符合 destructive 红线）
T3: Hermes 调 cronjob pause × 3
T4: 用户 OOB: "清理旧版cron" 二次确认 + 列出 4 个 choices
T5: 用户选 choice 1 = "只删除旧版mac-doctor 3 个"
T6: Hermes 调 cronjob remove × 3
T7: 最终状态 = 12 个 cron（3 旧 mac-doctor 删除 + 4 新 mac-doctor v3.0 + 8 非 mac-doctor）
```

**问题**：T2 → T3 多了一次 pause → remove 状态转换（如果用户没二次确认，T3 之后就停在 paused 状态）

### 1.2 教训

- **第一次 OOB 不应直接推断**——`清理/重置/对齐/同步/恢复` 等模糊动词在 destructive 语境下最危险
- **destructive 操作必须 ask 用户 3+ 选 1**（暂停/删除/保留）
- **保留当前状态是合法选项**（用户可能没意识到已经在跑什么）

## 2. 通用 ask pattern

### 2.1 触发条件

OOB 消息包含以下任一关键词：

| 关键词类别 | 例子 |
|-----------|------|
| 清理 / 清空 | "清理 cron", "清空缓存", "清掉旧的" |
| 重置 / 重启 | "重置状态", "重启一下", "刷新配置" |
| 对齐 / 同步 | "对齐一下", "同步过去", "匹配 cron list" |
| 恢复 / 修复 | "恢复默认", "修复一下", "回到之前" |
| 删除 / 移除 | "删掉", "移除", "kill" |
| 强制 / 覆盖 | "强制执行", "覆盖", "force" |

### 2.2 ask 模板（用 `clarify` 工具）

```python
clarify(
    question="OOB「[用户原话]」涉及 destructive 操作,如何执行?",
    choices=[
        "A. [只动指定子集] + 可恢复（推荐）",
        "B. 全部动 + 不可逆 destructive",
        "C. 保留当前状态不变（不动）",
        "D. 干运行（只展示影响,不实际改）",
    ],
)
```

### 2.3 mac-doctor 案例 ask 实际输出

```
❯ OOB「清理旧版cron」涉及 destructive 操作,如何执行?

  1. 只删除旧版mac-doctor 3 个（quick/deep/weekly 旧 v2.4.1/v2.5）。
     保留其他 11 个 cron 不动。安全（只动 mac-doctor）。 ← 用户选
  2. 只删除旧版mac-doctor 3 个,同时把项目归档的其他「完整」表
     (Plan/Verify/Complete) 保留。
  3. 删除全部 15 个 cron（重新注册需要的）—— 不推荐,破坏太大。
  4. 不删,只保持 pause（当前状态,与我刚才误读"清理"=pause不同）。
```

**用户选 1** → Hermes 调 3 次 cronjob remove。

## 3. 3 档可逆性分类

### 3.1 Pause / Soft Delete（可逆）

- **操作**：`pause` / `disable` / `disable-but-keep-config`
- **可逆**：✅ 调 `resume` / `enable` 恢复
- **数据丢失**：❌ 不丢数据
- **影响**：scope 内的对象停止行为
- **适用**：临时下线、调试、A/B test

### 3.2 Remove / Hard Delete（不可逆）

- **操作**：`remove` / `delete` / `rm -rf`
- **可逆**：❌ 不能 undo（除非有 backup）
- **数据丢失**：✅ 元数据 + 配置 + 历史
- **影响**：scope 内的对象消失
- **适用**：清理、归档、迁移

### 3.3 Force Override（不可逆 + 危险）

- **操作**：`--force` / `force=true` / 跳过确认 gate
- **可逆**：❌ 不可逆 + 跳过安全门
- **数据丢失**：✅ + 可能绕过审计
- **影响**：scope 内的对象被强制覆盖
- **适用**：紧急修复、生产事故恢复（**需 Alex 显式授权**）

## 4. OOB destructive ask 的 4 步法

### 4.1 步骤 1：识别 destructive 信号

OOB 消息命中 §2.1 关键词 → 触发 ask

### 4.2 步骤 2：限定 scope

不要让 OOB 触发无限连带操作。明确 scope：
- "哪个子集?"（如 mac-doctor 旧 vs 全部 cron）
- "影响范围?"（如 1 个对象 vs 全部）
- "是否级联?"（如删 cron 会触发依赖它的 trigger）

### 4.3 步骤 3：4-choice ask

按 §2.2 模板给 4 个 choices。**第 3 个必须是「保留现状」**——保护用户反悔。

### 4.4 步骤 4：执行 + 汇报

执行用户选的 choice + 立即跑 `cronjob list` / `find` 验证 + 用 📡 块汇报。

## 5. 反模式（不要做）

### 5.1 反模式 1：OOB 推断为「保守」操作

```
用户 OOB: "清理 cron"
Hermes: pause 3 个（推断"清理"="暂停"）
```

**错误**：pause ≠ 清理。destructive 上下文下 "清理" 几乎总是 "delete"。

### 5.2 反模式 2：OOB 推断为「激进」操作

```
用户 OOB: "清理 cron"
Hermes: 全部 15 个 remove（推断"清理"="全删"）
```

**错误**：scope 没限定就 destructive，破坏远超用户意图。

### 5.3 反模式 3：直接执行不 ask

```
用户 OOB: "清理 cron"
Hermes: 调 cronjob remove × 3
```

**错误**：任何 destructive 操作都该 ask。

### 5.4 反模式 4：ask 后跳过 verify

```
用户选 choice 1 → Hermes: 执行 → 不验证 → 不汇报
```

**错误**：destructive 操作后必须跑客观验证（`cronjob list` / `find`） + 📡 块汇报。

## 6. 沉淀到 SKILL.md

- Pitfall #45 OOB destructive signal（已在 v1.32+ 加入）
- Verification Checklist 增项"destructive 操作前用 clarify ask + verify 后跑客观命令"
- Red Flag 新增"OOB 模糊动词（清理/重置/对齐/同步/恢复/删除/强制）→ 立即触发 ask"

## 7. 关联 Pitfall

- **Pitfall #22 残留清不掉**：`cc-finish.sh` exit 2 + `--force` 不能覆盖残留 gate——destructive (--kill-session) + 残留保护是双层防御
- **Pitfall #31 send-keys 绕过**：`tmux send-keys` Enter 未生效——OOB 消息送达也是 send-keys，OOB 时同样要走 cc-send.sh
- **Pitfall #45 OOB destructive**（本次新加）：本文主

详见 SKILL.md ⚠️ Pitfalls 段。
