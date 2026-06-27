# Agent Team Disk-Output Verification

> **何时使用：** CC agent team workers 运行 3+ 分钟后，tmux pane 只显示时间和 token 数，无法判断实际进度。用磁盘验证绕过 UI 盲区。

---

## 问题

CC agent team 的 tmux task board 只显示：
```
◯ general-purpose  建 3 个新 references    2m 40s
◯ general-purpose  改写 4 个 references     2m 4s
```

你看不到 workers 具体在写什么文件、是否真的在产出。等 5+ 分钟可能发现 worker 已经假死。

## 方案：`find -newer` 磁盘验证

在 CC 启动前创建一个标记文件，运行期间用 `find -newer` 检查哪些文件被修改过：

```bash
# 步骤 1：CC 启动前，在 workdir 创建标记文件
touch /tmp/cc-start-marker

# 步骤 2：CC 运行期间（每 30-60s），检查磁盘产出
find <workdir> -newer /tmp/cc-start-marker -type f | sort

# 步骤 3：统计产出文件数
find <workdir> -newer /tmp/cc-start-marker -type f | wc -l
```

## 真实案例：SIL v5.0 改造（本会话）

5 个 workers 并行修改 30+ 个文件，tmux task board 只显示运行时间。通过 `find -newer` 每 30s 检查，得到精确进度：

| 时间 | `find -newer` 结果 | 推断 |
|------|-------------------|------|
| 4min | `dual-axis-methodology.md`, `quality-gates.md` | Worker A/B 在写 references |
| 6min | + `agent-pipeline.md`, `framework-library.md`, 3 agent files | Workers 加速产出 |
| 8min | + `anti-ai-blacklist.md`, `output-finalizer.md`, `insight-synthesizer.md` | 写作/研究 workers 就位 |
| 10min | 23 files total, 2 workers disappeared from board | 2 workers 完成退出 |
| 12min | `SKILL.md` 出现（306 行） | Leader 完成主文件 |

**关键洞察**：当 task board 上 worker 消失但 leader 还在 "Calculating" 时，`find -newer` 能确认文件确实在磁盘上——不是卡死，是 leader 在读入所有 worker 产出后综合生成。

## 与 Worker 假死检测的区别

| 场景 | Worker 假死检测 | 磁盘验证 |
|------|----------------|---------|
| 触发条件 | task board 显示 worker running >2min 但 token 不变 | 每次轮询（主动） |
| 目的 | 诊断单个 worker 是否卡死 | 追踪整体产出进度 |
| 方法 | `ls -la <expected path>` | `find -newer` 全目录扫描 |
| 粒度 | 单个 worker → 单文件 | 全 team → 全文件变化 |

两者互补：磁盘验证用于持续监控，假死检测用于精准诊断。

## 最佳实践

1. **CC 启动前必建 marker**：`touch /tmp/cc-marker-$(date +%s)`，避免与前次运行混淆
2. **每轮进度汇报附带文件计数**：`📊 17 files modified` 比 `workers running` 信息量大得多
3. **关注增量**：两次 `find -newer` 结果的 diff = 本轮新产出
4. **组合 agent file 过滤**：`find ... -newer ... -name "*.md" | grep agents` 只看 agent 文件
5. **配合 task board 解读**：worker 数量减少 + 文件数增加 = worker 完成退出，非异常
