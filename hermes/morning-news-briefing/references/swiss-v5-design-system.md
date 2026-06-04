# Swiss v5 设计系统 — 早新闻简报

> 2026-06-04 迭代。从 LOCKED CSS v1.0（奶油 newsletter）迁移到 Swiss × Editorial 混血系统。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 视觉系统 | Swiss International + Editorial serif 正文 | 数据密集适合 Swiss，长文适合衬线 |
| 锚点色 | IKB `#002FA7` | 冷静权威，严肃新闻 |
| 字体栈 | Inter/Helvetica + Noto Serif SC + IBM Plex Mono | Swiss 三件套 |
| 卡片 | card-ink 黑底 + card-fill 浅灰 | 去圆角、去边框、去暖色 |
| 章节标签 | MONO 大写 | 替代 emoji |

## 三层时间线系统 (v5 新增)

1. **分区脉络框** — 板块开头，浅灰底 + 蓝左边框 + mono 日期链
2. **新闻条目小时间线** — 每条新闻上方，mono 箭头链
3. **嵌套** — 大脉络给图景，小时间线给前因后果

## CSS Token

--paper: #fafaf8; --ink: #0a0a0a; --grey-1: #f0f0ee; --grey-2: #d4d4d2; --grey-3: #737373; --accent: #002FA7;

## 与 v1.0 LOCKED CSS 区别

v1.0 奶油底+铜金+emoji / v5 纸白底+IKB蓝+MONO标签+历史时间线

## 已知限制

当前为硬编码示例，需参数化为 {{PLACEHOLDER}}；A4 版未适配；来源双栏偏挤。
