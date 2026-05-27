---
name: xiaohongshu-cards
description: "小红书图文卡片制作工具。将文章、方法论、知识点等内容转化为适合小红书发布的精美卡片图组。核心能力：(1) 内容分析与卡片规划——从源文档提炼核心信息，规划卡片数量和内容分配 (2) Notion 风格设计系统——白底、Callout 块、Emoji 图标、大字排版 (3) HTML→PNG 精确渲染——Playwright 截图，1080×1440px（3:4 小红书标准比例）(4) 视觉 QA 闭环——渲染后检查溢出、填充率、字号，自动修复 (5) 内容审查——对照源文件验证准确性，防止信息失真 (6) PDF 合并输出——所有卡片合并为单 PDF 便于预览和分享。触发词：小红书图、小红书卡片、做小红书、制图、卡片图、红书图文、xiaohongshu cards。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [xiaohongshu, image-generation, design, content-creation, social-media]
---

# 小红书图文卡片制作

## 变量

```
SKILL_DIR    = ~/.hermes/skills/xiaohongshu-cards  (或 jz-skills/shared/xiaohongshu-cards)
SCRIPTS_DIR  = $SKILL_DIR/scripts
THEME_CSS    = $SCRIPTS_DIR/notion-theme.css
RENDERER     = $SCRIPTS_DIR/generate-slides.mjs
```

## 依赖

- **Playwright**: `npm install playwright && npx playwright install chromium`
- **Pillow** (PDF 合并): `pip3 install Pillow`
- **Google Fonts**: Noto Sans SC（HTML 中通过 CDN 引入，需联网）

---

## 工作流程（7 步）

### Step 1: 分析源内容 & 确认需求

读取用户提供的源文件（Markdown / 文本 / 主题描述）。

用 `clarify` 确认：

| 确认项 | 说明 | 默认值 |
|--------|------|--------|
| 卡片数量 | 根据内容量建议 8-15 张 | 按内容自动推荐 |
| 风格主题 | notion / minimal / dark | notion |
| 目标受众 | 决定语言深度和专业术语 | 通用 |
| 输出目录 | 卡片和 PDF 存放位置 | `~/Downloads/{主题名}-小红书图/` |

**卡片数量参考：**
- 短文/单主题: 6-8 张
- 中篇/方法论: 10-12 张
- 长文/完整体系: 12-15 张

### Step 2: 规划卡片大纲

输出大纲表格供用户确认：

```
| # | 卡片标题 | 内容要点 | 类型 |
|---|---------|---------|------|
| 01 | 封面 | 主标题 + 副标题 + 标签 | cover |
| 02 | 核心发现 | 关键数据对比 | content |
| ... | ... | ... | ... |
| NN | 封底 | 总结金句 + CTA | back-cover |
```

**卡片类型：**
- `cover` — 封面（居中排版，大标题，标签）
- `content` — 内容页（标题 + 正文 + callout 块）
- `data` — 数据页（数字指标 + 对比卡片）
- `grid` — 网格页（2×3 或 2×2 卡片阵列）
- `steps` — 步骤页（编号列表 + 说明）
- `comparison` — 对比页（左右对比，红/绿色块）
- `back-cover` — 封底（居中金句 + 总结）

### Step 3: 编写 slides.html

在输出目录创建 `slides.html`。

**HTML 结构：**
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  /* 从 $THEME_CSS 复制完整 CSS */
</style>
</head>
<body>
  <!-- 每张卡片一个 .slide div -->
  <div class="slide" id="slide-01">...</div>
  <div class="slide" id="slide-02">...</div>
  ...
</body>
</html>
```

**必须遵守的规则：**

1. **每个 `.slide` 的 `id` 必须以 `slide-` 开头**，格式 `slide-NN` 或 `slide-NN-slug`
2. **画布固定 1080×1440px**，不可更改
3. **padding 固定 `50px 50px 46px`**，内容区实际 980×1344
4. **`overflow: hidden`** — 任何超出的内容会被裁切，必须在编写时控制内容量
5. **字号下限**：正文不小于 28px，标题不小于 34px。小红书在手机上看，字太小看不清

**CSS 类速查（Notion 主题）：**

| 类名 | 用途 | 字号 |
|------|------|------|
| `.t1` | 页面大标题 | 58px, 800 weight |
| `.t2` | 副标题/引导语 | 30px, 灰色 |
| `.t3` | 区块标题 | 34px, 700 weight |
| `.p` | 正文 | 32px |
| `.ps` | 正文（稍小） | 28px |
| `.pm` | 辅助说明 | 26px, 灰色 |
| `.b` | 加粗 | — |
| `.blue` `.green` `.red` `.purple` `.orange` | 颜色 | — |

| 类名 | 用途 | 说明 |
|------|------|------|
| `.co` | 灰色 Callout | 默认背景色块 |
| `.co-blue` `.co-green` `.co-red` `.co-yellow` `.co-purple` `.co-orange` | 彩色 Callout | 搭配 `.ic` emoji 图标 |
| `.card` | 边框卡片 | 白底+灰边框 |
| `.qt` | 引用块 | 左侧竖线 |
| `.tag` | 标签 | 圆角色块 |
| `.g2` | 两列网格 | 1fr 1fr |
| `.g3` | 三列网格 | 1fr 1fr 1fr |
| `.sn` | 编号圆块 | 蓝底白字 46px |
| `.met` | 大数字指标 | 54px, 800 weight |
| `.div` | 分隔线 | hr 替代 |

**Callout 用法示例：**
```html
<div class="co-blue">
  <div class="ic">💡</div>
  <div class="ps"><strong>核心观点：</strong>这里是内容文字</div>
</div>
```

**内容量控制经验法（关键！）：**
- 一页最多放 **3-4 个 callout 块**（含标题区域）
- 或 **1 个标题 + 1 个 card + 2 个 callout**
- 或 **1 个标题 + 6 格 grid**（每格 2-3 行文字）
- 封面/封底居中排版用 `style="justify-content:center; align-items:center;"`
- **写完后心算**：标题区约 120px，每个 callout 约 120-180px，card 约 200-400px，总和不超过 1344px

### Step 4: 渲染 PNG

```bash
node $SCRIPTS_DIR/generate-slides.mjs --dir <输出目录>
```

脚本自动：
1. 打开 slides.html
2. 等待字体加载（3 秒）
3. 遍历所有 `.slide` 元素逐个截图
4. 用 Pillow 合并为 PDF

输出文件：
```
<输出目录>/
├── slides.html
├── 01-slide-cover.png
├── 02-slide-xxx.png
├── ...
├── NN-slide-back-cover.png
└── <目录名>.pdf
```

### Step 5: 视觉 QA（必做！）

用 `vision_analyze` 逐张检查 PNG：

**检查清单（每张卡片）：**

- [ ] **底部无截断** — 内容没有被 overflow:hidden 裁切
- [ ] **填充率 ≥ 75%** — 没有大面积空白（尤其底部 1/3）
- [ ] **字号可读** — 最小字不小于 26px
- [ ] **标题醒目** — 每页有清晰的视觉层级
- [ ] **颜色和谐** — callout 颜色有语义（蓝=信息，绿=正面，红=警示，黄=注意，紫=强调）

**常见问题与修复：**

| 问题 | 原因 | 修复 |
|------|------|------|
| 底部文字截断 | 内容超出 1440px | 减少内容或拆分到下一页 |
| 大面积空白 | 内容不够 | 增加 callout、补充说明、加大字号 |
| 中间出现空洞 | flex 布局中有 `flex:1` | 去掉 `flex:1`，改用固定 margin |
| 视觉平淡 | 全是灰色 callout | 穿插 co-blue、co-green 等彩色块 |

**发现问题时直接修改 slides.html，然后重新渲染。**

### Step 6: 内容审查（有源文件时必做！）

如果卡片基于源文档制作，必须逐页比对：

**审查维度：**

1. **数据准确性** — 数字、百分比、引用来源与原文一致
2. **概念完整性** — 核心框架没有被简化到变形
3. **措辞精确性** — 关键限定词（"强制""客观""认为"等）没有被省略
4. **逻辑忠实性** — 因果关系、结论指向与原文一致
5. **来源可追溯** — 数据标注了出处或方便读者查证

**常见内容失真：**
- 主观自评数据被写成客观事实（"14.3%真正了解" vs "14.3%认为自己真正了解"）
- 结论丢失参照基线（"反而更差" vs "反而不如不用AI"）
- 限定词被省略（"非编程场景" 缺少领域限定）
- 框架结构被篡改（核心概念被替换为其他词）

### Step 7: 交付

输出文件清单和预览信息：
- PNG 数量和文件名
- PDF 路径
- 总文件大小
- 如有修复记录，列出修复清单

---

## 设计风格选项

### Notion（默认，推荐）
- 白底 `#FFFFFF`，浅灰块 `#F7F6F3`
- 文字色 `#37352F`，辅助色 `#787774`
- 6 色 Callout 系统（蓝/绿/红/黄/紫/橙）
- 6px 圆角，无阴影
- CSS 参考: `$THEME_CSS`

### Minimal
- 纯白底，无背景色块
- 仅用字号和字重区分层级
- 分隔线替代色块
- 适合文字密集、学术感内容

### Dark
- 深色底 `#191919`，浅色文字 `#E0E0E0`
- 色块改为半透明
- 适合科技感、酷炫风格

> 如需新增风格，在 `$SCRIPTS_DIR/` 下创建对应 CSS 文件，在 Step 3 引入即可。

---

## 封面/封底模板

### 封面模板
```html
<div class="slide" id="slide-01" style="justify-content:center; align-items:center;">
  <div style="text-align:center; width:100%;">
    <div style="margin-bottom:36px;">
      <span class="tag" style="background:var(--blue-bg); color:var(--blue); font-size:28px; padding:12px 32px;">标签</span>
    </div>
    <div style="font-size:120px; font-weight:900; color:var(--text); line-height:1.1; letter-spacing:-3px;">
      主标题
    </div>
    <div style="width:72px; height:5px; background:var(--blue); border-radius:3px; margin:36px auto;"></div>
    <div style="font-size:42px; font-weight:700; color:var(--blue); line-height:1.4; margin-bottom:40px;">
      副标题 · 关键词 · 关键词
    </div>
    <div class="co" style="display:inline-flex; padding:26px 48px;">
      <div class="ic">🎯</div>
      <div style="font-size:30px; color:var(--text);">一句话说明适用场景</div>
    </div>
    <div style="font-size:30px; color:var(--text2); margin-top:24px;">作者名</div>
    <div style="margin-top:16px;">
      <span class="tag" style="background:var(--bg2); color:var(--text2);">#标签1</span>
      <span class="tag" style="background:var(--bg2); color:var(--text2);">#标签2</span>
    </div>
  </div>
</div>
```

### 封底模板
```html
<div class="slide" id="slide-NN" style="justify-content:center; align-items:center;">
  <div style="text-align:center; width:100%;">
    <div style="font-size:84px; font-weight:900; color:var(--text); line-height:1.15; letter-spacing:-2px;">
      总结金句<br>第二行
    </div>
    <div style="width:64px; height:5px; background:var(--blue); border-radius:3px; margin:36px auto 40px;"></div>
    <div style="max-width:860px; margin:0 auto;">
      <div class="co-blue" style="padding:34px 40px; margin-bottom:18px; justify-content:center;">
        <div style="text-align:center; width:100%;">
          <div style="font-size:46px; font-weight:800; color:var(--blue);">❶ 第一点</div>
          <div style="font-size:28px; color:var(--text2); margin-top:10px;">解释说明</div>
        </div>
      </div>
      <!-- ❷ ❸ 同上格式 -->
    </div>
    <div style="margin-top:32px;">
      <div style="font-size:38px; font-weight:800; color:var(--text);">收尾金句</div>
    </div>
  </div>
</div>
```

---

## 常用内容页模式

### 模式 A: 标题 + Callout 列表（信息传达）
```
.t1 标题
.t2 副标题
.co-blue  核心观点
.co       补充信息 1
.co       补充信息 2
.co-green 正面总结
```

### 模式 B: 标题 + Card + Callout（结构化内容）
```
.t1 标题
.t2 副标题
.card {
  .t3 区块标题
  .sn 步骤 1 + 说明
  .sn 步骤 2 + 说明
  .sn 步骤 3 + 说明
  hr.div
  .ps 小结
}
.co-blue  关键提示
```

### 模式 C: 标题 + 2×3 Grid（多维度展示）
```
.t1 标题
.t2 副标题
.g2 {
  .co [emoji + 维度1 + 说明]
  .co [emoji + 维度2 + 说明]
  .co [emoji + 维度3 + 说明]
  .co [emoji + 维度4 + 说明]
  .co [emoji + 维度5 + 说明]
  .co [emoji + 维度6 + 说明]
}
.co-blue  总结
```

### 模式 D: 标题 + 左右对比（A vs B）
```
.t1 标题
.t2 副标题
.g2 {
  .co-red  { 反面 / 错误做法 }
  .co-green { 正面 / 正确做法 }
}
.co-blue  核心对比结论
```

---

## 注意事项

1. **字号是第一优先级** — 小红书在手机上看，宁可少放内容也不能字太小
2. **每页一个核心信息** — 不要在一页塞太多。信息密度高时拆页
3. **颜色有语义** — 蓝=信息/重点，绿=正面/正确，红=警示/错误，黄=注意，紫=强调/特殊
4. **Emoji 是视觉锚点** — 每个 callout 配一个相关 emoji，帮助快速扫描
5. **封面决定点击率** — 主标题要大（≥100px）、有冲击力、3-4 个标签
6. **内容忠实于源文件** — 简化可以，失真不行。数据必须准确，概念不能变形
7. **填充率 75-90% 最佳** — 太满压迫感，太空显得内容单薄
