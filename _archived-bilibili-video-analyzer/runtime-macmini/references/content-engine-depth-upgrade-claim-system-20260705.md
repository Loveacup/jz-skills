# 内容引擎深度升级：从摘要生成器到主张系统（Claim System）

> 记录：2026-07-05 用户反馈当前 bilibili-video-analyzer 输出“分析深度不够”，经对照用户方法论（战略洞察长文完整方法论 v5.5 + Research Fortification v2.0.2）与外部参考（William Gieng 的 transcript-analysis-pipeline、BiliInsight）后形成的升级方向。

## 问题诊断

当前 pipeline 本质上仍是“单视频一次性摘要生成”：
- LLM 直接按 8-section 模板写散文；
- 证据（字幕/评论/弹幕）与分析结论之间没有显式结构；
- QA gate 只能拦截“差”的输出，无法把“流畅但支撑不足”的内容降级。

这导致用户反馈的四个问题同时出现：
1. 像摘要——因为没有“观察→推理→结论”的强制跳跃；
2. 缺因果链——因为段落内不强制 A→B→C；
3. 证据密度低——因为 ASR chunk 大、引用稀疏、无来源分级；
4. 部分 section 无 LLM writer——因为 writer 覆盖不完整。

## 方法论交集

| 来源 | 核心思想 | 在本项目的落点 |
|---|---|---|
| 战略洞察长文完整方法论 v5.5 | 结构密度 ≥ 信息密度；H-V 双轴 × S-T-D 立方体；Toulmin 论证六要素；三次受控跳跃（发现→判断→情景→启示） | 把每个 section 改造成 `claim + grounds + warrant + backing + qualifier + rebuttal` 结构；强制相乘判据 |
| Research Fortification v2.0.2 | 外置透镜诊断；additive-first 加固；warrant/backing 分层；G1-G4 质量门 | 在 QA 之后加一层“审计”：外部子 agent 审查每个 claim 的支撑，只能弱化不能增强 |
| William Gieng 2026-05 | LLM summarizers skip the identification step；主张必须声明 observed / inferred / recommendation；审计只能 delete/downgrade/move/replace/collapse | 引入 identification 层：每个 claim 先声明证据类别，再进入渲染 |
| BiliInsight (Xuuuuu04) | 多模态输入（字幕+关键帧+弹幕+评论+统计+相关视频+UP 主系列）；deep research 聚合 20+ 视频；prompt 强调长段落、深度成因、多方对比 | 提升输入源广度；单视频分析后可扩展为多视频聚合研究 |

## 推荐升级方向

### 轻量版（先验证）

1. 在现有 writer prompt 中强制“三段式”：
   - 观察（素材中的具体事实/数据/引语）
   - 推理（A→B→C，为什么这些观察能推出结论）
   - 结论（限定强度 + 可行动建议）
2. 新增 `audit_claims()`：用独立子 agent 审查每个 section 的 claims，只能降级或删除，不能改写增强。
3. 扩展 QA gate：D4（insight-density）升级为检查“因果词 + 推理链显性化”。

### 完整版（架构重构）

引入显式 claim 数据结构：

```python
class Claim:
    statement: str
    grounds: list[str]  # 证据指针，如 [E3] 或 MM:SS 时间戳
    warrant: str        # 为什么 grounds 支持 statement
    backing: str        # warrant 的学术/行业/方法论语境
    qualifier: str      # 置信度/限定条件，如“推测/待证”
    rebuttal: str       # 什么情况下不成立
    label: Literal["observed", "inferred", "recommendation"]
```

Pipeline 改为：

```
transcript + social data
    ↓
extract_claims()          # 保守提取显式事实、主张、数量、承诺
    ↓
synthesize_section_claims() # 按 section 生成 labeled claim objects
    ↓
audit_claims()             # 只能弱化/删除/标记证据不足
    ↓
render_claims()            # claim objects → 可读 prose + 引用标签
    ↓
publish_markdown()
```

### 多模态/多视频输入（提升证据密度）

- 关键帧：与 BiliInsight 一致，只在画面中明确看到的元素才写入报告；
- 弹幕/评论：继续做情绪与舆情分析，但输出改为“claim + 证据”形式；
- 相关视频/UP 主系列：为 deep research 模式做准备；
- 统计/标签：作为 claim 的 backing 或 qualifier。

## 实施顺序建议

1. 先在现有 LLM writer prompt 中强制“观察→推理→结论”三段式（轻量版）。
2. 跑真实样片验证用户是否觉得“深度提升”。
3. 若仍不够，再引入显式 `Claim` 数据结构和 `audit_claims()`。
4. 最后扩展多模态/多视频输入。

## 参考来源

- `20-Areas/00-方法论/20_战略洞察&研究强化/战略洞察长文完整方法论_双轴立方体v5.5_20260703.md`
- `20-Areas/00-方法论/20_战略洞察&研究强化/research-fortification-skill-方法论方案_20260609.md`
- William Gieng, “LLM Summarizers Skip the Identification Step”, Towards Data Science, 2026-05-10
- github.com/williamgieng/transcript-analysis-pipeline
- github.com/Xuuuuu04/bilibili-analysis-helper
