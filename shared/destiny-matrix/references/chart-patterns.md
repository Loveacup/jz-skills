# 图表模式库 · chart-patterns（v4 新建 · 2026-07-15）

> **本文件是什么**：destiny-matrix v4 的 16 种图表模式库（P01–P16）。每种模式含四要素：① SVG/HTML 骨架模板（数据处用 `{占位符}`）② 坐标计算公式 ③ 从 2026-07-15 案例A命书（27 图已验证渲染版）原文抠出的完整已验证实例 ④ 适用场景与变体建议。
> **数据源**：`案例A_命书.html`（8 章 27 图，浏览器实测渲染通过）+ `references/output-template.md` 第 3 节既有 SVG 模板。P16 双轮对照无现成实例，仅给骨架与公式（已标注）。
> **权威关系**：本文件与 V4_PLAN §3.1/§3.2 对齐；配额、锚点六图、命名规范同时写入 SKILL.md 与 `locked-checklist.md`（C 组），冲突时以 locked-checklist 为准。

---

## 〇、使用说明（chart-director 与 book-writer 如何选用/组合）

### chart-director（S7 图表规划）工作流

1. 通读 S3–S6 全部素材，先把**锚点六图**（见第五节）直接登记进图表规划表——这六张任何命书必有，不需要理由。
2. 逐章扫描素材中的**可视化事实**（数值序列、结构关系、时间序列、流向、对照），为每个事实从 P01–P16 中选模式；同一事实可组合模式（如 P11+P12 时间轴叠曲线）。
3. 对照第四节**配额下限表**补齐缺口；配额之上按命主特异点**加码**（特殊格局、交界上升、从格、异常 Grip、空宫借星等各值一张专图），加码行必须写理由。
4. 产出图表规划表（schema 见第三节），经 task I/O 交给 book-writer；表中每行的「模式」列必须引用本库的模式 ID（或 ID 组合、或「新变体：说明」）。

### book-writer（S8 成文）工作流

1. 按图表规划表逐行落图：复制对应模式的**骨架模板**，用坐标公式算出数值，替换全部 `{占位符}`；不确定视觉细节时，对照该模式的**已验证实例**（它们全部在真实浏览器里渲染通过，是安全基线）。
2. 每张图的外层容器必须是 `<div class="chart-container" data-chart-id="{规划表中的图表 ID}">`，内部第一个元素是 `chart-title`；图下建议配一行 `chart-data` 图注（实例中的图注写法可直接仿写）。
3. 坐标一律**算好再写死**进 SVG（本体系无 JS，SVG 是静态的）；可调用 `scripts/chart_data.py` 算雷达顶点、宫位布局、行星角度、时间轴刻度。
4. 视觉呈现（配色、标注密度、比喻性元素、图注措辞）由 book-writer 自主拿捏，但要过 locked-checklist C4 渲染健康检查（SVG 语法合法 / viewBox 存在 / path·polygon 非空非退化）。
5. 允许叠加与发明新变体，条件见文末「组合与发明授权条款」。

### 通用容器规范

```html
<div class="chart-container" data-chart-id="chart-{章号}-{序号}">
  <p class="chart-title">{图号} · {标题}（{括注：单位/图例说明}）</p>
  {SVG 或 table.chart-data 或 .ziwei-board}
  <p class="chart-data" style="font-size:12.5px;color:var(--text-secondary);text-align:center;margin-top:0.5rem;">
    {一句图注：把图里最重要的一个视觉事实翻译成人话，并回扣性格签名}
  </p>
</div>
```

- `data-chart-id` 命名规范：`chart-{章号}-{序号}`，章号 1–8，序号从 1 起（如 `chart-2-3`）。合盘场景章号后可加后缀（如 `chart-7-2b`）。validate_book.py 按此属性核销。
- 配色使用模板 CSS 变量族：主红 `#8a1a1a`（--inferior/accent）、软红 `#b85c5c`、蓝 `#2c5f7c`（--hero）、绿 `#4a8b5c`（--parent）、金 `#d4a574`/`#c8963c`（--child）、灰阶 `#5a5a5a/#8a8a8a/#a8a59a`、辅助线 `#d5d2c8/#e2e0d8`。占星章允许独立暖金紫色系（`#b08d57/#7a5c9e`，见 P07 实例）。
- SVG 必须带 `viewBox` 且宽度自适应（`width="100%"` 或 `style="max-width:…;width:100%"`）；建议带 `role="img" aria-label="…"`。
- 字体只用系统栈（`STSong, Songti SC, serif` / `sans-serif`），禁外链字体（PDF 导出与 CSP 都过不了）。
- 同一 SVG 内 `<marker>`/渐变的 `id` 必须全书唯一（实例中 `id="ah"`、`id="ar"` 若一书多用会互相覆盖——落图时改为 `id="{chart-id}-ah"`）。

---

## 一、强度类

### P01 · 八轴雷达（认知功能强度）

**适用场景**：荣格八功能强度总览（Ch1 锚点图）；亦可用于任何「8 维度 0–max 强度」数据（如八宫强度）。

**坐标计算公式**：

- 中心 `(cx, cy) = (200, 200)`，最大半径 `R = 150`（即 viewBox 400×400）。
- 八轴顺序固定 Ni-Ne-Si-Se-Ti-Te-Fi-Fe，从正上方起顺时针，第 i 轴（i=0..7）角 `θ = i × 45°`。
- 数据点：`x = cx + r·sin(θ)`，`y = cy − r·cos(θ)`，`r = 强度 / 强度满分 × R`。
  - 0–100 制：`r = 强度 × 1.5`（v3 模板）；0–25 制（16 分聚合均值）：`r = 强度 × 6`（案例A版）。
- 背景同心八边形取 r = 37.5 / 75 / 112.5 / 150（即 25%/50%/75%/100% 圈），顶点同公式。
- 轴端标签放 r ≈ 160–170 处（实例中手工微调避让）。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:340px;width:100%;">
  <!-- 背景同心八边形（25/50/75/100 四圈，顶点按公式预算好，可直接沿用实例数值） -->
  <g fill="none" stroke="#d5d2c8" stroke-width="0.5">
    <polygon points="200,125 253,147 275,200 253,253 200,275 147,253 125,200 147,147" />
    <polygon points="200,50 275,95 320,200 275,305 200,350 125,305 80,200 125,95" stroke="#a8a59a" />
    <polygon points="200,87 264,121 297,200 264,279 200,312 136,279 103,200 136,121" />
    <polygon points="200,162 241,174 252,200 241,226 200,238 159,226 148,200 159,174" />
  </g>
  <!-- 八条轴线（固定） -->
  <g stroke="#d5d2c8" stroke-width="0.5">
    <line x1="200" y1="200" x2="200" y2="50" /><line x1="200" y1="200" x2="306" y2="94" />
    <line x1="200" y1="200" x2="350" y2="200" /><line x1="200" y1="200" x2="306" y2="306" />
    <line x1="200" y1="200" x2="200" y2="350" /><line x1="200" y1="200" x2="94" y2="306" />
    <line x1="200" y1="200" x2="50" y2="200" /><line x1="200" y1="200" x2="94" y2="94" />
  </g>
  <!-- 数据多边形：8 顶点按公式计算 -->
  <polygon points="{NiX},{NiY} {NeX},{NeY} {SiX},{SiY} {SeX},{SeY} {TiX},{TiY} {TeX},{TeY} {FiX},{FiY} {FeX},{FeY}"
           fill="rgba(184,92,92,0.16)" stroke="#b85c5c" stroke-width="1.5" />
  <!-- 关键节点：Hero 实心大点、Parent 实心中点、特异功能（如明亮阴影双峰）空心圈 -->
  <circle cx="{HeroX}" cy="{HeroY}" r="5.5" fill="#8a1a1a" />
  <circle cx="{ParentX}" cy="{ParentY}" r="4.5" fill="#4a8b5c" />
  <circle cx="{特异X}" cy="{特异Y}" r="6" fill="none" stroke="#2c5f7c" stroke-width="2" />
  <!-- 八轴标签 + 数值（tspan 缀小号数值，重点轴换色） -->
  <g font-family="STSong, Songti SC, serif" font-size="13" fill="#1a1a1a" text-anchor="middle">
    <text x="200" y="38">Ni <tspan font-size="10" fill="#5a5a5a">{Ni值}</tspan></text>
    <text x="322" y="92">Ne <tspan font-size="10" fill="#5a5a5a">{Ne值}</tspan></text>
    <text x="368" y="205">Si <tspan font-size="10" fill="#5a5a5a">{Si值}</tspan></text>
    <text x="322" y="322">Se <tspan font-size="10" fill="#5a5a5a">{Se值}</tspan></text>
    <text x="200" y="372">Ti <tspan font-size="10" fill="#5a5a5a">{Ti值}</tspan></text>
    <text x="78" y="322">Te <tspan font-size="10" fill="#5a5a5a">{Te值}</tspan></text>
    <text x="32" y="205">Fi <tspan font-size="10" fill="#5a5a5a">{Fi值}</tspan></text>
    <text x="78" y="92">Fe <tspan font-size="10" fill="#5a5a5a">{Fe值}</tspan></text>
  </g>
</svg>
```

**已验证实例**（案例A · Ch1「认知功能强度 · 八轴雷达」，注意其对「明亮阴影双峰」的空心圈标记手法）：

```html
<div class="chart-container">
  <p class="chart-title">认知功能强度 · 八轴雷达（16 分聚合均值）</p>
  <svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:340px;width:100%;">
    <!-- 背景同心八边形 -->
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
    <!-- 数据多边形：Ni19.75 Ne17.35 Si14.8 Se13.0 Ti11.95 Te11.8 Fi19.55 Fe17.5（r=score×6） -->
    <polygon points="200,81.5 273.6,126.4 288.8,200 255.2,255.2 200,271.7 149.9,250.1 82.7,200 125.8,125.8"
             fill="rgba(184,92,92,0.16)" stroke="#b85c5c" stroke-width="1.5" />
    <!-- Hero 节点 Fi -->
    <circle cx="82.7" cy="200" r="5.5" fill="#8a1a1a" />
    <!-- Parent 节点 Ne -->
    <circle cx="273.6" cy="126.4" r="4.5" fill="#4a8b5c" />
    <!-- 阴影双峰标记：Ni（明亮阴影） -->
    <circle cx="200" cy="81.5" r="6" fill="none" stroke="#2c5f7c" stroke-width="2" />
    <!-- Fe（明亮对立） -->
    <circle cx="125.8" cy="125.8" r="4.5" fill="none" stroke="#2c5f7c" stroke-width="1.5" />
    <!-- 八轴标签 + 数值 -->
    <g font-family="STSong, Songti SC, serif" font-size="13" fill="#1a1a1a" text-anchor="middle">
      <text x="200" y="38">Ni <tspan font-size="10" fill="#2c5f7c">19.8</tspan></text>
      <text x="322" y="92">Ne <tspan font-size="10" fill="#5a5a5a">17.4</tspan></text>
      <text x="368" y="205">Si <tspan font-size="10" fill="#5a5a5a">14.8</tspan></text>
      <text x="322" y="322">Se <tspan font-size="10" fill="#5a5a5a">13.0</tspan></text>
      <text x="200" y="372">Ti <tspan font-size="10" fill="#5a5a5a">12.0</tspan></text>
      <text x="78" y="322">Te <tspan font-size="10" fill="#5a5a5a">11.8</tspan></text>
      <text x="32" y="205">Fi <tspan font-size="10" fill="#8a1a1a">19.6</tspan></text>
      <text x="78" y="92">Fe <tspan font-size="10" fill="#2c5f7c">17.5</tspan></text>
    </g>
  </svg>
  <p class="chart-data" style="font-size:12.5px;color:var(--text-secondary);text-align:center;margin-top:0.5rem;">
    <span style="color:#8a1a1a;">●</span> Hero·Fi 19.6
    <span style="color:#4a8b5c;">●</span> Parent·Ne 17.4
    <span style="color:#2c5f7c;">○</span> 明亮阴影 Ni 19.8 / Fe 17.5
  </p>
</div>
```

**变体建议**：双人雷达（两个半透明多边形叠加，合盘用）；4 轴/6 轴变体（θ 步长改 90°/60°）；把 Hero→Inferior 栈序 4 点连成第二条细虚线多边形以对照「理论栈 vs 实测强度」。

---

### P02 · 分组条形（横向条形排行）

**适用场景**：16 功能亚型分数（Ch1）、五行能量权重（Ch2 锚点图）、十神力量分布（Ch2）、任何「类目 × 单数值」排行。

**坐标计算公式**：

- 横向条：`width = 数值 / 刻度满分 × 可用宽度`。
  - 五行权重版：基线 `x=34`，`width = 百分比 × 13`（26.2% → 340px，满格 ≈ 35%）。
  - 16 亚型版：基线 `x=105`，`width = 分数 × 13`（每 5 分 65px，纵刻度线在 170/235/300/365/430）。
- 行距：条高 16–18px，同组内行距 20px，组间距 26px；第 k 行 `y = y0 + k × 行距`。
- 标签：类目名放条左（`text-anchor="end"`, x = 基线−5）或最左侧；数值标签放条右端外 8px。
- 分组语义：同组两条用同色，「深色 = 较高亚型，浅色 = opacity 0.45–0.55」。

**SVG 骨架模板**（单层条形，五行权重版）：

```html
<svg viewBox="0 0 460 220" width="100%" role="img" aria-label="{图表说明}">
  <!-- 每行：类目名 + 条 + 数值注（按数值降序排列） -->
  <text x="8" y="{y+10}" font-size="13" fill="currentColor">{类目1}</text>
  <rect x="34" y="{y}" width="{数值×13}" height="18" rx="3" fill="{类目色}"/>
  <text x="{34+数值×13+8}" y="{y+14}" font-size="12" fill="currentColor">{数值}% ({权重}) {← 特殊标注}</text>
  <!-- …… 重复 N 行，行距 36 …… -->
  <line x1="34" y1="{底部y}" x2="374" y2="{底部y}" stroke="currentColor" stroke-opacity="0.3"/>
  <text x="34" y="{底部y+16}" font-size="10" fill="currentColor" opacity="0.7">数据源:{cast_chart 输出字段}</text>
</svg>
```

**已验证实例 A**（案例A · 图 2-2 五行能量权重——锚点六图之一；注意「← 日主」「← 最枯」的行内标注手法与数据源脚注）：

```html
<div class="chart-container">
    <div class="chart-title">图 2-2 · 五行能量权重（横轴为占比 %）</div>
    <svg viewBox="0 0 460 220" width="100%" role="img" aria-label="五行能量条形图">
      <!-- 水 26.2 -->
      <text x="8" y="30" font-size="13" fill="currentColor">水</text>
      <rect x="34" y="20" width="340" height="18" rx="3" fill="#2b6cb0"/>
      <text x="382" y="34" font-size="12" fill="currentColor">26.2% (2.1)</text>
      <!-- 金 23.8 -->
      <text x="8" y="66" font-size="13" fill="currentColor">金</text>
      <rect x="34" y="56" width="309" height="18" rx="3" fill="#a0aec0"/>
      <text x="351" y="70" font-size="12" fill="currentColor">23.8% (1.9)</text>
      <!-- 土 22.5 -->
      <text x="8" y="102" font-size="13" fill="currentColor">土</text>
      <rect x="34" y="92" width="292" height="18" rx="3" fill="#b7791f"/>
      <text x="334" y="106" font-size="12" fill="currentColor">22.5% (1.8)</text>
      <!-- 火 20.0 日主 -->
      <text x="8" y="138" font-size="13" fill="currentColor">火</text>
      <rect x="34" y="128" width="260" height="18" rx="3" fill="#c53030"/>
      <text x="302" y="142" font-size="12" fill="currentColor">20.0% (1.6) ← 日主</text>
      <!-- 木 7.5 -->
      <text x="8" y="174" font-size="13" fill="currentColor">木</text>
      <rect x="34" y="164" width="97" height="18" rx="3" fill="#2f855a"/>
      <text x="139" y="178" font-size="12" fill="currentColor">7.5% (0.6) ← 最枯</text>
      <line x1="34" y1="196" x2="374" y2="196" stroke="currentColor" stroke-opacity="0.3"/>
      <text x="34" y="212" font-size="10" fill="currentColor" opacity="0.7">数据源:case-a_chart.json 五行权重/比例</text>
    </svg>
  </div>
```

**已验证实例 B**（案例A · Ch1 16 功能亚型分组条形——A/H·O/B 成对分组、深浅区分高低亚型、纵刻度线）：

```html
<div class="chart-container">
  <p class="chart-title">16 功能亚型分数 · A/H · O/B 分组条形（按 INFP 栈序）</p>
  <svg viewBox="0 0 470 420" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
    <!-- 纵向刻度线 5/10/15/20/25 -->
    <g stroke="#e2e0d8" stroke-width="0.5">
      <line x1="170" y1="28" x2="170" y2="400" /><line x1="235" y1="28" x2="235" y2="400" />
      <line x1="300" y1="28" x2="300" y2="400" /><line x1="365" y1="28" x2="365" y2="400" />
      <line x1="430" y1="28" x2="430" y2="400" />
    </g>
    <g font-family="sans-serif" font-size="9" fill="#8a8a8a" text-anchor="middle">
      <text x="170" y="20">5</text><text x="235" y="20">10</text><text x="300" y="20">15</text>
      <text x="365" y="20">20</text><text x="430" y="20">25</text>
    </g>
    <!-- 基线 x=105 -->
    <line x1="105" y1="28" x2="105" y2="400" stroke="#a8a59a" stroke-width="0.8" />
    <!-- 每对：solid=较高亚型/主色，lighter=较低亚型 -->
    <g font-family="sans-serif" font-size="10" fill="#1a1a1a">
      <!-- Fi -->
      <rect x="105" y="40" width="322.4" height="16" fill="#b85c5c"/><text x="100" y="52" text-anchor="end">FiA 24.8</text>
      <rect x="105" y="60" width="185.9" height="16" fill="#b85c5c" opacity="0.45"/><text x="100" y="72" text-anchor="end">FiH 14.3</text>
      <!-- Ne -->
      <rect x="105" y="86" width="235.3" height="16" fill="#2c5f7c"/><text x="100" y="98" text-anchor="end">NeO 18.1</text>
      <rect x="105" y="106" width="215.8" height="16" fill="#2c5f7c" opacity="0.55"/><text x="100" y="118" text-anchor="end">NeB 16.6</text>
      <!-- Si -->
      <rect x="105" y="132" width="128.7" height="16" fill="#4a8b5c" opacity="0.5"/><text x="100" y="144" text-anchor="end">SiO 9.9</text>
      <rect x="105" y="152" width="256.1" height="16" fill="#4a8b5c"/><text x="100" y="164" text-anchor="end">SiB 19.7</text>
      <!-- Te -->
      <rect x="105" y="178" width="137.8" height="16" fill="#c8963c" opacity="0.5"/><text x="100" y="190" text-anchor="end">TeA 10.6</text>
      <rect x="105" y="198" width="169.0" height="16" fill="#c8963c"/><text x="100" y="210" text-anchor="end">TeH 13.0</text>
      <!-- Fe -->
      <rect x="105" y="224" width="213.2" height="16" fill="#b85c5c" opacity="0.5"/><text x="100" y="236" text-anchor="end">FeA 16.4</text>
      <rect x="105" y="244" width="241.8" height="16" fill="#b85c5c"/><text x="100" y="256" text-anchor="end">FeH 18.6</text>
      <!-- Ni -->
      <rect x="105" y="270" width="234.0" height="16" fill="#2c5f7c" opacity="0.55"/><text x="100" y="282" text-anchor="end">NiO 18.0</text>
      <rect x="105" y="290" width="279.5" height="16" fill="#2c5f7c"/><text x="100" y="302" text-anchor="end">NiB 21.5</text>
      <!-- Se -->
      <rect x="105" y="316" width="122.2" height="16" fill="#4a8b5c" opacity="0.5"/><text x="100" y="328" text-anchor="end">SeO 9.4</text>
      <rect x="105" y="336" width="215.8" height="16" fill="#4a8b5c"/><text x="100" y="348" text-anchor="end">SeB 16.6</text>
      <!-- Ti -->
      <rect x="105" y="362" width="114.4" height="16" fill="#c8963c" opacity="0.5"/><text x="100" y="374" text-anchor="end">TiA 8.8</text>
      <rect x="105" y="382" width="196.3" height="16" fill="#c8963c"/><text x="100" y="394" text-anchor="end">TiH 15.1</text>
    </g>
  </svg>
  <p class="chart-data" style="font-size:12px;color:var(--text-secondary);text-align:center;margin-top:0.5rem;">
    <span style="color:#b85c5c;">■</span> 情感 F　<span style="color:#2c5f7c;">■</span> 直觉 N
    <span style="color:#4a8b5c;">■</span> 感觉 S　<span style="color:#c8963c;">■</span> 思考 T
    （深色＝较高亚型，浅色＝较低亚型）
  </p>
</div>
```

**已验证实例 C**（案例A · 图 2-3 十神力量分布——条右侧直接写证据注记「透1+藏2 ★纲」，替代纯数值）：

```html
<div class="chart-container">
    <div class="chart-title">图 2-3 · 十神力量分布（按天干透出 + 地支藏干计次）</div>
    <svg viewBox="0 0 460 250" width="100%" role="img" aria-label="十神分布图">
      <g font-size="12" fill="currentColor">
        <text x="8" y="26">七杀</text><rect x="52" y="16" width="180" height="16" rx="3" fill="#742a2a"/><text x="238" y="29">透1+藏2 ★纲</text>
        <text x="8" y="52">食神</text><rect x="52" y="42" width="135" height="16" rx="3" fill="#22543d"/><text x="193" y="55">藏3</text>
        <text x="8" y="78">偏财</text><rect x="52" y="68" width="90" height="16" rx="3" fill="#975a16"/><text x="148" y="81">藏2</text>
        <text x="8" y="104">伤官</text><rect x="52" y="94" width="60" height="16" rx="3" fill="#9b2c2c"/><text x="118" y="107">透1</text>
        <text x="8" y="130">正财</text><rect x="52" y="120" width="60" height="16" rx="3" fill="#b7791f"/><text x="118" y="133">透1</text>
        <text x="8" y="156">偏印</text><rect x="52" y="146" width="55" height="16" rx="3" fill="#276749"/><text x="113" y="159">藏1（调候用神）</text>
        <text x="8" y="182">正印</text><rect x="52" y="172" width="55" height="16" rx="3" fill="#2f855a"/><text x="113" y="185">藏1</text>
        <text x="8" y="208">正官</text><rect x="52" y="198" width="55" height="16" rx="3" fill="#2b6cb0"/><text x="113" y="211">藏1（坐空）</text>
        <text x="8" y="234">比肩</text><rect x="52" y="224" width="55" height="16" rx="3" fill="#c53030"/><text x="113" y="237">藏1（禄根巳，坐空）</text>
      </g>
    </svg>
  </div>
```

**变体建议**：镜像双向条形（左右对比两人/两运）；条内嵌文字（条足够长时）；与 P08 表格并用（条形给直觉、表格给精确值）。

---

### P03 · 堆叠/对比条形（双组横条）

**适用场景**：元素 × 模式能量分布（Ch4 星盘统计）、任何「两组各 3–5 类目」的并置对比。

**坐标计算公式**：

- 每组独立基线；`width = 计数 / max计数 × 180`（实例 max=5 → 每单位 36px）。
- 组标题（如「四元素」「三模式」）用主题色加粗小字；条右侧放 9px 解释性小注（这是本模式的灵魂——每根条都要翻译成性格语言）。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 440 250" width="100%" style="max-width:460px;display:block;margin:0 auto" font-family="sans-serif">
  <text x="10" y="18" font-size="12" fill="#7a5c9e" font-weight="bold">{组1标题}</text>
  <g font-size="11" fill="#333">
    <text x="10" y="{y+10}">{类目} {计数}</text>
    <rect x="55" y="{y}" width="{计数×36}" height="14" fill="{类目色}" opacity="0.8"/>
    <!-- …… 组1 各行，行距 22 …… -->
  </g>
  <text x="245" y="{y+10}" font-size="9" fill="{类目色}">{该类目包含的星体清单 → 性格翻译}</text>
  <text x="10" y="{组2y}" font-size="12" fill="#7a5c9e" font-weight="bold">{组2标题}</text>
  <!-- …… 组2 同构 …… -->
</svg>
```

**已验证实例**（案例A · 图 4-2 元素 × 模式能量分布；图注直接承担「量化印证性格结构」的论证任务）：

```html
<div class="chart-container">
<div class="chart-title">图 4-2　元素 × 模式能量分布（含日月五星＋三王＋上升 MC）</div>
<svg viewBox="0 0 440 250" width="100%" style="max-width:460px;display:block;margin:0 auto" font-family="sans-serif">
  <text x="10" y="18" font-size="12" fill="#7a5c9e" font-weight="bold">四元素</text>
  <!-- bars: max 5 -> width 180 -->
  <g font-size="11" fill="#333">
    <text x="10" y="45">火 4</text><rect x="55" y="35" width="144" height="14" fill="#c0392b" opacity="0.8"/>
    <text x="10" y="67">土 1</text><rect x="55" y="57" width="36" height="14" fill="#8d6e3a" opacity="0.85"/>
    <text x="10" y="89">风 5</text><rect x="55" y="79" width="180" height="14" fill="#2a7ab0" opacity="0.8"/>
    <text x="10" y="111">水 2</text><rect x="55" y="101" width="72" height="14" fill="#3a8f7a" opacity="0.8"/>
  </g>
  <text x="245" y="45" font-size="9" fill="#c0392b">太阳·水·冥·上升</text>
  <text x="245" y="67" font-size="9" fill="#8d6e3a">仅月亮 → Si/Te 落地弱</text>
  <text x="245" y="89" font-size="9" fill="#2a7ab0">火·土·天·海·MC → 思维/概念主导</text>
  <text x="245" y="111" font-size="9" fill="#3a8f7a">金·木</text>
  <text x="10" y="150" font-size="12" fill="#7a5c9e" font-weight="bold">三模式</text>
  <g font-size="11" fill="#333">
    <text x="10" y="177">基本 2</text><rect x="70" y="167" width="72" height="14" fill="#b08d57" opacity="0.85"/>
    <text x="10" y="199">固定 5</text><rect x="70" y="189" width="180" height="14" fill="#7a5c9e" opacity="0.8"/>
    <text x="10" y="221">变动 5</text><rect x="70" y="211" width="180" height="14" fill="#5a8f6a" opacity="0.8"/>
  </g>
  <text x="260" y="199" font-size="9" fill="#7a5c9e">固定：忠诚·执拗·全有全无</text>
  <text x="260" y="221" font-size="9" fill="#5a8f6a">变动：思维流动·适应·多向</text>
</svg>
<div class="chart-data">风象 5 一骑绝尘、土象仅 1（且只是月亮那一点感官）——星盘量化地印证了「概念/思维主导、落地功能薄弱」的性格结构：NeB 场域直觉在风象里如鱼得水，而 Te 劣势、Si 待觉醒在土象的荒芜里露了底。固定 5 对应 Fi 的极端忠诚，变动 5 对应 NeB 的多向流动，两股几乎等量的力，就是她「一边死忠、一边想漂走」的内在拉扯。</div>
</div>
```

**变体建议**：真正的堆叠条（单条内分段 rect 并排）适合「一个整体的构成占比」（如某宫吉煞星比例）；组数 ≥3 时改用 P13 矩阵热力表。

---

### P04 · 仪表盘/弧线（过程曲线示意）

**适用场景**：Grip 四幕弧线（Ch1）、任何「无精确纵轴、只示意过程形态」的曲线（压力-恢复、能量起落）。另：v3 模板的 Grip Meter 进度条（HTML div，见 output-template.md §3.4）是本模式的最简变体，仍然可用。

**坐标计算公式**：

- 示意曲线不需要数据坐标，用贝塞尔手绘形态：U 型 = `M x0 y高 C … y低 … L …（谷底平台）C … y高'`（下沉-谷底-回升）。
- 幕节点圆点放在曲线上的近似位置即可（视觉贴合曲线，偏差 ≤5px 无碍）；节点上方 serif 幕名、基线下方 9px 灰字幕义。
- 基线 `y=150` 一条横线即可，不画纵轴（示意图不标刻度，避免伪精确）。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 460 180" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
  <line x1="30" y1="150" x2="440" y2="150" stroke="#a8a59a" stroke-width="0.8"/>
  <path d="M 40 {y常态} C 110 {y常态} 120 {y低} 165 {y低} L 230 {y低} C 300 {y低} 300 {y复原} 420 {y复原}"
        fill="none" stroke="#8a1a1a" stroke-width="2.2"/>
  <circle cx="{幕1x}" cy="{幕1y}" r="4" fill="#4a8b5c"/>
  <text x="{幕1x}" y="{幕1y-17}" font-family="STSong,serif" font-size="11" fill="#1a1a1a" text-anchor="middle">第一幕</text>
  <text x="{幕1x}" y="172" font-size="9" fill="#8a8a8a" text-anchor="middle">{触发}</text>
  <!-- …… 幕 2/3/4 同构，谷底幕节点用 #8a1a1a 加大半径 …… -->
</svg>
```

**已验证实例**（案例A · Ch1 Grip 弧线四幕）：

```html
<div class="chart-container" style="padding:1.5rem 1.25rem;">
  <p class="chart-title">Grip 弧线 · 四幕（横轴：时间）</p>
  <svg viewBox="0 0 460 180" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
    <line x1="30" y1="150" x2="440" y2="150" stroke="#a8a59a" stroke-width="0.8"/>
    <!-- U 型弧线：正常→下沉→谷底→复原 -->
    <path d="M 40 60 C 110 60 120 140 165 140 L 230 140 C 300 140 300 60 420 55" fill="none" stroke="#8a1a1a" stroke-width="2.2"/>
    <!-- 四幕节点 -->
    <circle cx="55" cy="62" r="4" fill="#4a8b5c"/><text x="55" y="45" font-family="STSong,serif" font-size="11" fill="#1a1a1a" text-anchor="middle">第一幕</text><text x="55" y="172" font-size="9" fill="#8a8a8a" text-anchor="middle">触发</text>
    <circle cx="150" cy="135" r="4" fill="#c8963c"/><text x="150" y="118" font-family="STSong,serif" font-size="11" fill="#1a1a1a" text-anchor="middle">第二幕</text><text x="150" y="172" font-size="9" fill="#8a8a8a" text-anchor="middle">退行</text>
    <circle cx="200" cy="140" r="5" fill="#8a1a1a"/><text x="200" y="118" font-family="STSong,serif" font-size="11" fill="#8a1a1a" text-anchor="middle">第三幕</text><text x="200" y="172" font-size="9" fill="#8a8a8a" text-anchor="middle">谷底</text>
    <circle cx="410" cy="57" r="4" fill="#4a8b5c"/><text x="405" y="42" font-family="STSong,serif" font-size="11" fill="#1a1a1a" text-anchor="middle">第四幕</text><text x="405" y="172" font-size="9" fill="#8a8a8a" text-anchor="middle">复原</text>
  </svg>
</div>
```

**变体建议**：半圆仪表盘（`A` 弧 + 指针线，适合单值风险评分）；双弧线对照（健康路径 vs Grip 路径）；与 P10 组合（弧线讲时间进程、流转图讲状态结构）。

---

## 二、结构类

### P05 · 同心圆环（Beebe 八原型环）

**适用场景**：Beebe 八原型剧场（Ch1 锚点级；v3 模板既有资产升级版）；任何「同心层级 + 扇区」结构。

**坐标计算公式**：

- 中心 `(180, 180)`，四层同心圆 r = 160 / 120 / 80 / 40。
- 八扇区分隔线：过中心的 4 条直线（0°、45°、90°、135°），端点 `x = 180 ± 160·sin(θ)`，`y = 180 ∓ 160·cos(θ)`（画到 r=160 即可，实例取 20/340 边界近似值）。
- 扇区高亮 path：`M 180 180 L x1 y1 A 160 160 0 0 1 x2 y2 Z`，其中 `(x1,y1)`、`(x2,y2)` 为该扇区两条边界角 θ1、θ2（顺时针 θ2=θ1+45°）在 r=160 上的点，公式同上。
- 八原型标签顺时针从顶部右扇区起：英雄→父母→少年→劣势→对立→批评→骗子→恶魔；标签放 r≈130–145、扇区中线角上，`x = 180 + 138·sin(θ中)`，`y = 180 − 138·cos(θ中)`（实例手工微调）。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:330px;width:100%;">
  <g fill="none" stroke="#d5d2c8" stroke-width="0.5">
    <circle cx="180" cy="180" r="160" /><circle cx="180" cy="180" r="120" />
    <circle cx="180" cy="180" r="80" /><circle cx="180" cy="180" r="40" />
  </g>
  <g stroke="#d5d2c8" stroke-width="0.5">
    <line x1="180" y1="20" x2="180" y2="340" /><line x1="20" y1="180" x2="340" y2="180" />
    <line x1="67" y1="67" x2="293" y2="293" /><line x1="293" y1="67" x2="67" y2="293" />
  </g>
  <!-- Hero 扇区高亮（顶部右）；特异扇区（如明亮阴影）用第二色低透明度 -->
  <path d="M 180 180 L 180 20 A 160 160 0 0 1 293 67 Z" fill="rgba(138,26,26,0.18)" stroke="#8a1a1a" stroke-width="1" />
  <path d="M 180 180 L {θ1x} {θ1y} A 160 160 0 0 1 {θ2x} {θ2y} Z" fill="rgba(44,95,124,0.14)" stroke="#2c5f7c" stroke-width="0.8" />
  <!-- 八原型标签：名 + 小号数值 -->
  <g font-family="STSong, Songti SC, serif" font-size="11.5" fill="#1a1a1a" text-anchor="middle">
    <text x="238" y="52">英雄·{Hero功能}</text><text x="238" y="66" font-size="9" fill="#8a1a1a">{值}</text>
    <text x="306" y="152">父母·{Parent}</text><text x="306" y="166" font-size="9" fill="#4a8b5c">{值}</text>
    <text x="306" y="218">少年·{Child}</text><text x="306" y="232" font-size="9" fill="#5a5a5a">{值}</text>
    <text x="238" y="312">劣势·{Inferior}</text><text x="238" y="326" font-size="9" fill="#5a5a5a">{值}</text>
    <text x="120" y="312">对立·{Opposing}</text><text x="120" y="326" font-size="9" fill="#5a5a5a">{值}</text>
    <text x="52" y="218">批评·{Senex}</text><text x="52" y="232" font-size="9" fill="#5a5a5a">{值}</text>
    <text x="52" y="152">骗子·{Trickster}</text><text x="52" y="166" font-size="9" fill="#5a5a5a">{值}</text>
    <text x="120" y="52">恶魔·{Demon}</text><text x="120" y="66" font-size="9" fill="#5a5a5a">{值}</text>
  </g>
  <text x="180" y="176" font-family="STSong, serif" font-size="13" fill="#5a5a5a" text-anchor="middle">{类型}</text>
  <text x="180" y="192" font-family="sans-serif" font-size="9" fill="#8a8a8a" text-anchor="middle">{一行状态注：如"阴影半整合"}</text>
</svg>
```

**已验证实例**（案例A · Ch1 Beebe 八原型环——注意 ★ 前缀 + 蓝色扇区标记「明亮阴影」的特异点手法）：

```html
<div class="chart-container">
  <p class="chart-title">Beebe 八原型 · 性格剧场（★＝明亮阴影）</p>
  <svg viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:330px;width:100%;">
    <g fill="none" stroke="#d5d2c8" stroke-width="0.5">
      <circle cx="180" cy="180" r="160" /><circle cx="180" cy="180" r="120" />
      <circle cx="180" cy="180" r="80" /><circle cx="180" cy="180" r="40" />
    </g>
    <g stroke="#d5d2c8" stroke-width="0.5">
      <line x1="180" y1="20" x2="180" y2="340" /><line x1="20" y1="180" x2="340" y2="180" />
      <line x1="67" y1="67" x2="293" y2="293" /><line x1="293" y1="67" x2="67" y2="293" />
    </g>
    <!-- Hero 扇区高亮（顶部右） -->
    <path d="M 180 180 L 180 20 A 160 160 0 0 1 293 67 Z" fill="rgba(138,26,26,0.18)" stroke="#8a1a1a" stroke-width="1" />
    <!-- 明亮阴影扇区：Ni（左）与 Fe（左下） -->
    <path d="M 180 180 L 20 180 A 160 160 0 0 1 67 67 Z" fill="rgba(44,95,124,0.14)" stroke="#2c5f7c" stroke-width="0.8" />
    <path d="M 180 180 L 67 293 A 160 160 0 0 1 180 340 Z" fill="rgba(44,95,124,0.10)" stroke="#2c5f7c" stroke-width="0.8" />
    <g font-family="STSong, Songti SC, serif" font-size="11.5" fill="#1a1a1a" text-anchor="middle">
      <text x="238" y="52">英雄·Fi</text><text x="238" y="66" font-size="9" fill="#8a1a1a">19.6</text>
      <text x="306" y="152">父母·Ne</text><text x="306" y="166" font-size="9" fill="#4a8b5c">17.4</text>
      <text x="306" y="218">少年·Si</text><text x="306" y="232" font-size="9" fill="#5a5a5a">14.8</text>
      <text x="238" y="312">劣势·Te</text><text x="238" y="326" font-size="9" fill="#5a5a5a">11.8</text>
      <text x="120" y="312">★对立·Fe</text><text x="120" y="326" font-size="9" fill="#2c5f7c">17.5</text>
      <text x="52" y="218">★批评·Ni</text><text x="52" y="232" font-size="9" fill="#2c5f7c">19.8</text>
      <text x="52" y="152">骗子·Se</text><text x="52" y="166" font-size="9" fill="#5a5a5a">13.0</text>
      <text x="120" y="52">恶魔·Ti</text><text x="120" y="66" font-size="9" fill="#5a5a5a">12.0</text>
    </g>
    <text x="180" y="176" font-family="STSong, serif" font-size="13" fill="#5a5a5a" text-anchor="middle">INFP</text>
    <text x="180" y="192" font-family="sans-serif" font-size="9" fill="#8a8a8a" text-anchor="middle">阴影半整合</text>
  </svg>
</div>
```

**变体建议**：按各原型实测强度改变扇区填充透明度（强 → 深）；中心圈放一句话画像缩写；与 P01 并排呼应（雷达讲强度、环讲角色）。

---

### P06 · 十二宫盘（紫微命盘 · HTML Grid）

**适用场景**：紫微本命盘（Ch3 锚点图）；大限盘/流年盘复用同骨架。**注意：本模式是 HTML Grid，不是 SVG**——十二宫内容量大（主星+辅星+四化+杂耀），Grid 比 SVG 文本排版稳得多，这是案例A版实测后的选型结论。

**布局公式**（地支 → grid 位置，固定不变，4×4 外圈，中央 2×2 为信息区）：

| 地支 | grid-column | grid-row | | 地支 | grid-column | grid-row |
|:--|:--|:--|:--|:--|:--|:--|
| 巳 | 1 | 1 | | 亥 | 4 | 4 |
| 午 | 2 | 1 | | 子 | 3 | 4 |
| 未 | 3 | 1 | | 丑 | 2 | 4 |
| 申 | 4 | 1 | | 寅 | 1 | 4 |
| 辰 | 1 | 2 | | 酉 | 4 | 2 |
| 卯 | 1 | 3 | | 戌 | 4 | 3 |

中央信息区：`grid-column:2/4; grid-row:2/4`。各宫的**宫名**（命宫/兄弟宫/…）按排盘结果落入对应地支格；地支位置永远固定，宫名随命主变动。

**HTML 骨架模板**：

```html
<div class="ziwei-board" style="display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(4,minmax(96px,auto));gap:2px;">
  <!-- 每宫一格；命宫加 class="ming" 并在宫名后加 ★，身宫加 class="shen" 并加 ◎身 -->
  <div class="ziwei-cell" style="grid-column:{列};grid-row:{行};">
    <div class="gz">{干支}</div><div class="palace-name">{宫名}{ ★ / ◎身 / ⟵命借}</div>
    <div class="major-star">{主星}<sup>{庙旺得平陷}</sup>{ · 次主星}<span class="sihua lu">禄</span></div>
    <div class="minor-star">{辅星 · 杂耀 · 神煞，重要辅星用 <b> 加粗}</div>
  </div>
  <!-- …… 12 宫 …… 空宫写法：<div class="major-star" style="opacity:.6">〔空宫 · 借{对宫星}〕</div> -->
  <div class="ziwei-center" style="grid-column:2/4;grid-row:2/4;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:.4em;padding:1em;">
    <div style="font-size:1.5em;font-weight:700;letter-spacing:.1em;">{命主姓名}</div>
    <div>{年柱}年 · {月柱}月 · {日柱}日 · {时柱}时</div>
    <div>命主 <b>{命主星}</b> · 身主 <b>{身主星}</b> · <b>{五行局}</b></div>
    <div>命宫在{支}{（空宫借某某）} · 身宫在{支}</div>
    <div style="opacity:.75;font-size:.9em;">{天干}年四化：{星}禄 · {星}权 · {星}科 · {星}忌</div>
  </div>
</div>
<div class="chart-data" style="opacity:.75;font-size:.85em;margin-top:.5em;">★＝命宫　◎身＝身宫　⟵命借＝命宫向此宫借星　<span class="sihua lu">禄</span><span class="sihua quan">权</span><span class="sihua ke">科</span><span class="sihua ji">忌</span>＝{天干}年四化落点</div>
```

**配套 CSS 注意**：`.ziwei-board / .ziwei-cell / .palace-name / .major-star / .minor-star` 已在 output-template.md 主 CSS 中；但案例A版用到的 `.gz / .sihua(.lu .quan .ke .ji) / .ming / .shen / .ziwei-center` **未定义 CSS**（实测靠默认样式渲染，能看但四化无色彩区分）。v4 落图时建议补一段：

```css
.ziwei-cell .gz { font-size:11px; color: var(--text-tertiary); }
.ziwei-cell.ming { background: rgba(138,26,26,0.06); border-color: var(--accent); }
.ziwei-cell.shen { background: rgba(74,139,92,0.06); }
.sihua { display:inline-block; font-size:10px; padding:0 3px; margin-left:2px; border-radius:2px; color:#fff; }
.sihua.lu{background:#3a9d6b;} .sihua.quan{background:#c98a2b;} .sihua.ke{background:#3f77c2;} .sihua.ji{background:#b23b3b;}
```

（此 CSS 为 v4 建议新增，未经案例A版实测，首次使用须过 C4；不加也能渲染，仅损失四化配色。）

**已验证实例**（案例A · 图一 十二宫命盘——含空宫借星、身宫/来因宫标注、四化落点，完整 12 宫 + 中宫）：

```html
<div class="chart-container">
<div class="chart-title">图一 · 十二宫命盘（辛巳年 · 金四局 · 命宫在未）</div>
<div class="ziwei-board" style="display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(4,minmax(96px,auto));gap:2px;">

  <!-- Row1 -->
  <div class="ziwei-cell" style="grid-column:1;grid-row:1;">
    <div class="gz">癸巳</div><div class="palace-name">夫妻宫</div>
    <div class="major-star">天梁<sup>平</sup></div>
    <div class="minor-star">凤阁 · 天福 · 空亡 · 年解</div>
  </div>
  <div class="ziwei-cell" style="grid-column:2;grid-row:1;">
    <div class="gz">甲午</div><div class="palace-name">兄弟宫</div>
    <div class="major-star">七杀<sup>陷</sup></div>
    <div class="minor-star"><b>文昌<span class="sihua ji">忌</span></b> · 天魁 · 咸池 · 天刑</div>
  </div>
  <div class="ziwei-cell ming" style="grid-column:3;grid-row:1;">
    <div class="gz">乙未</div><div class="palace-name">命宫 ★</div>
    <div class="major-star" style="opacity:.6">〔空宫 · 借日月〕</div>
    <div class="minor-star">火星 · 地空 · 恩光 · 蜚廉</div>
  </div>
  <div class="ziwei-cell" style="grid-column:4;grid-row:1;">
    <div class="gz">丙申</div><div class="palace-name">父母宫</div>
    <div class="major-star">廉贞<sup>平</sup></div>
    <div class="minor-star"><b>文曲<span class="sihua ke">科</span></b> · 陀罗 · 天巫 · 孤辰</div>
  </div>

  <!-- Row2 -->
  <div class="ziwei-cell" style="grid-column:1;grid-row:2;">
    <div class="gz">壬辰</div><div class="palace-name">子女宫</div>
    <div class="major-star">紫微<sup>得</sup> · 天相<sup>平</sup></div>
    <div class="minor-star">天喜 · 解神 · 截路 · 寡宿</div>
  </div>
  <div class="ziwei-center" style="grid-column:2/4;grid-row:2/4;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:.4em;padding:1em;">
    <div style="font-size:1.5em;font-weight:700;letter-spacing:.1em;">林 果 果</div>
    <div>辛巳年 · 己亥月 · 丙申日 · 壬辰时</div>
    <div>命主 <b>武曲</b> · 身主 <b>天机</b> · <b>金四局</b></div>
    <div>命宫在未（空宫借日月）· 身宫在卯</div>
    <div style="opacity:.75;font-size:.9em;">辛年四化：巨门禄 · 太阳权 · 文曲科 · 文昌忌</div>
  </div>
  <div class="ziwei-cell" style="grid-column:4;grid-row:2;">
    <div class="gz">丁酉</div><div class="palace-name">福德宫</div>
    <div class="major-star" style="opacity:.6">〔空宫 · 借机巨〕</div>
    <div class="minor-star"><b>禄存</b> · 龙池 · 天贵 · 旬空 · 破碎</div>
  </div>

  <!-- Row3 -->
  <div class="ziwei-cell shen" style="grid-column:1;grid-row:3;">
    <div class="gz">辛卯</div><div class="palace-name">财帛宫 ◎身</div>
    <div class="major-star">天机<sup>旺</sup> · 巨门<sup>得</sup><span class="sihua lu">禄</span></div>
    <div class="minor-star">地劫 · 三台 <span style="opacity:.7">（身宫·来因宫）</span></div>
  </div>
  <div class="ziwei-cell" style="grid-column:4;grid-row:3;">
    <div class="gz">戊戌</div><div class="palace-name">田宅宫</div>
    <div class="major-star">破军<sup>旺</sup></div>
    <div class="minor-star">擎羊 · 红鸾 · 天姚 · 月德</div>
  </div>

  <!-- Row4 -->
  <div class="ziwei-cell" style="grid-column:1;grid-row:4;">
    <div class="gz">庚寅</div><div class="palace-name">疾厄宫</div>
    <div class="major-star">贪狼<sup>旺</sup></div>
    <div class="minor-star">天钺 · 铃星 · 天德 · 天使</div>
  </div>
  <div class="ziwei-cell" style="grid-column:2;grid-row:4;">
    <div class="gz">辛丑</div><div class="palace-name">迁移宫 ⟵命借</div>
    <div class="major-star">太阳<sup>得</sup><span class="sihua quan">权</span> · 太阴<sup>庙</sup></div>
    <div class="minor-star"><b>左辅 · 右弼</b> · 华盖 · 天哭</div>
  </div>
  <div class="ziwei-cell" style="grid-column:3;grid-row:4;">
    <div class="gz">庚子</div><div class="palace-name">交友宫</div>
    <div class="major-star">武曲<sup>得</sup> · 天府<sup>庙</sup></div>
    <div class="minor-star">天才 · 天伤</div>
  </div>
  <div class="ziwei-cell" style="grid-column:4;grid-row:4;">
    <div class="gz">己亥</div><div class="palace-name">官禄宫</div>
    <div class="major-star">天同<sup>旺</sup></div>
    <div class="minor-star">天马 · 八座 · 天虚</div>
  </div>

</div>
<div class="chart-data" style="opacity:.75;font-size:.85em;margin-top:.5em;">★＝命宫　◎身＝身宫　⟵命借＝命宫向此宫借星　<span class="sihua lu">禄</span><span class="sihua quan">权</span><span class="sihua ke">科</span><span class="sihua ji">忌</span>＝辛年四化落点</div>
</div>
```

**变体建议**：大限盘 = 同骨架，宫名换成「大限命宫…」并标年龄区间；流年盘 = 在各格追加一行流曜；本命+大限双层标注（格内两行宫名，主次字号区分）。三方四正强调：给命宫及其三方四正格加 `outline: 1.5px solid var(--accent-soft)`。

---

### P07 · 星盘轮（本命星盘 · Placidus 简化示意）

**适用场景**：本命星盘（Ch4 锚点图）。定位是「简化示意」：不追求专业星历软件精度，追求把**行星聚簇、轴点、宫位大势**一眼呈现。

**坐标计算公式**（已对案例A实例反向验证）：

- 中心 `(cx, cy) = (210, 210)`；三圈：外圈（星座环外缘）r=175、中圈（星座环内缘/宫位环外缘）r=145、内圈 r=55。
- **ASC 固定在正左（9 点钟位），黄道逆时针增长**（从 ASC 向下进入 1 宫）。对黄经 λ 的点：
  - `offset = (λ − λ_ASC) mod 360`
  - `x = cx − r·cos(offset°)`，`y = cy + r·sin(offset°)`
  - 验证：offset=0 → (cx−r, cy) 正左 ✓；offset=90°（IC 方向）→ (cx, cy+r) 正下 ✓。
- 12 星座分界刻度：λ = 0°, 30°, 60°, …（白羊 0° 起），画 r 175→145 的短线，端点各按上式取 r=175 与 r=145。
- 宫始线（Placidus）：按各宫头黄经画 r 145→55 的线；ASC–DSC 轴与 MC–IC 轴加粗/标签（`ASC` 左、`MC` 上方附近——注意 MC 不必正上，按实际黄经算）。
- 行星符号：`☉☽☿♀♂♃♄♅♆♇☊`，放 r ≈ 60–135（同宫聚簇时错开半径防重叠），`font-size 15`。
- 聚簇是重点：同星座多星时，让它们在视觉上成「簇」，并在图注点破（见实例图注）。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 420 430" width="100%" style="max-width:440px;display:block;margin:0 auto" font-family="serif" aria-label="本命星盘简化轮">
  <circle cx="210" cy="210" r="175" fill="none" stroke="#b08d57" stroke-width="1.5"/>
  <circle cx="210" cy="210" r="145" fill="none" stroke="#b08d57" stroke-width="0.8" opacity="0.6"/>
  <circle cx="210" cy="210" r="55" fill="none" stroke="#b08d57" stroke-width="0.8" opacity="0.5"/>
  <!-- 12 星座分界（r=175→145），每 30° 一条，端点按公式 -->
  <g stroke="#c9b48a" stroke-width="0.6" opacity="0.7">
    <line x1="{x@175}" y1="{y@175}" x2="{x@145}" y2="{y@145}"/>
    <!-- …… ×12 …… -->
  </g>
  <!-- 宫始线（r=145→55），1-7 轴与 10-4 轴为主轴 -->
  <g stroke="#8a7a9a" stroke-width="0.7" opacity="0.45">
    <line x1="65" y1="210" x2="355" y2="210"/> <!-- ASC-DSC 轴 -->
    <line x1="{MC线}" y1="…" x2="…" y2="…"/> <!-- MC-IC 轴 -->
    <!-- …… 其余 4 条宫始线 …… -->
  </g>
  <text x="30" y="207" font-size="10" fill="#7a5c9e" font-weight="bold">ASC</text>
  <text x="358" y="207" font-size="9" fill="#9a8">DSC</text>
  <text x="{MCx}" y="{MCy}" font-size="10" fill="#7a5c9e" font-weight="bold">MC</text>
  <!-- 行星：按 offset 公式布点，同簇错开半径 -->
  <g font-size="15" fill="#2a2a3a" text-anchor="middle">
    <text x="{☉x}" y="{☉y}" fill="#c0392b">☉</text>
    <text x="{☽x}" y="{☽y}" fill="#2a6">☽</text>
    <!-- …… 水金火木土天海冥 + ☊ …… -->
  </g>
  <text x="210" y="214" font-size="8" fill="#b08d57" text-anchor="middle">{命主名}</text>
  <text x="210" y="424" font-size="8" fill="#999" text-anchor="middle">上升在左·逆时针·◐逆行行星见相位表</text>
</svg>
```

**已验证实例**（案例A · 图 4-1 本命星盘轮——注意图注把「29.87° 交界上升」「双聚簇」两个视觉重心点破）：

> ⚠️ 本实例只作 SVG 骨架与图注写法参考；其中「上升射手 29.87°」是 v4.0 重复经度校正的错盘数据，钟表时正确值为上升摩羯 3.34°、太阳落 11 宫（2026-09-27 复核）。

```html
<div class="chart-container">
<div class="chart-title">图 4-1　本命星盘轮（Placidus 分宫·简化示意）</div>
<svg viewBox="0 0 420 430" width="100%" style="max-width:440px;display:block;margin:0 auto" font-family="serif" aria-label="本命星盘简化轮">
  <circle cx="210" cy="210" r="175" fill="none" stroke="#b08d57" stroke-width="1.5"/>
  <circle cx="210" cy="210" r="145" fill="none" stroke="#b08d57" stroke-width="0.8" opacity="0.6"/>
  <circle cx="210" cy="210" r="55" fill="none" stroke="#b08d57" stroke-width="0.8" opacity="0.5"/>
  <!-- 12 星座分界 (r=175->145) -->
  <g stroke="#c9b48a" stroke-width="0.6" opacity="0.7">
    <line x1="210" y1="385" x2="210" y2="355"/><line x1="298" y1="361" x2="283" y2="335"/>
    <line x1="362" y1="297" x2="336" y2="282"/><line x1="385" y1="210" x2="355" y2="210"/>
    <line x1="361" y1="122" x2="335" y2="137"/><line x1="297" y1="58" x2="282" y2="84"/>
    <line x1="210" y1="35" x2="210" y2="65"/><line x1="122" y1="59" x2="137" y2="85"/>
    <line x1="58" y1="123" x2="84" y2="138"/><line x1="35" y1="210" x2="65" y2="210"/>
    <line x1="59" y1="298" x2="85" y2="283"/><line x1="123" y1="362" x2="138" y2="336"/>
  </g>
  <!-- 宫始线 (r=145->55) 淡 -->
  <g stroke="#8a7a9a" stroke-width="0.7" opacity="0.45">
    <line x1="65" y1="210" x2="355" y2="210"/> <!-- ASC-DSC 1-7 轴 -->
    <line x1="181" y1="68" x2="239" y2="352"/> <!-- MC-IC 10-4 轴 -->
    <line x1="88" y1="288" x2="332" y2="132"/><line x1="155" y1="344" x2="265" y2="76"/>
    <line x1="305" y1="320" x2="115" y2="100"/><line x1="343" y1="269" x2="77" y2="151"/>
  </g>
  <!-- 轴心标签 -->
  <text x="30" y="207" font-size="10" fill="#7a5c9e" font-weight="bold">ASC</text>
  <text x="358" y="207" font-size="9" fill="#9a8" >DSC</text>
  <text x="175" y="30" font-size="10" fill="#7a5c9e" font-weight="bold">MC</text>
  <!-- 行星点 -->
  <g font-size="15" fill="#2a2a3a" text-anchor="middle">
    <text x="88" y="163" fill="#c0392b">☉</text>
    <text x="113" y="167" fill="#5a6">☿</text>
    <text x="136" y="164" fill="#159">♀</text>
    <text x="65" y="176" fill="#4a148c">♇</text>
    <text x="298" y="304" fill="#2a6">☽</text>
    <text x="326" y="185" fill="#b8860b">♃</text>
    <text x="324" y="252" fill="#555">♄</text>
    <text x="133" y="317" fill="#0aa">♂</text>
    <text x="145" y="296" fill="#08c">♅</text>
    <text x="98" y="299" fill="#69c">♆</text>
    <text x="330" y="221" fill="#96a">☊</text>
  </g>
  <text x="210" y="214" font-size="8" fill="#b08d57" text-anchor="middle">案例A</text>
  <text x="210" y="424" font-size="8" fill="#999" text-anchor="middle">上升在左·逆时针·◐逆行行星见相位表</text>
</svg>
<div class="chart-data">上升射手 29.87°几乎抵摩羯门槛（左轴 ASC）；太阳·水星·冥王三点聚于左下方射手座（12 宫一侧），火星·天王·海王三点聚于左下水瓶座（2 宫）——两簇「隐匿的自我」与「叛逆的价值」是全盘视觉重心。</div>
</div>
```

**变体建议**：相位线版（内圈 r=55 内画行星连线：合相不画、对冲红实线、四分红虚线、三合/六合蓝细线——线多时只画偏差 <3° 的紧密相位）；行运叠加（外缘加一圈行运行星，空心符号）；P16 双轮对照由本模式派生。

---

### P08 · 结构化全表（数据密度型表格）

**适用场景**：四柱排盘全表（Ch2 锚点图）、主要相位全表（Ch4）、大运/流年细表、任何「精确值多列结构化」数据。SVG 讲直觉，表格讲精确——两者常配对使用。

**结构公式**（无坐标，只有列 schema）：

- 四柱表列序：柱位 | 年柱 | 月柱 | 日柱 | 时柱；行序：干支 → 天干十神 → 纳音 → 藏干 → 藏干十神 → 神煞 → 空亡（空亡行用 `colspan="2"` 并列年旬/日旬）。日主用 `<strong>` 突出。
- 相位表列序：相位 | 性质 | 偏差 | 回扣的张力；**按偏差紧密度升序排列**（0.00° 在最上），最重要的一条整行 `<strong>`；表下图注给符号图例 + 「偏差越小能量越纯粹」的读表法。
- 一律用 `table.chart-data`（CSS 已在主模板）。

**HTML 骨架模板**（四柱版）：

```html
<table class="chart-data">
  <thead>
    <tr><th>柱位</th><th>年柱（祖上/童年）</th><th>月柱（父母/青年）</th><th>日柱（自身/配偶）</th><th>时柱（子女/晚年）</th></tr>
  </thead>
  <tbody>
    <tr><th>干支</th><td>{年干} {年支}</td><td>{月干} {月支}</td><td><strong>{日干}</strong> {日支}</td><td>{时干} {时支}</td></tr>
    <tr><th>天干十神</th><td>{十神}</td><td>{十神}</td><td><strong>日主</strong></td><td>{十神}</td></tr>
    <tr><th>纳音</th><td>{纳音}</td><td>{纳音}</td><td>{纳音}</td><td>{纳音}</td></tr>
    <tr><th>藏干</th><td>{藏干}</td><td>{藏干}</td><td>{藏干}</td><td>{藏干}</td></tr>
    <tr><th>藏干十神</th><td>{…}</td><td>{…}</td><td>{…}</td><td>{…}</td></tr>
    <tr><th>神煞</th><td>{…}</td><td>{…}</td><td>{…}</td><td>{…}</td></tr>
    <tr><th>空亡</th><td colspan="2">年柱旬空:{支支}</td><td colspan="2">日柱旬空:{支支}</td></tr>
  </tbody>
</table>
```

**已验证实例 A**（案例A · 图 2-1 四柱排盘全表——锚点六图之一）：

```html
<div class="chart-container">
    <div class="chart-title">图 2-1 · 四柱排盘全表（含纳音 · 藏干 · 十神）</div>
    <table class="chart-data">
      <thead>
        <tr><th>柱位</th><th>年柱（祖上/童年）</th><th>月柱（父母/青年）</th><th>日柱（自身/配偶）</th><th>时柱（子女/晚年）</th></tr>
      </thead>
      <tbody>
        <tr><th>干支</th><td>辛 巳</td><td>己 亥</td><td><strong>丙</strong> 申</td><td>壬 辰</td></tr>
        <tr><th>天干十神</th><td>正财</td><td>伤官</td><td><strong>日主</strong></td><td>七杀</td></tr>
        <tr><th>纳音</th><td>白蜡金</td><td>平地木</td><td>山下火</td><td>长流水</td></tr>
        <tr><th>藏干</th><td>丙 庚 戊</td><td>壬 甲</td><td>庚 壬 戊</td><td>戊 乙 癸</td></tr>
        <tr><th>藏干十神</th><td>比肩·偏财·食神</td><td>七杀·偏印</td><td>偏财·七杀·食神</td><td>食神·正印·正官</td></tr>
        <tr><th>神煞</th><td>劫煞</td><td>天乙贵人·月德合·驿马·亡神</td><td>文昌贵人·孤辰·亡神</td><td>寡宿·华盖</td></tr>
        <tr><th>空亡</th><td colspan="2">年柱旬空:申酉</td><td colspan="2">日柱旬空:辰巳</td></tr>
      </tbody>
    </table>
  </div>
```

**已验证实例 B**（案例A · 图 4-3 主要相位全表，15 条按紧密度排序；此处截短为前 6 行 + 末行，结构完整可渲染，全表见原书）：

```html
<div class="chart-container">
<div class="chart-title">图 4-3　主要相位全表（15 条·按偏差紧密度排序）</div>
<table class="chart-data" style="width:100%;border-collapse:collapse;font-size:0.9em">
<thead><tr style="border-bottom:2px solid #b08d57"><th style="text-align:left;padding:4px">相位</th><th>性质</th><th>偏差</th><th style="text-align:left">回扣的张力</th></tr></thead>
<tbody>
<tr><td style="padding:3px">月亮 ✶ 木星（60°）</td><td>六合·助力</td><td><strong>0.00°</strong></td><td style="text-align:left">情感天生带福分、被滋养的救赎性温暖</td></tr>
<tr><td style="padding:3px">太阳 ✶ 海王（60°）</td><td>六合·天赋</td><td><strong>0.37°</strong></td><td style="text-align:left">灵性/共情/艺术通道 → 深湖诗人</td></tr>
<tr><td style="padding:3px">火星 ☌ 天王（0°）</td><td>合相·叠加</td><td>1.56°</td><td style="text-align:left">叛逆的、为自由而战的行动力</td></tr>
<tr><td style="padding:3px">土星 ☍ 冥王（180°）</td><td>对冲·世代</td><td>2.94°</td><td style="text-align:left">权力结构的世代张力（同代共题）</td></tr>
<tr><td style="padding:3px">金星 □ 火星（90°）</td><td>四分·考题</td><td>2.85°</td><td style="text-align:left">爱（天蝎深情）与欲/自主（水瓶）的拉扯</td></tr>
<tr><td style="padding:3px">水星 ✶ 海王（60°）</td><td>六合·天赋</td><td>2.91°</td><td style="text-align:left">直觉式、诗性的思维语言</td></tr>
<!-- …… 中略 8 行（结构同上，见原书） …… -->
<tr><td style="padding:3px">太阳 ☍ 土星（180°）</td><td>对冲·考题</td><td>5.00°</td><td style="text-align:left"><strong>宏大意义 vs 务实落地 → Te 劣势主轴</strong></td></tr>
</tbody>
</table>
<div class="chart-data">☌合 ☍冲 △三合 □四分 ✶六合。偏差越小，能量越纯粹显著。最紧密的两条（月亮六合木星 0.00°、太阳六合海王 0.37°）都是「顺流的天赋」，最沉重的一条（太阳对冲土星 5°）则是终身要整合的考题。</div>
</div>
```

**变体建议**：任何 P02/P03 条形图都可以配一张对应全表放附录；行高亮（inline `style="background:rgba(138,26,26,0.05)"`）标出与性格签名直接相关的行。

---

## 三、流动类

### P09 · 流向图（四化流向）

**适用场景**：辛年四化流向（Ch3）、任何「源 → 目标」的少量（≤6 条）定向关系。

**坐标计算公式**：

- 每条流向占一行：第 k 行 `y_k = 40 + k × 65`（末行可压缩间距）。
- 源节点：圆 `(70, y_k)` r=26，圈色 = 该化性质色（禄绿 `#3a9d6b`、权金 `#c98a2b`、科蓝 `#3f77c2`、忌红 `#b23b3b`）；星名 15px 加粗在圈内上、化名 11px 在圈内下。
- 箭头线：`x 98 → 300`，同色，忌用 `stroke-dasharray="5 3"` 虚线（负向能量视觉降权）；线上方居中 11px 语义注（「口才思辨 → 财源·福气」式）。
- 目标文本：`x=360`，13px 加粗宫名（可附「⟶ 照命」等关系注）。
- marker 箭头：`<marker>` 定义一次，`fill="currentColor"` + 在 line 上设 `color` 继承变色。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 640 240" width="100%" style="max-width:640px;font-family:inherit;">
  <defs>
    <marker id="{chartid}-ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="currentColor"/></marker>
  </defs>
  <!-- 每行一化：圆（源星）→ 箭头线（语义注）→ 目标宫 -->
  <circle cx="70" cy="{y}" r="26" fill="none" stroke="{化色}" stroke-width="2"/>
  <text x="70" y="{y-4}" text-anchor="middle" font-size="15" font-weight="700">{星名}</text>
  <text x="70" y="{y+12}" text-anchor="middle" font-size="11" fill="{化色}">化{禄/权/科/忌}</text>
  <line x1="98" y1="{y}" x2="300" y2="{y}" stroke="{化色}" stroke-width="2" marker-end="url(#{chartid}-ar)" color="{化色}"/>
  <text x="200" y="{y-10}" text-anchor="middle" font-size="11" fill="{化色}">{能量语义} → {去向语义}</text>
  <text x="360" y="{y+5}" font-size="13" font-weight="600">{目标宫}{（关系注）}</text>
  <!-- …… ×4 …… 化忌行：线加 stroke-dasharray="5 3"，目标文字同红色 -->
</svg>
```

**已验证实例**（案例A · 图二 辛年四化流向图）：

```html
<div class="chart-container">
<div class="chart-title">图二 · 辛年四化流向图</div>
<svg viewBox="0 0 640 240" width="100%" style="max-width:640px;font-family:inherit;">
  <defs>
    <marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="currentColor"/></marker>
  </defs>
  <!-- 禄 -->
  <circle cx="70" cy="40" r="26" fill="none" stroke="#3a9d6b" stroke-width="2"/>
  <text x="70" y="36" text-anchor="middle" font-size="15" font-weight="700">巨门</text>
  <text x="70" y="52" text-anchor="middle" font-size="11" fill="#3a9d6b">化禄</text>
  <line x1="98" y1="40" x2="300" y2="40" stroke="#3a9d6b" stroke-width="2" marker-end="url(#ar)" color="#3a9d6b"/>
  <text x="200" y="30" text-anchor="middle" font-size="11" fill="#3a9d6b">口才思辨 → 财源·福气</text>
  <text x="360" y="45" font-size="13" font-weight="600">财帛宫（身宫）</text>
  <!-- 权 -->
  <circle cx="70" cy="105" r="26" fill="none" stroke="#c98a2b" stroke-width="2"/>
  <text x="70" y="101" text-anchor="middle" font-size="15" font-weight="700">太阳</text>
  <text x="70" y="117" text-anchor="middle" font-size="11" fill="#c98a2b">化权</text>
  <line x1="98" y1="105" x2="300" y2="105" stroke="#c98a2b" stroke-width="2" marker-end="url(#ar)" color="#c98a2b"/>
  <text x="200" y="95" text-anchor="middle" font-size="11" fill="#c98a2b">在外权威 → 借入命宫</text>
  <text x="360" y="110" font-size="13" font-weight="600">迁移宫 ⟶ 照命</text>
  <!-- 科 -->
  <circle cx="70" cy="170" r="26" fill="none" stroke="#3f77c2" stroke-width="2"/>
  <text x="70" y="166" text-anchor="middle" font-size="15" font-weight="700">文曲</text>
  <text x="70" y="182" text-anchor="middle" font-size="11" fill="#3f77c2">化科</text>
  <line x1="98" y1="170" x2="300" y2="170" stroke="#3f77c2" stroke-width="2" marker-end="url(#ar)" color="#3f77c2"/>
  <text x="200" y="160" text-anchor="middle" font-size="11" fill="#3f77c2">才艺文名 → 长辈·文书</text>
  <text x="360" y="175" font-size="13" font-weight="600">父母宫</text>
  <!-- 忌 -->
  <circle cx="70" cy="215" r="0"/>
  <text x="70" y="220" text-anchor="middle" font-size="15" font-weight="700" fill="#b23b3b">文昌</text>
  <line x1="98" y1="215" x2="300" y2="215" stroke="#b23b3b" stroke-width="2" stroke-dasharray="5 3" marker-end="url(#ar)" color="#b23b3b"/>
  <text x="200" y="230" text-anchor="middle" font-size="11" fill="#b23b3b">文书契约的执念 → 平辈</text>
  <text x="360" y="220" font-size="13" font-weight="600" fill="#b23b3b">兄弟宫（化忌）</text>
</svg>
</div>
```

**变体建议**：飞宫式（源/目标都是宫，圆换方框）；大限四化第二组（并列两组、灰化本命组）；流向汇聚（多源指向同一宫时目标节点加大并计数）。

---

### P10 · 状态流转图（有向状态机）

**适用场景**：四态流转（Ch1：主轴↔暗层↔回圈↔抓取）、任何 3–5 节点的状态循环/退行/回归结构。

**坐标计算公式**：

- 菱形布局四节点：上 `(230,55)`、右 `(370,160)`、左 `(90,160)`、下 `(230,270)`；节点用 `<ellipse>` rx 76–95 / ry 32–34（rx 随文字长度取值）。
- 节点配色语义：健康态绿、暗层蓝、回圈金、谷底红；`fill` 同色 opacity 0.13–0.18 + `stroke` 全色，节点内两行字（13px 态名 + 9.5px 小注）。
- 边：二次贝塞尔 `M {源边缘} Q {控制点} {目标边缘}`，控制点取两点中垂线外侧 30–50px 制造弧度；普通边灰 1.2px，**回归边（最重要的一条）绿 2px 虚线 + 文字注**。
- 边端点取节点椭圆边缘（中心 + rx/ry 方向偏移），不从中心出发。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 460 320" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
  <defs>
    <marker id="{chartid}-ah" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#8a8a8a"/></marker>
    <marker id="{chartid}-ahg" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#4a8b5c"/></marker>
  </defs>
  <ellipse cx="230" cy="55" rx="95" ry="34" fill="#4a8b5c" opacity="0.14" stroke="#4a8b5c" stroke-width="1.5"/>
  <text x="230" y="50" font-family="STSong,serif" font-size="13" fill="#1a1a1a" text-anchor="middle">{健康态名}</text>
  <text x="230" y="68" font-family="sans-serif" font-size="10" fill="#4a8b5c" text-anchor="middle">{小注}</text>
  <!-- …… 右/左/下 三节点同构，各换色 …… -->
  <path d="M 300 78 Q 355 105 365 128" fill="none" stroke="#8a8a8a" stroke-width="1.2" marker-end="url(#{chartid}-ah)"/>
  <!-- …… 其余滑落边 …… -->
  <path d="M 230 232 L 230 96" fill="none" stroke="#4a8b5c" stroke-width="2" stroke-dasharray="6,3" marker-end="url(#{chartid}-ahg)"/>
  <text x="240" y="150" font-family="STSong,serif" font-size="10.5" fill="#4a8b5c" text-anchor="start">{回归路径名}</text>
  <text x="240" y="165" font-family="sans-serif" font-size="9" fill="#4a8b5c" text-anchor="start">最短路：{具体行为}</text>
</svg>
```

**已验证实例**（案例A · Ch1 四态流转图）：

```html
<div class="chart-container">
  <p class="chart-title">四态流转图 · 主轴 ↔ 暗层 ↔ 回圈 ↔ 抓取</p>
  <svg viewBox="0 0 460 320" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
    <!-- 四态节点 -->
    <!-- 健康主轴（顶部中央，绿） -->
    <ellipse cx="230" cy="55" rx="95" ry="34" fill="#4a8b5c" opacity="0.14" stroke="#4a8b5c" stroke-width="1.5"/>
    <text x="230" y="50" font-family="STSong,serif" font-size="13" fill="#1a1a1a" text-anchor="middle">健康 Fi-Ne 态</text>
    <text x="230" y="68" font-family="sans-serif" font-size="10" fill="#4a8b5c" text-anchor="middle">主轴 · 深湖诗人</text>
    <!-- 暗层 Ni-Fe（右，蓝） -->
    <ellipse cx="370" cy="160" rx="78" ry="32" fill="#2c5f7c" opacity="0.13" stroke="#2c5f7c" stroke-width="1.5"/>
    <text x="370" y="155" font-family="STSong,serif" font-size="12.5" fill="#1a1a1a" text-anchor="middle">暗层 Ni-Fe 态</text>
    <text x="370" y="172" font-family="sans-serif" font-size="9.5" fill="#2c5f7c" text-anchor="middle">预言者/维护者</text>
    <!-- Si 回圈 loop（左，金） -->
    <ellipse cx="90" cy="160" rx="76" ry="32" fill="#d4a574" opacity="0.18" stroke="#c8963c" stroke-width="1.5"/>
    <text x="90" y="155" font-family="STSong,serif" font-size="12.5" fill="#1a1a1a" text-anchor="middle">Si 回圈态</text>
    <text x="90" y="172" font-family="sans-serif" font-size="9.5" fill="#c8963c" text-anchor="middle">Fi-Si 反刍 loop</text>
    <!-- Te-grip（底部中央，红） -->
    <ellipse cx="230" cy="270" rx="92" ry="34" fill="#8a1a1a" opacity="0.13" stroke="#8a1a1a" stroke-width="1.5"/>
    <text x="230" y="265" font-family="STSong,serif" font-size="13" fill="#1a1a1a" text-anchor="middle">Te-grip 态</text>
    <text x="230" y="283" font-family="sans-serif" font-size="10" fill="#8a1a1a" text-anchor="middle">效率屠刀 · 谷底</text>
    <!-- 箭头：主轴→各态（滑落）与回归 -->
    <defs>
      <marker id="ah" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#8a8a8a"/></marker>
      <marker id="ahg" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#4a8b5c"/></marker>
    </defs>
    <!-- 主轴 → 暗层 -->
    <path d="M 300 78 Q 355 105 365 128" fill="none" stroke="#8a8a8a" stroke-width="1.2" marker-end="url(#ah)"/>
    <!-- 主轴 → 回圈 -->
    <path d="M 160 78 Q 105 105 95 128" fill="none" stroke="#8a8a8a" stroke-width="1.2" marker-end="url(#ah)"/>
    <!-- 回圈 → grip（恶化） -->
    <path d="M 108 190 Q 150 245 165 258" fill="none" stroke="#8a8a8a" stroke-width="1.2" marker-end="url(#ah)"/>
    <!-- 暗层 → grip（过载崩落） -->
    <path d="M 352 190 Q 310 245 295 258" fill="none" stroke="#8a8a8a" stroke-width="1.2" marker-end="url(#ah)"/>
    <!-- grip → 主轴（复原·最短路，绿粗） -->
    <path d="M 230 232 L 230 96" fill="none" stroke="#4a8b5c" stroke-width="2" stroke-dasharray="6,3" marker-end="url(#ahg)"/>
    <text x="240" y="150" font-family="STSong,serif" font-size="10.5" fill="#4a8b5c" text-anchor="start">回归主轴</text>
    <text x="240" y="165" font-family="sans-serif" font-size="9" fill="#4a8b5c" text-anchor="start">最短路：身体节律</text>
  </svg>
</div>
```

**变体建议**：三节点三角布局 / 五节点五边形布局（顶点角均分）；边上标注触发条件（「压力 >阈值」）；与 P04 组合成「结构 + 时间」双图。

---

## 四、时间类

### P11 · 多轨时间轴（带当前位置标记）

**适用场景**：大运时间轴（Ch2）、大限时间轴（Ch3）、双轨/四轨总时间线（Ch6 锚点图）、感情演化时间轴（Ch7）。本模式是全书出场率最高的模式（案例A版 4 张）。

**坐标计算公式**：

- 年龄 → x 线性映射：`x(age) = x0 + (age − a0) / (a1 − a0) × (x1 − x0)`。
  - 单轨节点式（大运/大限）：等距节点即可，第 k 步 `x = 45 + k × 55`。
  - 多轨块式（双轨总览）：区段矩形 `x = x(起始年龄)`，`width = x(结束) − x(起始)`；案例A版 4–54 岁映射到 x 70–660（每 10 年 120px）。
- **当前位置标记**（本模式的灵魂，缺了必改）：竖虚线贯穿全部轨道 + `▼ 现在 · {年份} · {岁数}` 文字；单轨式用加大红节点 + `★`。
- 多轨 y 布局：每轨一行「轨名（12px 加粗，轨色）+ 一排区段矩形（height 26, rx 4）」，行距 65；当前区段矩形用轨色高亮（fill 加深 + stroke 加粗 1.2），非当前区段 `fill:#f3f1ec; stroke:#d5d2c8`。
- 轨色语义：性格轨蓝 `#2c5f7c`、八字轨红 `#8a1a1a`、紫微轨绿 `#4a8b5c`、占星轨金 `#d4a574`（占星轨事件是点不是段，用 circle + 文字）。

**SVG 骨架模板**（双轨/四轨总览版）：

```html
<svg viewBox="0 0 680 300" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;width:100%;">
  <!-- 年龄刻度行 -->
  <g font-size="11" fill="#8a8a8a" text-anchor="middle">
    <text x="{x(a0)}" y="20">{a0}</text><!-- …… 每 10 岁一档 …… -->
  </g>
  <line x1="40" y1="28" x2="670" y2="28" stroke="#d5d2c8" stroke-width="0.5"/>
  <!-- 当前位置竖线（贯穿所有轨道） -->
  <g>
    <line x1="{x(now)}" y1="28" x2="{x(now)}" y2="280" stroke="#8a1a1a" stroke-width="1" stroke-dasharray="4 3"/>
    <text x="{x(now)}" y="296" font-size="11" fill="#8a1a1a" text-anchor="middle">▼ 现在 · {年份} 年 · {岁数} 岁</text>
  </g>
  <!-- 轨道 N（性格轨在最上——性格本位铁律） -->
  <text x="40" y="{轨y-7}" font-size="12" fill="{轨色}" font-weight="600">{轨名}</text>
  <g font-size="11" text-anchor="middle">
    <rect x="{x起}" y="{轨y}" width="{宽}" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="{中点}" y="{轨y+17}" fill="#1a1a1a">{区段标签}</text>
    <!-- 当前区段：fill="rgba({轨色rgb},0.18)" stroke="{轨色}" stroke-width="1.2" -->
    <!-- …… 每轨 4-6 段 …… -->
  </g>
  <!-- 事件点轨（占星行运）：circle + 下方文字 -->
</svg>
```

**已验证实例 A**（案例A · Ch6 双轨时间线 4–53 岁总览——锚点六图之一：性格轨在上、八字/紫微/占星三轨在下、▼ 当前位置贯穿）：

```html
<div class="chart-container">
<p class="chart-title">双轨时间线 · 4-53 岁总览（▼ = 当前位置 24 岁）</p>
<svg viewBox="0 0 680 300" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;width:100%;">
  <!-- 年龄刻度 -->
  <g font-size="11" fill="#8a8a8a" text-anchor="middle">
    <text x="70" y="20">4</text><text x="190" y="20">14</text><text x="310" y="20">24</text><text x="430" y="20">34</text><text x="550" y="20">44</text><text x="660" y="20">54</text>
  </g>
  <line x1="40" y1="28" x2="670" y2="28" stroke="#d5d2c8" stroke-width="0.5"/>
  <!-- 当前位置标记 24岁+2.6年 ≈ x=310+31 -->
  <g>
    <line x1="341" y1="28" x2="341" y2="280" stroke="#8a1a1a" stroke-width="1" stroke-dasharray="4 3"/>
    <text x="341" y="296" font-size="11" fill="#8a1a1a" text-anchor="middle">▼ 现在 · 2026 年 · 24 岁</text>
  </g>
  <!-- 轨道1 性格发展 -->
  <text x="40" y="55" font-size="12" fill="#2c5f7c" font-weight="600">性格轨</text>
  <g>
    <rect x="70" y="62" width="120" height="26" rx="4" fill="rgba(44,95,124,0.15)" stroke="#2c5f7c" stroke-width="0.8"/>
    <text x="130" y="79" font-size="11" fill="#1a1a1a" text-anchor="middle">Fi 主导确立</text>
    <rect x="190" y="62" width="120" height="26" rx="4" fill="rgba(44,95,124,0.25)" stroke="#2c5f7c" stroke-width="0.8"/>
    <text x="250" y="79" font-size="11" fill="#1a1a1a" text-anchor="middle">Ne 辅助扩张</text>
    <rect x="310" y="62" width="120" height="26" rx="4" fill="rgba(74,139,92,0.3)" stroke="#4a8b5c" stroke-width="1.2"/>
    <text x="370" y="79" font-size="11" fill="#1a1a1a" text-anchor="middle">Si 觉醒·Te 起步</text>
    <rect x="430" y="62" width="120" height="26" rx="4" fill="rgba(212,165,116,0.35)" stroke="#d4a574" stroke-width="0.8"/>
    <text x="490" y="79" font-size="11" fill="#1a1a1a" text-anchor="middle">Te 整合·个体化下半场</text>
    <rect x="550" y="62" width="110" height="26" rx="4" fill="rgba(138,26,26,0.15)" stroke="#b85c5c" stroke-width="0.8"/>
    <text x="605" y="79" font-size="11" fill="#1a1a1a" text-anchor="middle">阴影和解·Self</text>
  </g>
  <!-- 轨道2 八字大运 -->
  <text x="40" y="120" font-size="12" fill="#8a1a1a" font-weight="600">八字轨</text>
  <g font-size="11" text-anchor="middle">
    <rect x="70" y="127" width="120" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="130" y="144" fill="#1a1a1a">庚子 · 偏财/正官</text>
    <rect x="190" y="127" width="120" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="250" y="144" fill="#1a1a1a">辛丑 · 正财/伤官库</text>
    <rect x="310" y="127" width="120" height="26" rx="4" fill="rgba(138,26,26,0.12)" stroke="#8a1a1a" stroke-width="1.2"/>
    <text x="370" y="144" fill="#1a1a1a">壬寅 · 七杀+甲木入局</text>
    <rect x="430" y="127" width="120" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="490" y="144" fill="#1a1a1a">癸卯 · 正官/正印</text>
    <rect x="550" y="127" width="110" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="605" y="144" fill="#1a1a1a">甲辰 · 偏印透干</text>
  </g>
  <!-- 轨道3 紫微大限 -->
  <text x="40" y="185" font-size="12" fill="#4a8b5c" font-weight="600">紫微轨</text>
  <g font-size="11" text-anchor="middle">
    <rect x="70" y="192" width="120" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="130" y="209" fill="#1a1a1a">命宫限 · 乙未</text>
    <rect x="190" y="192" width="120" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="250" y="209" fill="#1a1a1a">父母限 · 丙申</text>
    <rect x="310" y="192" width="120" height="26" rx="4" fill="rgba(74,139,92,0.18)" stroke="#4a8b5c" stroke-width="1.2"/>
    <text x="370" y="209" fill="#1a1a1a">福德限 · 丁酉</text>
    <rect x="430" y="192" width="120" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="490" y="209" fill="#1a1a1a">田宅限 · 戊戌</text>
    <rect x="550" y="192" width="110" height="26" rx="4" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="605" y="209" fill="#1a1a1a">官禄限 · 己亥</text>
  </g>
  <!-- 轨道4 占星行运 -->
  <text x="40" y="250" font-size="12" fill="#d4a574" font-weight="600">占星轨</text>
  <g font-size="11" text-anchor="middle">
    <circle cx="370" cy="262" r="4" fill="#d4a574"/>
    <text x="370" y="280" fill="#5a5a5a">土星回归 ≈2030-31</text>
    <circle cx="250" cy="262" r="3.5" fill="#b85c5c"/>
    <text x="250" y="280" fill="#5a5a5a">冥王过水瓶群星 2024-40s</text>
    <circle cx="490" cy="262" r="3.5" fill="#8a8a8a"/>
    <text x="490" y="280" fill="#5a5a5a">天王对分 ≈2043</text>
  </g>
</svg>
</div>
```

**已验证实例 B**（案例A · 图 2-4 大运时间轴——单轨节点式，★ 当前大运加大加色、节点色编码喜忌）：

```html
<div class="chart-container">
    <div class="chart-title">图 2-4 · 大运时间轴（★为当前所处大运）</div>
    <svg viewBox="0 0 480 170" width="100%" role="img" aria-label="大运时间轴">
      <line x1="20" y1="60" x2="460" y2="60" stroke="currentColor" stroke-opacity="0.4"/>
      <!-- 8 steps -->
      <g font-size="11" fill="currentColor" text-anchor="middle">
        <!-- 庚子 -->
        <circle cx="45" cy="60" r="6" fill="#a0aec0"/><text x="45" y="42">庚子</text><text x="45" y="82" font-size="9">4-13</text>
        <!-- 辛丑 -->
        <circle cx="100" cy="60" r="6" fill="#a0aec0"/><text x="100" y="42">辛丑</text><text x="100" y="82" font-size="9">14-23</text>
        <!-- 壬寅 当前 -->
        <circle cx="155" cy="60" r="10" fill="#c53030" stroke="#742a2a" stroke-width="2"/><text x="155" y="38" font-weight="bold">壬寅★</text><text x="155" y="84" font-size="9" font-weight="bold">24-33</text><text x="155" y="96" font-size="8">← 24岁 现在</text>
        <!-- 癸卯 -->
        <circle cx="210" cy="60" r="6" fill="#2f855a"/><text x="210" y="42">癸卯</text><text x="210" y="82" font-size="9">34-43</text>
        <!-- 甲辰 -->
        <circle cx="265" cy="60" r="7" fill="#2f855a"/><text x="265" y="42">甲辰</text><text x="265" y="82" font-size="9">44-53</text>
        <!-- 乙巳 -->
        <circle cx="320" cy="60" r="7" fill="#2f855a"/><text x="320" y="42">乙巳</text><text x="320" y="82" font-size="9">54-63</text>
        <!-- 丙午 -->
        <circle cx="375" cy="60" r="7" fill="#c53030"/><text x="375" y="42">丙午</text><text x="375" y="82" font-size="9">64-73</text>
        <!-- 丁未 -->
        <circle cx="430" cy="60" r="6" fill="#c53030"/><text x="430" y="42">丁未</text><text x="430" y="82" font-size="9">74-83</text>
      </g>
      <text x="240" y="130" font-size="11" fill="currentColor" text-anchor="middle" opacity="0.85">早年金水（庚子辛丑）压抑 → 中年木火（癸卯甲辰乙巳丙午）补身补印，渐入佳境</text>
      <text x="240" y="150" font-size="10" fill="currentColor" text-anchor="middle" opacity="0.6">绿=喜用木运　红=喜用火运　灰=忌神金水运</text>
    </svg>
  </div>
```

**已验证实例 C**（案例A · 图 7-5 感情演化时间轴——三段色块 + 每段下方「性格：…／玄学：…」双行注释 + 底部主线总结条，是 P11 信息密度最高的变体）：

```html
<div class="chart-container">
    <div class="chart-title">图 7-5 · 感情演化时间轴（24–35 岁）</div>
    <svg viewBox="0 0 760 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="感情演化三阶段时间轴">
      <!-- 主轴 -->
      <line x1="60" y1="60" x2="700" y2="60" stroke="#8a7a5c" stroke-width="2"/>
      <!-- 刻度 -->
      <g font-size="12" fill="#6b5d45" text-anchor="middle">
        <line x1="60" y1="54" x2="60" y2="66" stroke="#8a7a5c" stroke-width="2"/>
        <text x="60" y="46">24岁</text>
        <line x1="273" y1="54" x2="273" y2="66" stroke="#8a7a5c" stroke-width="2"/>
        <text x="273" y="46">28岁</text>
        <line x1="486" y1="54" x2="486" y2="66" stroke="#8a7a5c" stroke-width="2"/>
        <text x="486" y="46">32岁</text>
        <line x1="700" y1="54" x2="700" y2="66" stroke="#8a7a5c" stroke-width="2"/>
        <text x="700" y="46">35岁</text>
      </g>
      <!-- 三段色块 -->
      <rect x="60" y="70" width="213" height="26" rx="4" fill="#b7d0c9" opacity="0.85"/>
      <rect x="273" y="70" width="213" height="26" rx="4" fill="#e3c9a0" opacity="0.85"/>
      <rect x="486" y="70" width="214" height="26" rx="4" fill="#d3b5c9" opacity="0.85"/>
      <g font-size="13" fill="#3d3527" text-anchor="middle" font-weight="bold">
        <text x="166" y="88">辅助 Ne 扩张期</text>
        <text x="379" y="88">Si 觉醒期</text>
        <text x="593" y="88">Te 整合启动期</text>
      </g>
      <!-- 段一说明 -->
      <g font-size="11.5" fill="#3d3527">
        <text x="70" y="128">性格：辅助 Ne 向外发散，</text>
        <text x="70" y="146">情感探索、多种可能并存；</text>
        <text x="70" y="164">阿尼姆斯"行动/英雄"投射高峰</text>
        <text x="70" y="188" fill="#7a5a3a">玄学：壬寅大运七杀活跃</text>
        <text x="70" y="206" fill="#7a5a3a">（感情剧场主窗口）</text>
      </g>
      <!-- 段二说明 -->
      <g font-size="11.5" fill="#3d3527">
        <text x="283" y="128">性格：Si-Child 开始整合，</text>
        <text x="283" y="146">渴望稳定、仪式、根基，</text>
        <text x="283" y="164">从"心动"转向"想安顿"</text>
        <text x="283" y="188" fill="#7a5a3a">玄学：土星回归 28–30</text>
        <text x="283" y="206" fill="#7a5a3a">（承诺评估期）</text>
      </g>
      <!-- 段三说明 -->
      <g font-size="11.5" fill="#3d3527">
        <text x="496" y="128">性格：劣势 Te 自我开发，</text>
        <text x="496" y="146">停止把人生规划外包，</text>
        <text x="496" y="164">阿尼姆斯向"言说"升级</text>
        <text x="496" y="188" fill="#7a5a3a">玄学：临近癸卯正官运</text>
        <text x="496" y="206" fill="#7a5a3a">（承诺落地窗口前段）</text>
      </g>
      <!-- 底部主题条 -->
      <rect x="60" y="240" width="640" height="60" rx="6" fill="#f2ece0" stroke="#cdbfa3"/>
      <text x="380" y="264" font-size="12.5" fill="#5a4d38" text-anchor="middle" font-weight="bold">主线：从「被击中」到「想安顿」到「自己长出地图」</text>
      <text x="380" y="286" font-size="11.5" fill="#6b5d45" text-anchor="middle">性格走多远，感情走多远；玄学只标注每一幕最容易发生的成长任务</text>
    </svg>
  </div>
```

**变体建议**：单轨 12 节点大限式（见案例A图三，与实例 B 同构）；时间轴 + 曲线叠加（P11+P12：区段做背景带、曲线画其上）；配 P08 双轨对照细表放图后（案例A Ch6 即如此配对）。

---

### P12 · 发展曲线（多线趋势）

**适用场景**：功能发展 0–24 岁（Ch1）、任何「多条强度随年龄演化」的趋势示意。数值是示意性的（相对形态正确即可），必须在图注声明「示意」。

**坐标计算公式**：

- x 轴（年龄）：`x = 60 + age / age_max × 370`（绘图区 x 60–430）。
- y 轴（强度 0–100 示意值）：`y = 250 − v / 100 × 210`（绘图区 y 40–250，基线 250）。
- 每条曲线一个 `<polyline>`，5–6 个采样点足够；特异曲线（如提前点亮的阴影功能）用 `stroke-dasharray="5,3"` 虚线并在图注点破。
- 阶段背景带：`<rect>` 淡色（opacity 0.05–0.12）分段铺底 + 顶部 9.5px 阶段名。
- 「今」标线：`x(当前年龄)` 竖虚线 + 顶部「今」字。
- 曲线端点标签放折线末端右侧（x=438），按末端 y 排布防重叠。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 460 300" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
  <!-- 阶段背景带 -->
  <rect x="{段起x}" y="40" width="{段宽}" height="210" fill="{阶段色}" opacity="0.06"/>
  <text x="{段中x}" y="54" font-family="sans-serif" font-size="9.5" fill="#8a8a8a" text-anchor="middle">{阶段名}</text>
  <!-- 坐标轴 + 年龄刻度 -->
  <line x1="60" y1="250" x2="430" y2="250" stroke="#a8a59a" stroke-width="0.8"/>
  <line x1="60" y1="40" x2="60" y2="250" stroke="#a8a59a" stroke-width="0.8"/>
  <g font-family="sans-serif" font-size="9" fill="#8a8a8a" text-anchor="middle">
    <text x="60" y="264">0</text><text x="245" y="264">{中点岁}</text><text x="430" y="264">{末岁} 岁</text>
  </g>
  <line x1="{x今}" y1="40" x2="{x今}" y2="250" stroke="#8a1a1a" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="{x今}" y="36" font-family="STSong,serif" font-size="10" fill="#8a1a1a" text-anchor="middle">今</text>
  <!-- 曲线（每功能一条 polyline，特异曲线虚线） -->
  <polyline points="{x0},{y0} {x1},{y1} {x2},{y2} {x3},{y3} {x4},{y4}" fill="none" stroke="{功能色}" stroke-width="2"/>
  <!-- 端点标签 -->
  <text x="438" y="{末端y}" font-family="STSong,serif" font-size="11" fill="{功能色}">{功能名}</text>
</svg>
```

**已验证实例**（案例A · Ch1 功能发展曲线 0–24 岁——Ni 虚线「异常陡升」即该命主的加码理由）：

```html
<div class="chart-container">
  <p class="chart-title">功能发展曲线 · 0–24 岁（强度示意）</p>
  <svg viewBox="0 0 460 300" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
    <!-- 阶段背景带 -->
    <rect x="60" y="40" width="185" height="210" fill="#8a1a1a" opacity="0.05"/>
    <rect x="245" y="40" width="123.3" height="210" fill="#4a8b5c" opacity="0.06"/>
    <rect x="368.3" y="40" width="61.7" height="210" fill="#d4a574" opacity="0.12"/>
    <g font-family="sans-serif" font-size="9.5" fill="#8a8a8a" text-anchor="middle">
      <text x="152" y="54">Fi 确立期</text>
      <text x="306" y="54">Ne 开窗期</text>
      <text x="399" y="54">Si 觉醒前夜</text>
    </g>
    <!-- 坐标轴 -->
    <line x1="60" y1="250" x2="430" y2="250" stroke="#a8a59a" stroke-width="0.8"/>
    <line x1="60" y1="40" x2="60" y2="250" stroke="#a8a59a" stroke-width="0.8"/>
    <g font-family="sans-serif" font-size="9" fill="#8a8a8a" text-anchor="middle">
      <text x="60" y="264">0</text><text x="152.5" y="264">6</text><text x="245" y="264">12</text>
      <text x="337.5" y="264">18</text><text x="430" y="264">24 岁</text>
    </g>
    <!-- 当下标线 -->
    <line x1="430" y1="40" x2="430" y2="250" stroke="#8a1a1a" stroke-width="1" stroke-dasharray="3,3"/>
    <text x="430" y="36" font-family="STSong,serif" font-size="10" fill="#8a1a1a" text-anchor="middle">今</text>
    <!-- 四条曲线 -->
    <polyline points="60,229 152.5,155.5 245,103 337.5,71.5 430,56.8" fill="none" stroke="#8a1a1a" stroke-width="2"/>
    <polyline points="60,233.2 152.5,208 245,155.5 337.5,107.2 430,86.2" fill="none" stroke="#4a8b5c" stroke-width="2"/>
    <polyline points="60,239.5 152.5,218.5 245,166 337.5,103 430,65.2" fill="none" stroke="#2c5f7c" stroke-width="2" stroke-dasharray="5,3"/>
    <polyline points="60,218.5 152.5,197.5 245,187 337.5,155.5 430,107.2" fill="none" stroke="#c8963c" stroke-width="2"/>
    <!-- 端点标签 -->
    <g font-family="STSong,serif" font-size="11">
      <text x="438" y="58" fill="#8a1a1a">Fi</text>
      <text x="438" y="88" fill="#4a8b5c">Ne</text>
      <text x="438" y="67" fill="#2c5f7c">Ni</text>
      <text x="438" y="110" fill="#c8963c">Si</text>
    </g>
  </svg>
  <p class="chart-data" style="font-size:12px;color:var(--text-secondary);text-align:center;margin-top:0.4rem;">
    Ni（蓝虚线）异常陡升，是你区别于典型 INFP 的曲线特征——阴影功能提前点亮
  </p>
</div>
```

**变体建议**：延伸到 60 岁的全程版（与 Ch6 呼应）；单功能聚焦版（一条主线 + 灰色参照线「典型同类型均线」）；与 P11 叠加。

---

## 五、关系类

### P13 · 矩阵热力表（评级矩阵）

**适用场景**：三维印证矩阵（Ch5 核心图）、功能互补配对表（Ch7）、任何「行要素 × 列维度 → 评级」结构。用 HTML 表格而非 SVG（文字量大）。

**结构公式**：

- 印证矩阵列序：性格签名要素 | 八字（解构）| 紫微（对应）| 占星（映照）| 印证度（★1–5）；行 = 性格签名的 5–7 个核心要素。要素格里放「要素名 + 一行小注 + `data-inline` 数值」；证词格一律「盘面事实——性格翻译」双段式。
- 配对表列序：伴侣类型 | A / C（吸引力/挑战度 ★）| 桥接机制 | 关系底色；最优组合行加 `class="highlight-row"`、警示组合行加 `class="warn-row"`（这两个 class 若未定义 CSS 也能安全渲染，仅失去底色；建议补 `tr.highlight-row td{background:rgba(74,139,92,0.07);} tr.warn-row td{background:rgba(138,26,26,0.07);}`）。
- 星级一律实体字符 ★☆（不依赖图形），满 5 星制。

**HTML 骨架模板**（印证矩阵版）：

```html
<table class="chart-data">
<tr><th>性格签名要素</th><th>八字（解构）</th><th>紫微（对应）</th><th>占星（映照）</th><th>印证度</th></tr>
<tr>
  <td><strong>{要素名}</strong><br>{一行小注} <span class="data-inline">{数值}</span></td>
  <td>{八字盘面事实}——{性格翻译}</td>
  <td>{紫微盘面事实}——{性格翻译}</td>
  <td>{占星盘面事实}——{性格翻译}</td>
  <td>★★★★★</td>
</tr>
<!-- …… 5-7 行 …… -->
</table>
```

**已验证实例 A**（案例A · Ch5 三维印证度矩阵——v4 判定 Gate 的核心证据图）：

```html
<div class="chart-container">
<p class="chart-title">三维印证度矩阵 · 性格签名要素 × 玄学证词</p>
<table class="chart-data">
<tr><th>性格签名要素</th><th>八字（解构）</th><th>紫微（对应）</th><th>占星（映照）</th><th>印证度</th></tr>
<tr><td><strong>Fi 主导</strong><br>内在价值罗盘 <span class="data-inline">FiA 24.8</span></td><td>丙火失令于亥月——太阳之火收进深冬，光向内烧</td><td>命宫无正曜、借太阴庙——以内在月光为主调</td><td>太阳射手落 12 宫——生命力藏在最内向的宫位</td><td>★★★★★</td></tr>
<tr><td><strong>Ne 辅助</strong><br>场域直觉 <span class="data-inline">NeB 16.6</span></td><td>月干己土伤官吐秀——才华以温和方式外泄</td><td>身宫天机巨门、巨门化禄——以智识深挖安身</td><td>水星射手合太阳——发散式远方思维</td><td>★★★★☆</td></tr>
<tr><td><strong>Ni/Fe 暗层</strong><br>「深层预言者」 <span class="data-inline">NiB 21.5 · FeH 18.6</span></td><td>时干壬水七杀透——深水在命局里常年在场</td><td>借对宫太阳化权——外相带 Fe 的公共光</td><td>太阳合冥王、六合海王——洞察与消融并存</td><td>★★★★★</td></tr>
<tr><td><strong>Te 劣势</strong><br>终身课题 <span class="data-inline">TeA 10.6</span></td><td>木仅 <span class="data-inline">7.5%</span> 最枯，调候甲木待补——结构性生扶缺位</td><td>兄弟宫文昌化忌、福德宫思辨过载——落地环节最涩</td><td>太阳对冲土星（差 5.0°）——理想与现实的正面拉扯</td><td>★★★★★</td></tr>
<tr><td><strong>关系模式</strong><br>深湖之爱（Fi）</td><td>七杀独透而官星不显——感情认「强度」不认「形式」</td><td>夫妻宫天梁——年长者/庇护者型剧场</td><td>金星天蝎 25° 四分火星——极端忠诚 × 独立留白的张力</td><td>★★★★☆</td></tr>
<tr><td><strong>节奏曲线</strong><br>Si 觉醒 → Te 整合</td><td>壬寅大运（24-33）甲木偏印入局——调候应期已开</td><td>丁酉大限（24-33）走福德宫——精神整备的十年</td><td>土星回归（约 2030-31，土星双子）——成年礼节点</td><td>★★★★★</td></tr>
</table>
</div>
```

**已验证实例 B**（案例A · 图 7-2 功能互补配对表——highlight/warn 行手法）：

```html
<div class="chart-container">
    <div class="chart-title">图 7-2 · INFP 视角的功能互补配对表（A=吸引力 / C=挑战度，满分 5★）</div>
    <table class="chart-data">
      <thead>
        <tr><th>伴侣类型</th><th>A / C</th><th>桥接机制</th><th>关系底色</th></tr>
      </thead>
      <tbody>
        <tr class="highlight-row">
          <td><strong>ENTJ</strong></td>
          <td>5★ / 4★</td>
          <td>Te-Fi 对位桥接（最深也最伤）</td>
          <td>「价值与帝国」——他给她"价值能变成现实"的证明，她给他"为什么要建帝国"的内核</td>
        </tr>
        <tr class="highlight-row">
          <td><strong>ENFJ</strong></td>
          <td>4★ / 3★</td>
          <td>Fe-dom 温暖包裹 Fi 深度</td>
          <td>被稳稳接住的温柔，气氛由对方主动维护，缓解她的 Fe 耗竭</td>
        </tr>
        <tr>
          <td><strong>INTJ</strong></td>
          <td>4★ / 4★</td>
          <td>Ni-Te 提供愿景与执行链</td>
          <td>安静的深度共鸣 + 强确定感；但两人都需主动破冰</td>
        </tr>
        <tr>
          <td><strong>ENTP</strong></td>
          <td>4★ / 3★</td>
          <td>Ne 对 Ne 的思想烟花</td>
          <td>永不无聊的对话，激活她的辅助 Ne；稳定性需另建</td>
        </tr>
        <tr>
          <td><strong>INFJ</strong></td>
          <td>4★ / 3★</td>
          <td>Ni-Fe 与 Fi-Ne 的灵魂相认</td>
          <td>初期极易"一眼千年"，深而温，但都偏内倾、需引入共同体验</td>
        </tr>
        <tr class="warn-row">
          <td><strong>ESTJ</strong></td>
          <td>2★ / 5★</td>
          <td>Fi-Te 直接相斥（主导互为劣势）</td>
          <td>「价值碰撞」——全书唯一需要标红的高消耗组合，除非双方都已走过 35+ 的劣势整合期，否则易互相摧毁</td>
        </tr>
      </tbody>
    </table>
  </div>
```

**变体建议**：单元格底色随星级加深（inline style 五档 rgba）；列可换成「大运 × 领域」应期矩阵；行末加「分歧披露」列对接判官报告（E 组证据）。

---

### P14 · 跷跷板/天平（对轴失衡）

**适用场景**：判断轴/感知轴失衡（Ch1）、任何「一对功能/能量的强弱对比 + 失衡方向」。比条形图多传达一层「杠杆感」。

**坐标计算公式**（已对案例A实例反向验证）：

- 每轴一组：支点三角 `polygon "{cx},{cy} {cx-12},{cy+38} {cx+12},{cy+38}"`，cx=230，各轴 cy = 90 / 200 / 310（行距 110）。
- 倾角：`α = k × (w左 − w右)`，`k ≈ 2°/单位分差`，建议 clamp 在 ±18°；重端下沉。
- 杠杆端点（半长 L=160）：左端 `(cx − L·cos α, cy + L·sin α)`，右端 `(cx + L·cos α, cy − L·sin α)`（α 取正 = 左重左沉）。
- 端点圆半径 `r ≈ 0.7 × 强度值`（视觉权重双编码：位置 + 大小）；轻端 opacity 0.55–0.75。
- 每端配两个标签：圆内功能缩写（白字 9–10px）、圆外侧「功能 数值」（12px，重端用功能色）。
- 轴下方 11px 灰字轴名 + 语义注（「价值秤 ↓ 效率屠刀 ↑」式）；特异轴（如双端皆重）支点换红色、线加粗并 ★ 标注。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 460 370" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
  <!-- 每轴一组（示例为一组，行距 110 复制） -->
  <polygon points="230,{cy} 218,{cy+38} 242,{cy+38}" fill="#a8a59a"/>
  <line x1="{左x}" y1="{左y}" x2="{右x}" y2="{右y}" stroke="#5a5a5a" stroke-width="3" stroke-linecap="round"/>
  <circle cx="{左x}" cy="{左y}" r="{0.7×左值}" fill="{左功能色}"/>
  <circle cx="{右x}" cy="{右y}" r="{0.7×右值}" fill="{右功能色}" opacity="0.75"/>
  <g font-family="STSong,serif" font-size="12" fill="#1a1a1a">
    <text x="{左x}" y="{左y+3.5}" text-anchor="middle" fill="#fff" font-size="10">{左缩写}</text>
    <text x="{右x}" y="{右y+3.5}" text-anchor="middle" fill="#fff" font-size="9">{右缩写}</text>
    <text x="{左外x}" y="{左外y}" text-anchor="middle" fill="{左功能色}">{左功能} {左值}</text>
    <text x="{右外x}" y="{右外y}" text-anchor="middle" fill="#5a5a5a">{右功能} {右值}</text>
    <text x="230" y="{cy+62}" text-anchor="middle" font-size="11" fill="#5a5a5a">{轴名} · {左语义} ↓ {右语义} ↑</text>
  </g>
</svg>
```

**已验证实例**（案例A · Ch1 三轴跷跷板——第三轴「双端皆重」的特异表达值得细看）：

```html
<div class="chart-container">
  <p class="chart-title">三轴跷跷板 · 判断轴 / 感知轴 / 明亮阴影轴</p>
  <svg viewBox="0 0 460 370" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
    <!-- 判断轴 Fi-Te，cy=90，左Fi重下沉 -->
    <polygon points="230,90 218,128 242,128" fill="#a8a59a"/>
    <line x1="74.8" y1="128.7" x2="385.2" y2="51.3" stroke="#5a5a5a" stroke-width="3" stroke-linecap="round"/>
    <circle cx="74.8" cy="128.7" r="14" fill="#8a1a1a"/>
    <circle cx="385.2" cy="51.3" r="8" fill="#c8963c" opacity="0.75"/>
    <g font-family="STSong,serif" font-size="12" fill="#1a1a1a">
      <text x="74.8" y="132" text-anchor="middle" fill="#fff" font-size="10">Fi</text>
      <text x="385.2" y="54.5" text-anchor="middle" fill="#fff" font-size="9">Te</text>
      <text x="40" y="150" text-anchor="middle" fill="#8a1a1a">Fi 19.6</text>
      <text x="415" y="45" text-anchor="middle" fill="#5a5a5a">Te 11.8</text>
      <text x="230" y="152" text-anchor="middle" font-size="11" fill="#5a5a5a">判断轴 · 价值秤 ↓ 效率屠刀 ↑</text>
    </g>
    <!-- 感知轴 Ne-Si，cy=200，左Ne略重 -->
    <polygon points="230,200 218,238 242,238" fill="#a8a59a"/>
    <line x1="70.9" y1="216.7" x2="389.1" y2="183.3" stroke="#5a5a5a" stroke-width="3" stroke-linecap="round"/>
    <circle cx="70.9" cy="216.7" r="12.1" fill="#4a8b5c"/>
    <circle cx="389.1" cy="183.3" r="10.4" fill="#4a8b5c" opacity="0.55"/>
    <g font-family="STSong,serif" font-size="12" fill="#1a1a1a">
      <text x="70.9" y="220" text-anchor="middle" fill="#fff" font-size="9">Ne</text>
      <text x="389.1" y="186.5" text-anchor="middle" fill="#fff" font-size="9">Si</text>
      <text x="38" y="240" text-anchor="middle" fill="#4a8b5c">Ne 17.4</text>
      <text x="418" y="178" text-anchor="middle" fill="#4a8b5c">Si 14.8</text>
      <text x="230" y="262" text-anchor="middle" font-size="11" fill="#5a5a5a">感知轴 · 可能星空 ↓ 经验之根 ↑（接近平衡）</text>
    </g>
    <!-- 明亮阴影轴 Ni-Fe，cy=310，双端皆重 -->
    <polygon points="230,310 218,348 242,348" fill="#8a1a1a"/>
    <line x1="70.4" y1="326.2" x2="389.6" y2="293.8" stroke="#2c5f7c" stroke-width="3.5" stroke-linecap="round"/>
    <circle cx="70.4" cy="326.2" r="13.8" fill="#2c5f7c"/>
    <circle cx="389.6" cy="293.8" r="12.3" fill="#2c5f7c" opacity="0.65"/>
    <g font-family="STSong,serif" font-size="12" fill="#1a1a1a">
      <text x="70.4" y="329.5" text-anchor="middle" fill="#fff" font-size="9">Ni</text>
      <text x="389.6" y="297" text-anchor="middle" fill="#fff" font-size="9">Fe</text>
      <text x="36" y="349" text-anchor="middle" fill="#2c5f7c">Ni 19.8</text>
      <text x="418" y="289" text-anchor="middle" fill="#2c5f7c">Fe 17.5</text>
      <text x="230" y="368" text-anchor="middle" font-size="11" fill="#8a1a1a">★明亮阴影轴 · 两端同时压满，抢主轴带宽</text>
    </g>
  </svg>
</div>
```

**变体建议**：单轴放大版（配长图注深写一对张力）；五行生克天平（两行五行力量对峙）；合盘版（我方功能 vs 对方功能同轴对置）。

---

### P15 · 会照关系图（三方四正）

**适用场景**：夫妻宫三方四正会照（Ch7）、命宫三方四正、任何「本宫 + 对宫 + 两三合宫」的会照结构。

**已验证形态是表格**（案例A版用 `table.chart-data` 呈现，见下）；SVG 关系图骨架为 v4 新给（**未经案例A版实测，首次使用必须过 C4 渲染健康检查**）。

**坐标计算公式**（SVG 版）：

- 四宫菱形布局：本宫下 `(230,300)`、对宫上 `(230,60)`、三合左 `(60,180)`、三合右 `(400,180)`；每宫一个圆角矩形（width 150 / height 56 / rx 6），中心对齐上述坐标。
- 连线：本宫—对宫竖直实线（对照关系最强，2px）；本宫—两三合宫斜线（1.2px）；线中点放关系标签（「对照」「三合」小字带白底 rect 垫底防穿线）。
- 宫内三行：宫名+地支（13px 加粗）、主星+亮度（12px，主星用 `--accent`）、关键辅星（10px 灰）。
- 本宫描边用 `--accent` 加粗，其余宫 `--border`。

**SVG 骨架模板**（v4 新给，待首用验证）：

```html
<svg viewBox="0 0 460 360" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;max-width:100%;width:100%;">
  <!-- 连线（先画线后画框，框压线） -->
  <line x1="230" y1="88" x2="230" y2="272" stroke="#8a1a1a" stroke-width="2"/>
  <line x1="135" y1="192" x2="180" y2="285" stroke="#a8a59a" stroke-width="1.2"/>
  <line x1="325" y1="192" x2="280" y2="285" stroke="#a8a59a" stroke-width="1.2"/>
  <rect x="205" y="170" width="50" height="16" fill="#fafaf8"/>
  <text x="230" y="182" font-size="10" fill="#8a1a1a" text-anchor="middle">对照</text>
  <!-- 四宫框：本宫（下，红描边）/ 对宫（上）/ 三合 ×2（左右） -->
  <g font-family="STSong, Songti SC, serif" text-anchor="middle">
    <rect x="155" y="272" width="150" height="60" rx="6" fill="rgba(138,26,26,0.06)" stroke="#8a1a1a" stroke-width="1.5"/>
    <text x="230" y="292" font-size="13" font-weight="600" fill="#1a1a1a">{本宫名}（{支}）</text>
    <text x="230" y="308" font-size="12" fill="#8a1a1a">{主星}<tspan font-size="9">{亮度}</tspan>{ + 关键星}</text>
    <text x="230" y="322" font-size="10" fill="#8a8a8a">{辅星清单}</text>
    <rect x="155" y="32" width="150" height="56" rx="6" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="230" y="52" font-size="13" fill="#1a1a1a">{对宫名}（{支}）</text>
    <text x="230" y="68" font-size="12" fill="#8a1a1a">{主星}</text>
    <text x="230" y="81" font-size="10" fill="#8a8a8a">{辅星}</text>
    <rect x="10" y="152" width="150" height="56" rx="6" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="85" y="172" font-size="13" fill="#1a1a1a">{三合宫A}（{支}）</text>
    <text x="85" y="188" font-size="12" fill="#8a1a1a">{主星}</text>
    <text x="85" y="201" font-size="10" fill="#8a8a8a">{辅星}</text>
    <rect x="300" y="152" width="150" height="56" rx="6" fill="#f3f1ec" stroke="#d5d2c8"/>
    <text x="375" y="172" font-size="13" fill="#1a1a1a">{三合宫B}（{支}）</text>
    <text x="375" y="188" font-size="12" fill="#8a1a1a">{主星}</text>
    <text x="375" y="201" font-size="10" fill="#8a8a8a">{辅星}</text>
  </g>
</svg>
```

**已验证实例**（案例A · 图 7-4 夫妻宫三方四正会照——表格形态，「宫位 | 星曜 | 对感情舞台的作用」三列，第三列承担性格翻译）：

```html
<div class="chart-container">
    <div class="chart-title">图 7-4 · 夫妻宫（巳）三方四正会照</div>
    <table class="chart-data">
      <thead>
        <tr><th>宫位</th><th>星曜</th><th>对感情舞台的作用</th></tr>
      </thead>
      <tbody>
        <tr><td>夫妻宫（本宫·巳）</td><td>天梁（平）+ 空亡 + 凤阁天福</td><td>成熟荫庇型伴侣；晚成、重精神；凤阁天福添一分文雅与福气</td></tr>
        <tr><td>官禄宫（对宫·亥）</td><td>天同（旺）+ 天马</td><td>天同福星旺照 → 关系温和、有情趣、不喜争斗；天马 → 缘分带流动、异地或晚动之象</td></tr>
        <tr><td>福德宫（三合·酉）</td><td>禄存</td><td>禄存会照 → 关系里衣食无忧、有物质托底的安稳</td></tr>
        <tr><td>迁移宫（三合·丑）</td><td>太阳化权 + 太阴（庙）+ 左辅右弼</td><td>日月双美 + 左右贵人夹 → 伴侣有内外兼备的潜质、且有贵人牵引之力</td></tr>
      </tbody>
    </table>
  </div>
```

**变体建议**：SVG 图 + 表格双件套（图给结构、表给解读）；在 P06 十二宫盘上直接给三方四正四格加描边（成本最低的替代方案）；大限夫妻宫叠加版。

---

### P16 · 双轮对照（合盘 · 从 P07 派生）

> **标注**：本模式无案例A版现成实例（案例A命书为单人命书）。以下骨架与公式从 P07 派生，逻辑经 P07 实例反向验证，但**成图未经浏览器实测**——首次用于合盘命书时必须通过 locked-checklist C4 渲染健康检查，并把实测通过的成品回填本节（施工备注：待第一个合盘案例）。

**适用场景**：双人合盘（synastry）总览图：内轮 = 命主 A 行星，外轮 = 命主 B 行星，中央画关键跨盘相位线。

**坐标计算公式**：

- 沿用 P07 的角度公式，**两人共用同一参考系（命主 A 的 ASC 在正左）**：`offset = (λ − λ_ASC_A) mod 360`，`x = cx − r·cos(offset°)`，`y = cy + r·sin(offset°)`；cx=cy=230（viewBox 460×460）。
- 半径分层：星座环 190→165（分界刻度同 P07）；**B 行星带 r=150**（外轮，符号加 B 色）；**A 行星带 r=105**（内轮）；相位线区 r<85，行星点向内引 2px 短刻度线到 r=85 锚点。
- 跨盘相位线：只画紧密相位（偏差 <3°，最多 8 条防糊）：两端点为 A、B 行星各自在 r=85 圆上的锚点；合相不画线改用外侧弧括注；对冲/四分红（`#b23b3b`，四分虚线）、三合/六合蓝（`#3f77c2`，六合虚线）。
- A/B 配色：A 行星深色（`#2a2a3a` 系，同 P07），B 行星统一换紫褐（`#7a5c9e`）并在图例声明；A 的 ASC/MC 轴照 P07 画，B 的 ASC 只画一根外缘短粗刻度 + 「B-ASC」小标。

**SVG 骨架模板**：

```html
<svg viewBox="0 0 460 460" width="100%" style="max-width:460px;display:block;margin:0 auto" font-family="serif" aria-label="双人合盘双轮对照">
  <!-- 三圈：星座环外缘/内缘 + 相位区边界 -->
  <circle cx="230" cy="230" r="190" fill="none" stroke="#b08d57" stroke-width="1.5"/>
  <circle cx="230" cy="230" r="165" fill="none" stroke="#b08d57" stroke-width="0.8" opacity="0.6"/>
  <circle cx="230" cy="230" r="85" fill="none" stroke="#b08d57" stroke-width="0.6" opacity="0.4"/>
  <!-- 12 星座分界刻度（r 190→165，同 P07 公式） -->
  <g stroke="#c9b48a" stroke-width="0.6" opacity="0.7">
    <line x1="{x@190}" y1="{y@190}" x2="{x@165}" y2="{y@165}"/><!-- ×12 -->
  </g>
  <!-- A 的 ASC-DSC / MC-IC 轴（r=165→85） -->
  <text x="28" y="227" font-size="10" fill="#7a5c9e" font-weight="bold">A-ASC</text>
  <!-- B 的 ASC 外缘刻度 -->
  <line x1="{Bascx@190}" y1="{Bascy@190}" x2="{Bascx@176}" y2="{Bascy@176}" stroke="#7a5c9e" stroke-width="2"/>
  <text x="{Basc标x}" y="{Basc标y}" font-size="8" fill="#7a5c9e">B-ASC</text>
  <!-- B 行星（外轮 r=150，紫褐） -->
  <g font-size="14" fill="#7a5c9e" text-anchor="middle">
    <text x="{B☉x}" y="{B☉y}">☉</text><!-- …… B 各星 …… -->
  </g>
  <!-- A 行星（内轮 r=105，深色系同 P07） -->
  <g font-size="14" fill="#2a2a3a" text-anchor="middle">
    <text x="{A☉x}" y="{A☉y}" fill="#c0392b">☉</text><!-- …… A 各星 …… -->
  </g>
  <!-- 跨盘紧密相位线（两端为 r=85 锚点，≤8 条） -->
  <g stroke-width="1">
    <line x1="{A锚x}" y1="{A锚y}" x2="{B锚x}" y2="{B锚y}" stroke="#b23b3b"/>
    <line x1="{…}" y1="{…}" x2="{…}" y2="{…}" stroke="#3f77c2" stroke-dasharray="4 3"/>
  </g>
  <text x="230" y="234" font-size="8" fill="#b08d57" text-anchor="middle">{A名} × {B名}</text>
  <text x="230" y="452" font-size="8" fill="#999" text-anchor="middle">内轮 {A名} · 外轮 {B名} · 红=张力相位 蓝=和谐相位 · 以 {A名} 上升为参考系</text>
</svg>
```

**变体建议**：组合盘（composite，中点法算一套「关系盘」再直接用 P07 画）；双轮 + P13 跨盘相位矩阵表配对（图给总览、表给逐条 A行星×B行星 评级）；三轨 P11 感情时间轴（A 性格轨 + B 性格轨 + 共同玄学应期轨）。

---

## 六、图表规划表 schema（V4_PLAN §3.2 · chart-director 运行时契约）

图表规划表经 task I/O 传递（不落盘），markdown 表格式：

```
| 图表 ID | 章节 | 标题 | 模式(可组合) | 数据来源字段 | 必配/加码 | 加码理由 |
|:---|:---|:---|:---|:---|:---|:---|
| chart-1-1 | Ch1 | 认知功能强度·八轴雷达 | P01 | jung_calc.function_stack | 必配（锚点） | — |
| chart-1-5 | Ch1 | 功能发展曲线 0-24 岁 | P12 | jung_calc.development_curve | 加码 | Ni 阴影功能异常陡升，值一张专图 |
```

- **图表 ID**：`chart-{章号}-{序号}`，book-writer 落 HTML 时写入 `data-chart-id` 属性，validate_book.py 逐行核销（locked-checklist C1）。
- **模式**：本库 P01–P16 的 ID；组合写 `P11+P12`；新变体写 `新变体：{一句话说明}`。
- **数据来源字段**：指向 cast_chart.py / jung_calc.py 输出 JSON 的具体字段，或 S3–S6 素材的具体小节——禁止「见上文」式模糊引用。
- **必配/加码**：锚点六图与配额内图标「必配」；配额之上标「加码」且**加码理由必填**（特殊格局、交界上升、从格、异常 Grip、空宫借星、双聚簇等）。

## 七、配额下限表（写入 SKILL.md + locked-checklist C2/C3）

| 章节 | 下限 | 案例A版实绩（参照） |
|:---|:---|:---|
| Ch1 性格画像 | ≥ 6 | 7（雷达/亚型条形/Beebe环/跷跷板/发展曲线/Grip弧线/四态流转） |
| Ch2 八字解构 | ≥ 4 | 4（四柱全表/五行权重/十神分布/大运时间轴） |
| Ch3 紫微对应 | ≥ 4 | 6（十二宫盘/四化流向/3张宫位表/大限时间轴） |
| Ch4 占星映照 | ≥ 4 | 4（星盘轮/元素模式条形/行星落座表/相位全表） |
| Ch5 印证评估 + Ch6 双轨时间线 | 合计 ≥ 3 | 4（判官披露表/印证矩阵/双轨时间线/双轨细表） |
| Ch7 感情专题 | ≥ 4 | 5（三维印证表/配对表/应期标注表/会照表/演化时间轴） |
| Ch8 终极课题 | ≥ 1 | 1（五条路径靶点与应期总览表） |
| **全书** | **≥ 26，上不封顶** | 31 个 chart-container |

计数口径：按 `data-chart-id` 容器计数；表格（`table.chart-data` 外层带 chart-container）与 SVG 同权计入。

## 八、锚点六图（任何命书必有，缺一即 locked-checklist M 组 fail）

| # | 图 | 模式 | 章 | 本库参照实例 |
|:---|:---|:---|:---|:---|
| 1 | 八维雷达 | P01 | Ch1 | 案例A Ch1 雷达 |
| 2 | 四柱全表 | P08 | Ch2 | 案例A 图 2-1 |
| 3 | 五行权重 | P02 | Ch2 | 案例A 图 2-2 |
| 4 | 十二宫命盘 | P06 | Ch3 | 案例A 图一 |
| 5 | 星盘轮 | P07 | Ch4 | 案例A 图 4-1 |
| 6 | 双轨时间线 | P11 | Ch6 | 案例A Ch6 双轨总览 |

## 九、组合与发明授权条款

本库不是围栏，是地基。对 chart-director 与 book-writer 的正式授权：

1. **允许模式叠加**：任何 P01–P16 可组合（如 P11+P12 时间轴叠曲线、P06+P15 命盘上加会照描边、P07+相位线、P13+星级底色），组合体在图表规划表「模式」列如实登记（`P11+P12`）。
2. **允许发明新变体**：素材里出现本库未覆盖的可视化事实（新格局、新结构、新对照关系）时，**应当**发明新图，而不是硬套旧模式或放弃可视化。新变体在规划表登记为 `新变体：{说明}`。
3. **唯一硬约束**：每张图（无论沿用、组合还是发明）都必须——
   - 登记进图表规划表并带 `data-chart-id`（locked-checklist C1）；
   - 通过 C4 渲染健康检查：SVG 语法合法、viewBox 存在、含 ≥1 个非空绘图元素、polygon points 非退化、无外链资源；
   - 遵守本文件第〇节通用容器规范（容器/标题/图注/配色 token/唯一 marker id）。
4. **回填义务**：发明的新变体若实测渲染通过且效果好，终审后由 memory 归档流程记一条到 `memory/`，供下版本吸收进本库。

> 定调：模式库保下限，规划表保数量，发明权保上限——三者合起来，图表既不会漏，也不会平庸。
