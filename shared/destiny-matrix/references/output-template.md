# 成品模板与版式（v5.3）

本文件规定成品 HTML 的内容组织、语义结构与全部版式。目标是一本气质沉静、带东方书卷气又现代的书：宋体正文、窄栏、大留白、朱砂只作点睛，图表像学术书里的插图。文风与段落写法由 `agents/book-writer.md` 规定，本文件不设写作规则。

用法：把 §2 骨架里的整段 `<style>` 原样放进成品，按骨架的结构写内容。三张核心盘面图用 `scripts/book_html.py` 生成（见 §5），其余图表按 `chart-patterns.md` 绘制。

## 1. 内容组织

全书顺序：封面 → 这本书怎么读（必要披露）→ 目录 → 正文各章 → 附录 → 版权行。各部分都在 `<main id="book">` 内。

| 部分 | 放什么 | 排法 |
|---|---|---|
| 封面 `header.book-cover` | 称呼 `.book-for`（“写给　某某”）、书名 `.book-title`、副标题 `.book-subtitle`、题记 `.opening-quote`、印章 `.book-seal`（固定两字“命书”）、日期 `.book-date`（汉字数字年月） | 独占一屏／一页，细线双框，全部居中；书名 4–10 字最好看，副标题一行，题记一句 |
| 这本书怎么读 | 这是什么、它不替读者决定什么、怎么读；`required_placement:"opening"` 的限制写在这里 | 三段以内，平排正文，上下各一条细线；隐私与运维说明放附录 |
| 目录 | 链接到正文各章已有的 `id`，可加一项附录 | 章号由样式自动生成；`.toc-title` 写章题，`.toc-desc` 写体系或主题名 |
| 正文各章 | 见下 | 每章另起一页 |
| 附录 | 排盘依据、各体系取法、本书没有采用的读法、引用索引 | 逐条 `<details>`，按正文首次引用顺序排列，引用索引最后 |

书名、副标题、题记都取自本书内容；题记是正文里最能代表全书的一句话，用楷体排，不加引号，不署名（它不是引文）。

完整报告的章序：`personality → bazi → ziwei → astrology → synthesis → timing → relationships → practice`。用户请求事业或健康专题时，分别在 `relationships` 后插入 `career`、`wellbeing`。合盘只放在 `relationships` 内的 `#module-synastry`。focused 报告只生成请求的章；缺资料时披露真实缺口，不用空章或占位内容充数。全书结尾段落位于最后一章末尾。

一章之内的顺序：

1. 章首 `header.chapter-head`：`.chapter-no` 写体系或主题名（“八字”“关系”），“第几章”由样式生成；`h2.section-title` 是关于读者的一句判断；`.chapter-lede` 是一句导语，楷体。
2. 正文段落与小节 `h3.subsection-title`。图紧跟解释它的段落，不集中堆放。
3. 限制说明 `aside` 紧邻受影响的判断（见 §2）。
4. 行动建议 `.action-block`（有则放在章末前）。
5. “本章带走” `.chapter-takeaway`：两到三条，每条一句。
6. 附录入口 `.see-appendix`。

限制按 `team-orchestration.md` §4 的两层与落点规则放置；框架省去的取法集中在附录“本书没有采用的读法”一处。

## 2. 唯一 HTML 语义结构

以下结构、类名与 data 属性是 `validate_book.py`、`guard_book.py`、`export_pdf.py` 依赖的合同，逐条照做：

- 恰有一个 `<main id="book">`，全部内容在其中。
- 每个 `<section>` 都带 `data-content-kind`，取值只有 `disclosure`、`body`、`appendix`；`disclosure` 与 `appendix` 各恰好一个。封面、目录、行动块、“本章带走”用 `header`、`nav`、`div`，不用 `section`。
- 正文章节写作 `<section data-content-kind="body" data-section-id="bazi" id="ch-bazi">`：`id` 等于 `ch-` 加 `data-section-id`，顺序与 `chart_plan.sections` 一致。
- 每个 `<aside>` 带唯一的 `data-disclosure-id`；承载读者层限制时再带 `data-limitation-id`，去掉编号后至少六个汉字。段内从句用 `<span data-limitation-id="…">`。同一限制在正文只出现一次。
- `<details>` 只在附录内，带 `data-appendix-id`，且 `id` 与之相同；正文里有指向它的链接，它内部有一个 `href="#ch-…"` 的返回链接。
- 图写作 `<figure class="chart-container" data-chart-id="chart-<section_id>-NN" data-representation="measured|computed|qualitative">`，内含 `figcaption`、`.chart-description`、`.chart-scroll`、数据表与 `.chart-note`；图表集合与 `chart_plan.chart_table` 一致。
- 精确计算值绑定 `data-value-ref="<artifact_id>#<json_pointer>"`、`data-value`、`data-unit`、`data-precision`，可见文字与绑定值一致。段落的 `data-claim-ids` 以空格分隔，只引用 active claim。
- 引文用 `<blockquote data-quote-id="…">` 或 `<q data-quote-id="…">`，文字与 `sources.json` 已核原文或译文逐字一致；出处写在紧随其后的 `<p class="quote-source">`。
- 合盘容器为 `relationships` 章内的 `<div id="module-synastry" data-module="synastry">`。
- 成品里没有 HTML 注释，没有隐藏元素（`hidden`、`aria-hidden="true"` 的含文字元素、`display:none`、`visibility:hidden`）；样式表里也不出现这两条隐藏规则。审稿记录与修订指令不进入成品。
- 导出器按标签核对 PDF 字号：正文 `p`、`li`、`h2`、`h3` 不小于 12pt，引文 11.5pt，图题与图注 10pt，表格 9.5pt，附录 10pt，SVG 文字 9pt。§2 的样式已经满足；新增样式时别让这些标签在打印下变小。

### 成品骨架（合成示例）

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>冬水向阳</title>
  <style>
    :root {
      color-scheme: light;
      --paper: #faf7f0;
      --surface: #f3eee2;
      --ink: #211d18;
      --ink-2: #574f44;
      --ink-3: #6b6256;
      --cinnabar: #9b2d23;
      --indigo: #2e4a62;
      --pine: #3b5d4a;
      --ochre: #7d5a24;
      --rule: #d8d0bf;
      --rule-strong: #8c826e;
      --wx-wood: #3b6b4a;
      --wx-fire: #a5382b;
      --wx-earth: #7d5a24;
      --wx-metal: #5d6470;
      --wx-water: #2e4a62;
      --serif: "Songti SC", "STSong", "Source Han Serif SC", "Noto Serif CJK SC", "Noto Serif SC", "SimSun", serif;
      --sans: "PingFang SC", "Hiragino Sans GB", "Source Han Sans SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
      --kai: "Kaiti SC", "STKaiti", "KaiTi", "Songti SC", "STSong", "SimSun", serif;
      --num: "Iowan Old Style", "Palatino Linotype", Palatino, "Times New Roman", "Songti SC", "SimSun", serif;
      --measure: 40rem;
    }
    * { box-sizing: border-box; }
    html { background: var(--paper); -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: var(--serif);
      font-size: 18px;
      line-height: 1.85;
      line-break: strict;
      overflow-wrap: break-word;
      -webkit-font-smoothing: antialiased;
    }
    #book { max-width: calc(var(--measure) + 3rem); margin: 0 auto; padding: 0 1.5rem 5rem; counter-reset: chapter; }
    p { margin: 0 0 1em; text-align: justify; }
    a { color: var(--indigo); text-decoration-thickness: .06em; text-underline-offset: .2em; }
    a:focus-visible, summary:focus-visible, .chart-scroll:focus-visible { outline: 2px solid var(--indigo); outline-offset: 3px; }
    strong { font-weight: 700; }
    dfn { font-style: normal; font-weight: 700; }
    h1, h2, h3, h4 { font-family: var(--serif); font-weight: 700; text-wrap: balance; }

    .book-cover {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      min-height: 100svh;
      padding: 4.5rem 2rem 4rem;
      text-align: center;
    }
    .book-cover::before {
      content: "";
      position: absolute;
      inset: 1.5rem 0;
      border: 1px solid var(--rule-strong);
      outline: 1px solid var(--rule);
      outline-offset: 5px;
      pointer-events: none;
    }
    .book-cover p { text-align: center; text-wrap: balance; }
    .book-for { margin: 0 0 auto; padding-top: 1rem; font-family: var(--sans); font-size: 15px; letter-spacing: .3em; color: var(--ink-2); }
    .book-title { margin: 3rem 0 0; font-size: 42px; line-height: 1.35; letter-spacing: .06em; }
    .book-subtitle { margin: 1.25rem 0 0; max-width: 26em; font-size: 18px; line-height: 1.7; color: var(--ink-2); }
    .book-subtitle::after { content: ""; display: block; width: 2.5rem; height: 2px; margin: 2rem auto 0; background: var(--cinnabar); }
    .opening-quote { margin: 2rem 0 3rem; max-width: 22em; font-family: var(--kai); font-size: 20px; line-height: 1.8; color: var(--ink); }
    .book-imprint { display: flex; flex-direction: column; align-items: center; gap: 1rem; margin: auto 0 0; padding-bottom: 1rem; }
    .book-seal {
      margin: 0;
      padding: .5em .32em;
      writing-mode: vertical-rl;
      font-family: var(--kai);
      font-size: 17px;
      font-weight: 700;
      line-height: 1.2;
      letter-spacing: .18em;
      color: var(--paper);
      background: var(--cinnabar);
      border-radius: 2px;
    }
    .book-date { margin: 0; font-family: var(--sans); font-size: 14px; letter-spacing: .25em; color: var(--ink-3); }

    .disclosure { margin: 4rem 0 0; padding: 2.5rem 0 1.5rem; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--rule); }
    .disclosure h2 { margin: 0 0 1.25rem; font-size: 24px; line-height: 1.4; letter-spacing: .04em; }
    .disclosure p { font-size: 17px; }

    .book-toc { margin: 4rem 0 0; }
    .book-toc h2 { margin: 0 0 1rem; font-size: 24px; letter-spacing: .3em; }
    .book-toc ol { margin: 0; padding: 0; list-style: none; counter-reset: toc; border-top: 1px solid var(--ink); }
    .book-toc li { counter-increment: toc; border-bottom: 1px solid var(--rule); }
    .book-toc a {
      display: grid;
      grid-template-columns: 5em minmax(0, 1fr) auto;
      gap: 0 1rem;
      align-items: baseline;
      padding: .85rem 0;
      color: var(--ink);
      text-decoration: none;
    }
    .book-toc a::before { content: "第" counter(toc, simp-chinese-informal) "章"; font-family: var(--sans); font-size: 14px; letter-spacing: .12em; color: var(--cinnabar); }
    .book-toc li.is-appendix { counter-increment: none; }
    .book-toc li.is-appendix a::before { content: "附录"; }
    .book-toc a:hover .toc-title { text-decoration: underline; text-decoration-thickness: .06em; text-underline-offset: .25em; }
    .toc-title { font-weight: 700; }
    .toc-desc { font-family: var(--sans); font-size: 14px; color: var(--ink-3); }

    .book-section { counter-increment: chapter; counter-reset: figure; margin: 5rem 0 0; padding: 5rem 0 0; border-top: 1px solid var(--rule); }
    .chapter-head { margin: 0 0 2.75rem; }
    .chapter-head::after { content: ""; display: block; width: 2.5rem; height: 2px; margin-top: 1.75rem; background: var(--cinnabar); }
    .chapter-no { margin: 0 0 1rem; font-family: var(--sans); font-size: 14px; letter-spacing: .25em; color: var(--cinnabar); text-align: left; }
    .chapter-no::before { content: "第" counter(chapter, simp-chinese-informal) "章 · "; }
    .section-title { margin: 0; font-size: 32px; line-height: 1.4; letter-spacing: .03em; }
    .chapter-lede { margin: 1rem 0 0; font-family: var(--kai); font-size: 20px; line-height: 1.75; color: var(--ink-2); text-align: left; }
    .subsection-title { margin: 3rem 0 1rem; font-size: 22px; line-height: 1.5; }
    .minor-title { margin: 2rem 0 .75rem; font-family: var(--sans); font-size: 16px; font-weight: 600; letter-spacing: .06em; }
    .book-section ul, .book-section ol { margin: 0 0 1em; padding-left: 1.5em; }
    .book-section li { margin: .35em 0; }
    .see-appendix { margin: 1.5rem 0 0; font-family: var(--sans); font-size: 14.5px; text-align: left; }

    aside[data-disclosure-id] {
      margin: 1.75rem 0;
      padding: .15rem 0 .15rem 1.1rem;
      border-left: 2px solid var(--ochre);
      font-family: var(--sans);
      font-size: 15px;
      line-height: 1.75;
      color: var(--ink-2);
    }
    aside[data-disclosure-id] p { margin: 0 0 .6em; text-align: left; }
    aside[data-disclosure-id] > :last-child { margin-bottom: 0; }
    [data-limitation-id]:not(aside):not(p) { text-decoration: underline dotted var(--ochre); text-decoration-thickness: .08em; text-underline-offset: .25em; }

    blockquote { margin: 2.25rem 0 .5rem; padding: 0 2em; font-family: var(--kai); font-size: 20px; line-height: 1.85; color: var(--ink); }
    blockquote p { margin: 0; }
    q { font-family: var(--kai); }
    .quote-source { margin: 0 0 2.25rem; padding: 0 2.2em; font-family: var(--sans); font-size: 14px; color: var(--ink-3); text-align: right; }

    .block-title { margin: 0 0 .75rem; font-family: var(--sans); font-size: 15px; font-weight: 600; line-height: 1.6; letter-spacing: .14em; }
    .action-block { margin: 2.5rem 0; padding: 1.25rem 1.5rem 1.35rem; border: 1px solid var(--rule); border-top: 2px solid var(--pine); }
    .action-block .block-title { color: var(--pine); }
    .action-block ol, .action-block ul { margin: 0; padding-left: 1.4em; }
    .action-block li { margin: .45em 0; }
    .action-block li::marker { font-family: var(--num); color: var(--pine); }
    .action-block > :last-child, .chapter-takeaway > :last-child { margin-bottom: 0; }
    .chapter-takeaway { margin: 3.5rem 0 0; padding: 1.5rem 1.5rem 1.6rem; background: var(--surface); }
    .chapter-takeaway .block-title { color: var(--cinnabar); }
    .chapter-takeaway ul { margin: 0; padding: 0; list-style: none; }
    .chapter-takeaway li { position: relative; margin: .5em 0; padding-left: 1.2em; }
    .chapter-takeaway li::before { content: ""; position: absolute; left: .2em; top: .82em; width: 5px; height: 5px; border-radius: 50%; background: var(--cinnabar); }

    .chart-container { counter-increment: figure; min-width: 0; margin: 2.75rem 0; padding: 1.1rem 0 1rem; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--rule); }
    .chart-container figcaption { margin: 0 0 .35rem; font-family: var(--sans); font-size: 15.5px; font-weight: 600; line-height: 1.6; }
    .chart-container figcaption::before { content: "图 " counter(chapter) "-" counter(figure); margin-right: .9em; color: var(--cinnabar); letter-spacing: .05em; }
    .chart-description { margin: 0; font-family: var(--sans); font-size: 14.5px; line-height: 1.75; color: var(--ink-2); text-align: left; }
    .chart-note, .appendix-note { margin: .9rem 0 0; font-family: var(--sans); font-size: 14px; line-height: 1.7; color: var(--ink-3); text-align: left; }
    .chart-scroll { max-width: 100%; margin: 1.1rem 0 0; overflow-x: auto; overscroll-behavior-inline: contain; }
    .chart-scroll svg { display: block; max-width: 100%; height: auto; margin: 0 auto; }
    .chart-scroll svg text { font-family: var(--sans); }

    table { width: 100%; border-collapse: collapse; font-family: var(--sans); font-size: 15px; line-height: 1.6; font-variant-numeric: tabular-nums; }
    .book-section > table, .appendix-body > table { margin: 1.75rem 0; }
    caption { caption-side: top; padding: 0 0 .5rem; font-size: 14.5px; font-weight: 600; color: var(--ink-2); text-align: left; }
    th, td { min-width: 3.6em; padding: .55rem .75rem; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: top; }
    thead th { border-top: 1.5px solid var(--ink); border-bottom: 1px solid var(--ink); font-size: 14px; font-weight: 600; color: var(--ink-2); vertical-align: bottom; }
    tbody th { font-weight: 600; }
    thead th, tbody th, td.nw { white-space: nowrap; }
    tbody tr:last-child > * { border-bottom: 1.5px solid var(--ink); }
    td[data-value-ref], th.num, td.num { font-family: var(--num); font-size: 1.04em; text-align: right; white-space: nowrap; }
    th.num { font-family: var(--sans); font-size: 14px; }

    .wx-wood { color: var(--wx-wood); }
    .wx-fire { color: var(--wx-fire); }
    .wx-earth { color: var(--wx-earth); }
    .wx-metal { color: var(--wx-metal); }
    .wx-water { color: var(--wx-water); }
    .pillar-chart { table-layout: fixed; }
    .pillar-chart th, .pillar-chart td { padding: .5rem .25rem; text-align: center; vertical-align: middle; text-wrap: balance; }
    .pillar-chart .pillar-glyph { vertical-align: top; }
    .pillar-chart thead th:first-child, .pillar-chart tbody th { width: 5.5em; white-space: normal; padding-left: .5rem; font-size: 14px; font-weight: 400; color: var(--ink-3); text-align: left; }
    .pillar-chart thead th { font-size: 15px; letter-spacing: .2em; color: var(--ink); }
    .pillar-chart thead th:nth-child(4), .pillar-chart td:nth-child(4) { background: var(--surface); }
    .pillar-stems td, .pillar-stems th { border-bottom-color: transparent; padding-bottom: 0; }
    .pillar-glyph .glyph { display: block; font-family: var(--serif); font-size: 40px; font-weight: 700; line-height: 1.2; }
    .pillar-wx { display: block; font-size: 14px; line-height: 1.3; }
    .pillar-mark { display: inline-block; margin: .3rem 0 .2rem; padding: 0 .5em; border: 1px solid var(--cinnabar); border-radius: 2px; font-size: 14px; line-height: 1.5; color: var(--cinnabar); background: var(--paper); }

    .bar-list { display: grid; gap: .5rem; margin: 1.4rem 0 0; font-family: var(--sans); font-size: 15px; line-height: 1.4; }
    .bar-row { display: grid; grid-template-columns: 1.6em minmax(0, 1fr) 4em; gap: 0 .9rem; align-items: center; }
    .bar-label { font-family: var(--serif); font-weight: 700; }
    .bar-track { display: block; height: 10px; border-left: 1px solid var(--ink); background: linear-gradient(var(--rule), var(--rule)) center / 100% 1px no-repeat; }
    .bar-fill { display: block; height: 100%; background: currentColor; }
    .bar-value { font-family: var(--num); font-variant-numeric: tabular-nums; text-align: right; color: var(--ink); }

    .ziwei-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      grid-template-rows: repeat(4, minmax(8.75rem, auto));
      min-width: 600px;
      border: 1.5px solid var(--ink);
      background: var(--paper);
      font-family: var(--sans);
      font-size: 14px;
      line-height: 1.5;
    }
    .ziwei-cell { display: flex; flex-direction: column; gap: .3rem; min-width: 0; padding: .55rem .6rem .5rem; border: .5px solid var(--rule-strong); }
    .ziwei-cell[data-branch="巳"] { grid-area: 1 / 1; }
    .ziwei-cell[data-branch="午"] { grid-area: 1 / 2; }
    .ziwei-cell[data-branch="未"] { grid-area: 1 / 3; }
    .ziwei-cell[data-branch="申"] { grid-area: 1 / 4; }
    .ziwei-cell[data-branch="辰"] { grid-area: 2 / 1; }
    .ziwei-cell[data-branch="酉"] { grid-area: 2 / 4; }
    .ziwei-cell[data-branch="卯"] { grid-area: 3 / 1; }
    .ziwei-cell[data-branch="戌"] { grid-area: 3 / 4; }
    .ziwei-cell[data-branch="寅"] { grid-area: 4 / 1; }
    .ziwei-cell[data-branch="丑"] { grid-area: 4 / 2; }
    .ziwei-cell[data-branch="子"] { grid-area: 4 / 3; }
    .ziwei-cell[data-branch="亥"] { grid-area: 4 / 4; }
    .ziwei-cell.is-center { position: relative; grid-area: 2 / 2 / 4 / 4; align-items: center; justify-content: center; padding: 0; }
    .ziwei-cell.is-ming { box-shadow: inset 0 0 0 2px var(--cinnabar); }
    .ziwei-grid .zw-lines { position: absolute; inset: 0; width: 100%; height: 100%; max-width: none; margin: 0; }
    .zw-centre-text { position: relative; display: flex; flex-direction: column; align-items: center; gap: .1rem; color: var(--ink-2); text-align: center; }
    .zw-centre-text > span { padding: 0 .6em; background: var(--paper); }
    .zw-title { margin-bottom: .2rem; font-family: var(--serif); font-size: 19px; font-weight: 700; letter-spacing: .2em; color: var(--ink); }
    .zw-legend { margin-top: .3rem; color: var(--ink-3); }
    .zw-stars { display: flex; flex-wrap: wrap; gap: .1rem .7rem; font-family: var(--serif); font-size: 17px; font-weight: 700; line-height: 1.45; }
    .zw-empty { font-family: var(--sans); font-size: 14px; font-weight: 400; color: var(--ink-3); }
    .zw-minor { display: flex; flex-wrap: wrap; gap: 0 .7rem; color: var(--ink-2); }
    .zw-bright { margin-left: .12em; font-family: var(--sans); font-size: 13px; font-weight: 400; color: var(--ink-3); }
    .zw-hua { display: inline-block; margin-left: .3em; padding: 0 .3em; border: 1px solid var(--cinnabar); border-radius: 2px; font-family: var(--sans); font-size: 14px; font-weight: 600; line-height: 1.35; color: var(--cinnabar); vertical-align: .08em; }
    .zw-foot { display: flex; justify-content: space-between; align-items: flex-end; gap: .4rem; margin-top: auto; padding-top: .35rem; border-top: .5px solid var(--rule); }
    .zw-names { display: flex; flex-wrap: wrap; gap: .25rem; }
    .palace-label { font-family: var(--serif); font-size: 15px; font-weight: 700; line-height: 1.45; }
    .is-ming .palace-label:first-child { padding: 0 .4em; color: var(--paper); background: var(--cinnabar); }
    .palace-label.is-shen-label { padding: 0 .35em; border: 1px solid var(--ink); font-family: var(--sans); font-size: 14px; font-weight: 400; }
    .zw-meta { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.35; color: var(--ink-3); white-space: nowrap; font-variant-numeric: tabular-nums; }
    .zw-gz { font-family: var(--serif); color: var(--ink-2); }

    .chart-scroll svg.wheel { width: 100%; min-width: 620px; max-width: 680px; }
    .wheel .wheel-sign { font-family: var(--serif); letter-spacing: .1em; }
    .timeline-panels { display: grid; gap: 1.75rem; }
    .timeline-panel { min-width: 600px; }
    .timeline-panel-title { margin: 0 0 .5rem; font-family: var(--sans); font-size: 14.5px; font-weight: 600; color: var(--ink-2); }
    .timeline-panel svg { font-size: 14px; }

    .appendix { margin: 5rem 0 0; padding: 5rem 0 0; border-top: 1px solid var(--ink); }
    .appendix > .appendix-title { margin: 0 0 .5rem; font-size: 32px; line-height: 1.4; letter-spacing: .3em; }
    .appendix-lede { margin: 0 0 2rem; font-family: var(--sans); font-size: 15px; color: var(--ink-2); text-align: left; }
    .appendix-entry { border-bottom: 1px solid var(--rule); }
    .appendix-entry:first-of-type { border-top: 1px solid var(--ink); }
    .appendix-entry summary, .appendix-entry > .appendix-title { margin: 0; padding: .9rem 0; font-family: var(--serif); font-size: 19px; font-weight: 700; line-height: 1.5; letter-spacing: 0; cursor: pointer; }
    .appendix-entry summary::marker { color: var(--cinnabar); }
    .appendix-body { padding: .25rem 0 1.5rem; font-size: 16px; line-height: 1.8; }
    .appendix-back { display: inline-block; margin-top: .25rem; font-family: var(--sans); font-size: 14px; }
    .colophon { margin: 5rem 0 0; padding: 1.5rem 0 0; border-top: 1px solid var(--rule); font-family: var(--sans); font-size: 14px; line-height: 1.7; letter-spacing: .08em; color: var(--ink-3); text-align: center; }

    @media (min-width: 1240px) {
      aside[data-disclosure-id] {
        float: right;
        clear: right;
        width: 13.5rem;
        margin: .45rem -16rem 1.25rem 0;
        padding: .7rem 0 0;
        border-left: 0;
        border-top: 2px solid var(--ochre);
        font-size: 14px;
        line-height: 1.7;
      }
    }
    @media (max-width: 480px) {
      body { font-size: 17px; line-height: 1.85; }
      #book { padding: 0 20px 3.5rem; }
      .book-cover { padding: 3.5rem 1.25rem 3rem; }
      .book-cover::before { inset: 1rem 0; }
      .book-title { font-size: 32px; letter-spacing: .04em; }
      .book-subtitle { font-size: 16.5px; }
      .opening-quote, .chapter-lede, blockquote { font-size: 18.5px; }
      .section-title, .appendix > .appendix-title { font-size: 26px; }
      .subsection-title { font-size: 20px; }
      .book-section, .appendix { margin-top: 3.5rem; padding-top: 3.5rem; }
      .book-toc a { grid-template-columns: 4em minmax(0, 1fr); }
      .toc-desc { grid-column: 2; }
      blockquote { padding: 0 1em; }
      .quote-source { padding: 0 1em; }
      .action-block, .chapter-takeaway { padding: 1.1rem 1.1rem 1.2rem; }
      table { font-size: 14.5px; }
      th, td { padding: .5rem .5rem; }
      .pillar-chart thead th:first-child, .pillar-chart tbody th { width: 4.6em; padding-left: .25rem; }
      .pillar-chart thead th { letter-spacing: .05em; }
      .pillar-glyph .glyph { font-size: 32px; }
    }
    @media (max-width: 340px) {
      #book { padding: 0 16px 3rem; }
      .book-title { font-size: 28px; }
      .pillar-glyph .glyph { font-size: 28px; }
    }
    @media print {
      @page { size: A4; margin: 20mm 14mm 18mm; }
      html, body { background: #fff; }
      body { font-size: 12pt; line-height: 1.8; }
      #book { max-width: none; margin: 0; padding: 0 12mm; }
      p { orphans: 2; widows: 2; }
      a { color: inherit; text-decoration: none; }
      h1, h2, h3, h4, figcaption, caption, summary, .chapter-no, .block-title, .timeline-panel-title { break-after: avoid; }
      .chapter-head, .chart-description { break-inside: avoid; break-after: avoid; }

      .book-cover { min-height: 0; height: 250mm; padding: 22mm 10mm 18mm; break-after: page; }
      .book-cover::before { inset: 4mm 0; }
      .book-for, .book-date { font-size: 12pt; }
      .book-title { font-size: 32pt; }
      .book-subtitle { font-size: 13pt; }
      .opening-quote { font-size: 14pt; }
      .book-seal { font-size: 13pt; }

      .disclosure { margin: 0; padding: 10mm 0 6mm; }
      .disclosure h2, .book-toc h2 { font-size: 17pt; }
      .disclosure p { font-size: 12pt; }
      .book-toc { margin: 12mm 0 0; break-inside: avoid; }
      .book-toc a { padding: 2.6mm 0; }
      .book-toc a::before, .toc-desc { font-size: 10.5pt; }

      .book-section, .appendix { margin: 0; padding: 0; border-top: 0; break-before: page; }
      .chapter-head { margin: 0 0 10mm; padding-top: 14mm; }
      .chapter-no { font-size: 12pt; }
      .section-title, .appendix > .appendix-title { font-size: 24pt; }
      .chapter-lede { font-size: 14pt; }
      .subsection-title { margin: 10mm 0 4mm; font-size: 15.5pt; }
      .minor-title, .block-title { font-size: 12pt; }
      .see-appendix { font-size: 12pt; }

      aside[data-disclosure-id] { font-size: 12pt; line-height: 1.7; break-inside: avoid; }
      aside[data-disclosure-id].long-aside { break-inside: auto; }
      blockquote { font-size: 13.5pt; break-inside: avoid; break-after: avoid; }
      .quote-source { font-size: 12pt; }
      .action-block, .chapter-takeaway { break-inside: avoid; }

      .chart-container { margin: 9mm 0; break-inside: auto; }
      .chart-container.is-wide, .chart-container:has(svg.wheel), .chart-container:has(.ziwei-grid) { margin-inline: -12mm; }
      .chart-container figcaption { font-size: 11pt; }
      .chart-description, .chart-note, .appendix-note, .appendix-lede { font-size: 10.5pt; }
      .chart-scroll { overflow: visible; }
      .chart-scroll svg, .ziwei-grid, .pillar-chart, .bar-list { break-inside: avoid; }
      table { font-size: 10pt; break-inside: avoid; }
      table.chart-data:not(.pillar-chart), table.long-table { break-inside: auto; }
      caption, thead th, th.num { font-size: 10pt; }
      thead { display: table-header-group; }
      tr { break-inside: avoid; }
      .pillar-chart thead th, .pillar-chart thead th:first-child, .pillar-chart tbody th, .pillar-wx, .pillar-mark { font-size: 10pt; }
      .pillar-chart th, .pillar-chart td { padding: 1.3mm 1mm; }
      .pillar-glyph .glyph { font-size: 24pt; }
      .chart-container { padding: 3mm 0; }
      .chart-scroll { margin-top: 3mm; }
      .bar-list { font-size: 10.5pt; }
      .ziwei-grid { min-width: 0; width: 100%; grid-template-rows: repeat(4, minmax(34mm, auto)); font-size: 10pt; }
      .zw-stars { font-size: 12pt; }
      .zw-title { font-size: 13pt; }
      .palace-label { font-size: 11pt; }
      .zw-bright, .zw-hua, .zw-empty, .palace-label.is-shen-label { font-size: 10pt; }
      .chart-scroll svg.wheel { min-width: 0; width: 176mm; max-width: 100%; }
      .timeline-panels, .timeline-panel { min-width: 0; width: 100%; }
      .timeline-panel-title { font-size: 10.5pt; }
      .timeline-panel svg { font-size: 9.5pt; }

      .appendix > .appendix-title { padding-top: 14mm; margin-bottom: 4mm; }
      .appendix-entry { break-inside: auto; }
      .appendix-entry summary, .appendix-entry > .appendix-title { font-size: 13pt; padding: 4mm 0 2mm; }
      .appendix-body { font-size: 10.5pt; line-height: 1.75; }
      .appendix-back { font-size: 10pt; }
      .colophon { margin-top: 14mm; font-size: 9pt; }
    }
  </style>
</head>
<body>
  <main id="book">
    <header class="book-cover">
      <p class="book-for">写给　阿澄</p>
      <h1 class="book-title">冬水向阳</h1>
      <p class="book-subtitle">在规矩里站稳，再为自己点一盏灯</p>
      <p class="opening-quote">腊月的江水不急着流，它先等一束光。</p>
      <div class="book-imprint">
        <p class="book-seal">命书</p>
        <p class="book-date">二〇二六年九月</p>
      </div>
    </header>

    <section class="disclosure" data-content-kind="disclosure" id="disclosure-basis" aria-labelledby="basis-title">
      <h2 id="basis-title">这本书怎么读</h2>
      <p>这本书把三种传统各自怎样读你的盘，依次写给你。每章先给判断，再给盘面依据；读的时候拿自己的经历去对，像的留下，不像的也记一笔。</p>
      <p data-limitation-id="L-open-01">阿澄是虚构的称呼，盘面取自一组合成资料，书里的判断只对这张合成的盘成立。</p>
    </section>

    <nav class="book-toc" aria-label="目录">
      <h2>目录</h2>
      <ol>
        <li><a href="#ch-bazi"><span class="toc-title">腊月的江水，遇见一位讲规矩的官</span><span class="toc-desc">八字</span></a></li>
        <li><a href="#ch-relationships"><span class="toc-title">把分歧变成一次可以商量的请求</span><span class="toc-desc">关系</span></a></li>
        <li class="is-appendix"><a href="#appendix"><span class="toc-title">盘面依据与取法</span></a></li>
      </ol>
    </nav>

    <section class="book-section" data-content-kind="body" data-section-id="bazi" id="ch-bazi" aria-labelledby="bazi-title">
      <header class="chapter-head">
        <p class="chapter-no">八字</p>
        <h2 class="section-title" id="bazi-title">腊月的江水，遇见一位讲规矩的官</h2>
        <p class="chapter-lede">你做事先问分寸，再问快慢；这份分寸感是你的底色。</p>
      </header>

      <p data-claim-ids="B-001">在子平的读法里，你是一条生在腊月的江。月令丑土里藏的是己土，对壬水而言叫<dfn>正官</dfn>——管束我、也成就我的那股力量。</p>

      <figure class="chart-container" data-chart-id="chart-bazi-01" data-representation="computed">
        <figcaption id="chart-bazi-01-caption">四柱盘与五行分布</figcaption>
        <p class="chart-description" id="chart-bazi-01-desc">四柱自左至右为年、月、日、时；底色一列是日柱。下方横条共用零点，满宽为 100%。</p>
        <div class="chart-scroll" role="region" tabindex="0" aria-labelledby="chart-bazi-01-caption" aria-describedby="chart-bazi-01-desc">
          〔book_html.py pillars 的输出〕
        </div>
        <div class="bar-list" role="group" aria-label="五行分布">
          <div class="bar-row wx-wood"><span class="bar-label">木</span><span class="bar-track"><span class="bar-fill" style="width:12.5%"></span></span><span class="bar-value" data-value-ref="bundle#/dimensions/bazi/data/五行比例/木" data-value="12.5" data-unit="%" data-precision="1">12.5%</span></div>
        </div>
        <p class="chart-note">排盘以节气定月、以真太阳时定时柱。</p>
      </figure>

      <h3 class="subsection-title">财来生官，印来护身</h3>
      <p data-claim-ids="B-002">月干丁火是正财，时干丙火是偏财，两重财星都在天干。</p>

      <aside data-disclosure-id="limit-bazi-hour" data-limitation-id="L-bazi-01"><p>时柱取决于出生时刻落在午时；如果实际出生早于十一点或晚于十三点，这一节关于“向阳”的读法需要重读。</p></aside>

      <blockquote data-quote-id="ziping-zhenquan-q01">八字用神，专求月令，以日干配月令地支，而生克不同，格局分焉。</blockquote>
      <p class="quote-source">沈孝瞻《子平真诠》· 论用神</p>

      <table>
        <caption>天干四字各自的角色</caption>
        <thead><tr><th scope="col">位置</th><th scope="col">十神</th><th scope="col">在这张盘里的读法</th></tr></thead>
        <tbody><tr><th scope="row">年干</th><td>正官</td><td>月令官星透出，立格之神</td></tr></tbody>
      </table>

      <div class="action-block">
        <h3 class="block-title">可以先试的一步</h3>
        <ol><li>这个月给自己留一段不必交代成果的时间，做一件纯粹因为想做而做的事。</li></ol>
      </div>

      <div class="chapter-takeaway">
        <h3 class="block-title">本章带走</h3>
        <ul><li>子平读你：正官立格，是守分寸、重承诺的人。</li><li>冬水要见太阳：留意那些让你主动起身的事。</li></ul>
      </div>
      <p class="see-appendix"><a href="#appendix-bazi">附录：八字的排盘依据与取法</a></p>
    </section>

    <section class="book-section" data-content-kind="body" data-section-id="relationships" id="ch-relationships" aria-labelledby="relationships-title">
      <header class="chapter-head">
        <p class="chapter-no">关系</p>
        <h2 class="section-title" id="relationships-title">把分歧变成一次可以商量的请求</h2>
        <p class="chapter-lede">分歧出现时，你先稳住自己，再开口。</p>
      </header>
      <div id="module-synastry" data-module="synastry"><p>〔合盘模块：取得双方资料且用户请求时写在这里〕</p></div>
    </section>

    <section class="appendix" data-content-kind="appendix" id="appendix" aria-labelledby="appendix-title">
      <h2 class="appendix-title" id="appendix-title">附录</h2>
      <p class="appendix-lede">盘面依据、各体系的取法，以及本书没有采用的读法。</p>
      <details class="appendix-entry" data-appendix-id="appendix-bazi" id="appendix-bazi">
        <summary>八字的排盘依据与取法</summary>
        <div class="appendix-body"><p>以子平格局法为主，月令取格，扶抑与调候为辅。盲派与新派的读法，本书没有采用。</p><a class="appendix-back" href="#ch-bazi">返回第一章</a></div>
      </details>
    </section>
    <footer class="colophon">合成示例 · 用于说明成品结构与版式</footer>
  </main>
</body>
</html>
```

## 3. 视觉、可读性与打印规则

### 3.1 色彩

| 变量 | 色值 | 用途 | 对纸色对比度 |
|---|---|---|---|
| `--paper` | `#faf7f0` | 页面底色（打印为白） | — |
| `--surface` | `#f3eee2` | “本章带走”、日柱列、黄道带的浅底 | — |
| `--ink` | `#211d18` | 正文、标题、图中主线 | 15.7 |
| `--ink-2` | `#574f44` | 次要文字、图注 | 7.5 |
| `--ink-3` | `#6b6256` | 辅助文字、表头侧栏 | 5.6 |
| `--cinnabar` 朱砂 | `#9b2d23` | 章号、图号、印章、命宫、紧张相位 | 7.0 |
| `--indigo` 黛蓝 | `#2e4a62` | 链接、图表第一数据色、和谐相位 | 8.6 |
| `--pine` 松绿 | `#3b5d4a` | 行动块、图表第三数据色 | 6.9 |
| `--ochre` 赭石 | `#7d5a24` | 限制边注、图表第四数据色 | 5.8 |
| `--rule-strong` | `#8c826e` | 图中结构线、封面框（3.4，达到图形 3:1） | 3.4 |
| `--rule` | `#d8d0bf` | 纯装饰的分隔线，不承载信息 | 1.4 |

五行色 `--wx-wood #3b6b4a`、`--wx-fire #a5382b`、`--wx-earth #7d5a24`、`--wx-metal #5d6470`、`--wx-water #2e4a62`，对纸色均在 5.5 以上；五行字旁同时写出“木火土金水”，颜色不单独承载信息。以上文字色在 `--surface` 上也都高于 4.5:1。朱砂一页之内只出现在小面积的标记上，不铺大色块。

### 3.2 字体

只用系统字体，不引任何外部字体文件，离线与 PDF 导出都可用。

| 变量 | 字体栈 | 用在哪里 |
|---|---|---|
| `--serif` | Songti SC → STSong → 思源宋体／Noto Serif CJK → SimSun → serif | 正文、标题、盘面大字 |
| `--sans` | PingFang SC → Hiragino Sans GB → 思源黑体／Noto Sans CJK → Microsoft YaHei → sans-serif | 图题、图注、表格、边注、章号等标签 |
| `--kai` | Kaiti SC → STKaiti → KaiTi → 宋体 → serif | 题记、章首导语、引文 |
| `--num` | Iowan Old Style → Palatino → Times New Roman → 宋体 | 表格与图中的数值 |

中文字体排在西文之前：弯引号、破折号、间隔号要取中文字形的全宽，西文字体在前会把它们排成半宽。数值单元格里没有中文标点，才用西文衬线数字。

### 3.3 字号与间距

| 层级 | 屏幕 | 手机（≤480px） | 打印 |
|---|---|---|---|
| 书名 | 42px | 32px | 32pt |
| 章题 `h2` | 32px | 26px | 24pt |
| 小节 `h3` | 22px | 20px | 15.5pt |
| 正文 | 18px，行高 1.85 | 17px | 12pt，行高 1.8 |
| 题记、导语、引文（楷体） | 20px | 18.5px | 14pt／13.5pt |
| 边注 | 15px（宽屏边栏 14px） | 15px | 12pt |
| 图题／图说明／图注 | 15.5／14.5／14px | 同左 | 11／10.5／10.5pt |
| 表格 | 15px | 14.5px | 10pt |
| 屏幕最小字号 | 13px（仅星曜亮度），其余不小于 14px | | |

正文栏宽 40rem，每行约 35 个汉字；段间距 1em，不缩进，两端对齐。章与章之间留 5rem 再加 5rem，中间一条细线。标题用 `text-wrap: balance`，避免最后一行只剩一两个字。

### 3.4 各部件

- **封面**：细线双框，称呼在上，书名居中，其下副标题、一道朱砂短线、题记；底部是朱砂竖排小印与日期。
- **章首**：朱砂小字“第几章 · 体系名”，章题，楷体导语，一道朱砂短线。
- **限制边注** `aside`：黑体小字、赭石色左线。视口不窄于 1240px 时浮到正文右侧的页边，成为真正的边注；更窄的屏幕与打印时留在栏内。
- **引文**：楷体，左右各缩两字，出处右对齐排在下一行。
- **行动块**：细框、松绿色顶线，标题是松绿色黑体小字，条目用有序列表。
- **本章带走**：浅底无框，标题朱砂色，条目前是朱砂小圆点。
- **表格**：三线表。顶线与底线 1.5px 墨色，表头下 1px，行间细线；没有竖线与底色。数值列右对齐（`td[data-value-ref]` 自动右对齐，表头加 `class="num"`）；不该折行的短单元格加 `class="nw"`。超过四列的表放进 `<div class="chart-scroll" role="region" tabindex="0" aria-label="…">`，窄屏时在框内横滑。
- **术语**：首次出现并解释的术语用 `<dfn>` 包住，排成粗体。
- **附录**：逐条 `<details>`，标题宋体粗体，正文 16px。

### 3.5 手机窄屏（320–430px）

页边距 20px（≤340px 时 16px）。封面仍占一屏。四柱盘整表收进屏宽，不滚动。十二宫盘保留 600px、星盘保留 620px 的最小画布，在可聚焦的 `.chart-scroll` 里局部横滑，整页不横移；“窄屏上可在图内左右滑动”这类提示全书只在第一张需要它的图的说明里写一次。目录的体系名折到章题下一行。

### 3.6 打印与 PDF

- A4。页边距由 `export_pdf.py` 给定：上 20mm、下 18mm、左右各 14mm；页眉是书名，页脚是页码，封面页不带页眉页脚。版心内再各留 12mm，正文行宽约 158mm、每行约 37 字。
- 封面独占一页；“这本书怎么读”与目录合为一页；每章、附录另起一页，章首上方留 14mm。
- 标题、图题、表题、块标题不与后文分开；段落首尾至少留两行。
- 图题、图说明与图形本体同页；图形本体（SVG、十二宫盘、四柱盘、五行条）不拆页。图后的数据表（`.chart-data`）可以跨页，表头在每页重复，单行不拆。正文里的普通表格默认整表不拆；超过半页的加 `class="long-table"` 允许跨页。
- 十二宫盘与星盘在打印时自动占满 182mm 的版心全宽，保证图内文字不小于 9pt；其他需要全宽的图加 `class="chart-container is-wide"`。
- 边注、行动块、“本章带走”、引文不拆页；超过半页的长边注加 `class="long-aside"` 允许拆页。
- 打印时不隐藏任何内容，不整体缩放图形；图形本体高于一页时按语义拆成两张图。

## 4. 常用语义类

| 类别 | 类名 |
|---|---|
| 封面 | `book-cover`、`book-for`、`book-title`、`book-subtitle`、`opening-quote`、`book-imprint`、`book-seal`、`book-date` |
| 前置 | `disclosure`、`book-toc`、`toc-title`、`toc-desc`、`is-appendix` |
| 章节 | `book-section`、`chapter-head`、`chapter-no`、`section-title`、`chapter-lede`、`subsection-title`、`minor-title`、`see-appendix` |
| 文内部件 | `quote-source`、`action-block`、`chapter-takeaway`、`block-title`、`long-aside`、`long-table`、`nw`、`num` |
| 图表 | `chart-container`、`is-wide`、`chart-description`、`chart-scroll`、`chart-data`、`chart-note`、`bar-list`、`bar-row`、`bar-label`、`bar-track`、`bar-fill`、`bar-value`、`timeline-panels`、`timeline-panel`、`timeline-panel-title` |
| 四柱盘 | `pillar-chart`、`pillar-gods`、`pillar-stems`、`pillar-branches`、`pillar-glyph`、`glyph`、`pillar-wx`、`pillar-mark`、`wx-wood`、`wx-fire`、`wx-earth`、`wx-metal`、`wx-water` |
| 十二宫盘 | `ziwei-grid`、`ziwei-cell`、`is-ming`、`is-shen`、`is-center`、`zw-stars`、`zw-star`、`zw-aux`、`zw-minor`、`zw-bright`、`zw-hua`、`zw-empty`、`zw-foot`、`zw-names`、`palace-label`、`is-shen-label`、`zw-meta`、`zw-limit`、`zw-gz`、`zw-lines`、`zw-centre-text`、`zw-title`、`zw-info`、`zw-legend` |
| 星盘 | `wheel`、`wheel-sign`、`wheel-house`、`wheel-axis`、`wheel-axis-label`、`wheel-cusp`、`wheel-planet`、`wheel-degree`、`wheel-aspect`、`is-harmonic`、`is-tense` |
| 附录与尾 | `appendix`、`appendix-title`、`appendix-lede`、`appendix-entry`、`appendix-body`、`appendix-back`、`appendix-note`、`colophon` |

全部样式在成品唯一的 `<style>` 里各定义一次。确需扩展时在同一规则集中增补，颜色与字体只引用 §3 的变量。

## 5. 三张核心盘面图

三张图由 `scripts/book_html.py` 从 `chart_bundle.json` 直接渲染，几何、字号与标注已经定好，输出的片段原样放进 `figure` 的 `.chart-scroll` 里：

```bash
"$DM_PY" scripts/book_html.py pillars --bundle "$WS/chart_bundle.json"
"$DM_PY" scripts/book_html.py ziwei   --bundle "$WS/chart_bundle.json"            # 加 --no-minor 则辅星不上图
"$DM_PY" scripts/book_html.py wheel   --bundle "$WS/chart_bundle.json" \
  --aspects "太阳-木星,月亮-海王星" --label-id chart-astrology-01-caption --desc-id chart-astrology-01-desc
```

| 图 | 画了什么 | 作者还要写什么 |
|---|---|---|
| 四柱盘 | 年月日时四列；十神、天干、地支大字（按五行着色并写出五行）、藏干十神、纳音；“日主”“月令”文字标签；日柱列浅底 | 图题、说明；五行条（`.bar-list`，数值绑定 `五行比例`）；图注 |
| 十二宫盘 | 固定地支位置的十二格；主星（亮度、生年四化）、辅星、宫名、宫干支、大限；命宫朱框朱底，身宫加框；空宫写“空宫”；中心画命宫三合（实线）与对宫（虚线） | 图题、说明；图下逐宫线性表（大限岁数绑定 `十二宫/N/大限/范围`）；图注 |
| 星盘 | 黄道十二宫带、真实宫始线、四轴（上升在左，天顶按实际黄经）、宫位数字、星体与宫内度分、所选相位（和谐相位黛蓝实线，紧张相位朱砂虚线，合相不画线） | 图题、说明（写明线型含义）；图下星体位置表（黄经绑定原值）；图注写宫制 |

渲染器只画计算输出里有的东西：缺宫始、缺黄经、相位不在计算结果里，都会报错退出，这时改用数据表并在图注里说明缺了什么。星盘默认画十大行星，`--bodies` 可增减；`--aspects` 只列正文讨论的相位，一般不超过六条。
