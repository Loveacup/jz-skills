---
name: destiny-matrix
description: 以人为本的传统文化与心理反思命书技能：八字、紫微、占星与人格资料各自完整解读，再围绕读者的问题做跨体系综合，写成有阅读价值、按证据边界发布的 HTML+PDF 命书；支持完整或专题任务，含关系与指定时间主题。触发词：命运分析、命理解析、命书、八字、紫微斗数、星盘、荣格八维、认知功能、人格分析、大运流年、合盘、BaZi、cognitive functions。
metadata:
  version: 5.1.0
  last_updated: 2026-09-28
---

# Destiny Matrix · v5.1.0

## 目标

四体系各自完整解读，以人的问题组织跨体系综合，写成有阅读价值的命书（HTML 与 PDF）。八字、紫微、占星各按本体系的推读路径讲清本盘结构、推读依据与含义；人格资料按原构念解释；综合回答读者关心的同一问题，说明各视角各自增加了什么理解。人格可以是默认阅读入口，但不是其他体系必须围绕的主答案；默认八主题是导航，不是等分篇幅或八章配额。保留传统体系的文化解释、人文文风和非决定论表达。

严格区分用户报告、测量结果、计算事实、传统解释、心理假说和实践选项。计算正确不代表个体解释已获科学验证；体系间相似也不构成效度证据。

## 启动

1. 识别当前运行时，读取对应的 `references/runtime-omp.md` 或 `references/runtime-cc.md`。
2. 读取唯一编排规范 `references/team-orchestration.md`，按 S0–released 流程执行；该规范决定依赖、隐私、复用、修订和状态迁移。
3. 用 `scripts/doctor.py --json` 确认技能根目录、依赖与可用运行能力；之后通过其返回的 `$DM_PY` 执行脚本。具体命令只从编排规范读取。
4. 派遣角色前完整读取对应 `agents/<role>.md` 及角色文档列出的依据。不要把角色合同全文复制进主提示或创建第二份流程规范。
5. 按条件读取下方参考索引；只加载当前主题、计算方法或验收所需资料。

## 关键红线

- 用户请求和 `scope` 决定主题。资料不足时补问或列明待接受限制，不静默缩小范围，不填造输入、量表、经历、计算值、来源或测量精度。
- NERIS 五维、自述类型、16 亚型及八功能分数保持原构念；无核准换算规则时不得相互推导。出生盘不能生成八维人格测量、能力评分或心理诊断。
- 用户历史事件只作背景，不反向校准出生时刻或宣称预测命中。未计算的月份、行运、推运不得写成已完成分析。
- 默认不向外部服务提交个案数据，不自动保存原始个案。外传需用户针对具体站点与字段明确授权；无授权不得宣称完成个案独立验盘。
- 按输入年龄与受众执行适龄合同。未成年人关系主题谈家庭、同伴、师长与边界，事业主题谈学习和兴趣；不推测未来婚恋、性化结论、疾病或生育结果。
- 引文逐条核实来源和支持范围；没有最低引用数量。未核实的原话不能署名或加引号。
- 图表数量、篇幅比例、章节数量、星级或评分均不构成质量目标。图表仅呈现真实输入、计算结果或有依据的定性关系。
- HTML 正文、必要披露与附录按语义结构发布；关键限制不能只藏在折叠内容中。每次 HTML 改动都使旧 PDF 与 PDF 验收失效。
- 发布必须通过 S9 终审、S10 实际 PDF 检查及哈希一致性。必过项失败时阻断；不降级交付。

## 条件索引

### 流程与验收

| 条件 | 唯一依据 |
|---|---|
| Leader 编排、输入契约、阶段依赖、盲审隔离、复用、预算、状态机、角色档位 | [`references/team-orchestration.md`](references/team-orchestration.md) |
| 当前环境 / 工具调用方式 | [`references/runtime-omp.md`](references/runtime-omp.md) 或 [`references/runtime-cc.md`](references/runtime-cc.md) |
| 终审 16 项、合法 na/deferred、阻断条件 | [`references/locked-checklist.md`](references/locked-checklist.md) |
| 来源与直接引文核验 | [`references/external-verification.md`](references/external-verification.md)、[`references/sources.json`](references/sources.json) |
| HTML 内容结构、样式、图表可读性与打印 | [`references/output-template.md`](references/output-template.md) |
| 图表模式及语义图表设计 | [`references/chart-patterns.md`](references/chart-patterns.md) |
| intake、计算结果、证据、评审、目录或发布校验 | `schemas/intake_brief.json`、其他对应 `schemas/*.json`、`scripts/quality_contracts.py` 与角色合同 |

### 按主题加载

| 任务 | 阅读 |
|---|---|
| 人格资料、Beebe 理论、访谈或认知功能 | `references/character-first-manifesto.md`、`character-inference-workflow.md`、`cognitive-functions.md`、`jung-classical-texts.md`（推读路径在 `cognitive-functions.md`） |
| 八字 | `references/bazi-framework.md`（独立推读路径）、`shensha-table.md`、`classical-texts.md` |
| 紫微 | `references/ziwei-framework.md`（独立推读路径）、`special-patterns.md` |
| 占星 | `references/astrology-framework.md`（独立推读路径）、`classical-texts.md` |
| 多体系综合 | `references/cross-analysis-patterns.md`（主题综合顺序与新增理解要求） |
| 成书文风、作者素材与缺口回提 | `agents/book-writer.md`；呈现与版式见 `references/output-template.md` |
| 双人关系 / 合盘 | `references/relationship-analysis.md`、`jung-relationship-dynamics.md` |
| 指定年份或月份 | `references/liunian-analysis.md` 与已实际计算的时间数据 |
| 健康、事业、行动建议 | `references/character-inference-workflow.md` 及本案明确请求、claims 与限制 |

### 脚本与角色

计算、契约校验、HTML 检查、受限修订和 PDF 导出的唯一命令签名见 `references/team-orchestration.md`。角色索引在 `agents/`：S0 `intake-refiner`；S1 `caster`；S2/S4C `external-verifier`；S3 四位 analyst；S4 四位 judge 与 `chief-judge`；S5 `synthesizer`；S6 `love-specialist` / `growth-specialist`；S7 `chart-director`；S8 `book-writer`；S9/S10 `book-finalizer`。

私有运行记忆只读 `memory/known-issues.md` 与 `memory/conventions.md` 的现行约定；其中清楚标为已废弃的历史记录不得作为操作指令。公开资料不含个案姓名、个案资料或私有绝对路径。
