---
name: cc-tmux
description: >
  Drive Claude Code via tmux with script-enforced safeguards.
  Thin skill — scripts do the enforcement, prose only tells you which script to call.
  Parallel version to claude-code skill for testing the simplified architecture.
  
  Use when: 调 CC, 用 claude, 拉 CC, delegate to CC, agent team, 重活调 CC.
  Do NOT use for: simple single-tool calls, grammar fixes, non-coding tasks.
type: routine
version: 1.38.0
author: "Hermes Agent + Claude Code (v1.38.0: cc-wait-marker startup gate — prevent IDLE/residual 900s empty waits)"
license: MIT
---

# CC via tmux — Script-Enforced Orchestration

> **设计原则**：脚本做 gate，LLM 做决策。"能不能做"由代码判，"怎么做"由 LLM 判。
> **与 claude-code skill 的关系**：并行版本，不覆盖。v4 是 full prose，v5 (cc-tmux) 是 thin prose + fat scripts。
> **核心赌注**：把义务数从 80+ 砍到 ~10 per turn（curse of instructions），让合规=最省事。

## 🚦 消息路由（cc-route.sh + cc-active-sessions.sh · R10 · v1.35.0）

当 Hermes 收到用户消息且存在活跃 CC session 时，**必须**先走路由层再行动：

1. `cc-active-sessions.sh --json` — 查有无 CC、什么状态
2. 分类 intent：`status_query` | `continuation` | `redirect` | `new_task` | `unknown`
3. `cc-route.sh --session <s> --intent <type>` — 获取路由建议
4. 按 `.recommendation.action` 行动

完整操作流程见 `references/routing-guide.md`；决策矩阵见 `scripts/cc-route.sh` 头部注释。
5 类 intent × 10 种 CC state → 4 种 action：`handle_directly` | `queue` | `forward_now` | `interrupt`（confirm_required=true）。
测试：test-route.sh 21/21 + test-active-sessions.sh 10/10。

## ⚠️ Pitfall #47：bash `local` 只在函数内合法

`local sm` 写在脚本顶层（非函数内）+ `set -euo pipefail` = 脚本立即 exit 1，无任何 stdout/stderr 输出。
症状：`bash -x` trace 显示 `local: can only be used in a function`。
**规则**：顶层用普通赋值（`sm=...`），仅在 `func() { ... }` 内用 `local`。

## ⚠️ Pitfall #48：touch -t 边界竞态（hermetic 测试中 mtime 敏感）

`touch -t $(date -v-180S +%Y%m%d%H%M)` 设置的文件 mtime 不含秒数（`hh:mm:00`），与 `NOW` 的秒差可能刚好落在阈值边界（如 120s 状态新鲜度窗口）。

症状：同一测试有时通过有时失败，`cc_state_source` 在 `hook_status`/`heartbeat`/`none` 间漂移。

**修复**：阈值敏感的测试，`touch -t` 加 `.SS` 秒数（如 `+%Y%m%d%H%M.%S`），或在测试中用 `CC_ROUTE_STATUS_MAX_AGE` 环境变量放大窗口。不要在边界附近设置 mtime。

## ⚠️ Pitfall #49：tmux pane buffer 有限 → CC 产出的长方案不可靠

tmux `capture-pane -S -` 只能读到 pane 的 scrollback buffer（默认 ~2000 行）。CC 产出的长方案（如增强方案 Markdown）可能被滚出 buffer。

症状：用 `capture-pane` 抓 CC 输出时只看到结尾几行，完整内容丢失。

**规则**：但凡要求 CC 产出方案/设计/分析文档，上下文里必须加"请把完整方案写到 `/tmp/<name>.md`"，事后读文件而非 capture-pane。不要把 CC 的 pane 输出当作唯一信息源。

## ⚠️ Pitfall #50：cc-start.sh / cc-send.sh 参数名易错（WRR v5.1 验证）

`cc-start.sh` 参数是 `--target`，不是 `--session`。用错会打印 "Unknown arg" 然后 exit 1。
`cc-send.sh` 参数是 `--context <文件路径>`，没有 `--stdin` 或 `--session`（session 参数名是 `--session`，仅此脚本用它）。

**快速对照**：
| 脚本 | session 参数 | 内容参数 |
|------|-------------|---------|
| `cc-start.sh` | `--target <name>` | `--task "描述"` |
| `cc-send.sh` | `--session <name>` | `--context <file>` + `--message "..."` |
| `cc-monitor.sh` | `--session <name>` | — |

## ⚠️ Pitfall #51：cc-send.sh --context 注入 markdown → CC 把散文当命令执行

当 `--context` 文件内容为 markdown 时，cc-send 将其 `send-keys` 到 CC pane。若 CC 未就绪（仍在 zsh 提示符），zsh 会逐行当命令执行，产生大量 `command not found` 错误且 CC 永不会处理任务。

症状：pane 里循环输出 `zsh: command not found: 阅读` / `cd: too many arguments` / 中文乱码，CC 状态永远是 STARTING。

**规则**：`cc-send.sh --message` 里只写简短指令 + 文件路径引用（如 "阅读 /tmp/brief.md，分析后产出报告到 /tmp/report.md"），**不要把完整评估简报用 --context 注入**。若需传递大段上下文，先启动 CC，确认 pane 显示 `❯` 提示符后再发。

## ⚠️ Pitfall #52：cc-start.sh exit 1 ≠ 无 session 创建（WRR v5.1 验证）

`cc-start.sh` 可能因 pane 名不匹配（脚本内用下划线替换连字符后 lookup 失败）而 exit 1，但 tmux session 已经创建成功。

症状：`cc-start.sh` 打印 "can't find pane: 1-<target>" 并 exit 1，但 `tmux list-sessions` 显示 session 存在。

**规则**：cc-start.sh exit 非零后，立即 `tmux list-sessions | grep cc` 检查。若 session 存在，直接 `cc-send.sh --session <完整session名>` 发送任务。

**兜底方案**：若 cc-start.sh 反复失败，直接用原生 tmux：

```bash
tmux new-session -d -s cc-<name> -c /tmp \
  \"claude --model claude-sonnet-4-5 --output-format stream-json --verbose\"
sleep 2
tmux send-keys -t cc-<name> \"任务描述\" Enter
```

此方式绕过 cc-start.sh 所有 gate，适用于简单短期任务。任务完成后用 `tmux kill-session -t cc-<name>` 清理。

## ⚠️ Pitfall #53：Sonnet "almost done thinking (high effort)" 过度思考陷阱

Sonnet 显示「Deciphering… / Choreographing… (N min · almost done thinking with high effort)」超过 8 分钟 **不是**「快了」——是模型在深度思考循环中卡死（#50 变种，不限于 Opus）。症状：
- 命令行显示 `Reading 2 files, running 1 shell command…` 但 turn-done 永远不会出现
- 反复回到 THINKING → TOOL → THINKING，产物文件从未创建
- 即使任务 prompt 写了「不要深度思考」「直接写」仍然进入此状态

**对策（三级升级）**：
1. **轻量**：C-c 中断 → 发送更简短的直接指令 → 检查是否迅速进入 TOOL 状态开始写文件
2. **中度**：C-c → `tmux kill-session` → 重新 `cc-start.sh` 启动新 session → 注入更紧凑的任务（砍掉「分析/思考/研究」措辞，改为「✓ 请直接写文件 /tmp/X.md。格式：...」）
3. **重度**：不要判定“CC 不可靠”；先收缩任务输入（单任务包、明确产物路径、去掉发散研究措辞）。若仍卡住，可让 Codex 产出紧凑方案/任务包，再交回 CC 执行或审查

**子模式：CC 完成所有复杂文件后卡在最后 1-2 个小修改上**（v1.38 · 2026-06-29 bilibili-skill 三阶段升级实战）：

症状：CC 已在 `/tmp/` 写出 3-4 个新建文件（全部正确），但在修改 `SKILL.md` / `fetch_all.py` 等已有文件时进入「almost done thinking」状态 10+ 分钟。`ls /tmp/` 显示产物已全，但 `done.txt` 未写。

**对策（此子模式专用）**：
- C-c → send-keys: `"已经产出 X 个文件了，做得很好。现在只做两件事：[file1具体改动]，[file2具体改动]。不要深度分析，直接写。完成写 done.txt。"` Enter
- 这比「中度」级别轻——因为不要 kill session（新文件已产出），只是把 CC 从过思考中拉出
- 旧 session 的上下文（已读文件、已产出的正确代码）保留，CC 只需完成收尾

**诊断**：`ls /tmp/phaseX-done.txt` 不存在 + `ls scripts/` 产物已全 + monitor 显示 THINKING >5min = 此模式。不要杀 session——C-c + 单行收尾指令即可。

完整案例：bilibili-video-analyzer Phase 2（900s）+ Phase 3（600s）两次命中，C-c+精简指令后均 2-3 分钟内完成。

## ⚠️ Pitfall #56：tmux send-keys 多行文本被 CC 队列化（v1.36 · 2026-06-29 WRR 实战）

CC 的输入模型对多行文本有**消息队列**机制：`tmux send-keys` 发送的多行文本（如 `cat file && claude --resume`、含换行符的长指令）会被 CC 解释为**待编辑的排队消息**而非立即执行。CC 显示「Press up to edit queued messages」+ `❯` 提示符，指令永远不会被处理。

症状：send-keys 后 pane 显示完整指令文本在 `❯` 下方，但 CC 无任何思考/工具调用动作，几秒后重回干净 `❯` 提示符。`Press up to edit queued messages` 是诊断关键词。

**对策**：
1. **永远不要用 send-keys 发多行指令**。所有指令压缩成一行：`按 /tmp/task.md 执行`，让 CC 自己去读文件。
2. 若必须传递长上下文，先 `write_file` 到 `/tmp/`，然后 send-keys 单行「读 /tmp/brief.md 然后...」。
3. 若已触发队列：`Escape` → `C-c` → `Enter` 清空队列，重新发单行指令。

完整实战记录：WRR OB 三梁重构（2026-06-29），5 次 send-keys 尝试（含 cat + 长中文指令）全部被队列化，换单行「按 /tmp/cc-task-ob.md 执行」后 CC 立即开始工作。

## ⚠️ Pitfall #57：CC persisted-output 污染导致新 session 假死（v1.36 · 2026-06-29 WRR 实战）

CC 的 `persisted-output` 机制会在新 session 中自动注入旧对话的持久化输出（如几周前的 roadmap review）。当旧输出包含大量 structured task cards（如 S408-S410，Jun 20）时，会**挤占 tmux scrollback buffer**，导致当前 session 的真实输出不可见。更严重的是，CC 可能因为旧上下文字段（如 `bypass permissions on · ← for agents`）误判为仍在某个流程中而拒绝处理新指令。

症状：`cc-start.sh` 后 CC pane 显示的是旧 session 的 `</persisted-output>` 内容（非当前任务），`❯` 后 CC 不响应新 send-keys 指令。monitor 显示 ACTIVE 但 pane 无新输出。

**对策**：
1. **首选**：不用 `cc-start.sh --task`（它可能在旧 persisted-output 前注入任务），改用**裸 tmux 启动** + 等待 `❯` 出现 + 单行 send-keys。
2. **裸 tmux 启动模板**：
```bash
tmux new-session -d -s "cc-<name>" -c /tmp "claude --model claude-opus-4-8"
sleep 5  # 等 ❯ 出现
tmux send-keys -t "cc-<name>" "读 /tmp/task.md 执行。" Enter
```
3. 检查 pane 第一行是否「尝试 "create a util..."」——那是干净 session 的标志。若看到旧日期/task cards = 被污染。

## References

- WRR v6 lesson: CC is reliable; implementation stalls usually mean task granularity/launch pattern is wrong (single-line + `/tmp` task file + small packages).

## ⚠️ Pitfall #58：任务粒度过大触发思考瘫痪（v1.37 · 2026-06-29 WRR v6 实战）

一次性给 CC 5 个大型任务包（每个含多文件+测试）是**确定的失败模式**。CC 读完 565 行实现方案后会在 THINKING 阶段循环：搜索项目 → 读文件 → 思考 → 回到 prompt，但永远不动手写第一行代码。这不是模型问题——Opus 和 Sonnet 都会中招，**`--effort high`/`xhigh` 会加剧**。

症状：CC 启动后 15+ 分钟仍在 ACTIVE 状态，`capture-pane` 显示反复 TOOL→THINKING 但零产物文件。monitor 显示 seq 22+、无 turn-done。

**对策**：
1. **单任务包原则**：每个 CC session 只给 1 个任务包（≤3 文件）。完成后 cc-finish → 启动新 session → 给下一个任务包。
2. **任务包描述 ≤10 行**：砍掉「分析/研究/思考/设计」措辞，改为「写 X/Y/Z 三个文件。写完跑测试。不改已有文件。」
3. **「先跑第一个任务再说」**：不要把所有任务都写在 brief 里让 CC 自己选——指定「只做 T1」。
4. 跨任务包的依赖从 brief 中移除——每个 session 只看到自己的任务包，不需要知道前面/后面还有啥。

**2026-06-29 WRR v6 实现阶段数据**：
- 5 任务包一次性 → 3 次 CC session 全部 900s 超时，零产出
- 改为 Codex exec 逐任务包 → 5 次，5 次通过，平均 3min/次
- Codex 对此模式免疫的原因：GPT-5.5 的思考模式不同，不会在「任务太大」时瘫痪

**CC 的正确用法（经此实战验证 + 用户纠正）**：
- ✅ 文档迁移/文件操作/审查类任务 — 一次给清晰上下文，单行指令启动
- ✅ 单个小代码任务（1-3 文件）— 单行指令 + read file 模式；CC 可靠性取决于任务包装，不应因一次失败否定 CC
- ✅ 多任务包代码实现 — 拆成多个 CC session，每次只给一个任务包；若需要抢进度，可用 Codex 并行跑腿，但最终判断仍由 Hermes 审核
- ✅ 分析/研究/设计类长任务 — 先给明确审查对象/产物路径；避免让 CC 从零发散研究

用户明确纠正：**“CC 可靠；如果不可靠，大概率是用法出问题。”** 未来遇到 CC 超时/零产出，优先诊断任务粒度、send-keys 注入、effort、session 污染和产物路径，而不是结论化为“CC 不可靠”。详见 `references/cc-reliability-is-usage-pattern.md`。

## ⚠️ Pitfall #59：`--effort high` 使思考瘫痪更严重（v1.37 · 2026-06-29）

CC 的 `--effort high` 和 `--effort xhigh` 对代码任务**不仅无益，反而有明确害处**。它们让 CC 在「我应该深度思考」和「我应该动手做事」之间反复徘徊，结果两样都没做好。

**经验数据**：
- `--effort medium`：OB 三梁重构一次成功（2min 启动→61行报告）
- `--effort high`：WRR v6 实现 3 次全部超时（900s）
- `--effort xhigh`：同样模式，零产出

**规则**：
- 文档/文件操作/审查：`--effort medium`（默认）
- 代码实现：CC 可以可靠执行，但必须拆小（≤3 文件/包）+ 单行指令 + 读 `/tmp/task.md`；不要一次塞多个任务包
- Codex exec 可作为 bounded patch 的并行/替代跑腿路径，但不要把“这次 Codex 更顺”误写成“CC 不可靠”
- 仅在 CC 作为审计/审核角色且任务确实需要深度推理时，才考虑 `--effort high`
- **默认不用 `--effort xhigh`**——除非用户明确要求深度审查且接受长时间等待；否则它容易触发 49+ 分钟思考零产出（见 #53）

## ⚠️ Pitfall #60：默认启动方式 = 裸 tmux + 单行指令 + 读文件（v1.37 · 2026-06-29）

经 WRR OB 三梁重构 + WRR v6 实现两轮实战，「裸 tmux + 单行指令 + 读文件」是**唯一跨任务类型稳定的 CC 启动模式**。

**2026-06-30 v1.38 脚本硬约束：`cc-wait-marker.sh` 内置 startup gate。** 不能只看 session 存在或输入框里出现文字；wait 前若没有新 turn-done marker，脚本会检查 pane：
- `IDLE` + 无 marker → exit 4 fail-fast，不再空等 900s
- `❯` 后有残留文本 → 默认 exit 4，不自动 Enter（防误提交旧残留）
- `Press up to edit queued messages` → exit 4，不自动 Enter（避免队列越积越多）
- 只有明确知道残留就是刚发送的任务行时，才可显式 `CC_WAIT_AUTO_SUBMIT_RESIDUAL=1 cc-wait-marker.sh ...` 让脚本补一次 Enter

因此标准流程变成：发送任务 → `cc-wait-marker.sh`。如果返回 4，说明任务根本没提交成功，先清/重发，不要继续 wait。

不要用 `cc-start.sh --task`（会注入长 prompt 触发过度思考）、不要用 send-keys 多行（会触发行队列）、不要用 `-p` 非交互模式（执行完即退出，不适合编码任务）。

**标准启动模板**：
```bash
# 1. 写任务到文件（≤10行，不含分析/研究措辞）
write_file /tmp/cc-task-<name>.md

# 2. 裸 tmux 启动
tmux new-session -d -s "cc-<name>" -c <workdir> "claude --model claude-opus-4-8 --effort medium"

# 3. 等 ❯ 出现
sleep 5

# 4. 单行指令
tmux send-keys -t "cc-<name>" "按 /tmp/cc-task-<name>.md 执行。直接动手。" Enter

# 5. 等 turn-done（v1.38: wait-marker 内置 startup gate）
# 如果任务没真正提交，cc-wait-marker 会 exit 4 fail-fast，不再空等 900s
cc-wait-marker.sh --session "cc-<name>" --timeout 600
```

这个模式下 CC 自己读文件 → 理解 → 执行，不会因「prompt 太长/太复杂」触发思考瘫痪。OB 三梁重构用它 2 分钟出审查报告。

## ⚠️ Pitfall #53 更新（v1.36 · 2026-06-29）：Opus 同样中招，"短指令+读文件"是通用解

v1.35 版只记录了 Sonnet 的过度思考陷阱。2026-06-29 WRR 实战确认 **Opus 同样会中招**：
- Opus + high effort：3.5 分钟「almost done thinking」→ 回到 prompt 零产出。
- Opus + xhigh effort：同样的 pattern。

**2026-06-29 WRR v6 实现阶段新增发现**：CC 对**代码实现任务**出现 zero-output 模式时，根因优先按**用法问题**排查：任务粒度过大、send-keys 多行被队列吞掉、`--task` 注入长 prompt、effort 过高、旧 session/persisted-output 污染。Codex exec 可以作为抢进度的可靠替代路径（一 shot 通过 T1：3 文件、7/7 tests），但不要把它表述为“CC 不可靠”。详见 `references/cc-reliability-is-usage-pattern.md`。

**唯一稳定解法（跨模型通用）**：
1. 不通过 `--task` 或 send-keys 给 CC 长指令
2. 把任务需求写到一个 `/tmp/` 文件
3. 用单行指令「读 /tmp/task.md。直接动手。」启动 CC
4. CC 自己读文件 → 理解 → 执行，不会陷入过度思考

这个模式在 WRR OB 三梁重构（Opus + medium effort）中从启动到产出 61 行审查报告仅需 **2 分钟**——对比之前 5 次 session 累计 40+ 分钟零产出。**结论：CC 的过度思考由「输入复杂度」触发，不是模型选择问题。砍输入复杂度 = 砍掉触发条件。**

## ⚠️ Pitfall #54：C-c 中断后 paste 指令需手动 Enter

CC 被 C-c 中断后进入「Interrupted · What should Claude do instead?」状态。此时 `tmux send-keys` paste 文本会出现在 prompt 后方，但 CC **不会自动执行**——必须额外 `send-keys Enter` 才能真正提交。

**症状**：paste 后 5 秒 pane 仍显示 paste 文本行 + 下方空 prompt，CC 没有任何动作。

**正确流程**：
```bash
tmux send-keys -t <session> C-c
sleep 1
tmux send-keys -t <session> "新的简明指令" Enter  # ← Enter 在文本行内，一次 send-keys 完成
```
不要分两次（先 paste 文本、再单独 Enter）——单次 `send-keys` 末尾加 `Enter` 最可靠。

## ⚠️ Pitfall #56：macOS `tmux send-keys` 多行文本被 CC 队列吞掉

`tmux send-keys` 发送多行文本时，CC CLI 将换行符解释为多行消息分隔符，触发「Press up to edit queued messages」模式——所有指令被队列化但永不执行。

症状：`tmux send-keys` 后 pane 显示 `❯ Press up to edit queued messages`，指令文本可见但 CC 无动作。`send-keys Enter` 追加一个空行，不提交队列。

**修复（三级）**：
1. **优先**：单行指令 + 引用文件路径。如 `按 /tmp/cc-task.md 执行。`——让 CC 自己读文件，不把长文本注入 send-keys。
2. **次选**：`claude -p '单行任务描述'` 非交互模式打印输出（适合短任务，执行完即退出）。
3. **兜底**：`tmux send-keys C-c` 取消队列 → 确认 `❯` 干净 → 重新单行发送。

**诊断**：pane 显示 `Press up to edit queued messages` 或空 `❯` 但无 thinking 指示器 = 中招。绝对不要连续 `send-keys Enter`——只会累积空行进队列。

## 📋 任务结构策略：新建 vs 修改（references/cc-task-structure-new-vs-modify.md）

CC 在新建立文件上快速准确（3-5min/文件），在修改现有 100+ 行文件上容易触发过度分析循环（Pitfall #53）。对策：拆分 session（新建和修改分开）、给修改指令提供代码片段而非「分析+实现」、中断后用单行指令。详见 `references/cc-task-structure-new-vs-modify.md`。

## ⚠️ Pitfall #57：CC persisted-output 污染旧会话上下文

CC 启动后自动注入 `<persisted-output>` 块，包含历史会话的摘要。当旧 conversation 与当前任务主题无关时（如 iii × cc-tmux roadmap 出现在 WRR OB 重构任务中），此块占满 tmux scrollback buffer 导致无法通过 `capture-pane` 观察 CC 当前工作状态。

症状：`tmux capture-pane` 只看到数月前的旧 S408-S410 任务摘要，看不到当前任务的 thinking/tool 指示器。CC 实际在工作但 pane 输出被旧上下文淹没。

**应对**：
1. 不依赖 pane 输出判断进展——用 `cc-monitor.sh`（读 hook 状态文件）+ 检查产物文件。
2. 启动新 session 前 `tmux kill-session` 旧 session，减少跨会话上下文泄漏。
3. persisted-output 是 CC 内置特性，无法从外部关闭——接受并绕过。

## ⚠️ Pitfall #55：HTTP_PROXY 泄漏到子进程导致外部 API 超时

`HTTP_PROXY=127.0.0.1:6152`（Surge/Clash）被 subprocess 继承后，httpx/curl 的外部 API 调用会在 TLS 握手阶段挂起，症状为 `ConnectTimeout`。但父 shell 的 `curl` 正常——因为代理规则作用在进程粒度。

**诊断**：`health_check → 200` 但 `deep=true → timeout`，且 `unset HTTP_PROXY` 后恢复正常。

**修复**：调用外部 API 前清代理（详见 skill 内部 proxy-env API 干扰记录）。

## 🔗 多 Agent 协作模式

五阶段 STDD 评估流水线：CC+Codex→规划→CC→OMP→验收。
案例：WRR v5.2 本地搜索层、WRR v6.0 OB 三梁重构。
OB 文档重构专用参考见 skill 内部 agent-team STDD Obsidian restructure 记录。
