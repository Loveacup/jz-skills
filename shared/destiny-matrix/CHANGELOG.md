# Destiny Matrix · 版本演进

---

## v5.1.0 — 2026-09-28

**内容与图文合同优化**：目标改为“四体系各自完整解读，以人的问题组织跨体系综合，写成有阅读价值的命书”。计算、证据链、盲判、schema、脚本与 CLI 均不变。

- **独立深读**：八字、紫微、占星、认知功能 framework 各加有序推读路径与完成边界；四位 analyst 指向该路径，findings 须含连续领域论述，改为“提供领域论述素材，不写最终 HTML”。神煞/特殊格局/流年/关系参考区分传统解释与现实建议。
- **主题综合**：`cross-analysis-patterns.md` 五步综合顺序；`matrix` 降为分析索引，新增理解写入 `synthesis_claims` 与 `required_content`；竞争解释改为分层检验（计算核方法、传统说明取法条件、个体假说才谈反例）。S5 新主张由 Leader 补 `owner/status` 登记，修正时走 `superseded/rejected`。
- **单一作者**：S6 按有效主题集合派遣；analyst/synthesizer/specialist 产物均为作者素材；新增作者缺口回提（team-orchestration §8.2）。`book-writer.md` 删去“一句命题＋至多三行导语”，改为五条编辑原则。
- **结构图**：P02/P06/P07/P08/P11/P13/P17 重写采用条件（紫微固定地支 4×4 盘、八字/紫微分面周期轴（两个 chart ID 紧邻）、真实宫头星盘、主题关系表）；chart-director 在 `planning_rationale` 逐项记录取舍；`data_refs` 只列可数值绑定字段，字符串来源写进 caption；P13 因无数值字段改为综合章内普通语义表，不登记 `chart_table`。output-template 增 `.ziwei-grid`、`.timeline-panels` 屏幕/打印规则与开篇顺序。
- **验收**：样章门由“800–1200 字＋一张代表图”改为功能性样章（最易失败的领域段＋关联综合段＋适用结构图）；R1/R2/D2/D3/D4 改为读者先行、可复述判定；I3 明确 minor_mode 下能力缺陷标签与为当事人编写亲历场景即失败（合成反例探测中旧 I3 措辞曾被判 pass）。
- **纠正轮新错可再修一次**（team-orchestration §3、chief-judge、`schemas/consistency_report.json`、`scripts/quality_contracts.py`）：round-1 复审时 chief 为每条 blocking 差异标 `introduced_in_round`（须并列 round-0/round-1 原文为证）。仍有原有问题（`0`）即 `blocked`；剩余 blocking 全为纠正稿新写入（`1`）时，同一 analyst 只就这些 claim 定点再修一次，fresh chief 记 `round:2`（新字段 `round2_trigger_discrepancy_ids`），之后仍阻断即 `blocked`。checker 拒绝对旧问题开 round 2，并补回归测试。起因：验证运行中纠正轮新写入的一处计数错误与一处越级表述使 S4 无出口阻断；中途试过“闭包撤回”规则，因连带删除人格 7 条、紫微 4 条 claim 使书无内容可写，且与 checker 冲突，已撤掉。
- **layout 修补上限**（team-orchestration §9）：每轮成书最多两次纯 layout 修补，第二次只能套用 `output-template.md` 已有规则；第一次修补后仅剩 layout 类 fail 时判 `revise` 而非 `blocked`。模板打印规则补上“图题、`.chart-description` 与图形本体同页，数据长表可分页”，起因：验证书中星盘图题与圆盘被拆到两页（P2 fail）。
- **合同缺口**：S3/S5/S6 claim 统一由 Leader 补 `owner/status` 登记；writer 输出统一为 `$WS/book.html`，交付副本另存 `{subject}_命书.html`。

## v5.0.0 — 2026-09-27

**质量优先的破坏性合同切换**：保留性格本位、人文文风、传统体系与 HTML+PDF 双交付；重做计算口径、证据链、质量门与版式合同。不兼容 v4 的 intake/判官/图表计划/终审字段，无别名。

### 计算

1. **单一时间管线**（`_common.normalize_birth_time`）：一次规范化出生输入，输出 `time_context`（UTC 瞬间、固定 UTC+8 节气轴、本地平/视太阳时、Swiss `time_equ` 均时差、fold/gap、公历/儒略历、农历含闰月）。删除按时区中心经线的旧公式与 UTC+8 兜底；城市重名返回候选。芝加哥例真太阳时 −56.45 分钟（旧实现差一小时）。
2. **四柱**：年/月柱、节气与起运走节气轴，日/时柱走本地视太阳时；`--zi-hour-rule midnight|zi_start` 用 `setSect`，不再移动出生瞬间；十神/神煞等从最终柱重算；缺 `calculation_sex` 不默认女命。
3. **紫微**：JD 适配后统一 `by_lunar`，闰月中分法主盘 + `fix_leap=False` 对照盘；删除按历史事件择盘。
4. **占星**：UT1、逐星 flags/引擎披露；Placidus 失败只标宫位不可用（保留 ASC/MC），显式 `whole_sign` 才切换；删除 Kerykeion；`standard-v1` 相位表。
5. **人格与合盘**：`jung_calc` 保留原分与量程，新增 `--scores16`（原值+差值，不聚合）；删除出生盘推人格、Grip 风险星数、缺陷字典、`--hints`。`synastry_calc` 删除匹配总分/星级，改为分层 available/unavailable 观察。
6. **统一外壳** `schemas/chart_bundle.json`（schema_version 2），CLI 退出码 0/1/2；`requirements.txt` 锁定直接依赖（含 jsonschema 4.25.1）。

### 证据与流程

- 新增 `intake_brief`、`case_evidence`、`sources`、`runtime_trace` schema 与 `scripts/quality_contracts.py`；重订 judge/consistency/chart_plan/final_verdict。
- 独立分析后综合：判官输入隔离、`expected_judges` 覆盖校验、每维一次纠正复审；chief 按证据分类分歧，删除一致性评级。
- `references/sources.json` 公共引文目录；未核原话不得署名引用；取消最低引文数。
- roles 分档与 `task_fingerprint` 同案复用、runtime_trace 成本观测。
- 适龄合同、截图双转录、隐私默认不外传。

### 成品与验收

- 输出模板合并为一套 CSS：disclosure/body/appendix 语义结构，details 仅附录；次文字色加深至 ≥4.5:1；打印字号底线。
- 图表计划删除 26 图/锚点六图配额；新增 P17 亚型哑铃图；图表数据 `data-value-ref` 回链。
- `validate_book.py`（必需 `--plan --evidence`）、新增 `guard_book.py`（受限修订与 prepare-revision）、`export_pdf.py`（`--verdict` 前置、附录展开、tagged/outline、内容与字号核对，删除页数门槛与自动剪页）。
- 终审改为 16 项 I/A/R/D/P，pre/post 裁决，删除降级交付。


### 验收记录（2026-09-28）

- 单元测试 70 项通过；回归 18 例（3 例有独立数值锚点 PASS，15 例 CONTRACT_OK，0 FAIL）。
- 真实个案（13 岁、JUNGUS 16 亚型截图）omp 端完整跑通 S0–S10：S4 拦下 4 项阻断（五行最少项计算错、分值升级为行为描述、来源状态越级、占星相位推个体困难），定点修订后 fresh chief 通过、判官未重跑；PDF 复核拦下短框跨页与表格字号 9.495pt 后纯排版修补；终审 16 项 pass、HTML/PDF 哈希一致。两名独立评审未发现阻断问题，一致指出防御性否定句重复、流程术语外露削弱文气。
- 侯稿失败机制负例（6 处注入）：终审全部定位并阻断；validate_book 机器拦截正文 details 与隐藏/注释夹带，语义类（比喻升级为能力、假想经历、盘面推疾病、NERIS 冒称实测）依赖终审。
- 验收后修正：导出字号门槛去掉 0.05pt 容差，模板打印字号按 Chromium 实测留 0.1pt 余量；validate_book 按 JSON Pointer 段匹配后代绑定；账本唯一 `case_evidence.json`；D1 须附 canonical 账本 validator ok 输出；D4 对隐藏/折叠关键信息一律 fail；book-writer 新增文风节（命题式开篇、先结论后展开、术语转译、可证伪的竞争解释、可调整行动；剔除宿命断语与贬义原型标签）；修正两条《子平真诠》引文原文。
- 文风重写复测（复用 S0–S4C，重跑 S5–S10）：终审 16 项 pass、22 页；八字图“五行统计口径”缺绑定已补。运行中暴露并修正三处工具问题：PDF 文本提取的 CJK 部首别名（如 ⺒→巳）误报缺块；页眉标题被当正文判字号；账本中未被引用的历史 artifact 被当作失效错误（被引用的非 current 产物仍无法解析而失败）。否定式边界句仅小幅减少，文气仍待改进。
- 未完成：Claude Code 端未跑真实成书；六个合成 fixture 双端矩阵按用户要求改为单一真实个案；成本遥测本次无可归属 usage，未做节省比例结论。
---

## v4.1.0 — 2026-09-27

**Claude Code / omp 双端适配 + 修复 v4.0 遗留的 🔴 缺陷**。做法沿用 strategic-insight-longform 的「单源 skill + 三层间接」：编排动词、能力词、模型角色三层中立化，工具名只出现在 `runtime-{omp,cc}.md`。

### 缺陷修复（先修后适配：回归不可信时无法判断适配是否引入差异）

1. **占星段重复经度校正**（`cast_chart.py`）：占星改传钟表时。回归新增「占星直调对照」后，v4.0 脚本在 17 条命例上**全部 FAIL**（上升偏 0.4°–10.2°），v4.1 全部一致。新增 `元数据.时刻口径` 说明八字/紫微（真太阳时）与占星（钟表时）的口径差。
2. **判官隔离数据层**：`bazi/ziwei/astro_calc.py` 默认不再输出 `性格映射提示`（预置荣格结论），需显式 `--hints`；判官链路永不使用。
3. **JUNGUS 0-30 量程**（`jung_calc.py`）：新增 `--scale`（缺省按最高分推断），置信度/预警/Grip/可塑性按 0-10 归一后判定；输出新增 `量程` 字段。0-10 输入的输出与 v4.0 逐字节一致。
4. **`--tz` 未传给占星**：显式 `--tz` 时占星段仍用 IANA 推导的偏移（1911 年前为 LMT），与八字口径不一致；现以显式 `--tz` 为准。
5. **子脚本解释器**：`cast_chart.py` 调子脚本改用 `sys.executable`；八字 JSON 的「真太阳时状态」不再误标「未校正」。
6. **S7→S9 契约不通**：chart-director 产出 `chart_plan.chart_table`，`validate_book.py --plan` 只认 `charts` 并在该形状上崩溃（AttributeError）；现直接读 `chart_table`，结构不符时 exit 2 并给出提示。
7. `astro_calc.py` 的 `from __future__` 位于 docstring 之前导致 `__doc__` 为 None、用法说明打印为「None」；已调整顺序。

### 回归套件

- 撤销 14 处早已过期的 astro nullable；每条命例新增度数级锚点（上升/太阳黄经，±0.02°）。
- 新增「占星直调对照」：钟表时直调 `astro_calc.py`，儒略日与上升黄经须与 `cast_chart.py` 一致——专拦时间管线错误。
- 过滤条件未匹配任何用例时 exit 2（原为 exit 0 的假绿）。

### 双端适配

- `references/team-orchestration.md`：中立动词（dispatch/barrier/collect/message/fresh_spawn/ask_user/teardown），新增 §9 能力词、§10 运行环境与工作区（`$DM` / `$DM_PY` / `$WS`，不用共享的 `local://`/scratchpad）、§11 模型分档、§12 schemas；§1 判官隔离补数据层/任务层/通道层封堵与污染分级处置。
- `references/runtime-omp.md` / `runtime-cc.md`：两端工具映射的唯一出处。
- `adapters/omp/dm-{deep,research,light}.md`：omp 三档 teammate agent，只写 omp 角色（`@slow/@default/@smol`），软链到 `~/.omp/agent/agents/`；skill 软链到 `~/.agents/skills/` 供 omp 发现。
- `schemas/`：judge_verdicts / consistency_report / chart_plan / final_verdict 四份 JSON Schema，派遣时挂载强校验。
- `scripts/doctor.py`：第 0 步 preflight（解析依赖齐备的 `$DM_PY`、实际启动 Chromium、样盘判官隔离自检、omp 适配件、可选完整回归），🔴 非 0 退出。
- agent 契约里的 `Read/Write/Bash/WebFetch/WebSearch/Playwright/AskUserQuestion/scratchpad` 全部改为能力词；intake-refiner 不再直接问用户，改为产出 `questions_for_user` 由 Leader 代问。
- 运行环境：本机 PATH 上没有依赖齐备的 python3（系统 3.9 缺 playwright/geo，homebrew 3.12 缺排盘库），统一用 venv `~/.local/share/destiny-matrix/venv`。

### 验收脚本加固（与 locked-checklist 对齐）

- `validate_book.py`：恰好 8 章（多于 8 → M-EXTRA 🔴）；C2/C3 只数带 `data-chart-id` 的图表容器；C1 必须提供 `--plan`，缺失/计划外/重复 id 均判 fail；W1 覆盖卷首与正文，否定豁免改为「同句 40 字内有否定/禁止提示词」（含「未使用」「严禁」「不得」等，列表形式整体豁免）——案例B成书 W1 误报从 8 处降为 1 处真实命中；E4 每章最多计一次评级块。
- `export_pdf.py`：`MIN_PAGES` 6→20（P1）；裁掉末尾空白页时打印数量；参数个数错误、输出与输入同路径 → exit 2；渲染/启动错误单行 `ERROR:`；pypdf 改为必需依赖。
- `chart_data.py`：`--step`/`--max` ≤0、非有限数、畸形键值、重复标签 → exit 2（原先死循环/除零）。
- `synastry_calc.py` / `jung_calc.py`：用户提供的 JSON 读不了即报错退出，不再静默当作缺省继续。

### 已交付命书复核与文档勘误

- 复核三份已交付命书的占星三轴心（记录见 `memory/analysis-sessions/2026-09-27-占星复核.md`）：案例A命书上升应为摩羯 3.34°（原书射手 29.9° 系本次修复的 bug 所致），案例C（v2）月亮应为天蝎（原书射手），案例B一致。
- 文档原把「案例A上升 29.87° 交界」当作交界警戒范例；该交界是错盘产物。SKILL.md、astro-analyst、external-verifier、external-verification、astrology-framework、chart-patterns 已更正，并新增教训：触发交界警戒时先核时间口径（占星钟表时、八字/紫微真太阳时），外部验盘也须输入钟表时。

---

## v4.0.0 — 2026-07-15

**Agent Team 重构**：从「单上下文按 Phase 自觉执行」→「Leader + 18 teammate 的 Stage DAG（S0-S10），质量门由阶段交接验收」。参照 strategic-insight-longform 架构。设计契约 `V4_PLAN.md`。

直接动因（案例A命书实测三问题 + 一新需求）：模块缺失靠人眼发现、无自动外部交叉比对、图表生成不稳定；新增 PDF 交付需求。

### 五大主线改动

1. **Stage DAG + 18 agent**（`agents/*.md` + `references/team-orchestration.md`）：三铁律（task I/O 不落盘/依赖显式/写盘所有权单一）、判官隔离铁律（S4 只喂 JSON 防叙事传染）、fresh-writer 修订流（max 1）、委派五要素、键序铁律。Leader 只路由不代笔。
2. **图表体系**（`references/chart-patterns.md`）：P01-P16 十六模式库（骨架+坐标公式+案例A版 31 图已验证实例）、运行时图表规划表契约、配额下限（全书 ≥26）、锚点六图、data-chart-id 核销、组合与发明授权条款。辅助脚本 `scripts/chart_data.py`（radar/wheel/timeline/arc 纯坐标计算）。
3. **外部验盘 S2**（`references/external-verification.md`）：7 校验点固定表、8 个 2026-07-15 实测可用在线源（含引擎独立性警告：ziwei.pub=iztro 同源）、交界警戒硬触发（±1°/±10min，案例A上升 29.87° 教训）、分歧仲裁三步、时辰反查三档。
4. **机器验收 + 双产物**：`scripts/validate_book.py`（M/C/W/E 机检，案例A回归实测抓出人眼漏掉的 r="0" 缺陷）+ `references/locked-checklist.md`（M/C/W/E/P 五组固定 ID，🔴/🟠 两级后果）+ `scripts/export_pdf.py`（Playwright，实测 84 页无劈断）+ output-template.md v4 增补 @media print。
5. **知识增强**（R1-R4 联网调研，全部带来源，以「v4 增补（2026-07-15）」小节追加）：Beebe 2016 核准表与引文勘误（A/H 编码「整体型」禁译「人本型」、"you will call it fate" 真出处 Aion CW 9ii §126）、《子平真诠》章次核对表与「调候之神」出处勘误、神煞出处分档、子时换日两派梳理（旧「early=主流」注释勘误）、紫微四化四版本与 iztro 偏差表与 37 杂耀清单、交界上升惯例与分宫制边界。

### 新增红线

- 典籍引用规范：伪引用 = 最高级 🔴；数量基线（玄学三章各 ≥3 处、性格章 ≥3 处、感情 ≥2 处）；未核实页码降级章节级引用。
- 调性红线：工程约束不得侵蚀文气；融合体 5 技法为 writer 硬契约；图表标题必须叙事性；机器校验不得要求诗性标题含固定关键词。

---

## v3.0.0 — 2026-05-11

**哲学骨架翻转**：从「四维平权 · 交叉验证」 → 「**性格本位 · 玄学辅证 · 命运可塑**」

v2 把荣格八维与八字/紫微/占星视为四维平权，横向投票得出共振结论。v3 翻转为纵向递进：**荣格八维是「主语」，玄学三维是「谓语与状语」**。玄学不"决定"任何事，只"印证 / 映照 / 解释"性格的展开；性格可发展（Jung 个体化进程），所以命运可塑。

### 三大主线改动

#### ① 哲学骨架层（核心理念落地）

| 维度 | v2 实现 | v3 实现 |
|:---|:---|:---|
| 定位 | 四维平权 · 共振投票 | 性格本位 · 玄学辅证 |
| Phase 2 | 四维并行独立分析 | Phase 2.0 性格画像（必先） → 2.1/2.2/2.3 玄学三维围绕性格签名 |
| Phase 3 | "一致性评级" = 信心度 | "玄学三维印证性格签名" = 文化坐标清晰度 |
| 命运密码公式 | 四维证据共振 | **性格底色 × 玄学时机** |
| 终极课题 | 含糊综合 | 必出自荣格劣势/阴影整合 |
| 输出章节 | 散乱并列 | **8 章固定结构**（性格 35-45% + 玄学三维各 15%）|

新增哲学文档：
- `references/character-first-manifesto.md` — Heraclitus + Jung + 萨特 + 神经可塑性 + 《了凡四训》
- `references/character-inference-workflow.md` — Tier 1（必测）/ Tier 2（访谈反推 10 题）/ Tier 3（玄学反推规则表）

《果老星宗》"体用相参"被重新解读：「**体**」= 性格本质（荣格），「**用**」= 玄学时机注解。

#### ② 计算引擎层（脚本工具链工程化平权）

| 维度 | v2 | v3 |
|:---|:---|:---|
| 荣格八维 | ❌ 无脚本 | ✅ `jung_calc.py`（性格签名 + Beebe 8 原型 + Grip 五档评估 + 16 类型 SIGNATURES）|
| 公共工具 | ❌ 无 | ✅ `_common.py`（geonamescache + timezonefinder + DST + 真太阳时校正）|
| 八字 | 12 组调候（仅甲木）| **120 组调候**（10 日主全覆盖）+ **17 神煞**（按四柱分列）+ 早/夜子时参数 + 跨节气警告 |
| 紫微 | 默认派别隐式 | 派别明示（三合派）+ 闰月双盘（中分法 / 正玄山人法）+ 性格映射提示 |
| 占星 | P0 bug + 仅基础配点 | 修 bug + 高纬度 Whole Sign fallback + Lilith/福点/Vertex/True Node 全配点 + kerykeion SVG 圆盘 |
| 合盘 | ❌ 无 | ✅ `synastry_calc.py`（性格层主语 + 玄学三层辅证 + 16×16 配对矩阵）|
| 城市覆盖 | 70 硬编码 | geonamescache 25000+ 城市 + 模糊匹配 + zoneinfo DST-aware |

#### ③ 文档体系层

| 文件 | v2 | v3 | 增量 |
|:---|---:|---:|:---|
| `cognitive-functions.md` | 123 行 | **1100+ 行** | 9 倍扩展（8 功能子模式 + Beebe 临床 + Grip 16 类型 + 个体化进程 + 阿尼玛/阿尼姆斯）|
| `jung-classical-texts.md` | — | **~600 行** | Jung CW 6/9i/9ii/14/16 + Beebe + von Franz + Quenk + Thomson + Hartzler |
| `jung-relationship-dynamics.md` | — | **~1100 行** | 8 桥接对 + 16×16 矩阵 + 阿尼玛 4 阶段 + Beebe Child + Inferior 投射 |
| `cross-analysis-patterns.md` | 212 行 | **~600 行** | 三精细映射表（十神↔功能 / 紫微 14 主星↔Beebe / 行星↔功能）+ 玄学解释力评级 |
| `shensha-table.md` | — | **~360 行** | 17 神煞详解 + 性格映射 + 女命解读硬性规则 |
| `output-template.md` | 652 行 | **1050 行** | 8 章结构 + 3 SVG 资产（雷达图/Beebe 环/Grip 仪表盘）+ 64 主导功能隐喻 |

#### ④ 防幻觉机制（v3 新增）

借鉴 `weizeW/mingli-skills` 的 Phase-Gating + Adversarial Evaluator：

- **6 道 Phase Gate**：Phase 1→1.5→2.0→2.x→3→5 每层禁止跳过
- **4 判官独立审查**（八字/紫微/占星/荣格）：仅看原始 JSON 重新推论一次，分歧 > 1 必须披露
- **禁词清单**：`克夫/真命天子/这辈子注定/改命` 等 7 条禁止表述
- **质量自检 10 项**：性格章占比、玄学解释力评级、命运密码公式、可塑路径、判官分歧披露、未承诺具体年份事件等

#### ⑤ 评估与质量保障

- `tests/regression_baseline.json` 17 用例（12 名人 + 5 边界）
- `tests/run_regression.py` graceful 运行器
- `tests/README.md` 用法 + 失败处理指引
- **回归测试 16/17 PASS**（毛泽东命宫 WARN，公开命例本身有争议）

---

### 文件结构变化

```
新增（13 个）：
├── V3_PLAN.md                              # 施工蓝图
├── references/
│   ├── character-first-manifesto.md        # ★ 哲学宣言
│   ├── character-inference-workflow.md     # ★ Tier 1-3 性格采集
│   ├── jung-classical-texts.md             # ★ 荣格典籍
│   ├── jung-relationship-dynamics.md       # ★ 关系动力学
│   └── shensha-table.md                    # 八字神煞
├── scripts/
│   ├── _common.py                          # 公共工具
│   ├── jung_calc.py                        # ★ 荣格计算引擎
│   └── synastry_calc.py                    # 合盘脚本
├── tests/
│   ├── regression_baseline.json            # 17 用例
│   ├── run_regression.py
│   └── README.md
└── memory/                                 # skill 内部记忆系统

重写：
├── SKILL.md                                # v3 性格本位骨架
├── references/
│   ├── cognitive-functions.md              # 123 → 1100+ 行
│   ├── cross-analysis-patterns.md          # 212 → 600+ 行
│   └── output-template.md                  # 652 → 1050 行
└── scripts/
    ├── bazi_calc.py                        # 调候补全 + 神煞 + 子时规则
    ├── astro_calc.py                       # P0 bug 修复 + 扩展配点 + SVG
    ├── ziwei_calc.py                       # 派别明示 + 闰月双盘
    └── cast_chart.py                       # geonamescache + DST + 真太阳时

不变：
├── references/astrology-framework.md
├── references/bazi-framework.md
├── references/classical-texts.md
├── references/liunian-analysis.md
├── references/relationship-analysis.md
├── references/special-patterns.md
├── references/ziwei-framework.md
└── _archive/v1/
```

注：v2 没有专门归档（直接演进到 v3）；v1 完整备份保留在 `_archive/v1/`。

---

### 依赖变化

```bash
# v3 新增
pip install geonamescache timezonefinder kerykeion --break-system-packages

# v2 保留
pip install lunar_python iztro-py pyswisseph sxtwl --break-system-packages
```

---

### 工程指标对比

| 指标 | v2 | v3 |
|:---|---:|---:|
| 计算脚本数 | 4 | **7** |
| references 文档数 | 10 | **15** |
| 总代码行 | ~3800 | **~9500+** |
| 荣格框架行数 | 123 | **1100+** |
| 调候用神组数 | 12 | **120** |
| 神煞数 | 0 | **17** |
| Phase Gate | 0 | **6** |
| 回归测试覆盖 | 0 | **17 用例 / 94% PASS** |

---

### v3 已知尾巴（待 v3.1 处理）

- 毛泽东命宫地支 WARN（公开命例本身争议，需人工核定真实出生时辰）
- geonamescache 缺县级城市（湘乡/余姚/淮安/绍兴/Seattle/SF），目前用显式 lat/lon 绕过
- Chiron 凯龙星报错 `seas_18.se1 not found`（swisseph asteroid 星历表缺失）
- 飞星派紫微校验未做（v3 默认三合派）

---

### 致谢与参考

新增致谢：
- [g-battaglia/kerykeion](https://github.com/g-battaglia/kerykeion) — 占星 SVG 圆盘
- [weizeW/mingli-skills](https://github.com/weizeW/mingli-skills) — Phase-Gating + Adversarial Evaluator 范式
- [smogievogie/ziwei_iztro-mcpserver](https://github.com/smogievogie/ziwei_iztro-mcpserver) — 真太阳时算法
- [DestinyLinker/MingLi-Bench](https://github.com/DestinyLinker/MingLi-Bench) — 命例回归测试启发

---

## v2.0.0 — 2026-05-02

**核心定位升级**：从「自助算命工具」 → 「分析师的命书生成框架」

v1 假设对话方为命主本人；v2 改为「分析师代他人分析」场景：使用者掌握命主完整信息（含已知历史事件），最终输出为给命主本人阅读的成品命书。

---

### 三大主线改动

#### ① 计算引擎层

| 维度 | v1 实现 | v2 实现 | 主要增益 |
|:---|:---|:---|:---|
| 八字 | sxtwl + 自写起运 | `lunar_python` (主) + sxtwl (校验) | 起运精度从「整数岁」到「年-月-日」；内置纳音/藏干/十神/空亡/大运/流年 |
| 紫微 | 自写安星诀 (260 行) | `iztro-py` | 完整十四主星 + 杂耀 + 亮度（庙旺得利平不陷）+ 长生/博士/将前/岁前十二神 + `horoscope()` 一键拿大限/流年/流月/流日/流时 |
| 占星 | 无脚本（手算） | `pyswisseph` (新建 `astro_calc.py`) | 上升 + 10 大行星 + 12 宫 + 相位（瑞士星历，业界标准）|
| 调度 | 各脚本分别调用 | `cast_chart.py` 统一调度 | 一次输出三体系 JSON |

#### ② 方法论层

- **新增 `references/classical-texts.md`**：九大命理典籍按 destiny-matrix 框架重组
  - 《滴天髓》《子平真诠》《渊海子平》《穷通宝鉴》《三命通会》《神峰通考》《果老星宗》《千里命稿》《协纪辨方书》
  - 每条命理论断要求标注典籍出处，提升专业性与可追溯性
- **《果老星宗》"星命合参"** 写入概述：占星×四柱在传统命理中的理论根据，非现代拼接
- **Phase 1.5 时辰反查校准**：用分析师已知的命主历史事件反推时辰准确度
  - 应期吻合 → 排盘可信，进入完整分析
  - 不吻合 → 提示时辰修正方向（早/晚一时辰、夜子时归属、真太阳时校正）

#### ③ 输出层

- **「融合体专业叙事」取代信息堆叠**——技术内容直接化作叙事的肌理，无折叠分层
- **新增 `references/output-template.md`**：
  - HTML 骨架（CSS 模板，黑红灰审美）
  - 术语词典 60+ 条（6 个域：性格 / 感情 / 事业 / 财运 / 健康 / 流年）
  - 措辞柔化对照表 35+ 条
- **5 个写作技法**编码进模板：
  1. 术语带电出场（专业术语第一次出现时即时携带解释）
  2. 数据嵌入叙事（年龄/度数/权重作为句子骨头）
  3. 典籍作为重音（古文引用是高潮锤音，非脚注）
  4. 判断—解释—行动暗示三段式
  5. 古典化收束（章节末"四字短语+一句注解"）

---

### 文件结构变化

```
新增：
├── CHANGELOG.md
├── _archive/v1/                    # v1 完整备份
├── references/
│   ├── classical-texts.md          # 九大典籍
│   └── output-template.md          # HTML 骨架 + 术语词典 + 柔化表
└── scripts/
    ├── astro_calc.py               # pyswisseph 占星
    └── cast_chart.py               # 统一调度

重写：
├── SKILL.md                         # 重构为分析师模式
├── references/
│   ├── astrology-framework.md      # 重写（接入 pyswisseph）
│   ├── bazi-framework.md           # 更新（lunar_python 调用）
│   ├── cross-analysis-patterns.md  # 加入《果老星宗》星命合参段
│   └── ziwei-framework.md          # 更新（iztro-py 调用）
└── scripts/
    ├── bazi_calc.py                # 重写（lunar_python 主）
    └── ziwei_calc.py               # 重写（iztro-py）

不变：
├── references/cognitive-functions.md
├── references/liunian-analysis.md
├── references/relationship-analysis.md
└── references/special-patterns.md
```

---

### 不再支持的功能

| 项目 | 移除原因 |
|:---|:---|
| 交互式信息收集（9 步问答） | 分析师模式下，分析师掌握信息，无需 Claude 一步步问 |
| 历史事件校准（用户层版） | 朋友只看一次成品；已反向用为时辰校准 |
| 双版本输出（友好+专业） | 已被融合体叙事替代 |
| 折叠技术档案 | 已被融合体叙事替代 |

---

### 依赖变化

```bash
# v2 新增依赖
pip install lunar_python iztro-py pyswisseph --break-system-packages

# v1 依赖（保留作交叉校验）
pip install sxtwl --break-system-packages
```

---

## v1.x — 2025

初始版本。核心架构（四维交叉、感情专题、双轨时间线、调候用神）成熟于此版本。完整文件保存于 `_archive/v1/`。

主要参考与致谢：
- [SylarLong/iztro](https://github.com/SylarLong/iztro) — 紫微安星权威实现
- [6tail/lunar-python](https://github.com/6tail/lunar-python) — 八字标准库
- [jinchenma94/bazi-skill](https://github.com/jinchenma94/bazi-skill) — 九大典籍论命方法论
