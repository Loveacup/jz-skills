# Effort Routing — Claude Code 智能 Effort 路由完整体系

> SKILL.md 主体只保留「地板 = high + 一句话路由 + 启动即定档」。本文件是完整体系：五级表、智能路由三档表、自检决策树、实战配置、成本换算、`/effort` 会话内切换陷阱。
>
> **v2.1.158 起可用。** Opus 4.8 默认 effort = `high`，支持五级思维链。

## 启动时指定

```bash
claude --model claude-opus-4-8 --effort max   # 完整模型名 + 最强推理
claude --model opus --effort xhigh             # 别名 + 高推理
claude --effort low                            # 轻量任务，省钱
```

## 五级 effort

| Level | CLI flag | 说明 |
|-------|----------|------|
| `low` | `--effort low` | 最少思考，适合简单翻译/格式转换 |
| `medium` | `--effort medium` | 中等 |
| `high` | `--effort high` | **Opus 4.8 默认** |
| `xhigh` | `--effort xhigh` | 更深推理，仅次 max（Opus 4.8/4.7 专属） |
| `max` | `--effort max` | 最强推理，Cogitated 时间最长 🧠 |

## 会话内切换：`/effort`

```
/effort xhigh
```

> ⚠️ 弹出确认对话框（默认是 "No, go back" → **选 1**）。切换会清除当前 cache，history 全部重读——长会话中慎用。确认后状态栏显示 `◉ xhigh`。

## 🧭 智能 Effort 路由（按任务信号选档）

> **🔒 默认地板 = `high`。** 除非用户明确说 "fast / cheap / quick / 快一点 / 省钱"，**永远不要低于 `high`**。没有信号 = 从 `high` 起步，按任务复杂度往上抬，**绝不往下降**。地板就是地板，不要因为"这任务看起来简单"就自作主张降到 `medium`——简单也得 `high`，除非用户开口要快。

调 CC 前先选档，不要默认全用 `high` 凑合：`high` 是地板不是天花板。多文件、审查、设计、根因——这些信号一出现，**必须**往上抬到 `xhigh` 或 `max`。该抬不抬 = 推理深度不够 = 返工。

### 三档路由表

| 任务信号 | 推荐 effort | 为什么 |
|---------|------------|--------|
| 简单重构、rename、提取函数 | `high` | 地板档，单点改动不需要更深推理 |
| 单文件编辑、局部 bugfix | `high` | 改动面小，`high` 足够覆盖 |
| 直白内容生成（翻译润色后的成文、模板填充） | `high` | 无架构判断，地板即可 |
| 基础研究（查一个 API、读一个模块） | `high` | 检索型任务，深思无增益 |
| 机械搬运/结构重组（移动段落到参考文件、删减行数、sed/awk 批量替换、逐节瘦身、行数统计） | `high` | 纯机械操作，max 会导致分析瘫痪（2026-06-08 实战验证） |
| 多文件架构改动、跨模块重构 | `xhigh` | 改动有连锁影响，需推演依赖关系 |
| agent team 审查、code review | `xhigh` | 要找出非显性问题，浅推理会漏 |
| 设计决策（选型、API 设计、方案权衡） | `xhigh` | 需要对比多方案 trade-off |
| 复杂内容创作、taste-skill 原型图 | `xhigh` | Design Read 质量随 effort 明显提升 |
| 深度架构分析、全栈功能实现 | `max` | 跨层推理 + 大量隐性约束 |
| 多 lens 并行审查（3+ lens） | `max` | 每个 lens 都要深推，汇总更要 |
| 根因调试、疑难 bug 定位 | `max` | 症状到根因链长，浅推理只能治标 |
| 安全审计、skill 撰写/重写 | `max` | 高风险 + 高抽象，错一处全盘塌 |

> 💡 **`xhigh` / `max` 仅 Opus 4.8/4.7 专属。** 别名机型上不可用——选 `max` 前确认 `--model` 是 Opus 4.8/4.7。

### 自检决策树（顺着走到一个明确档位）

```
选 effort 前 → ❓ 用户是否说了 "fast / cheap / quick / 快一点 / 省钱"？
            │
            ├── ✅ 是 → 可降到地板以下
            │        ├── 纯格式转换 / 一次性翻译 → `--effort medium`
            │        └── 用户说"越快越好" / 烟雾测试 → `--effort low`
            │        （⚠️ 仅此一种情况允许低于 high）
            │
            └── ❌ 否 → 🔒 从 `high` 起步，按信号往上抬：
                     │
                     ├── ❓ 涉及多文件 / 架构改动 / 任何审查 / 设计决策 / 原型图？
                     │   ├── 否 → 停在 `high`  ✅（单文件、直白生成、基础研究）
                     │   └── 是 → 抬到 `xhigh`，再问下一层 ↓
                     │
                     └── ❓ 是「深度」级别？（深度架构分析 / 多 lens 并行 / 根因调试 / 全栈功能 / 安全审计 / 写 skill）
                         ├── 否 → 停在 `xhigh`  ✅
                         └── 是 → 抬到 `max`  ✅（最强推理，认了这个成本）
```

**一句话规则：** 没信号 → `high`；碰到「多文件/审查/设计/原型」→ `xhigh`；碰到「深度/多 lens/根因/全栈/安全/写 skill」→ `max`。**只有用户喊"快"才允许往地板下走。** 拿不准时往上抬一档，不要往下省——返工的成本远高于多想几秒的成本。

## ⚙️ 实战配置（Effort in Practice）

智能 Effort 路由决定档位后，**首选在启动 CC 时就用 `--effort` 落地**——比会话内切换省事、省钱、省 cache。

**场景 → 启动 flag：**

| 场景 | 路由判断 | 启动 flag |
|------|---------|----------|
| 单文件小修，用户没说"快" | 地板档 | `--effort high` |
| Agent team code review | 多 lens 并行需深推理 | `--effort xhigh` |
| 安全审计 / skill 重写 | 高风险、根因级 | `--effort max` |

```bash
# 在目标 workdir 下启动 tmux session，按路由结果定档
# 单文件小修（用户未要求"快"）→ high
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort high

# agent team code review → xhigh
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort xhigh --teammate-mode tmux

# 安全审计 / skill 重写 → max
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort max
```

> 💡 启动命令照常带 `HOME=/Users/alexcai` + `--model`，并在目标 workdir 下启动 session，effort 只是多一个 flag。

**会话内临时改档**用 `/effort <level>`，见上方「会话内切换：/effort」节。

> ⚠️ **关键陷阱：切档会清空当前 prompt cache，整个 history 被重读——又慢又烧钱。** 所以**不要在会话中途随意切档**，除非任务性质真的变了（例如从研究阶段进入深度调试阶段）。**能在启动时就定对档位，永远比中途切强。**

> 💰 **成本提示：** `max` ≈ 2× `xhigh`，`xhigh` ≈ 1.5× `high` → 换算下来 **`max` ≈ 3× `high`**。"按需路由"不是抠门，是避免给简单任务付深度推理的钱。
> **结论：** 能用 `high` 解决的别开 `max`；但该上 `max` 的任务（安全审计、根因调试）省这点钱会得不偿失——**返工比深度推理贵得多。**

## 🚨 反模式：机械任务用 max → 分析瘫痪

> **2026-06-08 claude-code salience slim 实战验证。** max effort 在**纯机械/结构搬运任务**上不仅无增益，反而会反复进入 5-10 分钟思考循环，零产出。

| 任务类型 | 正确 effort | 错误 max 的症状 |
|---------|------------|----------------|
| 移动段落/表格到参考文件 | `high` | 反复 "De-forking…almost done thinking"，不写盘 |
| 行数统计、sed/awk 批量替换 | `high` | Cogitated 8 分钟，最后 API timeout |
| 逐节瘦身、每步跑脚本验证 | `high` | 轮巡 >80min 仅完成 2/5 手术 |
| 质量审核、路径追踪、hexdump 验证 | `high` | —（high 足够完成） |

> **规则：问自己"这个任务需要深度推理还是机械执行？"** 机械执行 → `high` 永远够用。max 是为"架构判断/根因推导/安全审计/多 lens 权衡"设计的，给机械任务用 = 白白烧钱 + 增加 timeout 风险。

**同 session 切换：** 如果 CC 已经用 max 启动但卡在思考循环，不要重建 session——用单行短命令推动（≤120 字符），CC 会在当前 effort 下执行。若连续 3 次推动仍卡 → `Ctrl+C` → 窄化到原子任务（如 "只 cat 合并 recon 文件"）。若仍不行 → 杀 session 重建，改用 `high`。
