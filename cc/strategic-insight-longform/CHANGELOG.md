# Changelog

## v5.0.0 (2026-05-31) — CC 原生语义反转 + 四层质量门 + 双轴方法论

### 破坏性变更（major bump 原因）

#### 1. CC 原生语义反转
- 删除 SKILL.md 顶部「Hermes 兼容层」主路径声明，Hermes 映射下沉为底部脚注
- 删除 160 行 Python 伪代码，下沉到 `references/agent-pipeline.md` 并改写为 CC 原生
- 删除全部自造 verb：`dispatch_teammate / wait_task / wait_all / run_script / broadcast_shutdown`
- 统一为 CC 工具白名单：`TeamCreate / TaskCreate / Task / TaskGet / TaskUpdate / TaskStop / SendMessage / Monitor / TeamDelete / Read / Write / Edit / Bash / WebSearch / WebFetch / Skill`
- 修复 `Skill()` 调用签名：`Skill(skill="obsidian-md-ac", args=...)` 三参数模板
- 16 agent 的 YAML `tools:` 字段全部统一为 CC 原生命名（MCP 工具下沉到说明段）
- 修复 `memory_reader.py` v3.0 老路径硬编码 → `${SKILL_DIR}/scripts/memory_reader.py`
- 修复 Stage 2 依赖错位：拆 Stage 2a（spatial+temporal+domain 并行）+ Stage 2b（stakeholder+causal，blocked_by 2a）

#### 2. 四层质量门 + Red Flags 预拦截
- **Red Flags 8 条**：SKILL.md 顶部前置拦截（主题 < 8 字 / 素材单一 / qmd+Exa 双空 / CoV 低于阈值 / 字数异常 / 标题偏离 / 政治敏感）
- **L1 硬扫**（output-finalizer 首段）：AI 词黑名单 + 教科书开头 + 禁止标点，命中阈值 = 0
- **L2 风格自检**（longform-writer 内置）：段长方差 ≥ 0.40 / 伏笔回收 ≥ 70% / 重复论点 = 0
- **L3 内容终审**（output-finalizer 中段）：论证链 ≥ 90% / CoV 引用 ≥ 95% / URL 可达 ≥ 85% / 交叉验证 ≥ 70% / HKR ≥ 3.5 / 引用密度 1 条/400 字 ±30%
- **L4 活人感**（output-finalizer 末段）：软违规自动调 `Skill(skill="de-slop", args="检测并改写以下文本的AI味：{text}")`；硬违规 SendMessage 回 writer
- **neat-freak**：膨胀比 ≤ 5.0 / 单章节占比 ≤ 35%
- **统一 verdict JSON Schema**：`{gate, pass, score, subscores, blocking, next_action}` 包裹在 `<verdict></verdict>`，Leader regex + json.loads 自动路由
- **任何 Gate 不死锁**：累计回炉到上限标记低置信度放行 + 评分扣分 + 报告告警
- 新建 `references/quality-gates.md`（重构自 `quality-checklist.md`，删除原 9 节布尔表）
- 新建 `references/anti-ai-blacklist.md`（L1 扫描词表 + 教科书开头 + 禁止标点）

#### 3. 双轴方法论显式嵌入
- 新建 `references/dual-axis-methodology.md`（纵轴 5 步模板 + 横轴 A/B/C 决策树 + 横纵交汇 5 问 + 三剧本输出 + 与 S-T-D 关系）
- `framework-library.md` 头部新增 analysis_type → 框架推荐路由表（6 条映射）+ 新增「双轴框架」一级条目
- `framework-builder` 输出 `multi-dim-framework.md` frontmatter 强制声明 `axis_type: std-cube | dual-axis`，作为下游 researcher 分流契约
- `spatial-researcher` 接入横轴 A/B/C 决策树（0 / 1-2 / 3+ 竞品三分支）
- `temporal-researcher` 接入纵轴 5 步模板（起源 / 诞生 / 演进 / 决策逻辑 / 阶段划分，硬区间 6000-15000 字）
- `insight-synthesizer` 新增「横纵交汇洞察」输出模板（与 S×T/S×D/T×D 并存）
- `std-cube-methodology.md` 末尾新增「与双轴的关系」段

#### 4. 取消三模式分支
- 删除 Deep / Standard / Quick 三模式，统一为「火力全开」单一执行流
- 删除 SKILL.md 「Execution Modes」节、`config.json` `execution_modes` 字段、agent .md 内所有 `if mode == "deep"` 类条件分支
- 全 16 agent 默认启用（包括原 optional/ 下的 5 个）
- 估算：12-20 分钟 / 86-136k output token

### 新增

- `references/agent-pipeline.md`（CC 原生执行流完整伪代码 + 失败恢复 + 超时治理）
- `references/quality-gates.md`（L1-L4 + Red Flags + neat-freak 量化阈值 + verdict schema + 失败回路图）
- `references/anti-ai-blacklist.md`（L1 黑名单 + 教科书开头 + 禁止标点）
- `references/dual-axis-methodology.md`（双轴方法论 + Worked Example）
- `config.json` 新字段：`quality_gates / neat_freak / task_timeouts / skill_invocations`，`frameworks.analysis_type_routing`
- TaskUpdate 心跳协议（每 90 秒 / 阶段切换 / 完成时），所有 16 agent 内置
- Verification Checklist（Leader 自检 10 条）
- description 加 8 条 DO-NOT trigger 反例（事实查询 / 翻译 / 邮件 / 代码 / 摘要 / 概念解释 / PPT / 主观偏好）

### 变更

- `SKILL.md`：513 行 → 306 行（下沉 254 行到 references，新增 ~140 行 Red Flags / Decision Tree / CC Dispatch / Quality Gates / Verification Checklist）
- `source-citation-guide.md`：新增「引用密度阈值」小节（1 条/400 字 ±30%）
- `output-finalizer.md`：重构为 L1 → L3 → L4 三段
- `longform-writer.md`：内置 L2 自检 + neat-freak 三原则 + 章节硬字数区间，文末输出 `<l2-verdict>`
- `source-manager.md`：CoV verdict 标准化（每层输出统一 JSON）+ Stage 3.5 早期触发钩子（L1 < 60% / L2 死链 > 40%）
- `memory-curator.md` + `pattern-crystallizer.md`：v3.0 老路径修正为 `${SKILL_DIR}/...`

### 移除

- `references/quality-checklist.md`（被 `quality-gates.md` 替代）
- `config.json` `execution_modes`（被 `execution.mode: full_power` 替代）
- 全部 agent .md 中 `agents.*.modes` 字段（火力全开后无意义）
- 精简版 `~/.hermes/profiles/regent/skills/strategic-insight-longform/` 归档（完整版同步 compliance 改造后无差异化价值，详见归档说明）

### 版本号说明

三项破坏性变更（CC 语义反转 + 四层质量门 + 双轴显式嵌入）+ 模式精简，符合 major bump（v4.2 → v5.0）。

---

## v4.2.0 (2026-02-21) - 框架扩展 + 格式美化版

### 新增

#### Obsidian 格式美化 (Stage 6.5)
- Leader 在 output-finalizer 之后直接调用 `obsidian-md-ac` skill 执行格式美化
- 美化内容：emoji 标题、==高亮==、Mermaid 图表、callouts、YAML 合规、链接关系分析
- 所有模式（Deep/Standard/Quick）均执行

#### 框架模型库扩展
- 新建 `references/framework-library.md`，收录 ~75 个分析框架
- 10 大类别：战略规划(A)、竞争分析(B)、营销增长(C)、商业模式(D)、组织管理(E)、创新方法(F)、思维工具(G)、宏观环境(H)、心理行为(I)、财务估值(J)
- framework-builder 升级为"必选 + 补充"二层选择机制
- 按 analysis_type 自动推荐补充框架（3-5 个），总计 6-8 个框架

### 变更
- `config.json`: version 升级到 4.2.0，frameworks 改为 core/supplementary/pre_enabled 三层结构，新增 obsidian_formatting 配置节
- `framework-builder.md`: 新增框架选择协议，从 references/framework-library.md 选择补充框架，输出新增"七、补充分析框架"章节
- `output-finalizer.md`: 审核清单新增 Obsidian 格式检查项（仅供验证参考，实际由 Leader Stage 6.5 执行）
- `SKILL.md`: 工作流架构图新增 Stage 6.5 格式美化步骤，执行逻辑新增 skill 调用

---

## v4.1.0 (2026-02-21) - Agent Team + 单文件输出版

### 架构变更
- **Agent Team 协调**：从独立 Task 调度迁移到 TeamCreate/TaskCreate/SendMessage 团队协调
  - Leader 通过 TaskList 监控进度
  - Agent 间通过 SendMessage 通信
  - 并行阶段（Stage 2）多 teammate 同时执行
- **单文件输出**：所有输出整合到唯一文件 `战略洞察-{提炼的主标题}.md`
  - 来源索引作为"附录：来源索引"整合到文末
  - 思维链内嵌到文章正文（主思维链 + 分章节 callout）
  - 不再生成独立的思维链、来源索引、执行摘要、质量报告、PPT大纲
- **文件命名**：`[主题]-战略洞察.md` → `战略洞察-{提炼的主标题}.md`

### 新增

#### 修订循环机制
- output-finalizer 审核后判断：评分 >= 4.0 且无❌项直接输出，否则 SendMessage 反馈给 longform-writer
- 最多 1 轮修订，避免无限回路

#### 论证质量检查
- output-finalizer 新增论证质量维度：逻辑跳跃、隐含假设、反证考虑、置信度标注、证据-结论匹配

#### 思维链内嵌
- 主思维链：全息摘要之后的专门章节（问题定义/框架选择/核心假设/推理路径/局限性）
- 分章节思维链：每个主要章节内以 `> [!ABSTRACT] 本章推理路径` callout 呈现

#### 洞察层级保真
- longform-writer 禁止压缩或省略 insight-synthesizer 的多层推论链
- 一阶→二阶→三阶推论、反事实分析、交叉矩阵洞察必须完整保留

### 变更
- `config.json`: output_formats 改为单文件配置，新增 revision_loop 配置，cot output_mode 改为 embedded_in_article
- `longform-writer.md`: 移除 writing-reasoning.md 输出，新增思维链内嵌+来源索引附录+洞察保真规则
- `source-manager.md`: 输出改为 source-verification.json（结构化 JSON）
- `output-finalizer.md`: 单文件输出+主标题提炼命名+修订循环+论证质量检查
- `SKILL.md`: 主工作流重写为 Agent Team 协调模式

### 移除
- `writing-reasoning.md` 独立输出
- `source-report.md` 独立输出
- `source-reasoning.md` 独立输出
- `executive-summary.md` 独立输出
- `quality-report.md` 独立输出
- `ppt-outline.md` 独立输出
- `sources-appendix.md` 独立输出

---

## v4.0.0 (2026-02-21) - 多模式自适应版

### 新增

#### 问题澄清预处理 (P0)
- **question-refiner** Agent (Pre-Stage -1): 意图清晰度评估 + 结构化 Prompt 生成
- confidence >= 0.8 时自动跳过问询，< 0.8 时通过 AskUserQuestion 提 3-5 个结构化问题
- 5 大类澄清问题：核心研究问题、范围边界、输出需求、来源偏好、特殊要求
- 输出 question-context.json 供下游 Agent 使用

#### CoV 反幻觉验证 (P0)
- source-manager 升级为三层验证机制：
  - Layer 1: 引用完整性检查（扫描所有事实声明，目标 100% 覆盖）
  - Layer 2: 来源可达性验证（crawling_exa 检查 URL，标记死链+幻觉红旗）
  - Layer 3: 关键声明交叉验证（提取 5-10 关键声明，web_search_exa 独立佐证）
- 输出验证报告：✅已验证 / ⚠️存疑 / ❌矛盾 + 整体可信度评分 (0-10)

#### 搜索迭代精炼 (P1)
- 5 个 researcher Agent 增加迭代搜索协议（最多 3 轮）
- 信噪比评估机制（0-1），signal < 0.6 时自动触发精炼搜索
- 每轮搜索记录：query、工具、结果数、信噪比、采取动作
- 各 Agent 按研究维度微调调整策略

#### GoT 自适应路径优化 (P2)
- **got-controller** Agent (Stage 1.5): Graph of Thoughts 路径评估
- 4 步流程：Generate(5) → Score → KeepBestN → 资源分配
- 评分标准：数据可获得性(0-3) + 主题契合度(0-3) + 洞察潜力(0-2) + 差异化价值(0-2)
- 路径决策：8-10 强化 / 6-7 标准 / 4-5 精简 / 0-3 跳过
- 3 种执行策略：Balanced / Breadth-First / Depth-First

#### 多模式执行 (P1)
- 恢复三模式支持（默认 Deep）：
  - Deep（默认）：16 Agent + GoT + CoV，12-20 分钟
  - Standard：9 核心 Agent，7-10 分钟（需用户显式指定）
  - Quick：5 核心 Agent，3-5 分钟（需用户显式指定）

### 架构变更
- Agent 总数: 14 (v3.1) → 16 (v4.0)
  - 新增: question-refiner, got-controller
- 新增配置节: search_iteration, got_controller, cov_verification, question_refiner
- 来源要求按模式分层: deep 5+/standard 3+/quick 2+
- 搜索迭代按模式分层: deep 3轮/standard 2轮/quick 1轮

---

## v3.1.0 (2026-02-08) - Deep-Only 深度版

### 架构变更
- **移除 fast/standard 模式**，仅保留 deep 模式作为唯一执行模式
- 所有 14 个 Agent 强制启用，无可选 Agent
- 6步思维链+元认知反思为默认（无简化版本）

### 增强
- 所有分析维度默认拉满：二阶/三阶推论、反事实分析、跨维度交叉矩阵
- 记忆/知识增强/学习系统始终启用，无条件判断
- WebSearch 始终执行（不再限于 deep 模式）
- 来源要求提升至 5+ 独立来源，每层 3+ 数据点
- stakeholder-analyst 和 causal-analyst 从可选变为必需

### 移除
- fast 模式（3步简化思维链、精简流程）
- standard 模式及其条件触发逻辑
- 所有 Agent 的 fast_mode_compatible 字段
- 所有 optional Agent 的 trigger_conditions

---

## v3.0.0 (2026-02-08) - 记忆增强版

### 新增

#### 执行模式
- **deep 模式**: 10-15分钟全维度深度分析，自动触发词支持
- deep 模式下 stakeholder-analyst 和 causal-analyst 强制启用
- 6步思维链 + 元认知反思 (full_with_metacognition)

#### 记忆系统 (6 个 JSON 文件)
- `memory/topics.json` - 分析主题历史
- `memory/sources.json` - 可靠来源数据库
- `memory/frameworks.json` - 框架效果跟踪（预填充 6 个框架）
- `memory/sessions.json` - 会话历史（最近 50 条）
- `memory/preferences.json` - 用户偏好
- `memory/patterns.json` - 学习模式库

#### 知识增强
- **knowledge-enricher** Agent (Stage 0.5): qmd vsearch + 历史分析 + WebSearch (deep)
- 输出 `knowledge-context.json` 供全流程使用
- qmd 不可用时优雅降级

#### 学习系统
- **memory-curator** Agent (Stage 7): 记忆更新 + 模式衰减
- **pattern-crystallizer** Agent (Stage 7): 模式结晶（≥3 未分析 sessions 自动触发）
- 5 种模式类型: framework_effectiveness, source_reliability, writing_optimization, analysis_depth, topic_association
- 置信度阈值: ≥0.85 自动生效, 0.70-0.85 待确认, <0.70 丢弃

#### Python 脚本
- `scripts/memory_reader.py` - 记忆上下文读取器（主题匹配 + 框架推荐 + 来源排序）
- `scripts/memory_writer.py` - 记忆持久化写入器（write-then-rename 原子写入）
- `scripts/pattern_analyzer.py` - 跨会话模式分析器

#### 参考文档
- `references/memory-schema.md` - 记忆 JSON Schema 文档
- `references/qmd-setup-guide.md` - qmd 向量检索部署指南

### 增强

#### Agent 增强 (9 个)
- **topic-preprocessor**: +记忆读取, +历史匹配, +deep 触发词检测
- **framework-builder**: +知识上下文, +框架推荐（基于历史效果）
- **spatial-researcher**: +知识参考, +来源记忆, +deep 增强（3+数据点/案例）
- **temporal-researcher**: +知识参考, +来源记忆, +deep 增强
- **domain-researcher**: +知识参考, +来源记忆, +deep 增强
- **insight-synthesizer**: +二阶/三阶推论, +跨维度交叉矩阵(S×T/S×D/T×D), +反事实分析
- **longform-writer**: 取消字数限制, +Wikilinks 嵌入, +deep 附录, +历史回顾开篇
- **output-finalizer**: +Wikilink 验证, +内容完整性检验（替代字数检查）, +deep 专项检查
- **source-manager**: +来源记忆读写

#### 配置增强
- `config.json` 新增 `memory`, `knowledge`, `learning` 三个配置节
- deep 模式完整配置（trigger_words, forced agents, metacognition CoT）

#### 质量检查
- `quality-checklist.md`: 字数检查改为内容完整性检验, 新增 deep 模式检查项

### 不变
- fast/standard 模式行为与 v2.1 完全兼容
- stakeholder-analyst.md, causal-analyst.md 不修改（仅通过 config.json 在 deep 模式强制启用）
- std-cube-methodology.md, obsidian-format-guide.md, source-citation-guide.md, cot-templates.md, cot-template.md 保持不变

### 架构变更
- Agent 总数: 11 (v2.1) → 14 (v3.0)
  - 核心: 8 → 9 (+knowledge-enricher)
  - 可选: 3 → 5 (+memory-curator, +pattern-crystallizer)
- 新增目录: `memory/`, `scripts/`
- 新增文件: 17 个
- 修改文件: 10 个
- 保留文件: 7 个

---

## v2.1.0 (2025-12-31) - 优化版

- Agent 精简: 14 → 11 个（合并 input-processor+topic-analyzer, source-tracker+source-validator）
- 新增快速模式: 3-5 分钟
- 模块化架构: config.json + 模板系统
- 智能调度: 可选 Agents 按需启用
- 进度反馈: 实时进度显示
- 性能提升: ~30% 速度提升
