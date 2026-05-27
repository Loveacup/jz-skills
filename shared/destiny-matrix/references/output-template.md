# 输出模板 · v3 · 性格本位重构

> v3 立场：**性格决定命运，玄学辅证，命运可塑**。本模板将「性格画像」抬升为命书第一主角（Chapter 1，篇幅 35-45%），八字 / 紫微 / 占星降为"解构 / 对应 / 映照"三个解释维度（各 15%）。所有 HTML 骨架、CSS、术语词典、措辞柔化对照表沿用 v2 工程资产，仅在结构层与措辞层做 v3 增量。

本文件是 Phase 6 输出的**唯一指导文档**。包含七部分：

1. v3 八章结构与篇幅表
2. HTML 骨架（CSS 模板 + 章节结构）
3. Chapter 1 性格画像专章模板（含三大可视化资产）
4. 玄学解释力评级 HTML 块（每个玄学章节末尾必须有）
5. 主导功能隐喻库（8 个主导各 6-8 个比喻 · v3 关键资产）
6. 术语词典（60+ 高频命理术语 · v2 沿用 + v3 新增荣格段）
7. 措辞柔化对照表（v2 沿用 + v3 增量五条）

---

## 〇、v3 八章结构与篇幅表

| Chapter | 标题 | 篇幅占比 | 角色 |
|:---|:---|:---|:---|
| 1 | **性格画像（荣格主导）** | 35-45% | ★ 主角 |
| 2 | 八字解构 —— 性格的能量基础 | 15% | 解构 |
| 3 | 紫微对应 —— 性格的剧场舞台 | 15% | 对应 |
| 4 | 占星映照 —— 性格的宇宙节律 | 15% | 映照 |
| 5 | 三维印证度评估 | 5% | 评级 |
| 6 | 双轨时间线（性格发展 + 玄学时机） | 5% | 时机 |
| 7 | **感情专题** | 必须充分 | 必有 |
| 8 | 终极课题（个体化任务 + 应期窗口） | 5% | 收束 |

**铁律**：
- Chapter 1 是命书的"主角"，所有玄学章节都必须以"印证 / 对应 / 映照 Chapter 1 已确立的性格签名"为叙述出发点。
- Chapter 2-4 末尾必须出现「玄学解释力评级」HTML 块（见第四节模板）。
- 措辞统一参考第七节的 v3 增量表：禁用"决定 / 命中注定 / 改命"。

---

## 一、核心写作技法（v2 沿用）

每次输出都必须遵循以下五条：

### 技法 1 · 术语带电出场

专业术语第一次出现时，**立刻并列携带解释或比喻**，不延后到下一段。

> ❌ 你的夫妻宫有武曲。武曲是一颗将星，主刚毅果决。
>
> ✅ 你的夫妻宫坐着武曲——紫微斗数十四主星里最讲究"主见"的将星。

视觉：用 `<span class="term">武曲</span>`（下划线-emphasis），不用 bold。

### 技法 2 · 数据嵌入叙事

年龄区间、五行权重、行星度数、十神比例不孤立列表，而是当作句子的"骨头"。

> ❌ 大运叠加：壬戌（24-33 岁），偏印透干。
>
> ✅ 这十年（壬戌大运，偏印透干），你的情感能量是从外向内沉淀的。

视觉：用 `<span class="data-inline">数据</span>` 作 inline 处理。

### 技法 3 · 典籍作为重音

古文引用是叙述高潮的"锤音"，不是脚注。落下后必须紧接一句"这一句几乎就是为你的性格写的"式的承接，把典籍力道转化为对命主的具体判断。

视觉：用 `<div class="classic">` 块，serif 字体 + 左竖线 + 灰底。

### 技法 4 · 判断—解释—行动暗示 三段式

每个核心论断包含三层：**判断**（性格 / 命理事实）—**解释**（在你身上长成什么样）—**行动暗示**（你该怎么活它）。

### 技法 5 · 古典化收束

每章末尾用 **"四字短语 + 一句注解"** 收束，类似传统命书的"断曰"。

视觉：用 `<div class="summary-frame">`，serif 大字 + 一行小注。

### 技法 6 · v3 新增 · "性格优先"修辞

凡论及玄学维度，开口必先回扣 Chapter 1 的性格签名，结构如：

> 你的 Ni 主导 + Te 副从（Chapter 1 已确立）—— **这一签名在八字里被解构为 X**：壬水日主透出辛金印星，正是 "Ni 看见远方 + Te 砌墙建构" 的能量底色。

禁用句式：「八字决定你 X」「紫微注定你 Y」「星盘命中你 Z」。

替换：「八字解构你的 X」「紫微对应你的 Y」「星盘映照你的 Z」。

---

## 二、HTML 骨架（v2 CSS 完整保留 + v3 视觉化扩展）

成品命书是单 HTML 文件。结构如下：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{命主姓名} · 命书</title>
<style>
:root {
  --bg: #fafaf8;
  --bg-alt: #f3f1ec;
  --text: #1a1a1a;
  --text-secondary: #5a5a5a;
  --text-tertiary: #8a8a8a;
  --accent: #8a1a1a;
  --accent-soft: #b85c5c;
  --border: #d5d2c8;
  --hero: #2c5f7c;
  --parent: #4a8b5c;
  --child: #d4a574;
  --inferior: #8a1a1a;
  --font-sans: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-serif: "STSong", "Songti SC", "SimSun", Georgia, serif;
}

body {
  font-family: var(--font-sans);
  font-size: 16px;
  line-height: 1.8;
  color: var(--text);
  background: var(--bg);
  max-width: 720px;
  margin: 0 auto;
  padding: 3rem 2rem;
}

/* 标题层级 */
.book-title {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 500;
  text-align: center;
  margin: 0 0 0.5rem;
  letter-spacing: 0.05em;
}

.book-subtitle {
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  letter-spacing: 0.1em;
  margin: 0 0 4rem;
  text-transform: uppercase;
}

.section-num {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
  margin: 4rem 0 0.25rem;
  text-transform: uppercase;
}

.section-title {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
  margin: 0 0 1.5rem;
  color: var(--text);
}

/* 主文 */
p.body {
  font-size: 16px;
  line-height: 1.85;
  color: var(--text);
  margin: 0 0 1.4rem;
}

p.body strong { font-weight: 500; color: var(--text); }

/* 命理术语 */
.term {
  color: var(--text);
  font-weight: 500;
  border-bottom: 1.5px solid var(--border);
  padding-bottom: 1px;
}

/* 数据嵌入 */
.data-inline {
  display: inline-block;
  padding: 1px 7px;
  background: var(--bg-alt);
  border-radius: 4px;
  font-size: 14px;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  margin: 0 2px;
}

/* 典籍引用 */
.classic {
  font-family: var(--font-serif);
  font-style: italic;
  padding: 14px 18px;
  border-left: 2px solid var(--text-secondary);
  margin: 1.5rem 0;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.7;
  background: var(--bg-alt);
}

.classic .src {
  display: block;
  font-style: normal;
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 8px;
  letter-spacing: 0.04em;
  font-family: var(--font-sans);
}

/* 多维交叉验证 grid */
.cross-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0;
  margin: 1.5rem 0;
  border-top: 0.5px solid var(--border);
  border-bottom: 0.5px solid var(--border);
}

.cross-cell { padding: 12px 16px; border-right: 0.5px solid var(--border); }
.cross-cell:last-child { border-right: none; }
.cross-label { font-size: 11px; color: var(--text-tertiary); letter-spacing: 0.05em; text-transform: uppercase; margin: 0 0 4px; }
.cross-data { font-size: 14px; color: var(--text); line-height: 1.5; font-weight: 500; }
.cross-gloss { font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-top: 4px; }

/* 章节定调 frame */
.summary-frame {
  border: 0.5px solid var(--text-secondary);
  padding: 1.5rem 1.75rem;
  margin: 2.5rem 0 1rem;
  border-radius: 4px;
}

.summary-frame .label { font-size: 11px; color: var(--text-tertiary); letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 8px; }
.summary-frame .verdict { font-family: var(--font-serif); font-size: 20px; font-weight: 500; line-height: 1.5; color: var(--text); margin: 0 0 6px; letter-spacing: 0.02em; }
.summary-frame .gloss { font-size: 13.5px; color: var(--text-secondary); line-height: 1.6; margin: 0; }

/* 数据可视化容器 */
.chart-container { margin: 2rem 0; padding: 1.25rem; background: var(--bg-alt); border-radius: 4px; }
.chart-title { font-size: 12px; color: var(--text-tertiary); letter-spacing: 0.05em; text-transform: uppercase; margin: 0 0 1rem; }

/* 表格 */
table.chart-data { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 14px; }
table.chart-data th { background: var(--bg-alt); padding: 8px 12px; text-align: left; border: 0.5px solid var(--border); font-weight: 500; }
table.chart-data td { padding: 8px 12px; border: 0.5px solid var(--border); }

/* 紫微 12 宫 */
.ziwei-board { display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(4, auto); gap: 0; border: 0.5px solid var(--border); margin: 2rem 0; font-size: 12px; line-height: 1.4; }
.ziwei-cell { border: 0.5px solid var(--border); padding: 8px; min-height: 100px; }
.ziwei-cell .palace-name { font-weight: 500; color: var(--text); font-size: 13px; margin-bottom: 4px; }
.ziwei-cell .palace-stem { font-size: 11px; color: var(--text-tertiary); }
.ziwei-cell .major-star { color: var(--accent); font-weight: 500; }
.ziwei-cell .minor-star { color: var(--text-secondary); }

/* 命主信息卡 */
.subject-card { background: var(--bg-alt); border-radius: 4px; padding: 1.5rem 1.75rem; margin: 0 0 3rem; font-size: 14px; line-height: 1.8; }
.subject-card .field-label { display: inline-block; width: 80px; color: var(--text-tertiary); font-size: 12px; }

/* === v3 新增 · 性格画像专章 === */

/* 一句话画像（serif 大字） */
.one-line-portrait {
  font-family: var(--font-serif);
  font-size: 22px;
  line-height: 1.6;
  color: var(--text);
  text-align: center;
  margin: 2rem 0 2.5rem;
  padding: 1.75rem 1.5rem;
  border-top: 0.5px solid var(--text-secondary);
  border-bottom: 0.5px solid var(--text-secondary);
  letter-spacing: 0.03em;
}

/* 性格签名行 */
.signature-line {
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin: 0.5rem 0 2rem;
}

/* 八功能详解卡片 */
.function-card {
  margin: 1.25rem 0;
  padding: 1rem 1.25rem;
  border-left: 3px solid var(--border);
  background: var(--bg-alt);
  border-radius: 0 4px 4px 0;
}

.function-card.hero { border-left-color: var(--hero); }
.function-card.parent { border-left-color: var(--parent); }
.function-card.child { border-left-color: var(--child); }
.function-card.inferior { border-left-color: var(--inferior); }

.function-card .role {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 4px;
}

.function-card .fn-name {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  margin: 0 0 6px;
  color: var(--text);
}

.function-card .fn-body { font-size: 14.5px; line-height: 1.7; color: var(--text-secondary); margin: 0; }

/* Grip 风险仪表盘 */
.grip-meter { margin: 1rem 0; }
.grip-meter .grip-label { font-size: 12px; color: var(--text-tertiary); margin-bottom: 4px; display: flex; justify-content: space-between; }
.grip-meter .grip-bar { height: 8px; background: var(--bg-alt); border-radius: 4px; overflow: hidden; }
.grip-meter .grip-fill { height: 100%; background: linear-gradient(90deg, var(--accent-soft), var(--inferior)); border-radius: 4px; transition: width 0.3s; }

/* 玄学解释力评级块 */
.evidence-rating {
  margin: 2rem 0 1.5rem;
  padding: 1.25rem 1.5rem;
  border: 0.5px solid var(--border);
  border-radius: 4px;
  background: var(--bg-alt);
}

.evidence-rating .er-title {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 0.75rem;
}

.evidence-rating .er-grade {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  margin: 0 0 0.5rem;
  color: var(--text);
}

.evidence-rating .er-grade.high { color: var(--parent); }
.evidence-rating .er-grade.mid { color: var(--child); }
.evidence-rating .er-grade.low { color: var(--text-tertiary); }

.evidence-rating .er-body { font-size: 13.5px; line-height: 1.65; color: var(--text-secondary); margin: 0; }

/* 卷尾 */
.colophon {
  margin: 5rem 0 0;
  padding-top: 2rem;
  border-top: 0.5px solid var(--border);
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

@media (max-width: 600px) {
  body { padding: 2rem 1.25rem; }
  .book-title { font-size: 26px; }
  .section-title { font-size: 20px; }
  .one-line-portrait { font-size: 18px; }
  .cross-grid { grid-template-columns: 1fr; }
  .cross-cell { border-right: none; border-bottom: 0.5px solid var(--border); }
  .cross-cell:last-child { border-bottom: none; }
}
</style>
</head>
<body>

<!-- 封面 -->
<h1 class="book-title">{命主姓名} · 命书</h1>
<p class="book-subtitle">DESTINY MATRIX v3 · 性格本位 · 玄学辅证</p>

<!-- 命主信息卡 -->
<div class="subject-card">
  <div><span class="field-label">公历</span>{yyyy 年 mm 月 dd 日 hh:mm}</div>
  <div><span class="field-label">农历</span>{农历日期}</div>
  <div><span class="field-label">四柱</span>{年柱} {月柱} {日柱} {时柱}</div>
  <div><span class="field-label">出生地</span>{出生地}</div>
  <div><span class="field-label">性格签名</span>{INTJ · Ni-Te-Fi-Se · 命宫{X}主星 · 太阳{Y}}</div>
</div>

<!-- Chapter 1 性格画像（35-45%）-->
<!-- Chapter 2 八字解构（15%）-->
<!-- Chapter 3 紫微对应（15%）-->
<!-- Chapter 4 占星映照（15%）-->
<!-- Chapter 5 三维印证度评估（5%）-->
<!-- Chapter 6 双轨时间线（5%）-->
<!-- Chapter 7 感情专题（必有）-->
<!-- Chapter 8 终极课题（5%）-->

<div class="colophon">
  此命书由 destiny-matrix v3 生成 · 性格决定命运 · 玄学辅证 · 命运可塑<br>
  荣格八维（主语）· 八字（解构）· 紫微（对应）· 占星（映照）
</div>

</body>
</html>
```

---

## 三、Chapter 1 · 性格画像专章模板（v3 主角）

### 3.1 章节骨架（HTML）

```html
<p class="section-num">CHAPTER 01 · 性格画像</p>
<h2 class="section-title">{命主中文名}的性格签名</h2>

<!-- 一句话画像（serif 大字定调） -->
<div class="one-line-portrait">
  {一句诗化定调，30-50 字。例：你是深井里打水的人——看一眼便知井有多深，却很少告诉别人那水的味道。}
</div>
<div class="signature-line">{INTJ · Ni-Te-Fi-Se · 性格签名}</div>

<!-- 开篇叙事（200-400 字）-->
<p class="body">{用 200-400 字铺开主导功能的"主旋律"，引出此命主的认知地图}</p>

<!-- 视觉化资产 1：认知雷达图 -->
<div class="chart-container">
  <p class="chart-title">认知功能强度 · 八轴雷达</p>
  {SVG 雷达图，见 3.2}
</div>

<!-- 视觉化资产 2：Beebe 8 原型环 -->
<div class="chart-container">
  <p class="chart-title">Beebe 八原型 · 性格剧场</p>
  {SVG 同心圆，见 3.3}
</div>

<!-- 八功能详解（每功能 1 段，共 8 个 .function-card）-->
<div class="function-card hero">
  <p class="role">英雄位 · Hero</p>
  <p class="fn-name">{Ni · 内倾直觉}</p>
  <p class="fn-body">{1 段叙述，含主导功能隐喻 1-2 个 + 在你身上的具体表现 + 一句行动暗示}</p>
</div>
<div class="function-card parent">...</div>
<div class="function-card child">...</div>
<div class="function-card inferior">...</div>
<!-- 后 4 个原型（Opposing/Senex/Trickster/Demon）省略样式细节，沿用 .function-card 基类 -->

<!-- 视觉化资产 3：Grip 风险仪表盘 -->
<div class="chart-container">
  <p class="chart-title">劣势功能抓取风险 · Grip Meter</p>
  {Grip 仪表盘，见 3.4}
</div>

<!-- 古典化收束 -->
<div class="summary-frame">
  <p class="label">本章定调</p>
  <p class="verdict">{四字 + 八字短语}</p>
  <p class="gloss">{一句注解：你的性格签名是恒量，玄学三维（Chapter 2-4）将从三个角度对它做解构、对应、映照。}</p>
</div>
```

### 3.2 认知雷达图 SVG 模板（八轴 · 可填充）

八轴顺序固定为 Ni-Ne-Si-Se-Ti-Te-Fi-Fe（顺时针，从正上方起）。每轴长度 0-100，高亮**主导（Hero）**与**辅助（Parent）**。

```html
<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:340px;width:100%;">
  <!-- 背景同心八边形（25/50/75/100 四圈） -->
  <g fill="none" stroke="#d5d2c8" stroke-width="0.5">
    <polygon points="200,125 253,147 275,200 253,253 200,275 147,253 125,200 147,147" />
    <polygon points="200,50 275,95 320,200 275,305 200,350 125,305 80,200 125,95" stroke="#a8a59a" />
    <polygon points="200,87 264,121 297,200 264,279 200,312 136,279 103,200 136,121" />
    <polygon points="200,162 241,174 252,200 241,226 200,238 159,226 148,200 159,174" />
  </g>
  <!-- 八条轴线 -->
  <g stroke="#d5d2c8" stroke-width="0.5">
    <line x1="200" y1="200" x2="200" y2="50" />
    <line x1="200" y1="200" x2="306" y2="94" />
    <line x1="200" y1="200" x2="350" y2="200" />
    <line x1="200" y1="200" x2="306" y2="306" />
    <line x1="200" y1="200" x2="200" y2="350" />
    <line x1="200" y1="200" x2="94" y2="306" />
    <line x1="200" y1="200" x2="50" y2="200" />
    <line x1="200" y1="200" x2="94" y2="94" />
  </g>
  <!-- 数据多边形（占位：Ni=92, Ne=38, Si=22, Se=45, Ti=58, Te=80, Fi=68, Fe=30）
       计算：cx + r * sin(theta), cy - r * cos(theta) ;轴心 (200,200) -->
  <polygon points="{NiX},{NiY} {NeX},{NeY} {SiX},{SiY} {SeX},{SeY} {TiX},{TiY} {TeX},{TeY} {FiX},{FiY} {FeX},{FeY}"
           fill="rgba(44,95,124,0.18)" stroke="#2c5f7c" stroke-width="1.5" />
  <!-- 主导功能高亮节点 -->
  <circle cx="{HeroX}" cy="{HeroY}" r="5" fill="#2c5f7c" />
  <circle cx="{ParentX}" cy="{ParentY}" r="4" fill="#4a8b5c" />
  <!-- 八轴标签 -->
  <g font-family="STSong, Songti SC, serif" font-size="13" fill="#1a1a1a" text-anchor="middle">
    <text x="200" y="40">Ni</text>
    <text x="318" y="92">Ne</text>
    <text x="365" y="205">Si</text>
    <text x="318" y="318">Se</text>
    <text x="200" y="368">Ti</text>
    <text x="82" y="318">Te</text>
    <text x="35" y="205">Fi</text>
    <text x="82" y="92">Fe</text>
  </g>
</svg>
```

**填充指南**：
- `{NiX}, {NiY}` 等坐标按公式 `cx + r * sin(θ), cy - r * cos(θ)` 算，r = 强度值 × 1.5（强度 100 对应 r=150，即雷达边缘）
- θ 顺时针：Ni=0°, Ne=45°, Si=90°, Se=135°, Ti=180°, Te=225°, Fi=270°, Fe=315°
- Hero / Parent 节点用更鲜艳的填充色
- 强度数据来自 `scripts/jung_calc.py` 输出的 `function_stack`

### 3.3 Beebe 8 原型环 SVG 模板（同心圆）

四圈同心圆代表 Hero / Parent / Child / Inferior 四象限的"高度"，外围八扇区分别填入八功能。

```html
<svg viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:320px;width:100%;">
  <!-- 四层同心圆（外圈 Hero，内圈 Demon） -->
  <g fill="none" stroke="#d5d2c8" stroke-width="0.5">
    <circle cx="180" cy="180" r="160" />
    <circle cx="180" cy="180" r="120" />
    <circle cx="180" cy="180" r="80" />
    <circle cx="180" cy="180" r="40" />
  </g>
  <!-- 八扇区分隔线 -->
  <g stroke="#d5d2c8" stroke-width="0.5">
    <line x1="180" y1="20" x2="180" y2="340" />
    <line x1="20" y1="180" x2="340" y2="180" />
    <line x1="67" y1="67" x2="293" y2="293" />
    <line x1="293" y1="67" x2="67" y2="293" />
  </g>
  <!-- Hero 扇区高亮（顶部） -->
  <path d="M 180 180 L 180 20 A 160 160 0 0 1 293 67 Z"
        fill="rgba(44,95,124,0.22)" stroke="#2c5f7c" stroke-width="1" />
  <!-- 8 原型标签（占位，按命主实际功能填入） -->
  <g font-family="STSong, Songti SC, serif" font-size="12" fill="#1a1a1a" text-anchor="middle">
    <text x="235" y="55">英雄 · {Hero 功能}</text>
    <text x="305" y="155">父母 · {Parent}</text>
    <text x="305" y="220">永恒少年 · {Child}</text>
    <text x="235" y="320">劣势 · {Inferior}</text>
    <text x="125" y="320">对立 · {Opposing}</text>
    <text x="55" y="220">批评家 · {Senex}</text>
    <text x="55" y="155">骗子 · {Trickster}</text>
    <text x="125" y="55">恶魔 · {Demon}</text>
  </g>
  <!-- 中心标签 -->
  <text x="180" y="185" font-family="STSong, serif" font-size="14" fill="#5a5a5a" text-anchor="middle">{命主类型}</text>
</svg>
```

### 3.4 Grip 风险仪表盘（HTML 进度条）

劣势功能在高压下的"抓取风险"评分（0-100），按性格类型默认值 + 命主自陈调整。

```html
<div class="grip-meter">
  <div class="grip-label">
    <span>劣势功能抓取风险（{Inferior}）</span>
    <span>{score}/100 · {等级：低 / 中 / 高}</span>
  </div>
  <div class="grip-bar">
    <div class="grip-fill" style="width:{score}%"></div>
  </div>
</div>
<p class="body" style="font-size:14px;color:var(--text-secondary);margin-top:0.75rem;">
  {1-2 句解释：在高压下你最容易被 {Inferior} 绑架，表现为 {具体行为}。下次发现就给它一个名字 —— 这是 Beebe 所说的"识别即解构"。}
</p>
```

---

## 四、玄学解释力评级 HTML 块（Chapter 2-4 末尾必备）

每个玄学章节（八字 / 紫微 / 占星）末尾必须出现以下评级块，对该维度"印证 Chapter 1 性格签名"的强度做出三档评估。

### 4.1 模板

```html
<div class="evidence-rating">
  <p class="er-title">玄学解释力评级 · {八字 / 紫微 / 占星}</p>
  <p class="er-grade {high / mid / low}">{强 / 中 / 弱} · {三个核心印证点}</p>
  <p class="er-body">
    {2-3 句说明：本维度通过 {X / Y / Z} 三个核心特征，{强 / 部分 / 微弱} 印证了 Chapter 1 已确立的性格签名。
    具体来说，{核心解释}。需要注意的是：玄学只做"印证 / 对应 / 映照"，不做"决定"，命主仍可在性格发展进程中重写默认路径。}
  </p>
</div>
```

### 4.2 三档判定标准

| 评级 | 判定标准 | 用色 |
|:---|:---|:---|
| **强**（high） | 该维度有 ≥3 个特征清晰指向同一性格签名 | `--parent`（绿） |
| **中**（mid） | 该维度有 1-2 个特征指向，其他模糊或矛盾 | `--child`（金） |
| **弱**（low） | 该维度难以印证此性格，需保留"性格 vs 玄学差异"的开放性 | `--text-tertiary`（灰） |

**铁律**：评级"弱"时，**不可强行解释**，应坦诚写出"此维度的解释力较弱，可能原因：(a) 出生时间存疑 (b) 命主仍在劣势功能整合期 (c) 玄学与性格的匹配本就不强求 100%"。

---

## 五、主导功能隐喻库（v3 关键资产）

每个主导功能配 6-8 个比喻，第一次描写主导功能时**至少使用 1-2 个**，避免反复用同一个比喻。后续章节描写性格表现时也可调用。

### Ni Hero（INTJ / INFJ）

1. 深井打水的人 —— 看一眼便知井有多深
2. 透过迷雾看见远方山形
3. 看一眼棋局就知赢家
4. 棱镜 —— 把一束光折成七色
5. 时间的接收器 —— 信号穿过你才落地
6. 缝隙里的光 —— 别人看墙，你看缝
7. 暗房里的显影液 —— 影像在你身上慢慢浮出
8. 单弦琴 —— 一根弦也能拉出整个乐章

### Ne Hero（ENTP / ENFP）

1. 风筝 —— 总在天上找下一阵风
2. 烟花 —— 一炸开就是十种颜色
3. 跳跃的火苗 —— 不在一处停留
4. 看见一棵树就想到一片森林
5. 万花筒 —— 转一下就是新世界
6. 触电 —— 灵感像电流一样找上你
7. 蒲公英 —— 一阵风带你去十个新地方
8. 拼图大师 —— 散落的碎片自动在你脑里成形

### Te Hero（ENTJ / ESTJ）

1. 建筑师 —— 把图纸变成大楼
2. 系统的指挥官 —— 让混乱听话
3. 把混沌变成清单的人
4. 砌墙工 —— 每一块砖都有它的位置
5. 算盘 —— 每一颗珠都精确归位
6. 装配线 —— 让零件按节拍前进
7. 总参谋长 —— 看着地图调动一切
8. 节拍器 —— 让所有人按你的拍子走

### Ti Hero（INTP / ISTP）

1. 精密仪器 —— 容不下半点误差
2. 拆解大师 —— 必须看到每一颗螺丝
3. 内在裁判 —— 自己先过自己这关
4. 黑箱里的光 —— 你一定要知道里面是什么
5. 公理化机器 —— 一切都从前提开始推
6. 心智迷宫 —— 越深处越享受
7. 钟表匠 —— 知道每一齿轮为什么咬合
8. 解剖刀 —— 干净、精准、不动感情

### Se Hero（ESTP / ESFP）

1. 豹 —— 当下扑上去，不犹豫
2. 即兴爵士手 —— 不读谱也能合奏
3. 当下的拥抱者 —— 此刻就是全部
4. 浪 —— 拍岸即生即灭
5. 触感的诗人 —— 用身体读世界
6. 闪电 —— 一瞬间照亮全场
7. 武术家 —— 身体先于思考反应
8. 摄影师的快门 —— 决定性瞬间不会等你

### Si Hero（ISTJ / ISFJ）

1. 档案柜 —— 每一格都收得整整齐齐
2. 老茶 —— 越久越有味道
3. 时间的守护者 —— 把昨天传给明天
4. 年轮 —— 一圈一圈记住你走过的年
5. 秤 —— 称量每一次细微的差别
6. 温柔的根 —— 别人看不见，但承托一切
7. 老厨师的手 —— 不用秤也知道几克盐
8. 家谱 —— 记得每一辈、每一桩

### Fe Hero（ENFJ / ESFJ）

1. 磁场 —— 一进屋气氛就变了
2. 调音师 —— 让每个声部和谐
3. 群体的心跳 —— 一个房间的体温计
4. 暖炉 —— 围着你就不冷
5. 桥 —— 让两岸的人能走到一起
6. 共鸣箱 —— 别人的情绪在你这里被放大
7. 牧者 —— 数清每只羊有没有掉队
8. 主持人 —— 把所有人的注意力编织成一张网

### Fi Hero（INFP / ISFP）

1. 内在的灯塔 —— 别人看不见，你自己很清楚
2. 不愿翻译的诗 —— 翻译就掉味
3. 价值的指南针 —— 偏一度都不行
4. 玉 —— 内润，不喧
5. 隐者 —— 不出门，但门里自有山河
6. 火种 —— 看似微弱，但能点燃整片森林
7. 深湖 —— 表面平静，水下另一种生态
8. 古琴 —— 弦少，音深，不是给所有人听的

---

## 六、章节结构标准（v3 八章版）

### 第 1 章 · 性格画像（35-45%）★ 主角

详见第三节模板。结构：一句话画像 → 200-400 字开篇 → 雷达图 → Beebe 环 → 八功能详解 → Grip 仪表盘 → 古典化收束。

### 第 2 章 · 八字解构 —— 性格的能量基础（15%）

**核心**：日主十干意象 + 五行权重 + 调候用神 + 神煞 → **解构 Chapter 1 已确立的性格签名**。

开篇句式：
> 你的 {性格签名简写}，在八字里被解构为这样一种能量配置——

**铁律**：
- 调候用神章节必须引《穷通宝鉴》。
- 末尾必有「玄学解释力评级 · 八字」HTML 块。
- 描写日主 → 立即对应荣格主导（如壬水 ↔ Ni 流动 / 甲木 ↔ Ne 生发）。

### 第 3 章 · 紫微对应 —— 性格的剧场舞台（15%）

**核心**：命宫主星 + 三方四正 + 四化 → **对应 Chapter 1 的性格签名在哪些"舞台"上演**。

开篇句式：
> 紫微斗数为你的性格搭了 12 个剧场，每个剧场都对应你性格的一个面向——

**铁律**：
- 末尾必有「玄学解释力评级 · 紫微」HTML 块。
- 命宫主星描写 → 立即与 Beebe 原型对位（如紫微独坐命 ↔ Hero 位的"领袖原型"）。

### 第 4 章 · 占星映照 —— 性格的宇宙节律（15%）

**核心**：太阳/月亮/上升 + 内行星 + 主要相位 → **映照 Chapter 1 性格签名的宇宙节律**。

开篇句式：
> 你出生那一刻的天空，是这样映照你的性格的——

**铁律**：
- 末尾必有「玄学解释力评级 · 占星」HTML 块。
- 太阳座 → 主导功能能量来源；月亮座 → Fi/Fe 的内在情感模式；上升 → 外显风格（人格面具）。

### 第 5 章 · 三维印证度评估（5%）

**核心**：将 Chapter 2-4 的三个评级汇总成一张总表，并给出"三维一致性 / 矛盾点 / 开放问题"。

模板：

```html
<div class="cross-grid">
  <div class="cross-cell">
    <p class="cross-label">八字</p>
    <p class="cross-data">强 · 印证</p>
    <p class="cross-gloss">{核心三特征}</p>
  </div>
  <div class="cross-cell">
    <p class="cross-label">紫微</p>
    <p class="cross-data">中 · 部分对应</p>
    <p class="cross-gloss">{核心两特征}</p>
  </div>
  <div class="cross-cell">
    <p class="cross-label">占星</p>
    <p class="cross-data">强 · 映照</p>
    <p class="cross-gloss">{核心三特征}</p>
  </div>
</div>
```

末尾古典化收束："三维印证 · 性格已立"或"三维背离 · 性格独行"等四字定调。

### 第 6 章 · 双轨时间线（5%）

**核心**：性格发展轨道（Jung 个体化 35-45 岁劣势功能整合期）+ 玄学时机轨道（八字大运 / 紫微大限 / 占星行运）。

**v3 关键**：双轨并置，**性格轨在上，玄学轨在下**，让读者一眼看出"哪些时点是性格成熟的天然窗口，玄学只是给这些窗口加了应期标注"。

### 第 7 章 · 感情专题（必有）

**核心**：荣格 Fi/Fe 骨架 + 玄学应期。

结构：
1. **性格底色**：你的爱与被爱的方式由 Fi/Fe + Si/Se 决定（占 50%）
2. **玄学应期**：八字配偶星 + 紫微夫妻宫 + 占星金星 7 宫，**仅作为"时机标注"**（占 50%）
3. **可塑路径**：如何让性格在合适的时机里展开

引用 `references/jung-relationship-dynamics.md` 与 `references/relationship-analysis.md`。

### 第 8 章 · 终极课题（5%）

**核心**：荣格个体化任务（劣势功能整合 / 阴影面对 / Self 显现）+ 玄学应期窗口。

铁律：
- 终极课题**必出自荣格劣势功能 / 阴影整合**，不是出自玄学
- 玄学只用来标注"什么时段最适合做这件事"
- 5 条具体可塑路径建议，每条遵循"判断—解释—行动暗示"三段式

---

## 七、术语词典（v2 沿用 + v3 荣格段补充）

每个术语包含三件事：**所属体系 · "带电出场"模板 · 可用比喻**。

### 性格域（v3 扩展荣格）

| 术语 | 体系 | 带电出场模板 | 比喻 |
|:---|:---|:---|:---|
| 日主 | 八字 | "你的日干 X——你性格签名在能量层的本命之气" | 性格的"主角能量" |
| 比劫 | 八字 | "比肩劫财——和你日主同类的能量" | 同行者 |
| 印星 | 八字 | "印星——生养你日主的能量，主学识与庇护" | 母性能量 |
| 命宫主星 | 紫微 | "你命宫坐着 X——紫微为你性格搭的核心舞台" | 你的性格主调 |
| 太阳星座 | 占星 | "你的太阳在 X 座——映照你核心生命力方向" | 内在驱动力 |
| 上升星座 | 占星 | "你的上升在 X 座——你给世界的第一印象（人格面具）" | 你穿的"外衣" |
| 月亮星座 | 占星 | "你的月亮在 X 座——映照你内在的情感模式" | 你的"内心地形" |
| 主导功能 | 荣格 | "你的主导功能是 X——你思考和感受的根本路径" | 你大脑的"操作系统" |
| 辅助功能 | 荣格 | "辅助功能是 X——主导的左右手，让你的能力对外可用" | 主帆的副舵 |
| 第三功能 | 荣格 | "第三功能是 X——少年期的玩耍能量，35 岁后逐渐成熟" | 永恒少年原型 |
| 劣势功能 | 荣格 | "劣势功能是 X——你最不熟练的那一面，是你后半生的功课" | 阴影里的火 |
| Beebe 原型 | 荣格 | "{某功能} 在你身上是英雄/父母/孩子/劣势位" | 内心人格剧场 |
| Hero 位 | 荣格 | "Hero 位 —— 你最自豪、最自动化的功能" | 主角光环 |
| Parent 位 | 荣格 | "Parent 位 —— 你照顾别人的功能" | 慈母慈父 |
| Child 位 | 荣格 | "Child / Eternal Youth —— 你玩耍与重启的功能" | 永恒少年 |
| Inferior 位 | 荣格 | "Inferior 位 —— 你的盲点，也是后半生整合的入口" | 阿基里斯之踵 |
| Grip Experience | 荣格 | "Grip —— 高压下被劣势功能绑架的状态" | 阴影抓人 |
| 个体化进程 | 荣格 | "个体化 —— Jung 称之为后半生最重要的功课" | 内在金花的开放 |
| 阳刃 | 八字 | "命带阳刃——日主气过旺时的极端表现" | 内在的"刚锋" |
| 性格签名 | v3 通用 | "你的性格签名 = {INTJ · Ni-Te-Fi-Se}" | 命书的"主标题" |

### 感情域（v2 沿用）

| 术语 | 体系 | 带电出场模板 | 比喻 |
|:---|:---|:---|:---|
| 夫妻宫 | 紫微 | "你的夫妻宫——紫微对应婚恋模式的舞台" | 感情的剧场 |
| 正官 | 八字 | "正官——女命论丈夫的星 / 男命论责任与规矩" | 正缘对象 |
| 七杀 | 八字 | "七杀——女命非正式感情对象，男命论压力与儿子" | 锋芒型对象 |
| 正财 | 八字 | "正财——男命论妻子的星 / 女命论务实收入" | 安定的伴侣 |
| 偏财 | 八字 | "偏财——主父亲、情人、偏门收入" | 流动的财与情 |
| 配偶星被合 | 八字 | "你的配偶星被 X 合住" | 配偶被外力牵走 |
| 化忌入夫妻宫 | 紫微 | "化忌——一种"执着"能量落进你的夫妻宫" | 感情上的"放不下" |
| 武曲化权 | 紫微 | "武曲化权落配偶位——你想要"被你撑得住的人"" | 主导型择偶 |
| 金星 | 占星 | "你的金星在 X 座——映照你爱与被爱的方式" | 爱的语法 |
| 7 宫 | 占星 | "你的 7 宫——婚姻与一对一关系" | 关系镜子 |
| 月亮受克 | 占星 | "你的月亮被 X 行星克制" | 情绪的暗流 |
| Fi 主导 | 荣格 | "你的 Fi 高——内在价值判断很强" | 内在的"价值秤" |
| Fe 主导 | 荣格 | "你的 Fe 高——对他人情绪极敏感" | 情绪的"接收器" |
| 官杀混杂 | 八字 | "你的命局正官与七杀同时出现" | 感情中"正与偏并存" |

### 事业财运域（v2 沿用）

| 术语 | 体系 | 带电出场模板 | 比喻 |
|:---|:---|:---|:---|
| 食伤 | 八字 | "食神伤官——日主表达和才华的能量" | 你的"输出端口" |
| 食神 | 八字 | "食神——温和的才华表达" | 慢炖的火 |
| 伤官 | 八字 | "伤官——锋芒型才华，叛逆克官" | 锐利的火 |
| 财星 | 八字 | "正财偏财——日主"克"的能量" | 你能驾驭的资源 |
| 官禄宫 | 紫微 | "你的官禄宫——紫微对应事业方向的舞台" | 事业舞台 |
| 财帛宫 | 紫微 | "你的财帛宫——主你的赚钱模式" | 财的活水来源 |
| 田宅宫 | 紫微 | "你的田宅宫——主家产、不动产、长期积累" | 财的库 |
| MC | 占星 | "你的天顶 MC 在 X——映照你公开形象与事业方向" | 你的"公开面" |
| 10 宫 | 占星 | "你的 10 宫——事业、社会身份" | 你的"职位" |
| 2 宫 | 占星 | "你的 2 宫——金钱与价值观" | 你的财库 |
| 杀破狼 | 紫微 | "你的命局会杀破狼——三方四正会齐七杀破军贪狼" | 创业基因 |
| Te | 荣格 | "Te 高——逻辑组织与外在系统化能力" | 大脑的"工程师" |

### 健康域（v2 沿用）

| 术语 | 体系 | 带电出场模板 | 比喻 |
|:---|:---|:---|:---|
| 五行偏枯 | 八字 | "你命局某一行 {极弱/极旺}" | 能量分布不均 |
| 疾厄宫 | 紫微 | "你的疾厄宫——紫微对应健康倾向的位置" | 身体的弱点图 |
| 6 宫 | 占星 | "你的 6 宫——健康、日常工作、身体习惯" | 身体的日常 |
| 火星 | 占星 | "你的火星在 X 座——映照你的能量爆发与防御方式" | 内在的"刚劲" |
| Si 低位 | 荣格 | "Si 是你的劣势功能——身体感受是你的盲区" | 身体的"低带宽" |

### 时机域（v3 改写："流年" → "应期窗口"）

| 术语 | 体系 | 带电出场模板 | 比喻 |
|:---|:---|:---|:---|
| 大运 | 八字 | "{X 干 X 支} 大运——这十年的能量场" | 十年的"大气候" |
| 大限 | 紫微 | "第 X 大限走入你的 {某宫}——这个剧场激活十年" | 十年的剧场幕 |
| 流年（应期） | 通用 | "{某年} 是你的 {年柱干支} 流年应期" | 一年的剧情 |
| 行运 | 占星 | "土星/冥王/木星行运到你 {本命某点}" | 当下的星空压力 |
| 三方四正 | 紫微 | "你的命宫三方四正——命宫加左右两方加对宫" | 你"看见"的范围 |
| 四化 | 紫微 | "{某星}化{禄权科忌}——星的四种状态" | 星的"情绪标签" |

### 占星专用域（v2 沿用）

| 术语 | 体系 | 带电出场模板 | 比喻 |
|:---|:---|:---|:---|
| 合相 | 占星 | "X 与 Y 合相——同度同方向，能量叠加" | 两股力合一 |
| 对冲 | 占星 | "X 与 Y 对冲（180°）——彼此对立拉扯" | 内在的两难 |
| 三合 | 占星 | "X 与 Y 三合（120°）——同一元素的协调" | 顺流的力 |
| 四分 | 占星 | "X 与 Y 四分（90°）——紧张的张力，催生行动" | 必须解决的考题 |
| 六合 | 占星 | "X 与 Y 六合（60°）——温和的合作流" | 助力的小风 |
| 世代行星 | 占星 | "天王/海王/冥王——同代人共有的集体能量" | 时代背景音 |

---

## 八、措辞柔化对照表（v2 沿用 + v3 增量五条）

**仅在主文 L1 适用**。技术性数据（紫微星盘表、四柱表）保留原始术语。柔化的核心：**不弱化判断，重写视角**。

### v3 增量（措辞统一表 · 必须严格执行）

| 旧（v2 / 传统命理） | 新（v3 性格本位） |
|:---|:---|
| "命里决定" / "决定" | "印证 / 映照 / 解释" |
| "命中注定" | "天然倾向 / 默认路径" |
| "命运" | "性格在时机中的展开" |
| "改命" | "可塑路径 / 个体化进程" |
| "克应" / "应验" | "应期窗口" |

**禁用清单**（出现即重写）：
- "你命里就是要 X"
- "命中注定 Y"
- "改不了的命"
- "克应在 Z 年"
- "八字决定你"

**替换示例**：
- ❌ "你命中注定要晚婚" → ✅ "你的性格签名让你倾向晚一些走入稳定关系——这是默认路径，不是判决"
- ❌ "大运克应感情破裂" → ✅ "这十年是你 Fi 整合的应期窗口，性格变化会重塑你对关系的定义"

### 八字类（v2 沿用）

| 命理判断（原话） | 命书表达（柔化） |
|:---|:---|
| 七杀重克身 | 早年承受过的压力，让你早早学会独立 |
| 伤官见官 | 你身上有一种"挑战权威"的本能，体制内会感觉憋闷，但在创造性工作里会发光 |
| 阳刃驾杀 | 你内在有一股"硬"，关键时刻能爆发出超出常人的力量 |
| 命局偏枯需调候 | 你的能量分布不均匀，这正是你独特天赋的来源 |
| 大运逆行 | 你的人生节奏是反着来的——别人冲刺时你沉淀，别人停下时你突进 |
| 食神制杀 | 你能用才华与温度化解压力——这是性格写好的"软武器" |
| 印星过重 | 你比常人需要更多的"被肯定"——这不是依赖，是你的能量补给方式 |
| 财多身弱 | 你周围有很多机会与资源，但需要先把"自己"练扎实，才扛得住 |
| 比劫夺财 | 你身边有强力的同辈竞争者——这不是消耗，是逼你跑得更快的同行人 |
| 官杀混杂 | 你的感情世界里"正与偏"会交织出现——这是性格底色，不是错误 |
| 伤官配印 | 你天生有"才华+智慧"的双轨——但需要把它们调和好，才不会左手打右手 |
| 子午冲 | 你内在有两股力量在拉扯——一旦你认清它们，反而成为你的双引擎 |
| 卯酉冲 | 你的人生里有"出走与回归"的交替主题——每一次离开都是为了更深的回来 |

### 紫微类（v2 沿用）

| 命理判断（原话） | 命书表达（柔化） |
|:---|:---|
| 化忌入命宫 | 你天生比常人更敏感——这种敏感是你最大的天赋，也是最难的功课 |
| 化忌入夫妻宫 | 你天生对感情比常人敏感得多，常把对方的不安当成自己的功课 |
| 化忌入福德宫 | 你的精神世界里有一种"放不下"——它让你深刻，也让你累 |
| 杀破狼坐命 | 你天生不适合一成不变的人生——动荡是你的能量来源 |
| 命宫见空劫 | 你比常人更容易"清空再来"——这是性格给你的反复重启权 |
| 火铃夹命 | 你早年承受过急速的环境变化——这让你比同龄人更"快" |
| 羊陀夹忌 | 你走过一段被"两面夹击"的时期——它磨出了你现在的韧性 |
| 命无正曜 | 你的人生路径不在常规轨道上——你是要自己定义自己的人 |
| 福德宫煞星多 | 你内心比表面看起来更操劳——你需要主动给自己"留白时间" |

### 占星类（v2 沿用）

| 命理判断（原话） | 命书表达（柔化） |
|:---|:---|
| 月亮受克 | 你的情绪比常人更深——这种深度是你成为好倾听者的根基 |
| 太阳合冥王 | 你身上有一种"重生"的力量——人生会有几次彻底的自我重塑 |
| 火星与土星四分 | 你的行动力会被"应不应该"反复审查——这让你慢，但走得更稳 |
| 海王在 12 宫 | 你比常人更容易感知到"未说出口的东西" |
| 凯龙在 X 宫 | 你在 {该宫领域} 有一道"古老的伤口"——它也正是你能治愈别人的地方 |
| 北交在 X 宫 | 这一生你被引导走向 {该宫领域}——哪怕一开始不舒服 |

### 荣格类（v3 扩展）

| 命理判断（原话） | 命书表达（柔化） |
|:---|:---|
| Fi 极低 | 你不太擅长说"我喜欢"——但你比谁都清楚什么是"应该" |
| Fe 极高 | 你能感受到对方没说出口的情绪——这是天赋，也容易让你过载 |
| Si 劣势 | 你不太关注身体细节——这十年要学会和"身体"重新交朋友 |
| Ne 主导，Si 劣势 | 你的注意力像探照灯，扫得远但容易忽略眼前 |
| 主导与劣势差距大 | 你的认知地图有"高峰"也有"深谷"——发展劣势是后半生的功课 |
| Grip Experience | 高压时你会被劣势功能"绑架"——下次发现就给它一个名字 |
| 主导 Ni + 劣势 Se | 你看得远，但容易踩空——身体感是你的修行 |
| 主导 Te + 劣势 Fi | 你能搞定一切系统，但在"我真正想要什么"前会卡住——这是后半生的入口 |
| 个体化进程未启 | 你前半生靠主导吃饭，后半生靠劣势翻身——这是 Jung 说的"中年危机正解" |

### 综合类（v2 沿用）

| 命理判断（原话） | 命书表达（柔化） |
|:---|:---|
| 大运不利 | 这十年是你的"沉淀期"——不是你不够努力，是性格在蓄力 |
| 流年不顺 | 这一年是你的"翻土年"——表面看是阻碍，实际是给来年松地 |
| 命格清苦 | 你的人生不靠"运气"，靠"心力" |

---

## 九、典籍引用密度规则（v2 沿用）

一份完整命书中，**主体引文（serif blockquote）3-5 处** 为佳。v3 分配建议：

| 位置 | 引文 | 出处 |
|:---|:---|:---|
| Chapter 1 · 性格画像 | 1 处 | 《荣格全集》第 6 卷"心理类型"或《滴天髓》十干体象（取一者对应主导功能） |
| Chapter 2 · 八字解构 | 1 处 | 《穷通宝鉴》对应日主月份的调候原则 |
| Chapter 3 · 紫微对应 | 0-1 处 | 《紫微斗数全书》主星论 |
| Chapter 4 · 占星映照 | 0-1 处 | 《果老星宗》"星命合参"传统 |
| Chapter 7 · 感情专题 | 1 处 | 《渊海子平》六亲论 / 《滴天髓》论日支 |
| Chapter 8 · 终极课题 | 1 处 | 《荣格自传》"个体化"段落 / 《神峰通考》"病药" |

**inline 简注**（斜体小字括注）可多用，每章 1-3 处。

---

## 十、定调收束模板（v2 沿用 + v3 性格本位示例）

| 章节 | 四字短语示例 | 注解结构 |
|:---|:---|:---|
| 性格画像 | "深井之水" / "棱镜成光" / "棋外观棋" | {主导 + 辅助 + Beebe 关键原型} — 你的性格签名 |
| 八字解构 | "壬水通天" / "甲木参天" | {五行+调候} — 你的能量底色解构了你的性格签名 |
| 紫微对应 | "紫微独坐" / "杀破狼会" | {主星+三方四正} — 紫微为你性格搭好了 12 个剧场 |
| 占星映照 | "日月同辉" / "土冥相位" | {核心相位} — 星空映照你性格的宇宙节律 |
| 三维印证 | "三维同声" / "二维印证" | {三个评级汇总} — 性格签名得到 X 维印证 |
| 感情专题 | "守而后破" / "迟来的真" | {Fi/Fe + 玄学应期} — 性格在时机中展开为爱 |
| 终极课题 | "归零再来" / "整合阴影" | {劣势功能整合 + 应期窗口} — 这是个体化的入口 |

---

## 十一、输出前自检 7 问（v3 扩展）

提交前，逐条检查：

1. ☐ Chapter 1 性格画像是否占 35-45% 篇幅，且作为命书"主角"出场？
2. ☐ Chapter 1 是否包含：一句话画像 + 雷达图 + Beebe 环 + 八功能详解 + Grip 仪表盘？
3. ☐ 每个专业术语第一次出现时是否"带电出场"（同句解释）？
4. ☐ Chapter 2-4 末尾是否都有「玄学解释力评级」HTML 块（强 / 中 / 弱）？
5. ☐ 主导功能描写是否使用了"主导功能隐喻库"中的 1-2 个比喻？
6. ☐ 是否完全避免了 v3 禁用句式（命中注定 / 决定 / 改命 / 克应 / 八字决定你）？
7. ☐ 每章末尾是否有"四字短语 + 一句话"的古典化收束？且收束句强调"性格本位"？

七条全过，方可输出。

---

## 十二、v3 哲学骨架在模板中的落地确认

本模板之所以重写，是因为 v2 把玄学放在主语位，v3 必须把性格放在主语位。具体落地表现：

1. **结构层**：Chapter 1 性格画像从原"第一章·性格底色"（约 12% 篇幅）扩张为命书主角（35-45%），并新增三大可视化资产
2. **修辞层**：所有玄学章节开篇必须先回扣 Chapter 1 性格签名，禁用"决定 / 命中注定 / 克应"
3. **评级层**：Chapter 2-4 末尾强制评级"玄学解释力"（强 / 中 / 弱），允许坦诚承认"弱"
4. **课题层**：Chapter 8 终极课题必出自荣格劣势功能 / 阴影整合，玄学只标注"应期窗口"
5. **可塑层**：所有"宿命"叙述都被改写为"默认路径 + 可塑路径"——性格可发展（个体化），因此命运可塑

> **本模板定调**：性格是恒量，玄学是注解，命运是性格在时机中的展开。
> 主语 · 谓语 · 状语 · 时机 — 四者各归其位，命书方为命书。
