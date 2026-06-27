# 新闻管线抓取断裂：根因与修复

> 2026-06-02 诊断 — 三省六部早新闻产出质量 D 级（956B 标题条 + 幻觉数据）。
> 对比 GitHub v3.0.0 设计与实际执行路径，定位断裂点。

## 断裂链（7 步坍塌）

```
1. 搜索正常 ✅ → Tavily/Brave/Exa 三引擎真发了，查询词切题
2. 抓取断裂 ❌ → web_extract SSRF 守卫拦截所有公网 URL（"Blocked: private/internal network"）
3. 引用照写 ❌ → agent 仍然把未读取的 URL 标为"来源"（伪引用）
4. 模型脑补 ❌ → LLM 用训练数据填充高精度数字（苹果 $111.2B、DeepSeek 0.025 元、英伟达 $5.2T）
5. 摘要无视 ❌ → 写 brief 的 protocol agent 0 搜索、0 抓取，只重排版
6. 交叉验证造假 ❌ → "多源交叉验证"声称为真，实则 3/4 管线打开页面数 = 0
7. 产出不可信 🔴 → 956B 标题条，数字全是幻觉，但外观精美
```

## 根因

`web_extract` 的 SSRF 守卫误判所有公网 HTTPS URL 为内网地址 → 一律拦截。
这不是 GitHub 特有问题——新闻站点（reuters.com / xinhuanet.com 等）全部被拦。

## 修复（已写入 morning-news-briefing v3.0.0 设计但未执行）

早新闻 v3.0.0 的 `search-workflow.md` 明确指定：
- **Lane B（en）全文提取**: `mcp_exa_web_fetch_exa` 取 5-8 篇高信号正文
- **Lane C 价格校验**: Tavily 三源交叉比对

但实际运行时，agent 未遵循此设计，而是走了 `web_extract` → 全断。

## 治理规则（AT-7 质量门草案）

审计报告建议的早新闻质量门：
- ≥8 条，每条带**已成功抓取**的源 URL + 时间戳 + ≥2 源印证
- 未抓取的 URL 不得出现在引用中
- 缺源即拒绝发布，不产空白 PDF

## 补充诊断：版本漂移与引擎实测 (2026-06-02 CC agent team 深度分析)

### 版本漂移根因

通过三方材料交叉对比发现，早新闻 v4.0.0 **对齐的是过时的 WRR v3.2**，而非当前 WRR v3.7+：

| 材料 | 版本 | SearXNG 定位 | 实际引擎状态 |
|------|------|-------------|-------------|
| 早新闻 v4.0 SKILL.md | WRR v3.2 对齐 | 默认起手 | — |
| WRR v3.7 tool-names.md | v3.7 | 降级为兜底 | SearXNG 实例已损坏 |
| WRR v3.9 (当前) | v3.9 | 仅兜底/弃用 | Google 死 / Bing 降级 / DDG CAPTCHA |

**后果**：agent 遵守 v4.0 SKILL.md → 调坏掉的 SearXNG 起手 → 噪声/空。agent 不遵守走默认 → 撞 web_extract → 幻觉数字。**两条路都通向 D 级。**

### Tavily Extract 中文源实测 (2026-06-02)

四家中文主流媒体全测，`tavily_extract` 零拦截、全部返回正文：

| 源 | extract 结果 | 正文量 | 问题 |
|----|-------------|--------|------|
| 新华网 | ✅ | 11,892 字符 | search 给的是栏目搜索页，导航噪声重 |
| 人民网 | ✅ | 10,487 字符 | search 给的是 2017 年繁体旧页 |
| 澎湃新闻 | ✅ | 9,030 字符 | 真文章，但是旧稿；混 Next.js logo 噪声 |
| 财新 | ✅ | 7,631 字符 | search 给的是免费列表页，未测到付费墙 |

**关键发现**：
- **Extract 层（抓取）**：Tavily Extract 对中文公开页技术上完全可行 ✅
- **Search 层（发现）**：Tavily 的中文索引新鲜度极差（返回 2017/7月旧页），**不可**用于中文新闻发现 ❌
- **去噪**：raw_content 混大量导航/logo，必须靠 WRR 的 fetch-extract-pattern (verbatim extract) 去噪

### 引擎按场景推荐 (更新)

| 场景 | 发现引擎 | 抓取引擎 |
|------|---------|---------|
| 中文新闻发现 | **Brave** (9/9，locale-aware，时效首选) + Exa 语义补 | Tavily Extract + Exa Fetch |
| 英文新闻发现 | **Exa** (语义精准) + Brave 交叉 | Exa Fetch + Tavily Extract |
| 科技/AI 中文资讯 | **aihot API** (零鉴权，publishedAt 时效) + Brave 补盲 | Tavily Extract |
| 价格/数据校验 | Exa + Brave 双主力 | Tavily (三源交叉) |
| 付费墙内容 | CDP browser fallback | 仅财新等需要登录态的场景 |

## 通用教训

对于任何自动化内容管线：
1. **抓取工具选择**：优先用 Exa Fetch / Tavily Extract，`web_extract` 不可靠
2. **硬规则**：未成功抓取的 URL ≠ 来源。禁止"搜索到了但没打开"的引用
3. **数字校验**：价格/市值/营收等数字必须三源交叉，不能来自模型记忆
4. **审计方法**：对比设计文档（SKILL.md）与实际执行日志（agent.log），找工具调用差异
5. **版本漂移检查**：下游 skill 引用的上游 skill 版本号必须定期校验——早新闻 v4.0 锁死 WRR v3.2 导致退步
6. **引擎分层思维**：发现(search)和抓取(extract)是不同的能力层，不可用同一引擎同时承担——Tavily extract 中文可行但 search 中文不可用
