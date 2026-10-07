# 图表模式库（v5.3）：P01–P17

图表是书里的插图：回答一个具体问题，用的是真实可追溯的资料，比正文或一张简表更容易看懂。先想清楚这张图要让读者看见什么，再选模式。版式变量、字体与类名见 `output-template.md` §3–§5。

## 1. 共用结构

```html
<figure class="chart-container" data-chart-id="chart-<section_id>-01" data-representation="computed">
  <figcaption id="chart-x-caption">图题：这张图在说什么</figcaption>
  <p class="chart-description" id="chart-x-desc">一两句话说明怎么看这张图，线型与颜色各指什么。</p>
  <div class="chart-scroll" role="region" tabindex="0" aria-labelledby="chart-x-caption" aria-describedby="chart-x-desc">
    <svg role="img" aria-labelledby="chart-x-caption" aria-describedby="chart-x-desc" viewBox="0 0 640 320" xmlns="http://www.w3.org/2000/svg">…</svg>
  </div>
  <div class="chart-scroll" role="region" tabindex="0" aria-label="图中数据">
    <table class="chart-data">
      <caption>图中数据</caption>
      <thead><tr><th scope="col">项目</th><th scope="col" class="num">值</th></tr></thead>
      <tbody><tr><th scope="row">合成项目</th><td data-value-ref="fixture#/values/item" data-value="12" data-unit="分" data-precision="0">12分</td></tr></tbody>
    </table>
  </div>
  <p class="chart-note">来源与单位。</p>
</figure>
```

- `data-chart-id` 为 `chart-<section_id>-<两位序号>`，全书唯一，与 `chart_plan.chart_table` 一一对应。图号（“图 2-1”）由样式按章自动生成，图题里不写编号。
- `data-representation` 取 `measured`、`computed` 或 `qualitative`。数值从输入或计算产物绑定：`data-value-ref`、`data-value`、`data-unit`、`data-precision` 四项齐全，可见文字与之一致。
- 每张图都有一张读者可读的数据表或逐项文字；图形与长表各放一个 `.chart-scroll`，图形不拆页，长表可以跨页。
- 缺值按 `omit_with_disclosure`：写明缺了什么，不补零、不插值、不闭合雷达。定性图在图题或图注标“概念示意”，只画有依据的类别与关系。
- `chart_table.limits` 属审计层，不写进图注。

## 2. 统一视觉

全书图表看上去出自同一只手：

| 项目 | 规定 |
|---|---|
| 画布 | SVG 用 `viewBox`，宽度随栏宽伸缩；常规图 `viewBox` 宽 640，屏幕栏宽 640px 时约 1:1 |
| 底色 | 不铺底色、不加外框；图上下各一条线由 `figure` 样式给出 |
| 线宽 | 网格与刻度 0.75；结构线（宫线、轴线以外的框线）1；数据线 1.5–2；强调线（四轴、当前标记）1.75–2.5 |
| 线色 | 网格与结构线 `#8c826e`；轴与主框 `#211d18`；纯装饰分隔 `#d8d0bf`（不承载信息） |
| 数据色 | 依次取黛蓝 `#2e4a62`、朱砂 `#9b2d23`、松绿 `#3b5d4a`、赭石 `#7d5a24`；一张图不超过四色 |
| 区分方式 | 颜色之外必有第二种区分：线型（实线／虚线 `7 5`）、标记形状（圆／方）或文字标签 |
| 数据点 | 圆点半径 4.5；方点边长 8 |
| 图内文字 | 黑体（`--sans`），标签 15、次要标注 14（`viewBox` 单位）；盘面大字与星座名用宋体；不用小于 14 的字 |
| 文字压线 | 标签落在线上时加纸色描边：`stroke="#faf7f0" stroke-width="4" paint-order="stroke"` |
| 横条 | 用 `.bar-list`：条高 10px，左端一条墨色零线，轨道是一条细线；数值右对齐 |
| 图题与图注 | 图题黑体加粗在上，朱砂图号在前；说明在图题下；图注在图的最下方，写来源、单位、宫制或量程 |

字号以渲染后的实际大小为准：屏幕上图内文字不小于 12px，PDF 里不小于 9pt。窄屏保留最小画布（常规图 600px）并在 `.chart-scroll` 内横滑，不把图压小。打印时需要占满版心的图加 `is-wide`。

## 3. 模式索引

| ID | 模式 | 用在哪里 | 表达边界 |
|---|---|---|---|
| P01 | 雷达图 | 完整且同量程的多维数值 | 任一维缺值就改用表格 |
| P02 | 分组条形图 | 同构类别的数值比较；五行比例 | 写明量程、单位、零点；五行只画一组共零点横条 |
| P03 | 并列／堆叠条形图 | 同尺度下的构成或组间比较 | 构成完整且可比才堆叠 |
| P04 | 定性过程示意 | 非量化的过程或阶段关系 | 标“概念示意”，不加刻度 |
| P05 | 同心层级／原型关系图 | 理论里的分类与位置 | 面积、半径不表示强度 |
| P06 | 紫微十二宫盘 | 十二宫盘面与宫位关系 | 见 §4 |
| P07 | 占星星盘 | 行星、轴点、宫始与黄道位置 | 见 §4 |
| P08 | 结构化数据表；四柱盘 | 精确多字段、相位、排盘明细 | 标来源、单位；长表可跨页 |
| P09 | 有向关系图 | 少量有来源的源→目标关系 | 每条边有依据；箭头只表示所定义的方向 |
| P10 | 状态关系图 | 离散状态与它们之间的转移 | 非观测过程标“概念示意” |
| P11 | 多轨时间轴 | 端点明确的周期区间 | 时间语义不同就分面板 |
| P12 | 多线序列图 | 有逐时点数据的数值趋势 | 没有逐点数据就不画曲线 |
| P13 | 关系矩阵表 | 多体系围绕同一主题的质性对照 | 不转成数字、星级或总分 |
| P14 | 成对对照图 | 同量纲的两项对照 | 同时给出原始值 |
| P15 | 关系网络图 | 盘面或文本中有定义的结构连接 | 只画已核关系 |
| P16 | 双人双轮对照 | 同图展示双方的星体位置 | 双方数据分色分表；不出总分 |
| P17 | 亚型哑铃图 | subtypes16 同一功能两端的原始分 | 缺一端只画已知端点 |

## 4. 三张核心盘面图

三张图都由 `scripts/book_html.py` 渲染，命令见 `output-template.md` §5。下面是它们的画法，供核对与局部调整。

### P08 · 四柱盘

语义表格 `table.chart-data.pillar-chart`，列为年柱、月柱、日柱、时柱，行自上而下：天干十神、天干、地支、藏干（有则列）、藏干十神、纳音。

- 天干、地支是宋体粗体大字（屏幕 40px，打印 24pt），按五行着色，字下写出五行。
- 日干下有朱砂框标签“日主”，月支下有“月令”；日柱整列浅底。
- 四柱盘不设最小宽度，320px 屏宽下整表可见。
- 同一张图里接着放五行分布：`.bar-list` 五行各一条，数值绑定 `/dimensions/bazi/data/五行比例/<五行>`，说明里写“共用零点，满宽 100%”，图注写明这是固定权重下的统计比例。
- 大运、流年等明细另列普通数据表，字段回链 `/dimensions/bazi/data/…`。

### P06 · 紫微十二宫盘

`div.ziwei-grid` 是 4×4 网格，外围十二格按地支固定位置，中心 2×2 为盘心：

| 巳 | 午 | 未 | 申 |
|---|---|---|---|
| 辰 | 盘心 | 盘心 | 酉 |
| 卯 | 盘心 | 盘心 | 戌 |
| 寅 | 丑 | 子 | 亥 |

- 每格自上而下：主星（宋体粗体 17px，后附亮度小字，生年四化为朱砂框“化禄／化权／化科／化忌”）；辅星一行；格底左侧宫名，右侧大限岁数与宫干支。
- 命宫整格朱砂内框，宫名朱底反白；身宫在宫名旁加墨色框“身宫”。两者都有文字，不靠颜色单独表达。
- 空宫写“空宫”，不补星；借对宫的读法在正文里讲。
- 盘心写盘名、五行局、命主、身主，并画命宫三方四正：命宫与两个三合宫连成朱砂实线三角，命宫到对宫一条墨色虚线。各宫在盘心边框上的锚点（0–100 坐标）：巳 (0,0)、午 (25,0)、未 (75,0)、申 (100,0)、酉 (100,25)、戌 (100,75)、亥 (100,100)、子 (75,100)、丑 (25,100)、寅 (0,100)、卯 (0,75)、辰 (0,25)。
- 辅星多到一格放不下时用 `--no-minor`，辅星改列在图下的线性表里。
- DOM 顺序从命宫起按宫序排列，位置由 `data-branch` 决定，读屏与 PDF 文字顺序因此是“命宫、兄弟、夫妻……”。
- 屏幕最小宽 600px，在 `.chart-scroll` 内横滑；打印占满版心，格内文字 10pt、主星 12pt。
- 图下的线性表逐宫列出干支、主星、辅星、大限，大限岁数绑定 `/dimensions/ziwei/data/十二宫/<N>/大限/范围/<0|1>`。

### P07 · 占星星盘

SVG `viewBox="0 0 720 720"`，圆心 (360,360)。上升点在正左，黄经逆时针增加：黄经 λ 的点在半径 r 处的坐标为 `x = 360 − r·cos(λ−ASC)`，`y = 360 + r·sin(λ−ASC)`。

| 圈层 | 半径 | 内容 |
|---|---|---|
| 黄道带 | 264–300 | 浅底；每 30° 一条分界线；星座名两字宋体 15，居中于各宫 15° 处；每 10° 一道小刻度 |
| 星体区 | 184–264 | 星体在 264 圈内侧画一道 9 长的短线标出真实位置；名称（黑体加粗 15）与宫内度分（14）上下两行，中心在半径 222 |
| 宫位环 | 158–184 | 宫位数字 14，放在相邻两条宫始线的中点 |
| 相位区 | 158 以内 | 相位弦线，端点在 158 圈上 |

- 宫始线按真实宫始黄经从 158 画到 264，线宽 0.75。四轴（上升—下降、天顶—天底）线宽 1.75，从 158 画到 310，轴名写在圈外半径 332 处。天顶按实际黄经放置。
- 标签排开：星体密集时，标签沿圆周推开到互不重叠，顺序不变，用一条细引线连回真实位置。所需间隔随位置变化——左右两侧按标签高度（约 11°），上下两端按标签宽度（约 16°）。
- 相位：三合、六合画黛蓝实线；四分、对冲画朱砂虚线；线宽 1.5。合相由相邻位置表达，不画线。只画正文讨论的相位，一般不超过六条，其余留在相位表。说明里写明两种线各指什么。
- 逆行的星体在度分后加“逆”字。
- 屏幕最小宽 620px；打印宽 176mm，图内最小字约 10pt。
- 图下的位置表逐星列出星座与度分、宫位、黄经，黄经绑定 `/dimensions/astrology/data/十大行星+北交+凯龙+莉莉丝/<星体>/黄经`。图注写宫制；时刻精度与星历放附录。
- 缺真实宫始或必要坐标时，渲染器报错退出，改用位置表与相位表。

## 5. 其余模式的画法

### P01 · 雷达图

全部维度真实存在、定义相同、量程一致时使用。中心 `(cx,cy)`、最大半径 `R`：`r = (v − min)/(max − min) × R`；第 `i` 轴角度 `θᵢ = θ₀ + i × 360°/n`；`xᵢ = cx + r sin θᵢ`，`yᵢ = cy − r cos θᵢ`。坐标取 `chart_data.py radar` 的输出。网格圈 0.75 线，数据多边形黛蓝 1.75 线、不填色或填 8% 透明度。

### P02 · 分组条形图

比较定义、单位、量程一致的数值，用 `.bar-list`。标签写清统计方式（“固定权重下的元素比例”），排序规则写在说明里。同一组原值只画一次。

### P03 · 并列／堆叠条形图

并列条各自按 P02 映射。堆叠段长 `wⱼ = vⱼ/总量 × W`，用于互斥且总量有意义的构成。不同体系的数值不归一化后并排。

### P04 · 定性过程示意

节点、箭头加文字，讲一个理论过程或次序。节点用 1 线宽的圆角矩形，箭头 1.5。节点说不清规则来源时改用文字。

### P05 · 同心层级／原型关系图

表示理论角色或分类层级，每个区域标出理论来源并配文字表。只需列出类别时用表格。荣格八功能的位置（主导、辅助、第三、劣势与阴影四位）适合这一式。

### P09 · 有向关系图

节点是有定义的实体或字段，边上标关系类型（生、克、合、冲、飞化）。图下列边表与来源。关系多到标签拥挤时改表。

### P10 · 状态关系图

节点是命名明确的离散状态，连线是有记录的转移或理论中写明的关系。线的粗细不表示频率。

### P11 · 多轨时间轴

区间端点与时间语义都明确时使用。八字用 `大运[].起始公历年`、`终止公历年`；紫微用 `十二宫[].大限.范围`。语义一致才共轴；否则上下两个 `.timeline-panel`，各带 `.timeline-panel-title`（“八字大运：公历年”“紫微大限：虚岁”）。区间画成 14 高的细框条，当前区间用朱砂 2 线宽描边并加文字“当前”；当前标记只取计算输出。刻度取 `chart_data.py timeline` 的输出，精度不超过输入粒度。面板最小宽 600px，图内文字屏幕 14px、打印 9.5pt。

### P12 · 多线序列图

每条线的点 `(t,v)` 回链源字段，标明单位、时间范围、缺失点。每条线末端直接写标签，不另设图例。

### P13 · 关系矩阵表

综合章里的精简对照表，列为“主题／各体系怎么读／汇聚或分歧”。多个体系落到同一处时直接写出来。它是普通语义 `<table>`，不登记进 `chart_table`（`chart_table.data_refs` 至少要有一项数值绑定，纯定性矩阵满足不了）；每行用 `data-claim-ids` 回链已登记的 synthesis claims。

### P14 · 成对对照图

两端同构同量纲时用点线图：`x = x₀ + (v−min)/(max−min) × W`。图下并列原始值与量表定义。定性观点的对照用双栏文字。

### P15 · 关系网络图

每个节点与连边对应可查的盘面或文本关系，图例说明关系类型。配一张可线性阅读的关系表。

### P16 · 双人双轮对照

两组独立输入各自计算。内圈一方、外圈一方，星体名前加称呼首字区分；双方数据分别绑定各自 artifact，图下各列一张位置表。一方资料不足时只画可用的一层，并写明缺什么。

### P17 · 亚型哑铃图

用于 `subtypes16` 原始分：同一功能两端共用量程，标原始分与有符号差。坐标取 `chart_data.py dumbbell --pairs … --min 0 --max …`。左端黛蓝圆点，右端朱砂方点，连线 2 线宽黛蓝；缺一端时只画已知端点，不连线、不算差。每行行高 56，标签写在点的上方（左端）与下方（右端），避免互相压住。完整 `functions8` 用 P02 横条。

```html
<figure class="chart-container" data-chart-id="chart-personality-02" data-representation="measured">
  <figcaption id="chart-personality-02-caption">两个亚型的原始分（量程 0–30 分）</figcaption>
  <p class="chart-description" id="chart-personality-02-desc">圆点是左端，方点是右端；连线表示同一功能两项分数之差。</p>
  <div class="chart-scroll" role="region" tabindex="0" aria-labelledby="chart-personality-02-caption" aria-describedby="chart-personality-02-desc">
    <svg role="img" aria-labelledby="chart-personality-02-caption" aria-describedby="chart-personality-02-desc" viewBox="0 0 640 100" xmlns="http://www.w3.org/2000/svg">
      <line x1="120" y1="50" x2="600" y2="50" stroke="#8c826e" stroke-width="0.75" />
      <line x1="{xL}" y1="50" x2="{xR}" y2="50" stroke="#2e4a62" stroke-width="2" />
      <circle cx="{xL}" cy="50" r="4.5" fill="#2e4a62" />
      <rect x="{xR-4}" y="46" width="8" height="8" fill="#9b2d23" />
      <text x="40" y="55" font-size="15" fill="#211d18">Ti</text>
      <text x="{xL}" y="34" font-size="14" fill="#211d18" text-anchor="middle">TiA 10</text>
      <text x="{xR}" y="76" font-size="14" fill="#211d18" text-anchor="middle">TiH 12</text>
    </svg>
  </div>
  <div class="chart-scroll" role="region" tabindex="0" aria-label="原始分数据">
    <table class="chart-data">
      <caption>原始分（量程 0–30 分）</caption>
      <thead><tr><th scope="col">功能</th><th scope="col" class="num">左端</th><th scope="col" class="num">右端</th><th scope="col" class="num">两端分差</th></tr></thead>
      <tbody><tr><th scope="row">Ti</th><td data-value-ref="synthetic-case#/personality_input/scores/TiA" data-value="10" data-unit="分" data-precision="0">TiA 10分</td><td data-value-ref="synthetic-case#/personality_input/scores/TiH" data-value="12" data-unit="分" data-precision="0">TiH 12分</td><td data-value-ref="synthetic-case#/derived/Ti_delta" data-value="2" data-unit="分" data-precision="0">+2分</td></tr></tbody>
    </table>
  </div>
  <p class="chart-note">合成示例。</p>
</figure>
```

## 6. 红线与核对

图表里同样守全书红线：不画健康、寿命、生育一类的推断；不画事件概率、运势曲线、关系匹配分、成功率；不把传统象义或偏好分数画成能力高低或实测能量。五行比例称“该统计方式下的元素分布”。

落图前核对来源字段、单位、量程、缺值处理、图表 ID 与章节归属。落图后核对 SVG 是合法 XML、`id` 不重复、坐标有限且图形不退化、说明与数据表同步。最后在桌面、390px 窄屏和实际 PDF 上各看一遍：文字读得清，线条分得开，表格没有被裁切。
