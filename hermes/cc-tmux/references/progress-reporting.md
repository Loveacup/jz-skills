# Progress Reporting — cc-tmux 中间过程可视化模板

> **何时读取：** in-turn wait / 事件驱动唤醒下，每次读 CC 状态、向用户汇报进度时参考本文。
> **来源：** 搬运并适配自旧 `claude-code` skill 的 `references/progress-reporting-enhanced.md`，
> 适配 cc-tmux 的 6 状态机（SHELL/WAITING_AGENTS/IDLE/TOOL/THINKING/STARTING）、turn-done marker、in-turn wait 三段协议。
> **核心原则：** Telegram 原生格式（无宽表格），emoji 状态映射，渐进式信息密度，**每块必含 Hermes 自主判断**。

---

## 解决的问题

in-turn wait 机制（`cc-wait-marker.sh` + `process(action=wait)`）下，用户反馈真实测试中**看不到中间过程**——只有「开始」和「结束」，缺少：

1. **CC 状态展示** —— CC 现在思考？调工具？走偏？
2. **Hermes 的判断和干预** —— Hermes 据状态做了什么决策。
3. **与 CC 的讨论** —— 发任务前的方案对齐、完成后的产物把关。

→ 每次读 CC 状态都用 📡 块汇报：**结构化总览 + Hermes 自主判断**，而不是一句「CC 在干 X」。

---

## 状态 Emoji 映射（对齐 cc-monitor 6 状态机）

| Emoji | 含义 | cc-monitor 状态 / pane 信号 |
|:--:|------|------|
| ⚡ | CC 工具调用中 | `TOOL` · `⏺/●` |
| 🧠 | CC 思考态 | `THINKING` · `✻/✽/✶/✢/✳` + THINK_TIME 递增 |
| 💤 | CC 空闲 / 可发新指令 | `IDLE` · `❯` 末行为空 |
| ✅ | 完成 | turn-done marker 出现 / 产物已写盘 |
| 🔵 | 进行中 | — |
| 🟡 | 假死（UI 卡但文件已写盘） | `WAITING_AGENTS` + token 冻结但 `ls` 有产出 |
| 🔴 | 真死（无磁盘产出，需接管） | `SHELL` 回落 / 双停 >3min 且产物目录空 |
| 🛡️ | Gate 安全门（正常流程） | cc-finish 7 步门 |
| ❌ | 出错 | pane 出现 `Error/Traceback` |
| ⏳ | 限流 / 等待 | rate limit |

**关键信号识别：** `⏺/●`→调工具 · `❯` 末行为空→空闲/完成 · `✻/✽/✶`→思考态 · `Error/Traceback`→**立即汇报**。

> ⚠️ Pitfall #6 已修但仍有盲区：`cc-monitor` 连报 `IDLE`+`changed=false` 时，用 `tmux capture-pane` 人工确认实况，别误判冻结（屏上有 `✢/✻/⏺` = CC 在工作，monitor 漏检）。

---

## 5 种场景模板

### ⓪ Pre-Send 理解对齐（发任务后、CC 开干前 — 对应三段协议节点①）
```
📡 CC [1min · 距上次 12s] 🧠 已读 context
  🧠 CC 复述理解: 要分析 X 测试覆盖率 + 列遗漏 + 建议补测
  └─ Hermes 判断: 理解到位 ✓ 确认开干 / 或 CC 漏了「保存到文件」→ 先纠正再开干
  📊 Token: 2.1k · 🛡️ Gate: 0 次
```
> ⚠️ 节点① 可操作前提：`cc-send.sh` 只传路径不加工内容，CC 读完默认直接开干。要产生可讨论停顿，context 末尾须含「先复述理解、停下等确认、勿直接执行」（见 `templates/discuss-first-snippet.md`）。

### ① 单任务进度
```
📡 CC [5min · 距上次 22s]
  ⚡ 当前: Write(src/auth/login.ts) — 重构 auth 模块
  ├─ ✅ 已完成: 读完 context + 列出 3 处改点
  └─ 🔵 进行中: 写 login.ts（已 142 行）
  📊 Token: 12.4k · 🛡️ Gate: 0 次
```

### ② 异常 / 假死
```
📡 CC [18min · 距上次 41s] ⚠️
  🟡 假死检测: WAITING_AGENTS + token 2min 不变
  ├─ `ls -la /tmp/cc-output` → 文件已写盘 (2.1KB) → 判定假死非真死
  └─ Hermes 判断: 不 C-c，发 "worker done, continue" 推一把
  📊 Token: 31k · ❌ 0 · 🛡️ Gate: 1 次
```

### ③ 等待中（in-turn wait 超时一轮）
```
📡 CC [9min · 距上次 180s] ⏳
  🧠 当前: THINKING（THINK_TIME 4m13s 仍在递增）→ 非冻结，继续 wait
  └─ Hermes 判断: 方向正常，不干预；本轮 wait 超时 → 再 wait 一轮
  📊 Token: ? (写文件中) · 🛡️ Gate: 0 次
```

### ④ 完成
```
📡 CC [12min] ✅ turn-done
  ✅ 产物: /tmp/cc-coverage.md (86 行) · /tmp/fix.diff (2 处)
  └─ Hermes 判断: 覆盖核心契约，但缺 X 边界 → 拟和 CC 讨论补测
  📊 Token: ~47k · 🛡️ Gate: 1 次
```

---

## 信息密度原则

- **第 1 行**：总览 = `[耗时 · 距上次抓屏 Xs]` + 整体状态标记（⚠️/⏳/✅）。
- **中间 N 行**：树形详情（`├─ └─`），每行一个 emoji + 关键指标（行数 / token / 文件路径+size）。
- **最后 1 行**：`📊 Token: X.Xk · 🛡️ Gate: N 次`（按需加 `❌`/`⏳` 计数）。
- **每块必含 Hermes 自主判断**：不是转述 CC 在干嘛，而是「我据此判断 → 要不要干预 / 下一步」。

---

## 与 in-turn wait 三段协议的对应

| 节点 | 用哪个模板 | 协议要点 |
|------|-----------|----------|
| 发任务前讨论 | ⓪ | send → 等读完 → 抓屏看理解 → 偏了先讨论再开干（context 须含「先复述」约定） |
| 中间状态汇报 | ②/③ | wait 超时不静默 → 抓屏 + 📡 汇报 → 走偏先汇报用户再 `C-c` |
| 完成后讨论 | ④ | turn-done → 读产物 → 先和 CC 讨论 → 带 Hermes 判断汇报 |

详见 SKILL.md `§3 In-Turn Wait` 三段协议 与 Pitfall #21。

---

## 与 Relay Contract 的关系（不冲突）

- `cc-monitor.sh` 的 `===📡 BEGIN (relay verbatim)===` / `===📡 END===` 块 = **机器产出，原样转发**（Relay Contract，不总结不改格式）。
- 本文的手写 📡 块 = **Hermes 读状态后的解读/判断层**。
- 两者分工：机器块给「客观状态」，手写块给「Hermes 的判断与下一步」。一次汇报可以先贴机器块，再补一句手写判断。

---

## 汇报节奏（被动模型下）

| 触发点 | 动作 |
|--------|------|
| 发送任务后首个 wait 周期 | 等 CC 读完 → 抓屏汇报理解（发任务前讨论） |
| 每次 `process(action=wait)` 超时 | 抓屏 + 📡 块汇报，**不静默再 wait** |
| 发现 `Error/Traceback` / 走偏 | 立即汇报（走偏先等用户确认再干预） |
| turn-done marker 出现 | 读产物 → 讨论 → 带判断汇报 |

> 被动模型（v1.9.0+）下 Hermes **无定时轮询义务**，但 in-turn wait 的每个 wait 周期边界 = 天然的汇报节拍点，不要浪费成静默。
