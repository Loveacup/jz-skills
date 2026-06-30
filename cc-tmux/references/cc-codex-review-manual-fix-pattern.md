# CC + Codex 审核 NEEDS_FIX → 手动修复决策模式

## 场景

Codex 独立审核 CC 产出后返回 **NEEDS_FIX**，但重启 CC 修复可能：
- 再次冻结（xhigh/high effort + 长思考）
- 引入新问题（每轮修复可能产生新 bug）
- 消耗额外 token/时间

## 决策树

```
Codex NEEDS_FIX
├── 问题定位精确？（具体文件 + 行号 + 修复方案明确）
│   ├── 是 → 评估修复大小
│   │   ├── < 10 行、纯逻辑调整（如 try-catch 包裹、条件分支）
│   │   │   └── ✅ 手动 patch（Hermes 直接改）
│   │   │       优势：避免 CC 冻结风险、避免新引入问题、快
│   │   │       验证：改后跑测试确认通过
│   │   └── >= 10 行或涉及架构调整
│   │       └── 评估是否可拆小
│   │           ├── 可拆 → 手动 patch 核心部分，剩余开新 CC session（窄范围）
│   │           └── 不可拆 → 开新 CC session（新上下文，避免旧 session 累积）
│   └── 否（模糊描述、无具体行号）
│       └── ❌ 不能让 CC 盲修 → 要求 Codex 补充定位 → 或 Hermes 先读代码理解
│
└── 已达轮次上限？（>3 轮 CC 修复 / >2 次拒绝）
    ├── 是 → 停止自动循环，升级用户
    └── 否 → 按上评估
```

## 本次实例（Phase 8 Slice 3，2026-06-28）

**Codex 发现 2 个问题**：
1. `session.js` orphan 逻辑：CC 实现为 TTL-based，但 Spec 要求 heartbeat-based（`last_seen_at + orphanMs`）
2. `remote.js` deps 解构：未 try-catch 包裹，throwing getter 会穿透

**决策**：手动修复（均 < 10 行、定位精确）

**修复过程**：
1. `session.js`：加 `DEFAULT_ORPHAN_MS` 常量 → `createSessionStore` 加 `orphanMs` 参数 → `effectiveState` 改签名 `(rec, t, orphanMs)` → 调用点全部更新 → `cleanup` 改逻辑
2. `remote.js`：三处 `const { sessions } = d` 改为 `let sessions; try { ... } catch { return fail(...) }`

**验证**：119/119 ssh-worker pass，432/432 全量 pass

**优势**：避免 CC 再次冻结（本次 CC 已 13m57s 思考后卡住），节省 token，无新引入问题

## 反模式

❌ **"CC 修吧，我等着"** — 如果 CC 已显示冻结倾向（长思考无输出、token 不动），继续等 = 浪费
❌ **"我手动修，但不跑测试"** — 手动修复必须跑测试验证，不能凭直觉
❌ **"问题小，直接改，不记文档"** — 即使手动修复，也要在 commit message / OB 文档中记录 "Codex NEEDS_FIX → 手动修复"

## 与 Pitfall #37 的关系

Pitfall #37（Codex 审核轮次耗尽）是**上限规则**——>3 轮 / >2 次拒绝必须停。
本模式是**上限内的决策**——未达上限时，评估是否手动修复而非自动循环。
两者互补：先按本模式评估，若决定 CC 修复但再次 NEEDS_FIX → 累加计数器 → 达上限 → 停。
