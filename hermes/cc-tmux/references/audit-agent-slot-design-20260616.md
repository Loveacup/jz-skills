# 审核 Agent 槽位：统一设计（2026-06-16 四轮 CC 迭代终稿）

> 来源：hermes-deck Primer 研究 → 三向交叉评判 → 三裁决 → 终稿制品

## 核心设计

**审核 = 一个带 `independence_level` 字段的槽位契约，不是一个 agent。**

```
audit(artifact, criterion, threshold, context, independence_level) → Verdict
  Verdict { severity: pass|nit|concern|blocker, evidence[], 退回指令? }
```

## 独立性四档 L0-L3

- **L0 禁用** — 同上下文自审（信息量为零）
- **L1 当前默认** — 切 auditor 身份自审，同 session。靠证据替换 + 脚本接管客观半压住独立性损失
- **L2 干净 session** — 开新对话审，设计上下文物理不在窗口
- **L3 独立 agent** — 独立 profile/进程，从未接触设计

## 审核劈客观/主观两半（整套设计的承重墙）

- **客观半 → 硬脚本 gate（不可绕）**：命令跑过/退出码/产物存在/危险拦截
- **主观半 → agent 审（L1 起步）**：只剩低后果的架构/品味判断

这是 L1 自审在只有两个 agent 时够用的根本理由。

## 审计四步机械过程（L1-L3 同一套，差在第①步强度）

1. 封掉自报证据（pass/fail 必指向此刻新取的证据）
2. 客观半重跑（gate 脚本现在重新执行，不信历史）
3. 对 criterion 审、不对意图审
4. 产出结构化 Verdict（每条挂新证据指针）

## 风险→门控→独立性对齐表

| 风险 | 委派门控 | 独立性档 |
|------|---------|---------|
| 只读（分析/设计） | 自动，异步报 | L1 |
| 写入（改代码/跑命令） | 先确认 | L1→L2 |
| 危险（删除/发布/core配置） | 永久人工 | L2/L3+人工红线 |

## severity 四级（nit 不计数防吹毛求疵）

pass / nit（非阻断，不计） / concern（阻断，+1） / blocker（强阻断，+1）

退回累计 2 次 → 停自动退回，升级人工。

## 三裁决

1. **通用化**：删 regent，只命名 delegator/auditor 两个角色
2. **切 auditor 身份** = 证据替换 + 上下文裁剪（四步过程），不是心态
3. **脚本落点**：gate 放 cc-tmux/scripts/gate/ 独立子目录，头注"零 tmux 耦合·遇第 2 消费者即提升独立 skill"

## 规则三层落点

| 层 | 判据 | 内容 |
|----|------|------|
| SOUL.md | 判断：低频、稳定、需理解 | 委派三级门控·审核独立性·客观主观分治·终止数字（3/2）·沉默不是通过 |
| cc-tmux SKILL.md | 流程：会迭代、需细节 | 委派包格式·criterion模板·severity细则·四步checklist·gate调用关系 |
| scripts/gate/ | 红线：agent可能绕过+后果不可逆 | gate-verify/gate-danger/gate-counter |
