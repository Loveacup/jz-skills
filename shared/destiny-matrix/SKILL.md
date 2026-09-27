---
name: destiny-matrix
description: 性格本位的多维命运深度解析框架（v4 · Agent Team 版，Claude Code / omp 双端）。立场：性格决定命运，玄学辅证，命运可塑。荣格八维为主语刻画"性格签名"，八字解构能量、紫微对应舞台、占星映照节律；玄学不预言，只印证、映照、解释。v4 以 Leader + 18 teammate 的 Stage DAG 运行：排盘 → 外部验盘 → 四维分析 → 判官复核 → 综合 → 专题 → 图表规划 → 成文 → 锁定清单终审 → HTML+PDF 双产物交付。触发词：命运分析、命理解析、八字、紫微斗数、紫微命盘、星座分析、荣格八维、认知功能、人格分析、大运流年、合盘、夫妻宫、BaZi、cognitive functions。
metadata:
  version: 4.1.0
  last_updated: 2026-09-27
---

# 多维命运深度解析 · v4 · Agent Team 版

## 核心理念（哲学骨架，每次分析必先内化）

**性格决定命运，玄学辅证，命运可塑。**

1. **性格是主语**：荣格八维 / Beebe 八原型给出"性格签名"，这是恒量；八字、紫微、占星是「谓语与状语」，用来解释"为什么是这种性格 / 这种性格如何在时代节律里展开"。
2. **玄学辅证**：玄学体系不"决定"任何事，它"印证 / 映照 / 解释"性格的展开路径。一次分析的可信度由"玄学三维对性格签名的印证度"评估。
3. **命运可塑**：性格可发展（Jung 个体化进程 CW 9i §490；成人大脑可塑性），因此命运不是预定剧本而是默认路径。每一份命书必须给出可塑路径与具体行动。

详见 `references/character-first-manifesto.md`（哲学锚点，每次开篇必读）。

**v4 的新增誓言——工程与文气并举**：v4 的全部工程化手段（DAG / 锁定清单 / 校验脚本 / 图表配额）只管三件事：**不缺、不崩、不假**。命书的文艺感与调性是本 skill 的核心资产，任何工程约束不得以牺牲文风为代价（详见「调性红线」一节）。

---

## 🚨 Red Flags（执行前默念）

| 若你（Leader / teammate）想… | 现实检验 |
|---|---|
| 「这章素材少，图表少配几张算了」 | 配额是下限不是参考。素材少标注「数据边界」，配额照满。 |
| 「Leader 顺手把命书写了吧」 | **越权代写是模块缺失头号元凶**。成文必须派 book-writer 独立完成，Leader 只路由不代笔。 |
| 「判官看一眼成稿更高效」 | 判官只接收排盘 JSON。读了成稿 = 叙事传染 = 复核作废，输入污染即中止上报。 |
| 「SVG 手写一下就行，不用查模式库」 | 案例A版翻在一个 `r="0"` 上，人眼审三遍没发现。骨架从 `chart-patterns.md` 取，落笔过 C4。 |
| 「这条典籍引文大概是《滴天髓》说的」 | **伪引用是最高级 🔴**。引用池以 references 各文件 v4 增补核准条目优先；未核实页码降级为章节/概述级引用。 |
| 「外部排盘网站结果不一致，取本地的就行」 | 走仲裁三步（第二源 → 口径核查 → 披露不强裁），禁止静默取舍。 |
| 「校验清单差一两项，先交付吧」 | locked-checklist 🔴（M/C 组）→ fresh writer 修订；🟠（W1/E4/P1）→ 交付阻断定点修补。没有「差不多」。 |
| 「时辰存疑，那就按最可能的写死」 | 「时辰假设」必须顶部标注，宫位/时柱论断降权，双候选并示。 |
| 「修订让原 writer 顺手改」 | 被拒稿留在上下文会结构性传染。修订 = 全新 book-writer 实例干净上下文，不给被拒章节原文。 |
| 「质检凭感觉打个分」 | 禁拍分。逐项过 `references/locked-checklist.md` 固定 ID，pass/fail + 强制引证，先判定后聚合。 |
| 「图表多了打断阅读，删几张」 | 图随文走、先文后图，用排版解决呼吸感，不用删图解决。 |

---

## 使用模式

本 skill 服务于**「分析师代他人分析」**场景：使用者作为分析师掌握命主完整信息（含已知历史事件），输出给命主本人阅读的**成品命书**（HTML + PDF 双产物）。

- 输入端：默认接受第三人称信息（"我朋友 1990 年生..."）
- 输出端：融合体叙事，技术内容化作叙述肌理
- **章节顺序固定**：第一章必为性格画像；玄学三维（八字/紫微/占星）作为后续支撑

## 体系定位

| 体系 | 角色 | 擅长维度 | 时间颗粒度 |
|:---|:---|:---|:---|
| 荣格八维 | **主语**（性格签名 · 恒量可发展） | 主导功能·Beebe 原型·阴影·个体化任务 | 终身 |
| 八字命理 | **解构**（性格的能量基础） | 五行格局·十神关系·调候 | 十年大运 + 流年 |
| 紫微斗数 | **对应**（性格的剧场舞台） | 十二宫位·星曜组合·四化 | 大限 + 流年 + 流月 |
| 西方占星 | **映照**（性格与时代节律的张力） | 日月关系·行星能量·世代张力 | 行运 + 推运 |

## 核心原则

1. **性格本位**：每一条玄学论断都要回到性格签名上印证，否则不写
2. **玄学是注解，不是预言**：用"印证 / 映照 / 解释"，不用"决定 / 命中注定"
3. **可塑路径必给具体行动**：终极课题不可悬空
4. **典籍出处可追溯**：关键论断标注典籍依据；伪引用是最高级 🔴（详见「典籍引用规范」）
5. **结构化叙事**：命运故事，不是信息堆砌
6. **感情分析必须充分**：以荣格关系动力学为骨架，玄学提供应期
7. **深度优先**：少数关键点深入，优于所有维度泛谈
8. **必须使用计算脚本**：不可手算关键命理数据
9. **外部验盘必做**：本地排盘须经独立引擎在线源交叉比对（S2），未验盘的命书不可交付
10. **机器验收兜底**：交付前必过 `validate_book.py` + locked-checklist，缺失以红字报错呈现，不靠人眼

---

## 分析师输入模板

```markdown
## 命主信息（必填）
- 姓名：____
- 性别：男 / 女
- 阳历生日：____ 年 __ 月 __ 日
- 出生时辰：__ 点 __ 分（或 __ 时）
- 出生地：__ 省 __ 市（用于真太阳时校正与占星上升计算）

## 关注重点（决定报告权重分配）
- [ ] 全维度命书
- [ ] 感情专题
- [ ] 事业财运
- [ ] 健康
- [ ] 当前/某年流年精析
- [ ] 合盘分析（需另一人完整信息）

## 已知背景（强烈推荐，用于时辰反查与分析校准）
- 重要人生节点：____ 年发生 ____
- 当前状态：职业、感情、健康
- 命主自我评价或主要困惑：____
- **荣格八维测试分数**（强烈建议）：16personalities / sakinorva / JUNGUS 测试
```

### 输入完整度场景路由

| 用户输入 | 分析范围 | 建议 |
|:---|:---|:---|
| 仅出生时间 | 玄学三维（无上升）+ 性格反推假说 | 走 Tier 3 反推流程 |
| 仅八维数据 | 完整性格画像，玄学缺位 | 建议补充出生时间 |
| 出生时间 + 八维 + 出生地 | 完整 v4 四维 | 最佳状态 |
| 两人完整信息 | 合盘分析 | `references/jung-relationship-dynamics.md` + `relationship-analysis.md` |
| 问具体年份 | 流年精析 | `references/liunian-analysis.md` |

### 性格数据缺位时的工作流

若无荣格八维测试分数，**不允许跳过性格画像**，按 `references/character-inference-workflow.md` 三层兜底：Tier 1 建议测试 → Tier 2 访谈 5-10 题反推 → Tier 3 玄学三维反推假说（明确标注「假说」）。无论哪一层，性格画像始终是命书第一章。

---

## 第 0 步 · 运行环境（每次分析开跑前）

1. **判定运行时**：工具表有 `task` 子代理工具 → omp，读 `references/runtime-omp.md`；有 `Agent` 工具 → Claude Code，读 `references/runtime-cc.md`。两份只做「中立动词/能力词 → 本端工具」映射，Stage 与质量门在两端完全相同。
2. **跑 preflight**：`python3 <skill 绝对路径>/scripts/doctor.py --json`。取其 `dm_root` 为 `$DM`、`dm_py` 为 `$DM_PY`，之后所有脚本一律 `$DM_PY $DM/scripts/<脚本>.py`——**PATH 上的 `python3` 在本机缺依赖**（系统 3.9 缺 playwright，homebrew 3.12 缺排盘库）。任何 🔴 → 停线报用户，不降级运行。
3. **建工作区**：`$WS=/tmp/dm-<slug>-<yyyymmdd>/`，每席位一个子目录；不用会话共享目录（omp `local://` / cc scratchpad）承载判官可见的文件。

细则见 `references/team-orchestration.md §9-§12`（能力词、工作区、模型分档、schemas）。

---

## v4 运行时架构 · Stage DAG

**Leader 只路由不代笔。** 每个 Stage 由专职 teammate 承担，契约在 `agents/{name}.md`；按 Stage 分批 `dispatch`、`barrier` 后再派下游（两端的具体工具见 runtime-*.md），编排细则（数据契约表、努力度基线、反模式、判官隔离）见 `references/team-orchestration.md`。

```
S0  输入核验   intake-refiner      模板核对 + Tier 路由 + 合盘判定
S1  排盘       caster              cast_chart.py + jung_calc.py            → Gate G1
S2  外部验盘   external-verifier   在线源交叉比对 7 校验点 + 时辰反查       → Gate G2
S3  分维分析   jung ‖ bazi ‖ ziwei ‖ astro 四 analyst          [4 并行]    → Gate G2.0/G2.x
S4  判官复核   judge-jung ‖ judge-bazi ‖ judge-ziwei ‖ judge-astro [4 并行, 只喂 JSON]
               → chief-judge 一致性评级；≤★★ 打回对应 analyst              → Gate G4
S5  综合       synthesizer         印证矩阵 + 命运密码 + 终极课题 + 双轨时间线 → Gate G3
S6  专题       love-specialist ‖ growth-specialist              [2 并行]   → Gate G5
S7  图表规划   chart-director      图表规划表契约（模式×配额×加码）          → Gate G7
S8  成文       book-writer         按素材+规划表独立成文 HTML
S9  终审       book-finalizer      locked-checklist 逐项判定 + validate_book.py + 视觉 QA
                                   🔴 → fresh writer 修订 (max 1)          → Gate G9
S10 交付       Leader              export_pdf.py → P 组回填 S9 → 双产物 → memory 归档
```

**三铁律**：① 中间数据走 task I/O 不落盘（例外：临时输入文件只写 `$WS/<席位>/`，如 S9 的 chart_plan.json）；② 依赖全显式——按 Stage 分批派遣，上游 barrier 后才派下游；③ 写盘所有权单一——book-writer 写 HTML、Leader 跑 export_pdf.py、memory 归档单独收口。

**判官隔离铁律**：S4 判官只接收排盘原始 JSON，严禁给 S3 成稿；分歧对比只在 chief-judge 发生；一致性 ≤★★ 打回对应 analyst 并重跑该维判官；分歧 >1 处必须在命书披露。

**fresh-writer 修订流**：S9 🔴 fail → 派全新 book-writer 干净上下文（注入修订指令 + 素材切片 + 未受影响章节全文，**不给被拒章节原文**），max 1 轮；仍不过则降级交付 + 显式披露缺陷清单。

**委派五要素**（每条派遣 prompt 必备）：目标 / 输出 schema（引用 `agents/{name}.md`）/ 工具与来源 / 边界不做什么 / 努力度区间。

**键序铁律**：所有结构化产物推理/证据键在前、结论键在后（NL-to-Format）；S3/S5/S6/S7/S9 一律先写完推理再转结构。

### Agent 一览（18 席，定义见 `agents/`）

| Stage | Agent | 一句话职责 |
|---|---|---|
| S0 | intake-refiner | 输入完整度路由（Tier 1/2/3、合盘判定、关注权重） |
| S1 | caster | 跑排盘脚本，G1 齐备核验，规避 memory/known-issues.md 已知坑 |
| S2 | external-verifier | 按 `references/external-verification.md` 作业（唯一联网前段席位） |
| S3 | jung-analyst | Phase 2.0：八功能 + Beebe 八位 + Grip + 个体化阶段 + **性格签名** |
| S3 | bazi-analyst | Phase 2.1：四柱纳音藏干 + 十神全量 + 格局喜用调候 + 神煞 + 大运流年 |
| S3 | ziwei-analyst | Phase 2.2：十四主星亮度 + 四化 + 14 辅星 + 杂耀 + 五宫展开 + 大限 |
| S3 | astro-analyst | Phase 2.3：三轴 + 十行星 + 12 宫主 + 相位 + 世代 + 关系模式 + 交界警戒 |
| S4 | judge-jung / judge-bazi / judge-ziwei / judge-astro | 只看 JSON 独立重推，产出分歧清单 |
| S4 | chief-judge | 汇总一致性评级（★~★★★★★，AB+BA 双向对比），≤★★ 打回 |
| S5 | synthesizer | 三维印证矩阵 + 命运密码（性格底色 × 玄学时机）+ 终极课题（必出自劣势/阴影）+ 双轨时间线 |
| S6 | love-specialist | 感情专题四要件（荣格关系动力学主骨架 + 玄学应期） |
| S6 | growth-specialist | 5 条可塑路径（功能/原型 + 行为练习 + 应期窗口）；健康专题与流年精析按需挂此席 |
| S7 | chart-director | 图表规划表（模式 ID × 配额 × 锚点六图 × 加码理由） |
| S8 | book-writer | 融合体叙事成文 + data-chart-id 落点 + 措辞约束 + print CSS 带出 |
| S9 | book-finalizer | locked-checklist 唯一出分 + validate_book.py + 真实浏览器视觉 QA + 修订触发 |

v3 Phase 编号与各 Phase 的完整内容要求**原样继承**在对应 agent 定义中（映射：Phase 1→S1，1.5→S2，2.0-2.3→S3，3.5→S4，3+4→S5，5→S6，6→S7-S10），SKILL.md 不再重复展开。

---

## 图表体系（v4 核心新增）

**唯一图表模式来源：`references/chart-patterns.md`**（P01-P16 十六模式，每种含 SVG 骨架 + 坐标公式 + 案例A版已验证实例 + 变体建议）。S7 规划、S8 落笔都从这里取。坐标计算可用 `scripts/chart_data.py` 辅助（雷达顶点/星盘轮角度/时间轴刻度等纯数学）。

**图表规划表**（S7 产出，S8 施工图，S9 验收单）：

```
| 图表 ID | 章节 | 叙事性标题 | 模式(可组合) | 数据来源字段 | 必配/加码 | 加码理由 |
```

**配额下限**（计数口径 = 带 `data-chart-id` 的 chart-container，表格与 SVG 同权）：

| 章节 | 下限 |
|:---|:---|
| Ch1 性格画像 | ≥ 6 |
| Ch2 八字 / Ch3 紫微 / Ch4 占星 | 各 ≥ 4 |
| Ch5 印证评估 + Ch6 双轨时间线 | 合计 ≥ 3 |
| Ch7 感情专题 | ≥ 4 |
| Ch8 终极课题 | ≥ 1 |
| **全书** | **≥ 26，上不封顶**（案例A版实绩 31 张） |

**锚点六图**（任何命书必有，缺一即 🔴）：八维雷达 P01(Ch1)、四柱全表 P08(Ch2)、五行权重 P02(Ch2)、十二宫命盘 P06(Ch3)、星盘轮 P07(Ch4)、双轨时间线 P11(Ch6)。

**加码规则**：配额之上按命主特异点加码且理由必填——特殊格局、交界上升、从格、异常 Grip、空宫借星、双聚簇等各值一张专图。

**组合与发明授权**：允许模式叠加（P11+P12）与发明新变体；唯一硬约束 = 通过 locked-checklist C4 渲染健康检查 + 登记图表规划表 + 遵守通用容器规范；新变体实测通过后经 memory 归档回填模式库。

**硬性工程约束**（book-writer 落笔必守）：
- 每个 `.chart-container` 必带 `data-chart-id="chart-{章号}-{序号}"`（S9 按此核销）
- 每个 SVG：合法 viewBox、≥1 个非空绘图元素、polygon ≥3 个不共点的点、**circle r > 0**（案例A版就翻在一个 `r="0"` 上）
- 同书多图的 marker/渐变 id 加 chart-id 前缀防覆盖；SVG 禁外链字体/资源
- 单图设计高度上限 ~240mm（A4 版心），超高拆分为多个容器各自领 ID
- 十二宫盘用 HTML Grid 而非 SVG（实测选型结论）；多轨时间线中**性格轨永远画在最上**（性格本位的视觉落地）

---

## 外部验盘（S2，v4 核心新增）

唯一作业依据：`references/external-verification.md`——7 校验点固定表（四柱干支 / 起运岁数 / 命宫主星 / 身宫五行局 / 日月星座 / 上升度数 / 主要相位）+ 已验证在线源清单 + 比对流程 + 产出 schema。要点：

- **引擎独立性原则**：与本地排盘同引擎的在线源（如 ziwei.pub = iztro）只能验证调用正确性，算法交叉验证必须用独立引擎源（紫微主源 iziwei.com.cn）；占星 astro.com 与本地 pyswisseph 为「同星历数据、异实现」，是理想验证源。
- **交界警戒硬触发**：上升/日月距星座边界 ±1° 或出生时刻距时辰边界 ±10 分钟 → 双源复算 + 双候选盘并示，无法裁决则「时辰存疑」标注且宫位论述降权（案例A案：v4.0 管线把真太阳时校正后时刻再喂给占星，算出「上升射手 29.87°·交界」；钟表时正确值为摩羯 3.34°——交界本身是错盘产物。教训：触发交界警戒时先核时间口径——占星用钟表时，八字/紫微用真太阳时——再谈双候选）。
- **分歧仲裁三步**：查第二外部源 → 核查真太阳时/时区/夏令时/子时规则/分宫制口径 → 仍分歧则命书披露不强裁。
- **子时规则**：23:00-23:59 出生必须双派并示（子初换日派/子正换日派）+ 披露取舍理由；iztro-py 与 lunar_python 的子时行为不同源，两处都要标。
- S2 是验证门不是排盘门：源全不可达时标「无法核验」并在 E 组披露，不阻断后续 Stage。

---

## 典籍引用规范（v4 强化，调性与证据的双重支柱）

古文引用作为叙述高潮的「锤音」出现在正文（非脚注），每处可追溯。**数量基线**：玄学三章每章 ≥3 处原文引用，性格画像章 Jung/Beebe 原典 ≥3 处，感情专题 ≥2 处。**伪引用（查无此文/张冠李戴）是最高级 🔴——宁少引不错引。**

引用池优先取各 references 文件「v4 增补（2026-07-15）」小节已核准的条目。硬规则：

- **格式**：书名+章名必备、通行本章次推荐、引号内一字不差；《子平真诠》标「通行评注本第 N 章《章名》」；《穷通宝鉴》标「论某行·某月某干」不写卷号；沈孝瞻原文与徐乐吾评注必须区分。
- **章次锚点**：论用神=第 8 章（「八字用神，专求月令」）、成败救应=第 9 章（原文「必是带忌」非「皆因带忌」）、格局高低=第 12 章（「有情无情、有力无力」）、调候=第 14 章。「调候之神，先其所急」**不得**标为《穷通宝鉴》原文（实出徐乐吾评注）。
- **神煞分档**：出处可确证者（天乙/太极/华盖/金舆等）可引原文；出处存疑者（红艳/流霞/国印等）一律暗用或「古歌云」软表述，不冠书名。
- **荣格线**：统一引「Beebe 2016」（非 2017）；原型官方名 Senex/Witch、Demonic/Daimonic Personality、Puer/Puella；未经核实的页码级引文降级为章节/概述级；"you will call it fate" 只能作转述，真原文引 Aion CW 9ii §126；功能发展年龄表署 Grant et al. 1983 并披露无实证支持，荣格名下只可引 CW 8 §749-§795 上下半场划分；Grip 表现可引 In the Grip (CPP, 2000) 官方 PDF。
- **16 亚型编码铁律**：A=分析型 / H=整体型（**禁译「人本型」**）/ O=对象取向 / B=背景取向；判断功能只配 A/H、感知功能只配 O/B；编码出处为 JUNGUS（jungus.cn）。

---

## 质量门 · locked-checklist（S9 唯一出分依据）

`references/locked-checklist.md`：**M1-M8**（模块完整）/ **C1-C5**（图表验收）/ **W1-W3**（措辞）/ **E1-E5**（证据：典籍出处、判官分歧披露、时辰假设、解释力评级、外部验盘披露）/ **P1-P3**（PDF 交付）。逐项二元 pass/fail + 强制引证 + 权重聚合，禁止拍总分。

**两级后果**：
- 🔴（M/C 组任一 fail）→ fresh book-writer 修订 max 1 轮，仍不过降级交付 + 披露缺陷清单
- 🟠（W1 硬禁词 / E4 解释力评级 / P1 PDF 生成）→ 交付阻断但定点修补，不触发全书重写

**机器验收命令**（S9 必跑）：

```bash
$DM_PY $DM/scripts/validate_book.py <命书.html> --plan $WS/book-finalizer/chart_plan.json [--json]
# --plan 直接吃 chart-director 产出的 chart_plan（读 chart_table；形状见 schemas/chart_plan.json）
# exit 0 = 通过；exit 1 = 存在 🔴 或 W1 fail
```

章节锚点机器约定：每章唯一一个 `<h2 class="section-title">`，全书恰好 8 个；章内小节不得用 h2.section-title。

---

## 双产物交付（S10）

```bash
$DM_PY $DM/scripts/export_pdf.py <命主名>_命书.html [输出.pdf]
# 成功打印页数/大小/页眉标题并 exit 0；任何 sanity fail（正文空白页/页数异常/体积异常）exit 1，必须处理不得忽略
```

- 依赖由 `$DM_PY` 所在 venv 提供（见「计算脚本」依赖行），`doctor.py` 会实际启动一次 Chromium 核验。**禁用 Chrome --virtual-time-budget 路线**（已知挂起），渲染流程已固化在脚本内。
- book-writer 的 HTML 必须包含 `references/output-template.md`「v4 增补」的 `@media print` 块（无它 PDF 图表会跨页劈断，案例A版实测）。
- P1-P3 结果回填 book-finalizer 的 P 组判定（S9↔S10 一次回环），实测基线：案例A HTML + print CSS = 84 页 / ~6.2MB / 无正文空白页。
- 文件命名：`{命主名}_命书.html` / `{命主名}_命书.pdf`。交付后归档 `memory/analysis-sessions/`（含 `runtime_trace`：运行时、各席位实际模型与是否 fallback、降级记录），最后 `teardown`。

---

## 调性红线（工程不得侵蚀文气，S9 验收必查）

- **融合体 5 技法**是 book-writer 硬性契约：术语带电出场 / 数据嵌入叙事 / 典籍作为锤音 / 判断—解释—行动暗示三段式 / 古典化收束（每章末尾「四字短语 + 一句话定调」）。
- **图表是叙事的一部分**：规划表「标题」列须为叙事性标题（参照「冬日之火，光向内收」），禁止工程性标题；图随文走、先文后图，禁止图表堆砌打断行文呼吸。
- **章节标题保持诗性**（如「深湖之爱——一个 FiA 主导者的爱的语法」）；机器校验按 h2 位置锚点计章，**不要求标题含固定关键词**。
- **PDF 排版继承屏显气质**：print CSS 只做分页与安全色，serif 引文块、留白节奏、变奏字号全部保留。
- 发现清单化/模板化写法侵入正文 = 🔴。

---

## 措辞统一调整表（强制）

| 旧 | 新 |
|:---|:---|
| "决定" | "印证 / 映照 / 解释" |
| "命中注定" | "天然倾向 / 默认路径" |
| "命运" | "性格在时机中的展开" |
| "天注定" | "性格签名的结构性倾向" |
| "无法改变" | "需通过个体化进程整合" |
| "克应" | "应期窗口" |
| "改命" | "可塑路径" |
| "人本型"（A/H 误译） | "整体型"（H = Holistic） |

### 禁词清单（命书严禁使用）

| 禁词 | 替代 | 理由 |
|:---|:---|:---|
| "可能" "也许" "大概率"（无证据链时） | "测试显示" / "三维印证" / "反推假说" | 必须明示证据来源 |
| "命中注定" / "命定" | "天然倾向" / "默认路径" | 反宿命论 |
| "克夫" / "克妻" | "感情能量需要主动调和的信号" | 反厌女 / 物化伴侣 |
| "改命" | "可塑路径" | 性格可发展，无需"改" |
| "真命天子 / 真爱" | "高契合度伴侣" | 反 Hollywood 神话 |
| "你这辈子注定..." | "你的天然倾向是..." + 可塑路径 | 反宿命 |
| "不可改变" / "无法逆转" | "整合任务" / "终身课题" | 命运可塑 |

W1 机器扫描硬禁词 12 个（命中注定/这辈子注定/天注定/克夫/克妻/改命/真命天子/真爱/不可改变/无法逆转/克应/命定），否定性提及（「而非/并非/不是」前缀）豁免；「决定/可能/命运」属语境词只做人工复核（"性格决定命运"是本 skill 哲学句）。

---

## 章节权重（v3 继承，M-LEN 校验基准）

| 章节 | 主题 | 篇幅占比 |
|:---|:---|:---|
| 1 | 性格画像（荣格主导） | 35-45% |
| 2 | 八字解构 —— 性格的能量基础 | 15% |
| 3 | 紫微对应 —— 性格的剧场舞台 | 15% |
| 4 | 占星映照 —— 性格的宇宙节律 | 15% |
| 5 | 三维印证度评估 | 5% |
| 6 | 双轨时间线 | 5% |
| 7 | 感情专题 | 必须充分 |
| 8 | 终极课题 | 5% |

---

## 计算脚本

所有脚本以 `$DM_PY $DM/scripts/<脚本>.py` 运行（第 0 步）。下表用法省略该前缀。

| 脚本 | 用途 | 用法 |
|:---|:---|:---|
| `scripts/doctor.py` | **第 0 步 preflight**：解析 `$DM_PY`、依赖、Chromium、判官隔离自检、omp 适配件 | `python3 doctor.py [--json] [--regression]` |
| `scripts/cast_chart.py` | **统一排盘调度**（八字+紫微+占星 JSON；八字/紫微用真太阳时，占星用钟表时，见 `元数据.时刻口径`） | `cast_chart.py 1993-09-30 17:30 f 杭州` |
| `scripts/bazi_calc.py` | 八字排盘（lunar_python 主 + sxtwl 校验） | `bazi_calc.py 1993-09-30 17:30 f` |
| `scripts/ziwei_calc.py` | 紫微排盘（iztro-py；三合派通行版四化；Config 是壳，中州派/自定义四化/年分界**不可配置**） | `ziwei_calc.py 1993-09-30 9 f` |
| `scripts/astro_calc.py` | 占星排盘（pyswisseph；高纬 >60° 自动 fallback Whole Sign；传钟表时） | `astro_calc.py 1993-09-30 17:30 30.27 120.16 Asia/Shanghai` |
| `scripts/jung_calc.py` | 荣格功能栈 + Beebe + Grip + 性格签名 | `jung_calc.py --scores <分数> --scale=30 --age=<年龄>`（JUNGUS 第二代满分 30；判定阈值按 0-10 归一） |
| `scripts/synastry_calc.py` | 合盘计算 | 见脚本头注释 |
| `scripts/chart_data.py` | **图表坐标计算**（雷达顶点/星盘轮角度/时间轴刻度） | `chart_data.py <cast_chart.json> --radar/--wheel/--timeline` |
| `scripts/validate_book.py` | **命书机器验收**（S9） | `validate_book.py <book.html> --plan <chart_plan.json>` |
| `scripts/export_pdf.py` | **PDF 导出**（S10，Playwright Chromium） | `export_pdf.py <book.html> [out.pdf]` |
| `tests/run_regression.py` | 回归：17 命例锚点 + 度数级锚点 + 占星直调对照 | 改任何排盘脚本后必跑 |

`bazi/ziwei/astro_calc.py` 的 `--hints` 会输出「性格映射提示」（内含预置荣格结论），**判官链路永不使用**，默认关闭。

依赖（venv，默认 `~/.local/share/destiny-matrix/venv`）：`python3.12 -m venv <venv> && <venv>/bin/pip install lunar_python iztro-py pyswisseph geonamescache timezonefinder kerykeion sxtwl playwright pypdf && <venv>/bin/python -m playwright install chromium`

紫微论断标注铁律：大限统一标「三合派通行起算：首限在命宫，起限虚岁=局数，虚岁按正月初一分界」；命主生年庚/壬干时涉天同/太阴/天相/天府的四化论断必须标「三合派通行版四化（iztro 默认）」，派别分歧实质影响结论须披露；立春至正月初一之间出生者是年干四化 + 大限干支高危区（S2 校验点必须覆盖）；涉太阴亮度的格局判定（上游 #270 未修）降权标注。

---

## 参考资源

| 文件 | 何时读取 |
|:---|:---|
| `references/character-first-manifesto.md` ★ | **每次分析开篇必读**（哲学锚点） |
| `references/team-orchestration.md` ★ | **Leader 编排必读**（数据契约/努力度/反模式/判官隔离/能力词/分档） |
| `references/runtime-omp.md` / `references/runtime-cc.md` ★ | 第 0 步按运行时二选一（中立动词与能力词 → 本端工具） |
| `schemas/*.json` | 判官、chief-judge、chart-director、book-finalizer 产出的 JSON Schema（派遣时挂载强校验） |
| `adapters/omp/dm-{deep,research,light}.md` | omp 三档 teammate agent（软链到 `~/.omp/agent/agents/`） |
| `references/locked-checklist.md` ★ | S9 终审唯一出分依据 |
| `references/chart-patterns.md` ★ | S7/S8 唯一图表模式来源（P01-P16） |
| `references/external-verification.md` ★ | S2 外部验盘作业手册 |
| `references/character-inference-workflow.md` | 无荣格测试数据时（Tier 1-3 兜底） |
| `references/cognitive-functions.md` | 性格画像必读（含 v4 增补：Beebe 核准表/Grip 速查/A-H·O-B 编码规范） |
| `references/jung-classical-texts.md` | 性格画像深度引证（含 v4 引文勘误） |
| `references/jung-relationship-dynamics.md` | 感情专题主骨架 |
| `references/bazi-framework.md` | 八字分析必读（含 v4 增补：子时换日两派梳理） |
| `references/shensha-table.md` | 八字神煞查表（4 条出处存疑，引用分档见 classical-texts v4 增补） |
| `references/ziwei-framework.md` | 紫微必读（含 v4 增补：四化派别/iztro 偏差表/37 杂耀清单/大限分歧） |
| `references/astrology-framework.md` | 占星必读（含 v4 增补：交界上升惯例/分宫制边界/行运推运惯例） |
| `references/classical-texts.md` | 玄学三维必读（含 v4 增补：章次核对表/引用格式范例/存疑清单） |
| `references/cross-analysis-patterns.md` | S5 三维印证度评估 |
| `references/output-template.md` | S8 成文必读（HTML 骨架 + v4 增补 print CSS + data-chart-id 规范） |
| `references/relationship-analysis.md` | 感情专题的玄学应期部分 |
| `references/liunian-analysis.md` | 分析具体年份/月份时 |
| `references/special-patterns.md` | 发现特殊格局时 |
| `agents/*.md`（18 件） | 派遣对应 Stage 时作为输出契约注入 prompt |
| `memory/known-issues.md` | caster 必读；遇报错优先查 |

---

## 历史版本

- v4.1.0（当前）：Claude Code / omp 双端适配（中立编排动词 + 能力词 + runtime-*.md + omp 三档 agent + schemas + doctor.py preflight）；修复占星段重复经度校正、`性格映射提示` 默认关闭（判官隔离数据层）、JUNGUS 0-30 量程、`--tz` 未传给占星、chart_plan 与 validate_book 契约不通；回归加度数锚点与占星直调对照。详见 `CHANGELOG.md`。
- v4.0.0：Agent Team 重构。Stage DAG + 18 席分工、外部验盘、图表模式库 P01-P16 + 配额契约、locked-checklist 机器验收、HTML+PDF 双产物、典籍引用规范强化、调性红线。设计契约见 `V4_PLAN.md`。
- v3.0.0：性格本位重构（完整归档 `_archive/v2/` 前版）。
- v2 / v1：`_archive/`。

版本演进详见 `CHANGELOG.md`。
