# 成品模板与阅读合同（v5）

本文件规定成品 HTML 的阅读层级、语义结构与呈现。报告围绕读者问题组织；图表及引文只在增加理解价值时使用。文风与段落写法由 `agents/book-writer.md` 规定，本文件不设 prose 句式或写作规则。

## 1. 内容组织

开篇顺序固定为：书名＋来自正文的短引言／阅读主题 → 必要披露 → 目录 → 正文。各部分均在 `<main id="book">` 中；目录链接到正文已有章节，不新建 `section_id`。不使用 hero、kicker 或摘要卡模板。图紧邻解释它的正文，不将图表集中堆放；逐项数据、方法记录及次要来源索引可放附录。

完整报告默认顺序：`personality → bazi → ziwei → astrology → synthesis → timing → relationships → practice`。用户请求事业或健康专题时，分别在 `relationships` 后插入 `career`、`wellbeing`。合盘只放在 `relationships` 内的 `#module-synastry`，不另设重复章节。focused 报告只生成请求落点；必要背景、边界与行动收束在该落点内，不静默添加其他主题。缺资料时须披露真实缺口；未经用户接受的关键缺失不能靠空章或占位内容伪装完成。

正文保留影响读法的限制；通用适用说明可置于必要披露，改变具体结论的限制放在相关正文附近。附录按正文首次引用顺序排列，引用索引最后。

## 2. 唯一 HTML 语义结构

- 开篇材料、目录及全部正文均位于 `<main id="book">`；目录使用 `<nav>` 链接到本书实际存在的正文 `id`，不能增加目录专用 `section_id`。
- 顶层内容类别只有 `disclosure`、`body`、`appendix`：必要披露用 `<section data-content-kind="disclosure">`；正文用 `<section data-content-kind="body" data-section-id="…" id="ch-…">`；附录用 `<section data-content-kind="appendix">`。
- 正文就近限制说明使用 `<aside data-disclosure-id="…">`，不得使用折叠面板。
- `<details>` 仅可出现在 appendix 内，并带全书唯一的 `data-appendix-id`。每个附录必须有正文可达链接及返回正文的锚点。审稿记录、失败日志和修订指令不得进入发布 HTML，包括隐藏 DOM 与 HTML 注释。
- 每个图使用 `<figure class="chart-container" data-chart-id="chart-<section_id>-01">`，包含 `<figcaption>`、可访问的简短说明及读者可访问的原始数据表/定性关系表。复用 `figure/figcaption/.chart-description/.chart-scroll/.chart-data` 与 `data-chart-id/data-value-ref/data-claim-ids`，不另建 DOM 合同。
- 精确计算值须绑定为 `data-value-ref="<artifact_id>#<json_pointer>"`、`data-value`、`data-unit`、`data-precision`。绑定值与读者可见文本一致。段落的 `data-claim-ids` 以空格分隔，仅引用有效 claim。
- 引文用带已核 quote ID 的 `<q data-quote-id="…">` 或 `<blockquote data-quote-id="…">`；引用标记不能替代相邻论述。
- 章节 ID 语义固定；合盘容器为 `div#module-synastry[data-module="synastry"]` 且置于 relationships 内。图表 ID 使用 `chart-<section_id>-<两位连续序号>`。

### 最小可用成品骨架（合成示例）

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>合成样本 · 阅读报告</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #fafaf8;
      --surface: #f3f1ec;
      --text: #1a1a1a;
      --text-secondary: #5a5a5a;
      --text-support: #666666;
      --accent: #8a1a1a;
      --blue: #2c5f7c;
      --green: #356746;
      --gold: #775e35;
      --rule: #d5d2c8;
      --sans: "PingFang SC", "Microsoft YaHei", sans-serif;
      --serif: "Songti SC", "STSong", "SimSun", serif;
    }
    * { box-sizing: border-box; }
    html { background: var(--bg); }
    body {
      margin: 0 auto;
      max-width: 44rem;
      padding: 3rem 1.5rem;
      color: var(--text);
      background: var(--bg);
      font-family: var(--sans);
      font-size: 17px;
      line-height: 1.9;
      line-break: strict;
      word-break: normal;
    }
    a { color: var(--blue); text-decoration-thickness: .08em; text-underline-offset: .16em; }
    .book-title, .section-title, .subsection-title, .appendix-title { font-family: var(--serif); font-weight: 500; line-height: 1.4; }
    .book-title { margin: 0; font-size: 32px; text-align: center; }
    .opening-quote { margin: 1.5rem auto .5rem; max-width: 36rem; color: var(--text-secondary); font-family: var(--serif); text-align: center; }
    .book-subtitle { margin: .5rem 0 2rem; color: var(--text-secondary); text-align: center; }
    .section-title { margin: 0 0 .25rem; font-size: 26px; }
    .subsection-title, .appendix-title { margin: 0 0 1rem; font-size: 20px; }
    .book-toc { margin: 0 0 3rem; padding: 1.25rem 1.5rem; border-block: 1px solid var(--rule); }
    .book-toc ol { margin: .5rem 0 0; padding-inline-start: 1.5rem; }
    .disclosure, .book-section, .appendix { margin: 0 0 3rem; }
    .disclosure { padding: 1rem 1.25rem; border-left: 3px solid var(--accent); background: var(--surface); }
    .chart-container { min-width: 0; margin: 1.5rem 0 2rem; padding: 1rem; background: var(--surface); border-radius: .25rem; }
    .chart-container figcaption { margin: 0 0 .75rem; font-weight: 600; }
    .chart-description, .chart-note, .appendix-note { color: var(--text-secondary); }
    .chart-scroll { max-width: 100%; overflow-x: auto; overscroll-behavior-inline: contain; }
    .chart-scroll:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
    .chart-scroll svg { display: block; max-width: 100%; height: auto; }
    .chart-data { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    .chart-data caption { padding: .5rem; text-align: left; font-weight: 600; }
    .chart-data th, .chart-data td { padding: .5rem .65rem; border: 1px solid var(--rule); text-align: left; vertical-align: top; }
    .chart-data th { background: var(--surface); }
    .chart-data td[data-value-ref], [data-value-ref] { font-variant-numeric: tabular-nums; }
    .ziwei-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      min-width: 600px;
      border: 1px solid var(--rule);
    }
    .ziwei-cell { min-height: 7rem; padding: .5rem; border: 1px solid var(--rule); font-size: 14px; }
    .ziwei-cell.is-center { display: flex; align-items: center; justify-content: center; color: var(--text-secondary); }
    .ziwei-cell .palace-label { display: inline-block; padding: 0 .25rem; border: 1px solid currentColor; }
    .timeline-panels { display: grid; gap: 1.5rem; }
    .timeline-panel { min-width: 600px; }
    .timeline-panel-title { margin: 0 0 .5rem; font-weight: 600; }
    .timeline-panel svg, .ziwei-grid svg { font-size: 14px; }
    .appendix-entry { margin: 1.5rem 0; }
    .appendix-entry summary { cursor: pointer; font-weight: 600; }
    .appendix-body { padding: 1rem 0; }
    .appendix-back { display: inline-block; margin-top: .5rem; }
    .colophon, .page-header, .page-footer { margin-top: 4rem; padding-top: 1rem; border-top: 1px solid var(--rule); color: var(--text-support); }
    @media (min-width: 320px) and (max-width: 430px) {
      body { padding: 2rem 20px; }
    }
    @media (max-width: 319px) {
      body { padding: 1.5rem 16px; }
      .book-title { font-size: 26px; }
    }
    @media print {
      @page { size: A4; margin: 18mm 14mm 16mm; }
      html, body { width: auto; max-width: none; margin: 0; padding: 0; background: #fff; }
      body { font-size: 12pt; line-height: 1.75; }
      .book-title { font-size: 24pt; }
      .section-title { font-size: 20pt; }
      .subsection-title, .appendix-title { font-size: 16pt; }
      .chart-description, .chart-note, .appendix-note { font-size: 10.1pt; }
      .chart-data { font-size: 9.6pt; }
      .chart-container { break-inside: auto; }
      .chart-description { break-inside: avoid; break-after: avoid; }
      .chart-scroll:has(svg), .chart-scroll:has(.ziwei-grid) { break-inside: avoid; }
      .chart-scroll { overflow: visible; }
      .ziwei-grid, .timeline-panels, .timeline-panel { width: 100%; min-width: 0; }
      .ziwei-cell { min-height: 0; padding: .35rem; font-size: 10pt; }
      .timeline-panel svg, .ziwei-grid svg { font-size: 9pt; }
      .page-header, .page-footer { font-size: 8.1pt; }
      .appendix, .appendix-entry { break-inside: auto; }
      h1, h2, h3, figcaption, summary { break-after: avoid; }
      table { width: 100%; break-inside: auto; }
      thead { display: table-header-group; }
      tr { break-inside: avoid; }
      a { color: inherit; }
    }
  </style>
</head>
<body>
  <main id="book">
    <h1 class="book-title">合成样本 · 阅读报告</h1>
    <p class="opening-quote">“遇到复杂任务时会先整理线索。”</p>
    <p class="book-subtitle">阅读主题：从已知资料出发，区分计算、传统解释与可尝试的选择</p>

    <section class="disclosure" data-content-kind="disclosure" id="disclosure-basis" aria-labelledby="basis-title">
      <h2 id="basis-title">阅读口径</h2>
      <p>本例仅演示结构。传统体系的解释属于文化方法，不等于对个人经历的测量或保证。</p>
    </section>
    <nav class="book-toc" aria-label="目录">
      <h2 class="subsection-title">目录</h2>
      <ol><li><a href="#ch-personality">性格与选择</a></li><li><a href="#ch-relationships">关系主题</a></li></ol>
    </nav>
    <section class="book-section" data-content-kind="body" data-section-id="personality" id="ch-personality" aria-labelledby="personality-title">
      <h2 class="section-title" id="personality-title">在变化中寻找稳定的支点</h2>
      <p>性格与选择 · 先看已知资料，再谈可能解释</p>
      <p data-claim-ids="J-001">合成样本在自述中提到，遇到复杂任务时会先整理线索。这里引用的是自述，而非从出生资料推导的事实。</p>
      <aside data-disclosure-id="limit-personality"><p>适用边界：这条观察来自单次自述，仍需结合不同情境中的反例修订。</p></aside>
      <figure class="chart-container" data-chart-id="chart-personality-01" data-representation="measured">
        <figcaption>合成样本的已记录分数</figcaption>
        <p class="chart-description" id="chart-personality-01-desc">表格逐项列出合成样本提供的数据；没有提供的项目不会补零。</p>
        <div class="chart-scroll" role="region" tabindex="0" aria-labelledby="chart-personality-01-caption" aria-describedby="chart-personality-01-desc">
          <table class="chart-data">
            <caption id="chart-personality-01-caption">已提供项目（量表分数）</caption>
            <thead><tr><th scope="col">项目</th><th scope="col">原始值</th></tr></thead>
            <tbody><tr><th scope="row">项目甲</th><td data-value-ref="fixture#/scores/item" data-value="12" data-unit="分" data-precision="0">12 分</td></tr></tbody>
          </table>
        </div>
        <p class="chart-note">数据来源：合成验收资料；不代表能力高低。</p>
      </figure>
      <p><a href="#appendix-personality">查看性格数据与方法</a></p>
    </section>

    <section class="book-section" data-content-kind="body" data-section-id="relationships" id="ch-relationships" aria-labelledby="relationships-title">
      <h2 class="section-title" id="relationships-title">把分歧变成一次可讨论的请求</h2>
      <p>关系主题 · 描述双方可观察的做法，不推断身份或结果</p>
      <div id="module-synastry" data-module="synastry"><p>合盘模块只在取得双方资料且用户请求时出现；本例不含个案结论。</p></div>
    </section>

    <section class="appendix" data-content-kind="appendix" id="appendix" aria-labelledby="appendix-title">
      <h2 class="appendix-title" id="appendix-title">附录</h2>
      <details class="appendix-entry" data-appendix-id="appendix-personality" id="appendix-personality">
        <summary>性格数据与方法</summary>
        <div class="appendix-body"><p>本例的合成分数用于演示数据绑定结构，不构成心理测量结论。</p><a class="appendix-back" href="#ch-personality">返回性格与选择</a></div>
      </details>
    </section>
    <footer class="colophon">合成示例 · 用于说明成品结构与阅读层级</footer>
  </main>
</body>
</html>
```

## 3. 视觉、可读性与打印规则

- 页面底色 `#fafaf8`、正文 `#1a1a1a`、次文 `#5a5a5a`、强调 `#8a1a1a`；分类色沿用蓝 `#2c5f7c`、绿 `#356746`、金 `#775e35`。`#d5d2c8` 仅作装饰线。颜色不能作为唯一信息编码；正文、次文与分类色在底色上的对比度均达到普通文字 4.5:1。
- 标题使用系统宋体（Songti SC / STSong / SimSun），正文使用系统黑体（PingFang SC / Microsoft YaHei）；不加载网络字体。屏幕正文 17px、行高 1.9、内容宽度上限 44rem；标题层级 32/26/20px。320–430px 使用 20px 页边距。
- 图与解释紧邻。所有图复用 `figure/figcaption/.chart-description/.chart-scroll/.chart-data` 与 `data-chart-id/data-value-ref/data-claim-ids`；复杂图保留最小可读画布，只在键盘可聚焦的 `.chart-scroll` 局部横滚。320、390、430px 下整页无横移。判断 SVG 实际字号须以屏幕和 PDF 渲染结果为准。
- A4 页边距上 18mm、下 16mm、左右各 14mm；正文 12pt、行高 1.75；引文 11.5pt；图注/附录说明 10pt；表格不低于 9.5pt；图内信息字不低于 9pt；页眉页脚 8pt。这些是本产品排版底线，不等于无障碍字号要求。
- P06 使用 `.ziwei-grid`：屏幕最小宽 600px，宫名及宫内文字至少 14px，由 `.chart-scroll` 局部滚动；打印宽 100%、宫内文字 10pt，完整盘优先容纳在一页，辅星过多则移至紧邻线性表，不缩字。P11 分面板放入 `.chart-scroll`，面板文字屏幕至少 14px、打印至少 9pt；时间语义不同则保持上下独立，不连线冒充同时发生。
- 打印样式集中在唯一 `<style>` 中，不增加后置覆盖层。打印不得隐藏、裁切图表数据表；长表可分页并重复 `thead`。图题、`.chart-description` 与图形本体（`.chart-scroll` 内的 SVG 或十二宫格）必须同页，图后的 `.chart-data` 长表可以分页；图形本体高于可用页高时按语义拆出说明或长表，不由导出器整体缩小。不得对整章或整份附录设置 `break-inside: avoid`。

## 4. 常用语义类

`book-title`、`book-subtitle`、`opening-quote`、`book-toc`、`section-title`、`subsection-title`、`disclosure`、`book-section`、`chart-container`、`chart-scroll`、`chart-description`、`chart-note`、`chart-data`、`ziwei-grid`、`ziwei-cell`、`timeline-panels`、`timeline-panel`、`appendix`、`appendix-entry`、`appendix-body`、`appendix-back`、`colophon`。以上类及骨架中的 CSS 在唯一 `<style>` 中各定义一次；若成品需扩展，只能在同一规则集中增加定义，不保留旧模板/后置补丁两套规则。
