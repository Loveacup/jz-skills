# CC Opus 49min 思考零产出模式 · 2026-06-27 实发

> 事件：WRR 自适应改造 Phase 1，Opus 4.8 high effort + Ultra Code，49min 思考→281k tokens→0 代码落地→文件幻觉→任务未实现。

## 症状

- CC 持续 THINKING 39-49min，token 从 4.7k 飙到 281k
- 最终产出 178 行"架构讨论稿"，但**文件从未落盘**
- CC 自曝："工具输出确实坏了；任务没实现；我对调研结论过度背书"
- 两次声称写文件成功，但 `find /tmp` 确认文件不存在

## 根因

三重叠加：

1. **Ultra Code 模式鼓励深度分析** — 适合调研，不适合工程实现
2. **Opus 调研惯性** — 倾向长篇分析而非代码落地
3. **tmux 下 Bash 工具间歇性不可靠** — 文件读写失败，CC 不自知

## 预防

### 任务拆分（调研+实现分离）
- Round 1: Sonnet Agent Team 做只读调研 → 写方案文档
- Round 2: 另起 session 做代码实现

### Ultra Code 适用边界
- ✅ 适合：纯调研/方案输出、多源交叉验证
- ❌ 不适合：需落地代码的工程任务、实现+调研混合

### 磁盘产出阈值告警
- 超 20min 思考 + 0 磁盘文件 → 抓屏看实际在做什么
- 持续无产出 >25min → 准备 C-c 缩小范围
- 声称写了但文件不存在 → 立即标记工具故障，介入

## 与既有 Pitfalls 的关系

- Pitfall #13 (Opus 报告幻觉) → 升级：工具链故障致全部产出不可信
- Pitfall #14 (xhigh 冻结) → 扩展：high + Ultra Code 同样风险
- Pitfall #16 (THINK_TIME 递增≠有效) → 需加磁盘产出检查
- Pitfall #28 (scope 过宽) → 同类机制

## 处置流程

```
发现 49min 思考 + 文件幻觉:
  1. 立即判定该 session 产物不可信
  2. 清理 IDLE session（Pitfall #9）
  3. 换 Sonnet 重跑，或拆任务为调研+实现两段
  4. 新 session 加明确落盘要求："所有产出必须用 write 工具写到磁盘"
```
