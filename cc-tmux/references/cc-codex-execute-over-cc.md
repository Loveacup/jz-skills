# CC 代码执行不可靠 → Codex 直接执行模式 (2026-06-29)

## 症状

CC（Sonnet 或 Opus）对**代码实现任务**出现以下模式：
- 读到任务文件 → 搜索项目结构 → "Hatching… / Forming…" → 回到 `❯` prompt
- 不写任何文件、不执行任何命令
- 反复 5+ 次都如此，无论 effort level 和 model

## 触发场景

- `--task "实现 wrr/runtime/detect.py 并跑测试"` → 读计划 → 空转
- `send-keys "只做 T1：写 detect.py + 测试"` → 队列化不执行
- `cc-send.sh --message` → 读文件 → "Hatching… (14s)" → 回 prompt
- 全程无产物、无错误、无 turn-done

## 根本原因

CC 对"读方案 → 理解 → 写代码 → 跑测试"这种需要**多步理解后执行**的任务，在 thinking 阶段消耗 token 后直接终止，不进入 execute 阶段。不是超时——是 thinking 完成后主动选择不行动。

## 已验证的替代方案

**Codex exec（GPT-5.5）直接执行**——一次通过：

```bash
cd ~/code/project && codex exec \
  "按 /tmp/plan.md P0-T1 节，实现 foo.py + tests/test_foo.py。严格按方案数据结构。写完跑 pytest -v" \
  2>&1
```

- ✅ 读计划 → 读现有代码 → 写实现 → 写测试 → 跑 pytest → 报告结果
- ✅ T1: 3 文件、7/7 tests、0.03s
- ✅ T2+T3: 可并行后台（`background=true`）

## 什么 CC 能做

CC **文档迁移/文件操作类**任务仍然可靠：
- OB 三梁重构（mv/mkdir/write 36 文件）→ ✅ 一次成功
- 审查已有方案（读文件 → 写审查报告）→ ✅ 一次成功

**判断边界**：任务需要"读方案 → 写代码 → 跑测试"→ 用 Codex。任务只需"读文件 → 移动/重命名/写文档"→ 用 CC。

## 任务队列陷阱

CC 有"Press up to edit queued messages"机制：
- `send-keys` 发送多行任务 → 被队列化，不执行
- 即使单行，有时也被队列化
- **绕开**：写任务到 `/tmp/cc-task-*.md`，然后 `send-keys "按 /tmp/cc-task-*.md 执行"`

## 复现记录

- 2026-06-29：CC Opus xhigh 分析 WRR v6 架构 → 15min 无产出
- 2026-06-29：CC Opus high 执行 P0 5 任务包 → 22 轮、15min、零文件写入
- 2026-06-29：CC Opus high 单任务 T1 → 读文件、thinking 后回 prompt
- 2026-06-29：Codex T1 → 一 shot 3 文件、7/7 tests ✅
- 2026-06-29：CC OB 重构 → 一 shot 36 文件迁移、14 新文档 ✅
