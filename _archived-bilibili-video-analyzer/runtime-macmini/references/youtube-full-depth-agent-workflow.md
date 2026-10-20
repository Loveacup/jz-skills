# YouTube 视频全量深度分析：Agent 手工编写工作流

> **状态**：YouTube 引擎（`fetch_youtube.py` → `video_analysis_engine.py` → `render_markdown()`）目前产出 P2-B2 skeleton 级别报告——各分析章节为 `_骨架占位_` + 证据候选（`> transcript证据：...`）。P2-C writer pipeline（EvidenceMap → SectionContext → HighlightsWriter → LLM writer）对 YouTube 路径尚未接线。
>
> **因此**：在 writer pipeline 落地前，agent 收到 YouTube 深度分析请求时，必须**手工编写**全量 8-section 报告。

## 完整流程

### Step 1: 跑引擎采集

```bash
cd ~/.hermes/skills/bilibili-video-analyzer
python3 scripts/fetch_youtube.py '<url>' --limit 50
# → /tmp/{video_id}_youtube_report.md（骨架，含证据候选）
# → RESULT_JSON 含 metadata/frontmatter/comments/trace
```

引擎报告包含：
- ✅ YAML frontmatter（metadata 完整）
- ✅ §0 Meta + Source Appendix（完整）
- ⚠️ §1–§5：骨架占位 + `> transcript证据：...` 行（逐句转录片段，非分析）
- ❌ §6–§8：空骨架

### Step 2: 阅读全量转录

引擎报告的 transcript evidence 是碎片化嵌入的，不适合直接分析。agent 必须**额外读全量纯文本转录**：

```bash
python3 scripts/fetch_youtube.py '<url>' --text-only --timestamps 2>/dev/null > /tmp/yt_transcript_{video_id}.txt
```

或用 `youtube-transcript-api` 直接抓：
```python
from youtube_transcript_api import YouTubeTranscriptApi
transcript = YouTubeTranscriptApi.get_transcript(video_id)
```

### Step 3: 手工编写全量 8-section 报告

从 0 写报告到 `/tmp/B站笔记_[主题简述]_YYYYMMDD.md`，不要 patch 骨架。

#### 关键写作规则

| 章节 | 规则 |
|:---|:---|
| **YAML** | 遵循 Obsidian vault AGENTS.md：status/type/priority/aliases/tags/created/modified |
| **§0 Meta** | 从 engine report frontmatter + yt-dlp 元数据提取 |
| **§1 Logic Chain** | ≤100 行。表格（叙事弧线）+ Mermaid。**禁止流水账**。逐句引用移到 §4 |
| **§2 Danmaku** | YouTube 无弹幕：写 "YouTube 平台，无弹幕数据。_本节留空。_" 即可 |
| **§2.5 Comments** | 从 engine report 提取 comments。做聚类分析。稀疏时 ≤50 字 |
| **§3 Key Insights** | ≥3 条 × ≥200 字。每条带 verbatim 引用。头用 `### 💡` |
| **§4 Deep Dive** | ≥3 模块 × ≥500 字。每模块含概念定义 + 架构图（Mermaid）+ 多角度分析 + 与用户体系的关联 |
| **§5 Highlights** | ≥5 条。格式：`> "quote" — [⏯](url)` |
| **§6 Knowledge Graph** | 核心概念表 + 交叉引用（链接用户已有资产） |
| **§7 Critical Review** | `### 独特价值` + `### 局限与偏见` + `### 可行动项`。价值/局限用 `- ` bullet（**不用** `1.` 有序列表）。行动项用 `- [ ]` |
| **§8 Appendix** | 数据源 + 工具链 + 时间轴索引 |

#### verify_report.py 格式陷阱（易踩）

- G7 价值/局限 **必须用 `- ` 无序列表**，`1.` 有序列表会被判定为 0 valid
- §3 insight 头 **必须含 💡 emoji**
- §5 highlight **必须用 `>` blockquote**
- Deep Dive 模块头 **必须用阿拉伯数字**：`### 模块 1：` 而非 `### 模块一：`
- section 头 **必须用 `## N.`** 而非 `## §N`

### Step 4: 验证 → 保存

```bash
# 验证
python3 scripts/verify_report.py /tmp/B站笔记_xxx_YYYYMMDD.md

# 保存（必须用 cp，不要用 write_file）
cp /tmp/B站笔记_xxx_YYYYMMDD.md ~/Documents/Obsidian/AlexCai/00-Inbox/
ls -la ~/Documents/Obsidian/AlexCai/00-Inbox/B站笔记_xxx_YYYYMMDD.md
wc -c ~/Documents/Obsidian/AlexCai/00-Inbox/B站笔记_xxx_YYYYMMDD.md

# 再次验证最终路径
python3 scripts/verify_report.py ~/Documents/Obsidian/AlexCai/00-Inbox/B站笔记_xxx_YYYYMMDD.md

# 清理
rm -f /tmp/{video_id}_youtube_report.md /tmp/yt_transcript_{video_id}.txt /tmp/B站笔记_xxx_YYYYMMDD.md
```

## 模式选择

与 Bilibili 路径相同：
- 用户明确指令 + ≥30min → **全量版**（走完整 8-section）
- 用户明确指令 + <20min → **精简版**（verify 用 `--mode condensed`）
- 未明确 → 先展示 metadata，询问

## Known Gap：YouTube Writer Pipeline

当前 P2-C writer pipeline（`build_writer_section_context()` / `write_highlights_section()` 等）对接的是 Bilibili `analyze_video()` 的 `report_plan` + `evidence_map` 数据结构。YouTube 引擎（`fetch_youtube.py` → `video_analysis_engine(platform='youtube')`）使用同一骨架 `render_markdown()`，但 `analyze_video(platform='youtube')` 未走 P2-B `EvidenceMap` 生成链路，因此 writer context adapter 拿不到 YouTube 的 `evidence_map`。

下一步：要么给 YouTube `analyze_video()` 接线 P2-B EvidenceMap，要么给 YouTube 路径写独立的 writer adapter。在此之前，agent 手工编写是 workable 的替代路径。
