# BiliInsight 交叉参考：为什么它的输出看起来“更深”

> 记录：2026-07-05 用户指出“GitHub 上之前的老版本效果非常好”。经拉取 `github.com/Xuuuuu04/bilibili-analysis-helper` 分析其 prompt 和架构，记录可借鉴点与边界。

## BiliInsight 核心结构

仓库：`Xuuuuu04/bilibili-analysis-helper`（BiliInsight）
Stars：55，创建于 2025-12-19，Python + FastAPI + OpenAI 工具调用。

主要模块：
- `src/backend/services/ai/prompts.py`：提示词集中管理
- `src/backend/services/ai/agents/deep_research_agent.py`：多轮工具调用 Agent
- `src/backend/http/usecases/analyze_service.py`：视频分析服务

## 单视频分析 prompt 特点

对单个视频，强制三大板块：
1. 内容深度总结与分析（核心概览 + 结构化内容详述 + 关键知识点与深度见解）
2. 弹幕互动与舆情分析（氛围洞察、情绪曲线、热梗解读、互动冲突）
3. 评论区深度解析与建议（用户画像、观点碰撞、舆情风险与优化建议）

强制要求：
- 禁止碎片化，必须长篇幅连贯段落；
- 每个核心发现从“现状描述、深度成因分析、多方观点对比、未来趋势预测”展开；
- 大量引用具体数据、画面细节、典型评论和弹幕热梗；
- 文内引用必须带 Markdown 链接或脚注；
- 严格防幻觉：仅限素材，禁止推测，画面冲突以画面为准。

## Deep Research 模式特点

对研究课题，强制：
- 拆分至少 5 个互补研究维度；
- 批量并行分析视频（同一轮发起多个 `analyze_video`）；
- 至少深入分析 20 个 B 站视频；
- 覆盖高赞、普通用户测评、争议吐槽、技术拆解、长尾低播放量视频；
- 结合高赞评论和弹幕热梗分析舆情；
- 收尾前自检：≥20 视频、多维度覆盖、足够数据点、交叉验证消除偏见。

## 为什么看起来“更深”

1. **输入源更广**：关键帧、弹幕、评论、统计、标签、相关视频、UP 主系列都进入 prompt；
2. **Prompt 更强调深度展开**：禁止碎片化、强制长段落、强制深度成因和多方对比；
3. **多视频交叉验证**：deep research 聚合 20+ 视频，幸存者偏差被主动抑制；
4. **引用纪律更强**：文内引用必须带链接/脚注，倒逼证据锚定。

## 局限性

1. **仍是一次性生成**：没有显式 claim 对象，没有“审计只能弱化”的机制；
2. **不区分 observed/inferred/recommendation**：所有结论混在一起，可能产生流畅但支撑不足的内容；
3. **成本更高**：deep research 模式每课题 20+ 视频，token 消耗大；
4. **不产结构化 Obsidian 资产**：输出是报告，但无固定 8-section 模板和 YAML frontmatter。

## 对本项目的借鉴

1. 在现有 8-section 模板中吸收“禁止碎片化、长段落、深度成因、多方对比”的写作纪律；
2. 把关键帧、弹幕、评论、统计等作为 claim 的 grounds 或 backing；
3. 未来 deep research 模式可参考其“多视频聚合 + 批量并行 + 自检清单”的编排；
4. 不要照搬其一次性生成本质，而是把它的输入广度和写作纪律嫁接到我们的 claim system 架构上。

## 参考文件位置

- `/tmp/bili_insight_ref/src/backend/services/ai/prompts.py`
- `/tmp/bili_insight_ref/src/backend/services/ai/agents/deep_research_agent.py`
- `/tmp/bili_insight_ref/src/backend/http/usecases/analyze_service.py`
