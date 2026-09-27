# Destiny Matrix v4 · 设计契约（Agent Team 施工蓝图）

> 本文件是 v4 升级的**唯一权威规格**。所有施工 agent 按本文件执行；与旧文档冲突时以本文件为准。
> 日期：2026-07-15。基线版本：v3.0.0。参照架构：`~/.claude/skills/strategic-insight-longform/`（下称 SIL）。

---

## 0. 升级动机（三大实测问题 + 一个新需求）

以 2026-07-15 案例A命书（`~/Downloads/案例A_命书.html`，8 章 27 图，为反复人工提示后的达标版）为参照：

1. **模块缺失**：完整性检查是散文式清单，靠模型自觉，单次长文生成必然漏。
2. **无自动外部交叉比对**：SKILL.md 无任何联网搜索/在线排盘比对环节；案例A的 7 点交叉验证全靠用户临场指挥。
3. **图表生成不稳定**：模板只定义 3 张 SVG，其余全靠即兴手写；无清单约束、无验收。
4. **新需求**：交付物从 HTML 单文件 → HTML + 高质量 PDF 双产物。

**v4 总方针**：质量优先。借 SIL 的「Leader 只路由不代笔 + Stage DAG + 委派五要素 + 锁定判定清单 + fresh 实例修订」控制质量门；图表走「模式库 × 运行时图表规划表」既保灵活又保数量。

---

## 1. v4 运行时架构 · Stage DAG

命书生成时（非本次施工），Leader 按以下 DAG 派遣 teammate。派遣统一 `Task(subagent_type="general-purpose", name="{agent}")`，委派五要素必备（目标/输出 schema/工具与来源/边界/努力度区间），数据走 task I/O 不落盘中间件。

```
S0  输入核验   intake-refiner      输入模板核对 + 完整度路由（Tier 1/2/3）+ 关注重点权重
S1  排盘       caster              cast_chart.py + jung_calc.py → Gate G1（数据齐备）
S2  外部验盘   external-verifier   web 检索在线排盘源，7 校验点交叉比对 + 时辰反查 → Gate G2
S3  分维分析   jung-analyst ‖ bazi-analyst ‖ ziwei-analyst ‖ astro-analyst   [4 并行]
                                   各产出章节素材 + 玄学解释力评级 → Gate G3
S4  判官复核   judge-jung ‖ judge-bazi ‖ judge-ziwei ‖ judge-astro [4 并行, fresh 上下文只喂 JSON]
               → chief-judge 汇总一致性评级；≤★★ 打回对应 analyst 修订 → Gate G4
S5  综合       synthesizer         三维印证矩阵 + 命运密码 + 终极课题 + 双轨时间线 → Gate G5
S6  专题       love-specialist ‖ growth-specialist   [2 并行] → Gate G6
S7  图表规划   chart-director      通读 S3-S6 全部素材 → 产出「图表规划表」契约 → Gate G7
S8  成文       book-writer         按素材+图表规划表独立成文 HTML；Leader 不代笔
S9  终审       book-finalizer      locked-checklist 逐项判定 + validate_book.py 机器校验
                                   + Playwright 截屏视觉 QA → 不过则派 fresh writer 修订(max 1)
S10 交付       Leader              export_pdf.py 出 PDF → 双产物交付 → 会话存档 memory/
```

**三铁律**（照搬 SIL）：① 中间数据走 task I/O 不落盘；② 依赖全显式 blockedBy；③ 写盘所有权单一——只有 book-writer 写 HTML、Leader 跑 PDF 脚本、memory 归档单独收口。

**判官隔离铁律**：S4 判官只接收排盘 JSON，**严禁**给 S3 成稿；判官产出与成稿的分歧由 chief-judge 对比。这是防叙事传染的结构性保证（v3 靠自觉，v4 靠上下文隔离）。

**修订铁律**：S9 拒稿 → 派全新 book-writer 实例干净上下文修订，不给被拒章节原文，max 1 轮；仍不过则降级交付并显式披露缺陷清单。

v3 的 Phase 编号与 Gate 内容**全部保留**，映射关系：Phase 1→S1，Phase 1.5→S2，Phase 2.0-2.3→S3，Phase 3.5→S4，Phase 3+4→S5，Phase 5→S6，Phase 6→S7-S10。

---

## 2. 质量门体系 · locked-checklist

新建 `references/locked-checklist.md`，把 SKILL.md 现有三张清单（输出前完整性检查 / 质量自检 / 措辞统一）+ 图表验收合并为**带固定 ID 的锁定判定清单**，S9 book-finalizer 运行时唯一出分依据，不得增删改。分组：

- **M 组（Module，模块完整）**：M1-M8 对应八章锚点及各章必备要素（沿用 v3 完整性检查逐条编号）。
- **C 组（Chart，图表验收）**：C1 图表规划表逐行核销（data-chart-id 全存在）；C2 各章配额达标；C3 全书总数达标；C4 SVG 渲染健康（语法合法/viewBox 正常/path·polygon 非空非退化）；C5 锚点六图齐全。
- **W 组（Wording，措辞）**：禁词清单 0 命中 + 措辞统一表 0 遗留（沿用 memory/conventions.md）。
- **E 组（Evidence，证据）**：典籍出处标注、判官分歧披露、时辰假设标注、玄学解释力评级齐全、外部验盘结果披露。
- **P 组（PDF，交付）**：P1 PDF 生成成功且页数合理；P2 无空白页/截断图表；P3 页码页眉正常。

判定协议照搬 SIL：逐项二元 pass/fail + 强制引证（fail 必须指认位置），先判定后聚合，禁止凭感觉拍总分。🔴 级 fail（M/C 组任一）→ 触发修订流。

---

## 3. 图表体系 · 模式库 × 图表规划表

### 3.1 `references/chart-patterns.md`（新建，chart-librarian 施工）

**16 种图表模式**，每种含：① SVG 骨架模板（占位符形式）② 坐标计算公式 ③ 一个**从案例A命书原文抠出的已验证完整实例** ④ 适用场景与变体建议。

| 类别 | 模式 ID | 模式 | 案例A版对应 |
|:---|:---|:---|:---|
| 强度类 | P01 | 八轴雷达 | 认知功能雷达 |
| | P02 | 分组条形 | 16 亚型分数 / 五行权重 / 十神分布 |
| | P03 | 堆叠/对比条形 | 元素×模式能量分布 |
| | P04 | 仪表盘/弧线 | Grip 弧线四幕 |
| 结构类 | P05 | 同心圆环 | Beebe 八原型环 |
| | P06 | 十二宫盘 | 紫微命盘 |
| | P07 | 星盘轮 | 本命星盘 Placidus |
| | P08 | 结构化全表 | 四柱排盘表 / 相位全表 |
| 流动类 | P09 | 流向图 | 辛年四化流向 |
| | P10 | 状态流转图 | 四态流转（主轴↔暗层↔回圈↔抓取） |
| 时间类 | P11 | 多轨时间轴 | 大运/大限/双轨时间线（带当前位置▼/★标记） |
| | P12 | 发展曲线 | 功能发展 0-24 岁 |
| 关系类 | P13 | 矩阵热力表 | 三维印证矩阵 / 功能配对表 |
| | P14 | 跷跷板/天平 | 三轴跷跷板 |
| | P15 | 会照关系图 | 夫妻宫三方四正 |
| | P16 | 双轮对照 | 合盘场景（从 P07 派生，可无现成实例，给骨架+公式） |

末尾必须有**组合与发明授权条款**：允许模式叠加（如 P11+P12）、允许发明新变体，唯一约束是通过 C4 渲染健康检查并登记进图表规划表。

### 3.2 图表规划表（运行时契约，chart-director 产出）

Schema（task I/O 传递，不落盘）：

```
| 图表 ID | 章节 | 标题 | 模式(可组合) | 数据来源字段 | 必配/加码 | 加码理由 |
```

- 图表 ID 命名 `chart-{章号}-{序号}`，book-writer 落 HTML 时写入 `data-chart-id` 属性。
- **配额下限**（写进 SKILL.md + locked-checklist C2/C3）：

| 章节 | 下限 |
|:---|:---|
| Ch1 性格画像 | ≥ 6 |
| Ch2 八字 / Ch3 紫微 / Ch4 占星 | 各 ≥ 4 |
| Ch5 印证评估 + Ch6 双轨时间线 | 合计 ≥ 3 |
| Ch7 感情专题 | ≥ 4 |
| Ch8 终极课题 | ≥ 1 |
| **全书** | **≥ 26，上不封顶** |

- **锚点六图**（任何命书必有，缺一即 M 组 fail）：八维雷达(P01)、四柱全表(P08)、五行权重(P02)、十二宫命盘(P06)、星盘轮(P07)、双轨时间线(P11)。
- chart-director 在下限之上按命主特异点加码（特殊格局、交界上升、从格、异常 Grip 等各值一张专图），加码必须写理由。

### 3.3 `scripts/chart_data.py`（新建，轻量）

只算**数据与坐标**不出成图：雷达顶点坐标（`cx + r*sin(θ), cy - r*cos(θ)`，r=强度×1.5）、十二宫盘宫位布局坐标、星盘轮行星角度→xy、时间轴刻度。输入 cast_chart JSON，输出坐标 JSON 片段。视觉呈现（配色/标注/图注/比喻元素）完全由 book-writer 决定。

---

## 4. 外部验盘 · `references/external-verification.md`（新建）

S2 external-verifier 的作业手册。内容：

1. **7 校验点固定表**：① 四柱干支 ② 起运岁数与大运序 ③ 紫微命宫位置+命宫主星 ④ 身宫与五行局 ⑤ 占星太阳/月亮星座 ⑥ 上升星座与度数 ⑦ 主要相位 top3。
2. **在线比对源清单**（施工时经 web 调研确认可用性，给 2-3 个/体系）：八字、紫微、占星各自的公开排盘网站/工具，标注访问方式与可信度。
3. **比对流程**：每点「本地值 vs 外部值 vs 判定（一致/偏差/无法核验）」三列表格；**交界警戒**——上升/日月在星座交界 ±1° 或时辰交界 ±10 分钟时必须显式标注（案例A上升 29.87° 教训）；分歧处理（本地脚本 vs 外部源不一致时的仲裁规则：查第二外部源 → 检查真太阳时/时区设置 → 仍分歧则在命书披露）。
4. **产出 schema**：外部比对表（进命书附录或 E 组证据）+ 时辰反查结论三档（吻合/修正/存疑）。

---

## 5. 交付 · PDF 双产物

### 5.1 `scripts/export_pdf.py`（新建，toolsmith-pdf 施工）

- Playwright Chromium 路线（参照 `~/.claude/skills/pdf/scripts/md2pdf_chrome.py` 成熟实现；**禁用** Chrome `--virtual-time-budget`，已知会挂）。
- 流程：加载 HTML → `wait_for_function` 等待全部 SVG 渲染完成（`document.querySelectorAll('svg').length > 0 && document.fonts.ready`）→ `page.pdf(format='A4', print_background=True, display_header_footer=True, margin=…)`。
- 页眉：命书标题；页脚：页码/总页数。CLI：`python3 export_pdf.py <input.html> [output.pdf]`。
- 自带 sanity check：输出页数、检测超尺寸空白页，异常时非零退出。

### 5.2 `references/output-template.md` 增补 print CSS（toolsmith-pdf 施工）

在现有 CSS 后追加 `@media print` 块：每章 `page-break-before: always`；`.chart-container, table, .classic, .summary-frame { break-inside: avoid; }`；打印配色（深色元素转印刷安全色）；超宽表格缩放策略。**不得改动现有屏显 CSS。**
另：全模板图表容器规范升级——每个 `.chart-container` 必须带 `data-chart-id` 属性（供 validate_book.py 核销）。

---

## 6. 机器验收 · `scripts/validate_book.py`（新建，toolsmith-validate 施工）

CLI：`python3 validate_book.py <book.html> [--plan <图表规划表.json>] [--json]`。纯标准库（html.parser + re），零第三方依赖。检查项与 locked-checklist 对齐：

- 8 章锚点存在（按 `section-title` 或 id 锚点）
- 图表统计：全书总数、各章计数 vs 配额表；`data-chart-id` 清单输出；有 --plan 时逐行核销
- SVG 健康：可解析、viewBox 存在、含 ≥1 个非空绘图元素、polygon points 非退化
- 禁词扫描（正文文本层，排除 HTML 属性）
- 章节篇幅占比（按可见文本字数）vs 权重表，偏差 >10 个百分点报 warning
- 输出：人读报告 + `--json` 机读结果；任何 🔴 项 → exit code 1

**回归基线**：对案例A命书运行，除「data-chart-id 缺失」（旧版无此约定）外应全绿；此结果作为 tests/ 回归样本记录。

---

## 7. Agent 定义 · `agents/` 目录（新建，agent-author 施工）

参照 SIL `agents/core/*.md` 的写法（角色一句话 + 输入契约 + 输出 schema 键序 + 工具 + 边界「不做什么」+ 努力度区间 + 红旗）。17 个文件：

| 文件 | Stage | 要点 |
|:---|:---|:---|
| intake-refiner.md | S0 | 输入模板核对、Tier 1/2/3 路由、合盘判定 |
| caster.md | S1 | 跑脚本、G1 齐备清单、已知问题规避（读 memory/known-issues.md） |
| external-verifier.md | S2 | 按 external-verification.md 作业；唯一允许联网的前段 agent |
| jung-analyst.md | S3 | Phase 2.0 全要求 + 性格签名短语产出 |
| bazi-analyst.md | S3 | Phase 2.1 全要求 + 每条回扣性格签名 |
| ziwei-analyst.md | S3 | Phase 2.2 全要求（含全部辅星杂耀） |
| astro-analyst.md | S3 | Phase 2.3 全要求 |
| judge-jung/bazi/ziwei/astro.md | S4 | 只喂 JSON 的独立重推 + 分歧清单 schema |
| chief-judge.md | S4 | 汇总一致性评级 ★~★★★★★，≤★★ 打回规则 |
| synthesizer.md | S5 | 印证矩阵 + 命运密码公式 + 终极课题（必出自劣势/阴影）+ 双轨时间线 |
| love-specialist.md | S6 | Gate 5 感情专题四要件 |
| growth-specialist.md | S6 | 5 条可塑路径（功能/原型 + 行为练习 + 应期窗口） |
| chart-director.md | S7 | 图表规划表 schema + 配额 + 加码规则 + 模式库引用 |
| book-writer.md | S8 | 融合体写作 5 技法 + 章节权重 + data-chart-id 落点 + 措辞约束 |
| book-finalizer.md | S9 | locked-checklist 逐项判定协议 + validate_book.py + 视觉 QA + 修订触发 |

另新建 `references/team-orchestration.md`（destiny 版）：三铁律、委派五要素、判官隔离、修订流、努力度基线表（external-verifier 5-12 次检索；4 analyst 各 0-3 次典籍核查性检索；judges/writer/finalizer 0 次联网）。

---

## 8. 知识增强（web 检索，research agents 施工）

原则：**只补有出处的内容**，每条增补带来源（典籍卷次 / Jung CW 编号 / 论文 / 权威网页），以「v4 增补」小节追加到对应 references 文件，不改写既有正文；无法确证的宁缺毋滥。

| Agent | 目标文件 | 调研任务 |
|:---|:---|:---|
| R1 荣格线 | cognitive-functions.md、jung-classical-texts.md | Beebe 八原型模型准确性核查（Beebe 原著 *Energies and Patterns in Psychological Type* 2016）；Grip/劣势功能理论对 Naomi Quenk *Was That Really Me?* 的引证补强；16 亚型 A/H·O/B 编码的通行表述核对（避免再出「人本型/整体型」误译，参照 2026-07-15 判官报告）；功能发展年龄阶段的可靠来源 |
| R2 八字线 | classical-texts.md、bazi-framework.md | 《子平真诠》格局判定与《穷通宝鉴》调候的关键条目卷次核对；神煞表主流出处；夜子时归属各派观点梳理 |
| R3 紫微线 | ziwei-framework.md | 三合派 vs 飞星派四化差异的权威表述；iztro/iztro-py 已知算法偏差社区报告；杂耀清单完备性 |
| R4 占星线+验盘源 | astrology-framework.md、（产出交 verifier-author）| 交界上升（cusp）处理的占星学界惯例；Placidus/Whole Sign 适用边界；行运/推运计算惯例核对；**调研可用的在线排盘比对源**（八字/紫微/占星各 2-3 个，验证 2026 年可访问性） |

---

## 9. SKILL.md v4 重构要点（主 Leader 亲自执笔，不委派）

- frontmatter description 更新（v4、team 模式、双产物）。
- 保留 v3 全部哲学骨架、措辞表、禁词清单、输入模板、Phase 内容要求。
- 新增：Stage DAG 图 + Agent 表 + 三铁律 + 委派五要素引用 + Red Flags 表（destiny 版，参照 SIL 开头样式）。
- Gate 全部改为指向 locked-checklist 的 ID。
- 图表配额表 + 锚点六图 + chart-patterns.md 引用。
- Phase 6 改双产物交付（HTML + PDF）+ S10 流程。
- 参考资源表补全新文件。
- CHANGELOG.md 追加 v4.0.0 条目。

## 10. 施工分工与顺序（本次升级的 team）

```
Wave 1（并行 8 席）:
  R1/R2/R3 research → 各自 references 增补
  R4 research → 返回 findings（不写文件）→ 链 verifier-author 写 external-verification.md
  chart-librarian → chart-patterns.md（从案例A HTML 抠实例）
  toolsmith-validate → validate_book.py + locked-checklist.md
  toolsmith-pdf → export_pdf.py + output-template.md print CSS（并用案例A HTML 实测出 PDF）
  agent-author → agents/*.md 17 件 + team-orchestration.md
Wave 2（Leader）: SKILL.md v4 重写 + CHANGELOG
Wave 3（并行 2 席验收）:
  consistency-checker → 全库交叉引用/命名/Gate-ID 一致性核查
  regression-tester → validate_book.py 对案例A HTML 回归 + export_pdf.py 实测 + 报告
Wave 4（Leader）: 修复验收问题 → 交付总结
```

文件所有权互斥，无写冲突。质量优先：所有 agent 遇不确定处标注「待定」上报，禁止编造。

## 11. 调性红线（用户明示，验收必查）

v4 的全部工程化手段（DAG/清单/脚本/配额）只管「不缺、不崩、不假」，**不得侵蚀命书的文艺感与调性**。v2/v3 沉淀的写作气质是本 skill 的核心资产，一字不减地保留并在 v4 各处强制引用：

- **融合体 5 技法**（术语带电出场 / 数据嵌入叙事 / 典籍作为锤音 / 判断—解释—行动暗示三段式 / 古典化收束「四字短语+一句话定调」）——写进 book-writer 的硬性契约，locked-checklist E 组增设 E-tone 项抽查。
- **典籍引用是调性的支柱，也是证据的支柱**：古文引用作为叙述高潮的「锤音」出现在正文（非脚注），且每处必须可追溯（书名+卷次/篇目，如《滴天髓·通神论》《穷通宝鉴·三秋》Jung CW 6 §556）。数量基线：八字/紫微/占星三章每章 ≥3 处原文引用，性格画像章 Jung/Beebe 原典引证 ≥3 处，感情专题 ≥2 处。伪引用（查无此文/张冠李戴）是最高级 🔴——宁可少引不可错引，R1/R2/R3 调研核实过的条目优先使用。locked-checklist E 组按此逐项验收。
- **图表是叙事的一部分**：图注文案要有文气（参照案例A版「冬日之火，光向内收」式标题），chart-director 规划表中「标题」列须为叙事性标题而非工程性标题；禁止图表堆砌打断行文呼吸——图随文走，先文后图。
- **章节标题保持诗性**（如「深湖之爱——一个 FiA 主导者的爱的语法」），机器校验章节锚点时按位置/class 匹配，**不得要求标题含固定关键词**。
- **PDF 排版继承屏显气质**：print CSS 只做分页与安全色处理，serif 引文块、留白节奏、变奏字号全部保留。
- 验收表述：Wave 3 consistency-checker 与最终 finalizer 均须核查「工程约束是否以牺牲文风为代价」，发现清单化/模板化侵入正文的写法视为 🔴。
