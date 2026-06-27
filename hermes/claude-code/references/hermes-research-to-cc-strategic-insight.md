# Hermes → CC 研究到战略洞察工作流

> 模式在 2026-05-28 好伴AI 深度研究会话中验证。核心流程：Hermes 做初始广扫研究 → CC agent team 做深度战略洞察/RCA。

## 适用场景

- 用户要求对某公司/产品/行业做深度评估
- 用户要求战略洞察、行业研究、竞争分析
- 研究发现事实偏差，需要根因分析（RCA）

## 工作流

### Phase 1：Hermes 初始研究（web-research-router）

1. 用 web-research-router deep loop（或 v3.4 后的产品评估快速模式）做广扫
2. 产出结构化产品评估报告（markdown）
3. 输出包含：公司画像、产品矩阵、模型能力、竞争格局、风险
4. 标注信源等级和潜在偏差

### Phase 2：CC Agent Team 深度分析（strategic-insight-longform）

1. 写 context 文件到 `~/.hermes/tmp/` 或 `/tmp/`，包含：
   - Phase 1 的输出摘要
   - 关键事实和数据点
   - 待验证的 claim（特别标注"第一/最/突破"等话术）
   - 原始报告完整路径
   - **本地知识库检索计划**：当源材料来自 Obsidian、公司内部资料、会议纪要或用户明确说“参考 OB/qmd”时，必须把 qmd collection、必跑 query、候选 OB 文件路径写进 context。不要只交给 CC“自己找”。
   - **本地事实锚点**：把 Hermes 已发现的 qmd hits（文件路径 + 1 行 relevance）列入 context；要求 CC 读原文件或 qmd 命中片段，并在最终文档列“本地知识库参考”。

2. 启动 CC tmux 长会话，加载 `strategic-insight-longform` skill

3. **必须在 context 文件中写明 worker timeout 规则：**
   ```
   Agent team workers 超时10分钟视为失败，Leader直接进入汇编。
   ```

4. CC 会用并行 Worker + CoV 验证机制，产出深度战略洞察

### Phase 3（可选）：CC RCA 诊断

如果需要分析为什么 Phase 1 的研究存在事实偏差：
1. 写 context 文件，对比 Phase 1 和 Phase 2 的事实差异
2. 让 CC 做根因分析，输出诊断报告
3. 根据诊断结果优化 web-research-router 技能

## 本会话案例对比

| 维度 | Hermes deep loop | CC strategic-insight |
|------|:---:|:---:|
| 蚂蚁阿福用户量 | "1亿+用户" ❌ | MAU 3000万 ✅ |
| Benchmark 叙事 | "全球第一" 单源采信 ❌ | 发现 HealthBench 百川M3 冲突 ✅ |
| 医保政策 | 笼统"政策红利" ❌ | 12个项目全是影像类 ✅ |
| Anthropic Healthcare | 完全遗漏 ❌ | 跨语言补搜召回 ✅ |

## 教训

- Hermes deep loop 适合广扫和信息收集，不适合独立事实验证
- 凡涉及"深度评估/战略洞察"的任务，Phase 1 完成后必须进入 Phase 2
- CC 的 CoV（Chain of Verification）+ 并行 Worker 是质量跃升的关键杠杆
- Context 文件中必须写 worker timeout 规则，否则可能无限等待
- **OB/qmd 不是可选背景**：如果用户要求“调阅 OB / 使用 qmd / 参考本地艾大力资料”，Hermes 必须先查 qmd collection 并把多轮 query 与命中文件路径写入 CC context。单个复合 query 无结果不等于本地无资料；要拆成实体词、平台词、业务词多轮检索。

## qmd/Obsidian 本地知识注入模板

在 CC context 中加入如下块，替换 query 与路径：

```markdown
## Local Obsidian/qmd requirement

- qmd collection: `alexcai-vault`
- 必跑检索：
  - `HOME=/Users/alexcai qmd search "<公司/项目名>" --collection alexcai-vault`
  - `HOME=/Users/alexcai qmd search "<平台/能力词>" --collection alexcai-vault`
  - `HOME=/Users/alexcai qmd query "<公司> <业务域> <平台> <目标>" --collection alexcai-vault`
- Hermes 已发现的候选 OB 文件：
  - `<relative/path/to/note.md>` — `<why relevant>`
- CC 必须读取这些 OB 文件或 qmd 命中片段，并在最终文档列出“本地知识库参考”。
- 单 query 未命中时不得停止；拆成实体词/平台词/业务词继续检索。
```
