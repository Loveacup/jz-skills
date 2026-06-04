# DailyBrief 项目 lessons 吸收记录

> 吸收自 [leiting-eric/DailyBrief](https://github.com/leiting-eric/DailyBrief) 项目的已批准优点。
> 仅记录经过门下封驳的已确认 lessons，不得削弱现有早新闻硬门槛。

## 1. 结构化 Source Registry 模式

DailyBrief 使用单一 JSON 文件 `sources.config.json` 作为信源注册中心，每个源带结构化元数据：

```json
{
  "id": "source-id",
  "name": "显示名",
  "type": "rss | api | scrape",
  "url": "https://...",
  "category": "tech | finance | politics",
  "subcategory": "ai-news | world | news",
  "enabled": true | false,
  "useCurl": false,
  "lang": "zh | en",
  "locales": ["zh", "en"],
  "notes": "为何添加/禁用/注意事项"
}
```

**已批准的吸收要点：**
- ✅ disabled 源保留在配置中并写清 `notes` 说明原因，不删除（便于后续重新评估）
- ✅ 为每个源标注 `lang`（是否已是中文）和 `locales`（中英模式都可用还是仅其一）
- ✅ 统一管理优于分散在 prompt 中硬编码

## 2. Locale 驱动的信源筛选

DailyBrief 通过 `locales` 数组控制每个源在 zh/en 模式下是否可用：

| 模式 | 有效信源数 | 关键差异 |
|------|-----------|---------|
| `REPORT_LOCALE=zh` | 23 个源 | V2EX + LinuxDo（中文社区）替换 Hacker News + Reddit |
| `REPORT_LOCALE=en` | 22 个源 | Hacker News + Reddit（英文社区）替换 V2EX + LinuxDo |

**已批准的吸收要点：**
- ✅ 早新闻各板块的中/英文源可分离管理，不混在一起计数
- ✅ 切换 locale 时自动替换社区讨论源，不额外增加搜索负担

## 3. 社区讨论源模式

DailyBrief 已验证以下社区源可用且无质量风险（对应 R9 决策：Reddit 禁用）：

| 源 | API 方式 | 启用状态 | 说明 |
|---|---------|---------|------|
| **V2EX 热帖** | `https://www.v2ex.com/api/topics/show.json`（公开 JSON API） | ✅ 已启用 | 中文社区，dev 向热点 |
| **LinuxDo 热帖** | `https://linux.do/top.rss?period=daily`（Discourse RSS） | ✅ 已启用 | 中文社区，AI/dev/devops 向；可回退 `/latest.rss` |
| **Hacker News** | `https://hacker-news.firebaseio.com/v0`（Firebase API） | ✅ 已启用（en 模式） | 英文社区，技术向 |
| **掘金** | RSS | ❌ 已禁用 | 信噪比低 |
| **Reddit (wallstreetbets/investing/stocks/ChinaStocks)** | RSS + `useCurl: true` | ❌ 全部禁用 | 已确认质量风险，保持禁用 |

**已批准的吸收要点：**
- ✅ V2EX API 极轻量（公开 JSON，无需 key），可作为中文社区讨论补充
- ✅ LinuxDo 的 Discourse RSS 在 Cloudflare WAF 后面，偶有失败，不可加激进重试（burst 会封 IP）
- ✅ Hacker News Firebase API 稳定可靠，适合英文模式
- ✅ 社区讨论源的质量门槛高于媒体源，谨慎启用

## 4. 交易数据模块架构

DailyBrief 的交易模块使用 Yahoo Finance 公开端点获取实时行情 + 技术指标，结构如下：

```
lib/trading/
  watchlist.ts    # 标的清单（symbol + displayName + group）
  indicators.ts   # SMA/RSI/MACD 技术指标计算
  quote.ts        # 实时报价获取
  commentary.ts   # LLM 生成每日交易点评
```

**已批准的吸收要点（对应 Trading 方案B）：**
- ✅ Python + akshare 做 A 股/中概标的（基于 `lib/trading/` 结构启示，但不限制实现细节）
- ✅ 标的清单与 fetch 逻辑分离（类似 `watchlist.ts` 模式）
- ✅ 交易点评由 LLM 单独完成（类似 `commentary.ts`），不混在新闻摘要中
- ✅ DailyBrief 已验证金融数据公开 RSS 源可用性：
  - `Bloomberg Markets`: `https://feeds.bloomberg.com/markets/news.rss` ✅
  - `WSJ Markets`: `https://feeds.a.dj.com/rss/RSSMarketsMain.xml` ✅
  - `Financial Times`: `https://www.ft.com/companies?format=rss` ✅
  - `The Economist Finance`: `https://www.economist.com/finance-and-economics/rss.xml` ✅

## 5. 单源错误非致命（Per-Source Error Resilience）

DailyBrief 核心原则：**单个源抓取失败不得导致整体运行失败。**

```typescript
// daily.ts — 每个源独立 try/catch
for (const source of enabledSources) {
  try {
    const articles = await fetchSource(source);
    allArticles.push(...articles);
  } catch (e) {
    logger.warn(`${source.id} FAILED — ${e.message}`);
    // 继续下一个源
  }
}
```

**已批准的吸收要点：**
- ✅ 早新闻检索时，某个媒体源不可用（web 搜索无结果/URL 失效）不阻断整条链
- ✅ 多源并行搜索中，单源失败仅为日志记录事项，不影响整体质量
- ✅ 御史检查时注意：某个源缺失 ≠ 新闻质量不合格（只要总体 ≥50 家即可）

## 6. 缓存 + 重渲染模式

DailyBrief 的 `npm run render` 命令可在 <1s 内重新生成 HTML，无需重新调用 LLM：

```
daily_reports/<YYYY-MM-DD>/
  <date>.html         # 渲染产物
  <date>.json         # 缓存 sidecar（含完整元数据）
  <date>-articles.json  # 原始文章缓存
```

**已批准吸收要点：**
- ✅ 早新闻 PDF 渲染也可考虑缓存模式：渲染卡只读已批准的数据 artifact，不重新搜索
- ✅ 这与现有 `references/mobile-pdf-pending-confirm-recovery.md` 的「不要重跑全链」原则一致

## 7. 启动日志模式

`scripts/run-daily.mjs` 的 logger 模式：

```javascript
// 实时 tee stdout+stderr 到 dated log 文件
const logFile = fs.createWriteStream(`logs/daily-${today}.log`, { flags: 'a' });
proc.stdout.pipe(logFile);
proc.stderr.pipe(logFile);
```

**已批准吸收要点：**
- ✅ 早新闻 kanban 链也可考虑在关键步骤记录结构化日志
- ✅ 便于调试「XX 没出来」类问题：看日志比重新跑完整链更快

## 8. GitHub Actions 部署 + 时区感知 Cron Gate

DailyBrief 的 GitHub Actions workflow 使用智能 gate 模式：

```yaml
# workflow 设为每小时跑一次
cron: '0 * * * *'

# gate 任务用 REPORT_TZ 判断当前小时是否匹配
# 匹配才往下跑 build，否则秒退
```

这个 gate 模式让 cron 在 UTC 每小时跑，但只在用户指定时区的指定小时才真正执行，夏令时自动跟随 IANA 时区。

**已批准吸收要点：**
- ✅ 当前早新闻走 Hermes kanban 链，不直接依赖 GH Actions，gate 模式不直接适用
- ✅ 但如果未来需要定时触发早新闻，可参考此 gate 模式避免时区计算错误

## 附录：DailyBrief 已验证信源 API 清单

以下为 DailyBrief 已验证可用的公开 API/RSS，供早新闻扩展参考：

### AI/科技类（当前早新闻未覆盖，可拓展）

| 源 | 类型 | URL | 状态 |
|---|------|-----|------|
| OpenAI News | RSS | `https://openai.com/news/rss.xml` | ✅ 稳定 |
| DeepMind Blog | RSS | `https://deepmind.google/blog/rss.xml` | ✅ 稳定 |
| Hugging Face Blog | RSS | `https://huggingface.co/blog/feed.xml` | ✅ 稳定 |
| TLDR AI | RSS | `https://tldr.tech/api/rss/ai` | ✅ 稳定 |
| Smol AI News | RSS | `https://news.smol.ai/rss.xml` | ✅ 稳定 |
| Latent Space | RSS | `https://www.latent.space/feed` | ✅ 稳定 |
| MIT Tech Review AI | RSS | `https://www.technologyreview.com/topic/artificial-intelligence/feed` | ✅ 稳定 |
| GitHub Trending | scrape | `https://github.com/trending` | ✅ 稳定 |
| V2EX 热帖（zh） | API | `https://www.v2ex.com/api/topics/show.json` | ✅ 轻量公开 |
| LinuxDo（zh） | RSS | `https://linux.do/top.rss?period=daily` | ⚠️ Cloudflare 偶阻 |
| Hacker News（en） | API | `https://hacker-news.firebaseio.com/v0` | ✅ 极稳定 |

### 国际时政补充

| 源 | 类型 | URL | 状态 |
|---|------|-----|------|
| DW中文（zh） | RSS | `https://rss.dw.com/rdf/rss-chi-all` | ✅ 稳定 |
| The Diplomat | RSS | `https://thediplomat.com/feed/` | ✅ 稳定 |
| NPR World | RSS | `https://feeds.npr.org/1004/rss.xml` | ✅ 稳定 |
| The Guardian World | RSS | `https://www.theguardian.com/world/rss` | ✅ 稳定 |
| BBC World | RSS | `https://feeds.bbci.co.uk/news/world/rss.xml` | ✅ 稳定 |
| NYT World | RSS | `https://rss.nytimes.com/services/xml/rss/nyt/World.xml` | ✅ 稳定 |
| Al Jazeera | RSS | `https://www.aljazeera.com/xml/rss/all.xml` | ✅ 稳定 |

### 财经补充

| 源 | 类型 | URL | 状态 |
|---|------|-----|------|
| 华尔街见闻（zh） | RSS | `https://rsshub.app/wallstreetcn/news/global` | ❌ 禁用（RSSHub 不稳定） |
| FT中文网（zh） | RSS | `https://www.ftchinese.com/rss/news` | ❌ 禁用 |
| MarketWatch | RSS | `https://feeds.content.dowjones.io/public/rss/mw_topstories` | ❌ 禁用 |

---

> 本文件由工部于 2026-05-25 吸收 DailyBrief 项目 lessons 撰写。
> 下次吸收前应复查 DailyBrief 仓库是否有新增已验证源或架构变化。
