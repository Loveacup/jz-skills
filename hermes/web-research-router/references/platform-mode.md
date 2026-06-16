# Platform Mode 🔌 — Agent-Reach 社交/视频/论坛/RSS 通道

> **Read when:** query 涉及社交媒体 / 视频 / 论坛 / 垂直社区 / RSS，5 个公网搜索引擎（Exa/Brave/Tavily/web_search/SearXNG）召不回平台原生内容时。
> **定位:** platform mode 是 v3.10 在五模式之外新增的**第 6 个补充模式**，调用 [Agent-Reach](https://github.com/Panniantong/Agent-Reach) 的多后端通道。**不替换 Exa/Brave/Tavily 主链路。**

---

## 0. 为什么要它（5 引擎的结构性盲区）

WRR 的 5 个引擎全在公网开放搜索空间。以下内容**默认搜不到或召回质量极差**：

| 盲区 | 公网引擎表现 | platform mode 通道 |
|------|------------|-------------------|
| Twitter/X 口碑、当事人发言 | 无解（登录墙） | `opencli twitter` |
| Reddit 帖子 / 讨论串 | 匿名 `.json` 已封 403 | `opencli reddit` |
| B站视频内容 / 弹幕 / 字幕 | 召不回站内 | `bili` + `opencli bilibili subtitle` |
| 小红书笔记 / 评论 | 召不回站内 | `opencli xiaohongshu` |
| YouTube 字幕 / 评论 | 无字幕通道 | `yt-dlp` |
| V2EX 主题 / 回复 | 召回零散 | V2EX 公开 API |
| 雪球行情 / 热帖 | 召不回 | 雪球公开 API |
| 小宇宙播客内容 | 音频无法搜 | `agent-reach transcribe` |
| RSS 订阅源 | 无订阅概念 | `feedparser` |

---

## 1. Step P0 — 先 doctor 再调（强制）

每次 platform mode 激活，**第一件事**跑体检，按各平台 `active_backend` 字段选命令组：

```bash
agent-reach doctor --json
```

**规则：**
- ✅ `status: ok` → 用 `active_backend` 对应命令组（见 §3）
- ⛔ `status: off`（当前实测 `linkedin` / `exa_search`）→ **静默跳过，不报错**
  - `exa_search` off 无所谓——本 router 已有 Exa 主力引擎，重叠通道无需配
  - `linkedin` off——需 `mcporter config add linkedin ...` 才激活
- ⚠️ 多后端平台（小红书/Reddit/Twitter/B站）的 `active_backend` 随登录态/环境变化，**不要硬编码命令**

**doctor 实测基线（2026-06-17，桌面环境）：11/13 ok**

| 通道 | status | active_backend | 交互环境? |
|------|:--:|----------------|:--:|
| github | ok | gh CLI | 否 |
| twitter | ok | OpenCLI | **是** |
| youtube | ok | yt-dlp | 否 |
| reddit | ok | OpenCLI | **是** |
| bilibili | ok | bili-cli | 否（字幕需 OpenCLI=是） |
| xiaohongshu | ok | OpenCLI | **是** |
| xiaoyuzhou | ok | groq-whisper | 否（需 Groq key） |
| v2ex | ok | V2EX API (public) | 否 |
| xueqiu | ok | Xueqiu API | 否（需 Cookie） |
| rss | ok | feedparser | 否 |
| web | ok | Jina Reader | 否 |
| linkedin | **off** | — | （未配置） |
| exa_search | **off** | — | （与 WRR Exa 重叠，无需） |

---

## 2. 触发词 → 通道映射表

query 命中以下任一类即考虑 platform mode：

| 类别 | 触发词 | 路由通道 |
|------|--------|---------|
| **平台名** | twitter / x / 推 / 推特 | twitter |
| | reddit / r/ | reddit |
| | b站 / bilibili / 哔哩哔哩 | bilibili |
| | 小红书 / xhs / 红书 | xiaohongshu |
| | youtube / yt / 油管 | youtube |
| | v2ex | v2ex |
| | 雪球 / xueqiu / 股票行情 | xueqiu |
| | 小宇宙 / 播客 / podcast | xiaoyuzhou |
| | rss / 订阅源 / feed | rss |
| **动作+平台** | 搜推 / 看看推上 / 推特上搜 | twitter |
| | 看reddit / reddit 上搜 | reddit |
| | b站搜 / 上b站看 | bilibili |
| **内容类型** | 推文 / tweet | twitter |
| | 帖子 / 讨论串 / 楼 | reddit / v2ex |
| | 弹幕 / 字幕 | bilibili / youtube |
| | 笔记 | xiaohongshu |
| | 播客 / 转录 | xiaoyuzhou |
| | 口碑 / 评价 / 大家怎么说 | twitter + reddit（多平台交叉） |

> **多义消解:** "x" 单字母歧义大；结合上下文（"x.com" / "马斯克的 x" → twitter；"x 项目源码" → github / discovery mode）。不确定时按 `research-modes.md` 的"When to ask"问用户。

---

## 3. 各通道命令速查

> 完整命令组与多后端重试链见 Agent-Reach 自带文档 `~/.claude/skills/agent-reach/references/{social,video,web}.md`。下面是 platform mode 路由够用的核心命令。

### Twitter / X（⚠️ 交互环境 / OpenCLI）

```bash
opencli twitter search "query" -f yaml      # 搜推文（首选，复用浏览器登录态）
opencli twitter user-posts @user -f yaml    # 用户时间线
opencli twitter article URL_OR_ID -f yaml   # 长文 / X Article
# search 失败重试链：直接重试 → twitter search "query" -n 10（twitter-cli）→ 改用 twitter feed 绕路
```

### Reddit（⚠️ 交互环境 / 无零配置路径）

```bash
opencli reddit search "query" -f yaml       # 搜帖子（首选）
opencli reddit read POST_ID -f yaml         # 读帖子全文 + 评论
opencli reddit subreddit LocalLLaMA -f yaml # 浏览 subreddit
# 服务器备选：rdt search "query" --limit 10（需 rdt login）
```

### B站 / Bilibili（免登录，bili-cli）

```bash
bili search "query" --type video -n 5       # 搜视频（免登录）
bili video BVxxx                            # 视频详情（标题/UP/播放/字幕可用性）
bili hot -n 10                              # 热门
opencli bilibili subtitle BVxxx             # 字幕（⚠️ 需桌面 Chrome）
# ⚠️ 不要用 yt-dlp 读 B站——风控 412 全面拦截
```

### 小红书 / XiaoHongShu（⚠️ 交互环境 / OpenCLI）

```bash
opencli xiaohongshu search "query" -f yaml  # 搜笔记
opencli xiaohongshu note "NOTE_URL" -f yaml # 读笔记正文+互动（用搜索结果的完整 URL，含 xsec_token）
opencli xiaohongshu comments NOTE_ID -f yaml
# ⚠️ xsec_token 机制：不能用裸 note_id 直读，先搜索拿完整 URL 再读；操作间隔 2-3 秒防验证码
```

### YouTube（免登录，yt-dlp）

```bash
yt-dlp --dump-json "ytsearch5:query"        # 搜视频
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --skip-download -o "/tmp/%(id)s" "URL"
cat /tmp/VIDEO_ID.*.vtt                      # 读字幕
agent-reach transcribe "URL"                 # 无字幕兜底：Whisper 转写（需 Groq key）
```

### V2EX（免登录，公开 API — 最稳）

```bash
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"
curl -s "https://www.v2ex.com/api/topics/show.json?node_name=python&page=1" -H "User-Agent: agent-reach/1.0"
curl -s "https://www.v2ex.com/api/replies/show.json?topic_id=TOPIC_ID&page=1" -H "User-Agent: agent-reach/1.0"
```

### 雪球 / Xueqiu（公开 API，需登录 Cookie）

```bash
# 行情 / 搜索 / 热帖 / 热股，经 agent-reach 通道调用（需 Cookie）
agent-reach doctor --json   # 确认 xueqiu active_backend，再按提示调用
```

### 小宇宙播客（需 Groq key）

```bash
~/.agent-reach/tools/xiaoyuzhou/transcribe.sh --polish "https://www.xiaoyuzhoufm.com/episode/EPISODE_ID"
# 输出 Markdown 到 /tmp/；--polish 用 Llama 3.3 70B 补标点+分段
```

### RSS（免登录，feedparser）

```bash
python3 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

### 通用网页兜底（Jina Reader）

```bash
curl -s "https://r.jina.ai/URL"             # 任意网页 → markdown
```

---

## 4. 输出映射规则（CLI 原始信源 → WRR source map）

🛑 **Agent-Reach CLI 吐出的是「原始信源」，不是答案。** 必须经 WRR 标准管线，禁止把 CLI 输出直接当结论写。

### 管线四步

1. **extractor** — 对每条 CLI 结果跑 verbatim quote 抽取（见 `fetch-extract-pattern.md`），只留与 sub-query 相关的原文，不综合、不改写。
2. **source map 条目** — 每条信源生成一条 source_map（schema 见 `source-map-schema.md`），字段映射如下表。
3. **cross-check** — 社交结论（口碑/单方说法/数字）的关键 claim 必须用 Exa/Brave 公网交叉，或多平台交叉（Twitter ↔ Reddit）。
4. **三分栏 + `[s<id>]`** — 社交口碑/观点入「推断 (Inference)」或「冲突缺口 (Conflicts & Gaps)」，**非「已确认 (Confirmed)」**（除非已被公网一手源 cross-check 过）。

### CLI 输出 → source_map 字段映射

| source_map 字段 | 取值 |
|----------------|------|
| `provider` | `agent-reach` |
| `platform` | `twitter` / `reddit` / `bilibili` / `xiaohongshu` / `youtube` / `v2ex` / `xueqiu` / `xiaoyuzhou` / `rss` |
| `source_tier` | **`social`**（社交/UGC 信源——区别于 primary/official/news） |
| `title` | 推文首行 / 帖子标题 / 视频标题 / 笔记标题 |
| `url` | CLI 结果里的完整 URL（小红书必须含 `xsec_token`） |
| `domain` | `twitter.com` / `reddit.com` / `bilibili.com` / `xiaohongshu.com` 等 |
| `extracted_quotes[].text` | CLI 输出里 `text` / 正文字段的 **verbatim** 原文 |
| `evidence_status` | `extracted`（抽过 quote）；经公网 cross-check 升 `verified` |
| `confidence` | 社交单方说法默认 `low`/`medium`；多平台一致或公网佐证升 `high` |
| `notes` | 互动数据（点赞/回复/播放）、发布时间、是否官方账号、是否需要交叉 |

> **互动数据是信号不是事实**：高赞 ≠ 真实。点赞/回复/播放数放 `notes`，用于判断代表性，不进 `confirmed`。

---

## 5. 交互环境需求标注

某些通道依赖**本地浏览器登录态**（OpenCLI 复用 Chrome session），在无头 / SSH / Docker / cron 环境**不可用**：

| 通道 | 交互环境? | 无头环境替代 |
|------|:--:|------------|
| twitter (OpenCLI) | **需要** | `TWITTER_AUTH_TOKEN`+`TWITTER_CT0` 环境变量 + twitter-cli；或回退 `web_search site:twitter.com` |
| reddit (OpenCLI) | **需要** | `rdt-cli` + 手写 Cookie；或回退 `web_search site:reddit.com` |
| xiaohongshu (OpenCLI) | **需要** | `xiaohongshu-mcp` 扫码登录；或回退 `web_search` |
| bilibili 字幕 (OpenCLI) | **需要** | `bili-cli` 只读搜索/详情免登录；字幕无替代 |
| bilibili 搜索/详情 (bili-cli) | 否 | — |
| youtube (yt-dlp) | 否 | — |
| v2ex / rss (公开 API) | 否 | — |
| xueqiu | 否（需 Cookie） | — |
| xiaoyuzhou | 否（需 Groq key） | — |

**规则：** platform mode 报告里凡用了「需要交互环境」的通道，**必须在结论或 notes 标注**——否则换到 cron/headless 复跑会静默失败。doctor 在无头环境会把这些通道标 `off`，照 §1 静默跳过 / 回退即可。

---

## 6. DO / DON'T

**DO ✅**
- 先 `agent-reach doctor --json` 体检，按 `active_backend` 选命令组
- 不可用通道**静默跳过**，或回退 `web_search site:平台域名`
- CLI 输出全程经 extractor → source map（`source_tier: social`）→ cross-check → 三分栏
- 口碑/评价类 query 默认**多平台交叉**（Twitter + Reddit）再下结论
- 用 `-f yaml` / `--json` 拿结构化输出（对抽 quote 友好）
- 标注「需要交互环境」的通道；互动数据进 `notes`
- 完成较大任务后顺手 `agent-reach check-update`（一个 API 调用，有新版在收尾附一句）

**DON'T ❌**
- ❌ 跳过 doctor 直接硬调 OpenCLI（无头环境必挂 / AUTH_REQUIRED）
- ❌ 把 CLI 原始输出直接当结论写（绕过 extractor = 幻觉 + 伪引用）
- ❌ 把社交单方说法 / 高赞推文当「已确认事实」（社交信源默认进推断/冲突缺口）
- ❌ 用 yt-dlp 读 B站（412 风控全面拦截）
- ❌ 小红书用裸 note_id 直读（xsec_token 机制，先搜索拿完整 URL）
- ❌ 高频批量调小红书/Twitter（触发验证码 / IP 风控；间隔 2-3 秒）
- ❌ 让 platform mode 替换 Exa/Brave 主链路（它是补充，不是替代）
- ❌ 在 agent workspace 建文件（临时输出放 `/tmp/`）

---

## 7. 实测验证记录（2026-06-17）

集成时三通道端到端跑通，确认 CLI 输出可映射到 source map：

- **V2EX**（公开 API）：`curl .../topics/hot.json` → 返回 10 条热门主题（node/title/replies/url），可直接填 source_map。
- **bilibili**（bili-cli 免登录）：`bili search "claude" --type video -n 3` → YAML 含 bvid/title/author/play/duration。
- **twitter**（OpenCLI）：`opencli twitter search "claude opus" -f yaml` → 含 id/author/bio/text 结构化字段，verbatim text 可直接抽 quote。

> doctor 实测 11/13 ok（linkedin / exa_search = off）。exa_search 与 WRR 现有 Exa 重叠，无需配置；linkedin 需 `mcporter config add` 激活。
