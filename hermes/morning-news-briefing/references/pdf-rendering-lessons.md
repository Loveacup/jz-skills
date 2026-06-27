# PDF 渲染教训：LOCKED 模板 vs 手写 CSS

日期 2026-06-03 · 关联：morning-news-briefing v4.0

## 三次渲染迭代，前两次全翻车

核心教训：**render_pdfs.py 必须使用 LOCKED 模板，禁止自创 CSS。**

### v1：手写 Markdown→HTML 转换器（失败）

- 逐行 if-else 状态机，不处理嵌套结构
- Google Fonts 嵌入 → PDF 膨胀到 2.7MB
- Headless Chromium 下 Google Fonts 加载不稳定
- 块级元素闭合逻辑有 bug
- 结果：排版重叠/错乱

### v2：自创 CSS（失败）

- 完全废弃 LOCKED 模板，自己写 MOBILE_CSS/A4_CSS
- Cover 页、卡片、分析块等精心调试的 CSS 全丢
- 结果：用户投诉"版面设置全丢了"

### v3：LOCKED 模板填充器（成功）

正确做法：
1. 解析 Markdown → 结构化数据
2. 读取 `assets/mobile-template.html` / `assets/standard-template.html`
3. 替换 `{{PLACEHOLDER}}` 占位符
4. Playwright 渲染 → PDF

### 教训

- **永不自创 CSS** — LOCKED 模板含历史排版规范
- **模板占位符 > MD→HTML 转换器**
- **用系统字体，不用 Google Fonts** — headless 不可靠
