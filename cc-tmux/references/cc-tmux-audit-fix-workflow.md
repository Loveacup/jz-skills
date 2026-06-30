# cc-tmux 自审计 → 修复工作流

> 2026-06-24 实战验证：用 CC 审计 cc-tmux，再按分级修复，是高效且可复现的模式。

## 流程

```
CC 代码审计（逐文件实读 + 测试 + md5 parity）
  → 分级发现（P0/P1/P2，按正确性/可靠性/可维护性）
  → Hermes 审核（gate-verify + 独立取证）
  → 分轮修复（P0→P1→P2，每轮跑全量测试）
  → deploy sync（md5 parity 校验）
  → OB 回写（CQI 文档 + 审计报告落库）
```

## 关键经验

### 1. CC 模型选择
- 代码审计用 **high effort**（非 xhigh）——xhigh 容易 20min Boogie 无产出
- Opus 4.8 适合推理密集型审计；Sonnet 适合格式化/简单提取
- 任务太宽时拆两轮：先代码级审计，再架构对齐评估

### 2. CC 冻结处理
- "Boogieing 20min" + idle prompt = CC 思考完但可能未调工具
- API 500 打断后 CC 可能进入 queued-message 循环 → 杀掉重建
- 不要等超过 15min 无产出的 CC session

### 3. 分级修复顺序
```
P0（正确性）→ P1（可靠性）→ P2（可维护性）→ 新功能（不影响核心）
```
每轮跑全量测试再进下一轮，避免叠加引入 bug 后难以定位。

### 4. 测试适配
- 重构改变退出码语义时（如 verify_delivered → send_to_pane），测试必须同步适配
- EXIT trap `return 0` 是 bash 通用坑：`cleanup()` 里 `rm` 失败的返回值会覆盖 `exit 0`

### 5. CC 自主纠偏
- 任务文字可能过时（如 "PostCompact" 事件不存在）——CC 若不盲从、主动查证并提议替代方案，价值远超机械执行
- 在任务里给 CC 留「纠正任务文字里不准确假设」的空间

### 6. deploy discipline
- 每轮修改后 `md5` 校验源码 ↔ 运行时 parity
- `run-tests.sh` 统一 runner 是必备基础设施——不要依赖「记得跑全部测试」

## 产物落盘约定

| 产物 | 位置 |
|------|------|
| CC 审计报告 | `/tmp/cc-tmux-code-audit-YYYYMMDD.md` |
| OB 归档 | `30_审计/cc-tmux 代码审计 YYYYMMDD.md`（加 full frontmatter） |
| CQI 更新 | 原 CQI 文档 inline 更新（新增线程 + 版本条目） |
| deploy | `~/.hermes/skills/autonomous-ai-agents/cc-tmux/`（md5 parity） |
