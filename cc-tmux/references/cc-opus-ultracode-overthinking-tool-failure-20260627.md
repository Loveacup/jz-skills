# CC Opus UltraCode Overthinking + Tool Failure (2026-06-27)

> 实发事件：WRR 自适应改造 Phase 1，Opus 4.8 high effort + Ultra Code，49min 思考后工具不可靠、文件幻觉、任务未实现。

## 任务背景

- **目标**：实现 WRR Skill 运行时检测 + Hermes 适配层
- **配置**：`--effort high --model claude-opus-4-8`，context 指示 Ultra Code
- **产物预期**：`runtime-detector.ts` + `wrr-hermes/` 插件 + 验证测试

## 时间线

| 时间 | 状态 | 观察 |
|------|------|------|
| 0-5min | TOOL | CC 读 context + 项目文件 |
| 5-39min | THINKING | 深度思考，token 4.7k→281k，读取 Hermes 源码 |
| 39min | 产出 | 178 行"架构讨论稿"，但**文件未落盘** |
| 42-49min | THINKING | "almost done"但持续思考 |
| 49min | turn-done | 报告完成，但产物目录为空 |
| 追问 | TOOL | CC 声称 cp 成功（8730 字节），但磁盘无文件 |
| 终局 | 自曝 | CC："工具输出确实坏了；任务没实现；我对调研结论过度背书" |

## 根因分析

三重叠加触发：

1. **Ultra Code 鼓励深度多源交叉验证** — Opus 把"查证 Hermes 源码"当成了需要穷举分析的任务，产出是讨论稿而非代码
2. **Opus 调研惯性** — 倾向产出长篇分析而非代码落地。49min 只产出讨论稿，0 行代码，281k tokens
3. **tmux 下 CC Bash 工具间歇性不可靠** — 文件读写间歇失败，CC 不自知，基于幻觉结果推进分析

## 预防措施

### 1. 任务拆分（调研+实现分离）
- Round 1: Sonnet Agent Team 做只读调研 → 写方案文档（落盘验证）
- Round 2: 另起 session 做代码实现

### 2. Ultra Code 适用边界
- ✅ 适合：纯调研/方案输出、多源交叉验证（非代码）
- ❌ 不适合：需落地代码的工程任务、实现+调研混合、开放式"分析架构"

### 3. 磁盘产出阈值告警
- 超 20min 思考 + 0 磁盘文件 → 抓屏看 CC 实际在做什么
- 持续无产出 >25min → 准备 C-c 缩小范围
- 声称写了但文件不存在 → 立即标记工具故障，介入

### 4. 报告幻觉置信度信号
- CC 声称文件已保存但 `find` 找不到 → 不问 CC（会继续幻觉）
- 直接 `C-c` → 发 `cat 文件路径` 让 CC 回显
- 回显失败 → 收尾 session，产物不可信

## 与既有 Pitfalls 的关系

- **Pitfall #13**：Opus 报告幻觉 — 本次升级：工具链故障致全部产出不可信
- **Pitfall #14**：xhigh 思考冻结 — 扩展到 high + Ultra Code
- **Pitfall #16**：THINK_TIME 递增≠产出有效，需加磁盘产出检查
- **Pitfall #28**：scope 过宽 → 分析瘫痪，同类机制
