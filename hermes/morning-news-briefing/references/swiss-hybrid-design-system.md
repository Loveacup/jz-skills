# Swiss Hybrid 设计系统 — 早新闻简报

> 2026-06-04 确立。从 Guizang Swiss International 设计系统迁移而来。
> 模板：`assets/mobile-template.html`（手机 430×932）、`assets/standard-template.html`（A4）

## 设计决策

旧版用暖色 newsletter 风格（奶油底 #fffdf8、青铜金 #b47a32、卡片式布局）→ 与 Guizang 的 Swiss/Editorial 双系统零关系 → 全面迁移到 Swiss Hybrid。

**Swiss Hybrid = Swiss 做结构性元素 + Editorial 做正文阅读**

| 层级 | 系统 | 说明 |
|------|------|------|
| 封面 | Swiss S01 Accent Cover | IKB 蓝底 (#002FA7)、超细字重标题、数据摘要 |
| 章节标签 | Swiss mono | IBM Plex Mono 大写标签 |
| KPI 数据条 | Swiss | 6 列紧凑数据卡片 |
| 分区脉络框 | Swiss 变体 | 左侧 IKB 粗线 + mono 日期 + 箭头链 |
| 正文 | Editorial | Noto Serif SC serif、连续阅读流 |
| 新闻条目 | Editorial | 点线分隔、无圆角卡片 |
| 每条小时间线 | Swiss mono | 紧凑箭头链、accent 色日期 |
| 深度分析 | Swiss 变体 | 左侧 IKB 细线 + mono 标签 |
| 总结卡片 | Swiss card-ink | 黑底白字、accent 色变体 |

## 设计 Token

```
--paper: #fafaf8;  --ink: #0a0a0a;
--grey-1: #f0f0ee; --grey-2: #d4d4d2; --grey-3: #737373;
--accent: #002FA7; --accent-on: #fff;
```

## 字体栈

| 角色 | 字体 |
|------|------|
| 正文 | Noto Serif SC → Source Han Serif SC → Georgia, serif |
| 标题/标签 | Inter → Helvetica Neue → PingFang SC, sans-serif |
| 数据/日期/信源 | IBM Plex Mono → SF Mono, monospace |

## 字号体系（430×932px 手机 PDF）

| 元素 | 字号 | 行高 | 字重 |
|------|------|------|------|
| body 正文 | 14px | 1.65 | 400 |
| 新闻内容 .content | 12px | 1.65 | 400 |
| 执行摘要 .lead | 13px | 1.65 | 400 |
| 章节标题 .sec-head | 16px | — | 500 |
| 深度分析标题 .title | 14px | — | 500 |
| 深度分析正文 .body | 12px | 1.65 | 400 |
| 卡片正文 .card-ink p | 12px | 1.7 | 400 |
| 时间线日期 | 7.5px | — | 500 mono |
| 信源/脚注 | 6.5px | — | 400 mono |
| 章节标签 .section-label | 7px | — | 600 mono |
| KPI 数字 | 10px | — | 300 mono |

**硬规则**：body 不得低于 14px，content 不得低于 12px。用户已验证过小字号不可接受。

## 页面设置

```
@page { size: 430px 932px; margin: 14px 16px 14px; }
```

- 自然流排版，不硬断页（仅封面独立一页）
- 内容自然填满每页，不留大片底部空白
- 目标：7-10 页装下 40 条新闻 + 6 条分析 + 总结 + 50 信源

### ⚠️ 排版 pitfall：不要硬断页

```css
/* ❌ 错误：每个内容块一个 .page div + page-break-after: always */
/* 后果：内容只占 60-70% 高度，下面大片空白 → 用户反馈"空白太多了" */

/* ✅ 正确：自然流，仅封面用 page-break-after */
.page { page-break-after: always; } /* 仅 .cover-wrap */
/* 其余内容让浏览器自然分页，@page margin 控制边距 */
```

用户明确反馈"每页的空白太多了（下面），内容还是太少"→ 根因就是硬断页。

## 时间线模式

### ⚠️ 关键 pitfall：两种"时间线"易混淆

| 用户说的 | 实际含义 | 错误理解 |
|---------|---------|---------|
| "每条新闻的历史时间线" | 事件的**来龙去脉**（背景脉络）：2/28 开战→4月停火→5月违反→6/3升级 | ❌ "今天几点发生"（凌晨/上午/下午） |

**永远不要做"时间-of-day"时间线。** 用户要的是事件链（event chain），不是当日时刻表。

### 分区脉络框 (.sec-timeline)
- 每个有历史纵深的板块开头放置
- 灰底 (#f0f0ee)、左侧 IKB 3px 粗线
- mono 日期 + 简短描述 + 箭头链
- 示例：美伊冲突 2/28 开战→4月停火→5月违反→6/2外溢→6/3升级

### 每条新闻小时间线 (.story-tl)
- 新闻正文上方一行 mono 小字
- accent 色日期 + 灰色箭头 + 紧凑脉络
- 示例：`4月 停火 → 5月 反复违反 → 6/3 升级`
- 无历史纵深的新闻（如"微信支持PayPal"）不加

## 与旧版对比

| | 旧版 | Swiss Hybrid |
|----|------|------|
| 底色 | #fffdf8 奶油 | #fafaf8 |
| 主色 | #b47a32 青铜金 | #002FA7 IKB |
| 字体 | PingFang SC | Noto Serif SC + Inter + IBM Plex Mono |
| 卡片 | 圆角 + 边框 | 无圆角 + card-ink/card-fill |
| 标签 | emoji 🔥🇺🇸 | 大写 mono 标签 |
| 排版 | 每页硬断 | 自然流 |
| body 字号 | 14px | 14px（不变） |
| 时间线 | 无 | 分区脉络 + 每条新闻小时间线 |
| 信源 | 30 | 50（sources.json 50+ outlets） |

## 市场数据

### 双层展示规则

市场数据必须在**两个位置**出现：

| 位置 | 形式 | 指标数 |
|------|------|--------|
| 摘要页（执行摘要下方） | KPI strip 横条 | 6 World + 6 China |
| 市场板块（深度分析前） | 2 列卡片 grid | 10 World + 10 China |

**双层不可省略。** 摘要页给速览，市场板块给详情。

### 国际市场卡片（10 项）
S&P 500, NASDAQ, BRENT, WTI, GOLD, BITCOIN, USD/JPY, S&P 500 PE, COPPER, BTC 清算

### 中国市场卡片（必须包含，10 项）
上证综指, 深证成指, 沪深300, 恒生指数, USD/CNY, 中国10年国债, GDP预测, 北向资金, 创业板指, 科创50

### 卡片 CSS
```css
.mkt-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.mkt-card { background: var(--grey-1); padding: 8px 10px; }
.mkt-card .mkt-label { font: 7px IBM Plex Mono; text-transform: uppercase; color: var(--grey-3); }
.mkt-card .mkt-val { font: 14px/300 IBM Plex Mono; color: var(--ink); }
.mkt-card .mkt-change.up { color: #2e7d32; }
.mkt-card .mkt-change.down { color: #c62828; }
.mkt-card .mkt-note { font-size: 7.5px; color: var(--grey-3); }
```
