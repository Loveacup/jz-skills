---
name: bilibili-video-analyzer
description: >
  type: routine
  深度分析 Bilibili 视频内容，生成结构化知识资产（13,000+ 字 Obsidian 级 Markdown 报告）。
  支持官方字幕、PlayURL 直拉音频、H200 ASR 默认转录，以及 whisper.cpp/mlx-whisper 本机 fallback。功能：弹幕情绪分析、评论深度解读、逻辑拆解、批判审视。
  支持多视频合并分析（同系列/同UP主）。
  🆕 搬运视频支持 YouTube 原字幕/评论跨平台同步（向 bilibili×youtube 演进中）。

  Use when: user provides Bilibili video link (BV号 or full URL), or says 解析B站视频 / analyze bilibili video / bilibili summary / 视频总结 / 弹幕分析 / 分析这个视频.

  DO NOT use for: non-Bilibili videos, general video editing, one-off transcript requests without analysis.
version: 2.6.0
author: "Hermes Agent (v2.6.0: WRR fact-check integration for policy/news videos → references/wrr-fact-check-policy-videos.md)"
---

# Bilibili 视频深度解析器 v2.4

Transform Bilibili videos into structured, searchable, actionable knowledge assets for Obsidian.

## 🚨 Red Flags: Don't Cut Corners on Analysis

| Excuse | Why it's wrong |
|--------|---------------|
| "The video is short, I'll skip ALL sections" | Even a short tutorial gets metadata + insights + action items. But adapt depth to video type—don't force 8-section analysis on a 10-min how-to. |
| "Danmaku is only 1-3 comments, I'll write 300 words about scarcity" | Acknowledge scarcity in ≤50 words and move on. Don't inflate empty data into a full section. "数据不足，跳过" is better than filler. |
| "I'll save to the old clawd path, the user won't notice" | Output path MUST be Obsidian 00-Inbox. Wrong path = lost file. |
| "Subtitles failed, I'll just summarize from memory" | Fallback chain: 官方/AI字幕 → PlayURL 直拉音频 → H200 ASR → whisper.cpp → mlx-whisper. Exhaust fallbacks before summarizing. |
| "We improved fetching, so the project is done" ★ | Wrong priority. Fetching is only the data supply layer; the analysis/content-generation engine is the core product asset. Preserve Alex's distilled old report framework and upgrade it incrementally with BiliNote/GitHub ideas. See `references/content-engine-upgrade-principles-20260630.md`. |
| "I'll replace the old report engine with BiliNote's NoteGenerator/template" ★ | Do NOT replace the old content engine. BiliNote / GitHub projects are additive references for layering, chunking, checkpoints, and recovery; the old full/condensed/merged report framework + Quality Gates remain the baseline. |
| "I'll write the Logic Chain as narrative prose with every quote" ★ | Logic Chain is a **structural overview**, not a transcript retelling. Use **tables (narrative arcs) + Mermaid flowcharts** — keep it under 100 lines. Move verbatim quotes and detailed analysis to Deep Dive / Key Insights. Bloated prose in §1 makes the report unreadable. |
| "I'll skip adding YAML frontmatter, it's just metadata" | Obsidian CLAUDE.md requires frontmatter. Missing = broken knowledge graph. |
| "Report looks thorough, I'll save without running verify_report.py" ★ | Phase 4 STEP 0 is a **blocking gate**. Run `scripts/verify_report.py <草稿>` before saving — "looks thorough" is exactly the judgment the gate exists to catch. Save only on exit 0. |
| "User didn't ask for full analysis, but I'll do it anyway" | **Check first.** Present metadata + ask the user which depth they want. Never assume. |
| "User said to just do it but I showed metadata anyway" ★ | When the user explicitly tells you what to do (整理文档 / 直接分析 / 用bilibili skill 帮我...), skip Phase 0 confirmation. Asking again when they already gave instructions is wasteful. Infer mode from video duration: <20min → 精简版, >=30min → 全量版, unknown → 精简版 (safe default). |
| "Full version report is done at 10KB" ★ | Size is **not** the bar — **Depth Quality Gates** are. 全量版 must pass G3 (≥3 insights × ≥200 字), G4 (≥3 modules × ≥500 字), G5 (≥5 金句), G7 (≥3 价值 + ≥2 局限 + ≥3 行动). A thin report fails gates regardless of KB. Run `scripts/verify_report.py` to check; if a gate fails, expand that section. |
| "`verify_report.py` / coherence / OMP passed, so this can enter Obsidian" ★ | Wrong after BV1zrTq6sEPB. Those are **engineering gates**. Before saving a formal `B站笔记_*.md`, run `scripts/verify_publishable_report.py <report.md>` or `run_quality_gate.py --publishable`; skeleton/debug output, long transcript dumps, and overlong quotes must fail. |
| "I'll use my own section header style, the verify script will be fine" ★ | `verify_report.py` enforces **exact format** requirements that are easy to miss: (a) section headers MUST be `## N.` (NOT `## §N`); (b) Deep Dive module headers MUST use Arabic digits — `### 模块 N：` (matching `\d`) NOT Chinese `### 模块一：`; (c) G7 subsections MUST contain specific keywords: `独特价值` (NOT bare `价值点`), `局限` or `偏见`, `可行动` or `行动项`; (d) G7 value/blind-spot items MUST use `- ` bullet format (NOT `1. ` ordered list); (e) §3 insight headers MUST contain 💡 emoji; (f) §5 highlights MUST use `>` blockquote format. If verify_report.py says "section missing" despite the content being there, check these format rules first. |
| "Deep Dive modules are fixed at 3" ★ | Deep Dive modules are **extensible** — user can request additional modules (e.g. "加一个板块着重研究Codex"). Each module needs: concept definition, architectural context, multi-angle analysis, a Mermaid diagram where applicable, and explicit linkage to the user's own stack where relevant. |
| "I'll guess the danmaku file path" ★ | As of **v2.4** `fetch_danmaku_v2.py`/`fetch_all.py` save danmaku to **`/tmp/{BV号}_danmaku.json`** (BV-prefixed, aligned with comments/subtitle artifacts). Pure-CID input falls back to `/tmp/cid_{数字}_danmaku.json`. The RESULT_JSON `path` field is authoritative — read it, don't guess. |
| "I'll pass the b23.tv short link directly to the scripts" ★ 🆕 | `fetch_all.py` / `fetch_danmaku_v2.py` / `fetch_comments.py` / `fetch_subtitle_auto.py` all require **BV号 format** (e.g. `BV1p2DyB4Ee3`). b23.tv short links, bare video IDs, or full bilibili.com URLs will fail with parse errors. **Always resolve short links first**: `curl -sI -o /dev/null -w '%{redirect_url}' '<b23.tv URL>'` → extract `BV...` from the redirected full URL. Then pass the BV号 to scripts. |
| "fetch_all 字幕失败不是终点，所以我可以直接写完整版" ★ | Wrong. `fetch_all` 字幕失败后必须继续手动排查 PlayURL/H200 ASR，直到拿到 transcript 或明确证明所有 ASR 路径不可用。**无字幕/无 ASR 不得保存正式 full 报告**；只能生成 `预分析_未通过ASR_...`，并在 YAML/标题/正文显式降级。简介/时间轴/金句只能做预分析素材，不能替代 transcript 证据链。详见 `references/asr-evidence-gates-and-single-note-output-20260630.md`。 |
| "LLM writer 失败了，所以报告失败" ★ 🆕 | Wrong. P2-D writer pipeline 是可插拔增强层：`render_markdown(report, provider=None)` 默认保持旧骨架/确定性输出；`--writer-provider cli|deepseek` 失败或 validation fail 时 fallback 到 skeleton 并 `warnings.warn`。CLI 路径优先用 `BILI_WRITER_CLI` / OMP 继承调用方模型配置。见 `references/content-engine-p2d-llm-writer-pipeline-triad-20260701.md`。 |
| "B站 412 = 需要 cookie" ★ | Wrong default diagnosis. Cookie is only login-state assistance. For no-subtitle B站 videos, Hermes runtime should prefer **PlayURL API direct DASH audio per `page.cid` → H200 ASR → local whisper/mlx fallback** before any yt-dlp audio fallback. BiliNote `dm_img` patch helps only **in-process yt-dlp**; it does not protect CLI yt-dlp. See `references/playurl-multip-asr-lock-20260630.md`. |
| "ASR model is fixed" ★ | Wrong. ASR provider/model/path/language are configurable: `BILI_ASR_PROVIDER=auto|h200_asr|whisper_cpp|mlx_whisper`, `BILI_ASR_ENDPOINT`, `BILI_ASR_MODEL`, `BILI_ASR_MODEL_PATH`, `BILI_ASR_LANGUAGE`. Default `auto` is now H200 HTTP ASR → VoiceInk/whisper.cpp → mlx-whisper; explicit provider must not silently fall through. See `references/playurl-multip-asr-lock-20260630.md`. |
| "H200 ASR is available, so set `BILI_ASR_MODEL_PATH=http://...`" ★ | Wrong variable. SURGExZR H200 is an HTTP ASR gateway (`POST /ASR/transcribe`) and is now exposed as `BILI_ASR_PROVIDER=h200_asr` / default `auto` first step. Use `BILI_ASR_ENDPOINT` to override its URL. `BILI_ASR_MODEL_PATH` remains for local whisper.cpp/mlx model paths. Verify short + minutes-long audio before documenting. See `references/h200-asr-vs-bili-asr-20260630.md`. |
| "fetch_all 的 info 是 null，所以我没法写元数据" ★ | `fetch_all.py` can return `info:null` while danmaku/comments still include title/owner and `/x/web-interface/view` public API works. Always recover metadata with `curl 'https://api.bilibili.com/x/web-interface/view?bvid={BV}' -H 'User-Agent: ...' -H 'Referer: https://www.bilibili.com/'` before drafting a report. |
| "中文标题的视频，转录也一定是中文" ★ | B站搬运/解说视频可能中文标题 + 英文原声/英文转录。If transcript language differs from title/description, explicitly add a data-limitation note: analysis is based on the transcribed audio, do not infer unverified original-source facts. |
| "技术解读视频里 UP 主已经总结了官方事实，我照抄即可" ★ 🆕 | 对外部产品/API/论文/框架的技术解读视频，视频转录只是二手来源。若简介或内容指向官方博客/Docs/GitHub/论文，必须用官方/一手资料交叉校验关键数字、API 名称、版本、限制与 availability，再写事实对照表；不要把 UP 主口播当最终事实。 |
| "标题/简介说了 Profile Builder、Agent Swarms、Kanban，所以报告就按这些写" ★ 🆕 | 技术/产品视频常有标题党或搬运再包装：标题/简介/UP主置顶评论可能强调一组功能，但实际转录只讲其中 1-2 个点（如 `/learn` + Petdex）。必须做 **标题/简介 vs 实际转录 Alignment Check**：列出承诺点、转录覆盖度、证据和判断；报告以转录和一手资料为准，明确标注错位。详见 `references/title-description-transcript-mismatch.md`。 |
| "mlx-whisper is pre-installed, just use it" ★ 🆕 | mlx-whisper may NOT be installed. If `import mlx_whisper` fails, install: `pip3 install mlx-whisper` (~60s, installs to `/Users/alexcai/Library/Python/3.9/` for `/usr/bin/python3`). Do NOT waste time searching for it across Python versions. |
| "B站 26 分钟，P1 肯定覆盖全部内容，P2 不用看" ★ 🆕 | B 站多 P 视频的总时长 = 各 Part 之和，不一定是额外内容。曾踩坑：P1 (13:19 中文配音) + P2 (13:18 英文原声) = 26:37 总时长 → 双音轨，零额外内容。用户明确要求「这么长的时长都要完整看一遍」——`fetch_subtitle_auto.py` v2.6.1 在 whisper fallback 会遍历 `pages[]`、逐 CID 走 PlayURL API 直拉音频并合并 P1/P2 转录；报告前仍要检查合并 TXT 中是否包含所有 `## Pn` 标题。 |
| "verify_report says G4 failed with 'min X words' but I'll just add text to the last module" ★ 🆕 | verify_report.py 的 G4 输出 `min X words` 是**所有模块的最小值**——它不告诉你哪个模块拖后腿。不要盲目给最后一个模块加文字。用 `references/merged-report-tips.md` 中的诊断脚本找出具体哪个模块不足，精准扩充。 |
| "I'll use write_file to save the final report to Obsidian" ★ 🆕 | `write_file`（无论是直接调用还是通过 `execute_code`）在 Obsidian vault 路径（iCloud/Documents 同步目录）上可能**静默成功但文件未实际落盘**。`ls` 后文件不存在是已知症状。**Phase 4 保存必须用 terminal `cp`**，不要用 `write_file`。`cp` 后立即 `ls -la` + `wc -c` 确认文件存在且非空。 |
| "字幕全失败了，一定是 Phase 1 改坏了" ★ 🆕 | 字幕失败 ≠ 代码回归。先读 RESULT_JSON 的 `trace` 数组逐步骤诊断：方案0/1 fail + reason=「无字幕」→ 视频确实没字幕（B站未生成AI字幕），**代码正常**；方案2 fail + reason=「412」→ 当且仅当之前同一视频方案2成功过才算回归。**不要因为一个没字幕的视频而回滚整个 subtitle 模块。** |

## 🔀 Decision Tree

```
🆕 Received a YouTube URL (非搬运，直接分析原片)?
└── → scripts/fetch_youtube.py <url> [--limit N] → /tmp/{video_id}_youtube_report.md (引擎报告，独立流程)

Received Bilibili URL(s)?
├── Multiple URLs (same creator/series)? → 🆕 Offer merged report. Collect all metadata first.
│   └── User confirms merge → Phase 1 for all videos → generate unified report
├── Single URL → Phase 0: Fetch metadata ONLY (no transcription yet)
│   ├── 🆕 Is it a b23.tv short link? Resolve first:
│   │   `curl -sI -o /dev/null -w '%{redirect_url}' '<b23.tv URL>'` → extract BV号
│   ├── Get: title, author, duration, views, subtitle availability
│   │   🆕 When yt-dlp 412's (no Chrome cookies), use public API directly:
│   │   `curl -s 'https://api.bilibili.com/x/web-interface/view?bvid={BV}' -H 'User-Agent: ...' -H 'Referer: https://www.bilibili.com/'`
│   │   → Parse `data.title|owner.name|duration|stat.view|stat.danmaku|stat.reply|stat.favorite|cid|desc`
│   └── ⚠️ STOP HERE. Present metadata to user. Ask: "先看看再说" or "完整版" or "精简版"?
│       ├── "先看看再说" → Wait for user decision. Do NOT transcribe.
│       ├── "完整版" → Phase 1 full: transcription + all sections (see 全量版 below)
│       ├── "精简版" → Phase 1 full: transcription + condensed report (see 精简版 below)
│       └── 🆕 BYPASS: User gave explicit instruction ("帮我整理文档到01", "直接分析",
│           "用bilibili skill 帮我...") → skip confirmation, auto-select mode:
│           <20min → 精简版, ≥30min → 全量版, unknown → 精简版 (safe default)
├── Phase 1: Fetch data (metadata → subtitles → danmaku → comments)
│   ├── Subtitles: official/AI subtitles → PlayURL direct audio → H200 ASR → whisper.cpp → mlx-whisper
│   ├── Danmaku: ≥30-60 samples
│   ├── Comments: top 50 hot comments
│   └── 🆕 YouTube cross-platform (搬运视频): detect YouTube URL in description → fetch original subtitles + comments
├── Phase 2: Analysis engine (type diagnosis → evidence map → depth selection → report plan)
│   ├── ⚠️ Core asset: preserve Alex's old report framework as baseline; GitHub/BiliNote ideas are additive only
│   ├── Type diagnosis: Tutorial / Interview / Review / Narrative / Speech
│   └── Depth: 全量版 vs 精简版 (see below)
├── Phase 3: Generate report (adaptive sections)
│   ├── 🆕 引擎快速通道：`fetch_all.py BV.. --report`（或 `generate_report.py`）一键产出 /tmp/{BV}_report.md
│   │   适合「直接分析/整理文档」类指令；人工深度版仍走下方全量/精简 8-section 模板
│   └── 🆕 Merged report: per-video Meta tables, interleaved analysis, unified Insights/Deep Dive
└── Phase 4: 🚦 verify_report.py depth gate (blocking) → Save to Obsidian 00-Inbox + cleanup temp files
```

### Output Mode Selection

After Phase 0 metadata is shown, user picks one. If they don't specify, default to **presenting metadata first**, not auto-running full analysis.

| Mode | When to use | Sections | Good for |
|:---|:---|:---|:---|
| **全量版** | 深度访谈/演讲 ≥30min, or user explicitly says "完整版" | All 8 sections (0-8) | Interviews, keynotes, research talks |
| **精简版** | 教程/How-to <20min, or user says "精简版" | 0 (Meta) + 3 (Key Insights) + 7 (Action Items) + selected Deep Dive modules | Tutorials, config walkthroughs, quick demos |
| **🆕 合并版** | Multiple related videos (same creator, same series) | 全量版 structure, per-video Meta tables, interleaved analysis | Series, build+Demo pairs, multi-part tutorials |

**精简版 rules**:
- Skip or minimize §2 (Danmaku) and §2.5 (Comments) if data is sparse. One sentence acknowledging scarcity is enough.
- §4 (Deep Dive): reduce to 2-3 modules max, each ≤300 words
- §5 (Highlights): reduce to 2-3 quotes max
- §6 (Knowledge Graph): keep only the core concept table, skip cultural references
- Still include: YAML frontmatter, §0 Meta, §1 Logic Chain (shortened), §3 Key Insights, §7 Critical Review & Action, §8 Appendix
- Quality bar: **Depth Quality Gates 精简版列** (G3 ≥2×150字, G4 2-3模块, G5 2-3, G7 full). Verify with `verify_report.py --mode condensed`. No KB target — size follows content.

**🆕 合并版 rules** (thresholds = Depth Quality Gates 合并版列):
- §0 Meta: per-video tables, then merged summary
- §1 Logic Chain: one flowchart per video (**G1: each ≤100 行**), then a "两篇的逻辑关系" comparison
- §2/2.5: per-video danmaku/comment analysis with data-sparsity guard
- §3 Key Insights: **G3: ≥3 unified insights** spanning both videos (not 3-per-video)
- §4 Deep Dive: **G4: ≥3 modules**, each drawing material from both videos where relevant
- §5 Highlights: **G5: ≥5 金句** pooled across videos
- §7 Critical Review & Action: **G7: ≥3 价值 + ≥2 局限 + ≥3 行动** (unified assessment)
- Verify: `verify_report.py <merged.md>` (full mode) treats the merged file as one report — unified §3/§4/§5/§7 clear full-版 gates directly; keep the combined §1 (all per-video arcs + comparison) within G1's ≤100 行.
- Filename: `B站笔记_[系列主题]_YYYYMMDD.md`

## Phase 1: Data Collection

```bash
# One-shot all data (recommended)
python3 scripts/fetch_all.py BV1ut6YByEZq

# 🆕 一键采集 + 引擎报告：附 --report 自动产出 Obsidian Markdown 到 /tmp/{BV号}_report.md
python3 scripts/fetch_all.py BV1ut6YByEZq --report
#   · 向后兼容：原 RESULT_JSON 输出不变，仅追加 report_path 字段
#   · 搬运视频自动含 cross_platform（B站 vs YouTube 评论）对比

# Individual scripts
python3 scripts/fetch_danmaku_v2.py BV1ut6YByEZq    # Danmaku
python3 scripts/fetch_comments.py BV1ut6YByEZq       # Comments
python3 scripts/fetch_subtitle_auto.py BV1ut6YByEZq  # Subtitles (auto-fallback)
```

> [!tip] 🆕 **引擎报告流水线（Phase 3 引擎对接）**：`generate_report.py` 把 `fetch_all.py` 的结果收敛为分析引擎输入并渲染完整 Obsidian Markdown。三种喂入方式：
> ```bash
> python3 scripts/generate_report.py --bvid BV1xx                  # 直接读 /tmp/{BV}_*.json 重建
> python3 scripts/generate_report.py --input /tmp/BV1xx_fetch_all.json  # 读 fetch_all 输出文件
> python3 scripts/fetch_all.py BV1xx | python3 scripts/generate_report.py  # 管道
> ```
> P2-D 起可选 LLM writer：`--writer-provider cli` 通过 `BILI_WRITER_CLI` / 默认 OMP CLI 继承调用方模型配置；`--writer-provider deepseek` 直接读 `DEEPSEEK_API_KEY`；默认 `none` 保持旧骨架/确定性输出。
> 自动从 `/tmp/{BV}_fact_checks.json` 读 claim（无则从字幕现场提取）。`fetch_all --report` 内部即复用此模块。

See `references/execution-guide.md` for dependencies (yt-dlp, whisper.cpp) and troubleshooting.

> [!note] 弹幕文件路径（v2.4 起 BV 前缀）
> `fetch_all.py`/`fetch_danmaku_v2.py` 现保存到 **`/tmp/{BV号}_danmaku.json`**（BV 前缀，与评论/字幕产物对齐）；纯 CID 输入时回退 `/tmp/cid_{数字}_danmaku.json`。无论哪种，RESULT_JSON 的 `path` 字段都是权威来源——直接读它，别猜路径。

## Phase 2: Deep Analysis

2. **Type diagnosis**: Tutorial / Interview / Review / Narrative / Speech
3. **Danmaku analysis**: 6 emotion categories, high-frequency terms, cultural memes → see `references/danmaku-analysis-guide.md`
4. **Comments analysis**: Hot comment curation, opinion clustering, creator interaction
5. **🆕 First-source cross-check for technical/news/policy videos**: 
   - **技术/产品类**：视频解释外部产品/API/框架/论文，且简介或内容指向官方博客/Docs/GitHub/论文 → 用官方/一手资料交叉校验关键数字、API 名称、版本、限制与 availability
   - **政策/新闻类**：视频做公共政策解读（教育/医疗/房地产/社保等），UP 主以"专家/教师/内部人士"身份做断言式声明 → 启用 WRR 多引擎交叉验证（Brave + Exa 双主力，grounding 模式），逐条核查可验证声明
   - 两种类型均在报告 §8 附录中加入「事实核查溯源」Source Map 表格（ID / 来源 / 核心事实 / URL）
   | `references/wrr-fact-check-policy-videos.md` |
   | **🆕 技术视频标题/简介错位核查**：标题/简介/UP主热评 vs 实际转录 Alignment Check，尤其适用于 Hermes/AI 工具类搬运或营销视频 → 见 `references/title-description-transcript-mismatch.md` |
   - 核心原则：B站转录是评论，不是最终权威；弹幕中的众包质疑是高质量的核查信号
6. **🆕 Dominant-entity detection**: During type diagnosis, scan for entities (tools/APIs/characters/technologies) referenced in ≥3 sections. If found, auto-propose an additional Deep Dive module for panoramic analysis. Example: Codex appeared in architecture, insights, demo, and critical review of the Niuma videos → triggered "模块 7：Codex 角色全景".
7. **3-layer dissection**: Explicit / Implicit / Meta-narrative
8. **Critical review**: Validity / Blind spots / Audience fit

Full analysis framework: `references/v3-detailed-prompt.md`

## Phase 3: Output (Adaptive — See 全量版/精简版 Mode Selection Above)

### 📏 Depth Quality Gates (深度质量门槛 — 取代 KB 体量目标)

> 报告质量按**结构充实度**衡量，不按文件大小。KB 数是深度的副产物，不是目标——
> 不要为了凑 KB 注水，也不要因为"到了 30KB"就停。用下表门槛自检，或运行
> `python3 scripts/verify_report.py <报告.md>`（`--mode condensed` 校验精简版）。

| Gate | 章节 | 全量版 | 精简版 | 合并版 |
|:---|:---|:---|:---|:---|
| **G1** | §1 逻辑链 | ≤100 行（含 Mermaid） | ≤100 行 | ≤100 行/视频 |
| **G3** | §3 核心洞察 | ≥3 洞察 × 每条 ≥200 字 | ≥2 洞察 × ≥150 字 | ≥3 洞察（跨视频统一） |
| **G4** | §4 Deep Dive | ≥3 模块 × 每个 ≥500 字 | 2–3 模块 × ≤300 字 | ≥3 模块（取材双视频） |
| **G5** | §5 高光时刻 | ≥5 条金句 | 2–3 条 | ≥5 条 |
| **G7** | §7 批判与行动 | ≥3 价值点 + ≥2 局限 + ≥3 行动项 | 同全量版（教程最高价值区，不削减） | ≥3 + ≥2 + ≥3（统一评估） |

> [!tip] 门槛是**下限**不是上限。访谈/演讲常超出 G3/G4，按内容自然展开；`verify_report.py` 只拦截"不足"。

### 全量版 (All 8 Sections)

| # | Section | Requirement |
|---|---------|------------|
| **YAML** | Frontmatter | 必填：status/type/priority/aliases/tags/created/modified（遵循 Obsidian CLAUDE.md） |
| 0 | Meta | Video title, UP主, play count, CID, duration |
| 1 | Logic Chain | **G1**: Tables (narrative arcs) + Mermaid flowcharts — structural overview, NOT prose retelling. **≤100 lines**. Verbose quotes → Deep Dive. |
| 2 | Danmaku Intelligence | Emotion quantification, meme analysis |
| 2.5 | Comments Analysis | Hot comments curation, opinion clustering |
| 3 | Key Insights | **G3**: ≥3 insights, each ≥200 字 with verbatim support |
| 4 | Deep Dive | **G4**: ≥3 modules (extensible on user request), each ≥500 字, Mermaid diagram per module where applicable |
| 5 | Highlights & Quotes | **G5**: ≥5 金句 (视频金句 + 弹幕金句) with timestamps |
| 6 | Knowledge Graph | Concept map, cross-references, linkage to user's own stack |
| 7 | Critical Review & Action | **G7**: ≥3 价值点 + ≥2 局限/偏见 + ≥3 行动项 |
| 8 | Appendix | Data sources, tools used, full quotes, timestamp index |

**全量版 quality bar: 满足 Depth Quality Gates (G1/G3/G4/G5/G7) above.** 体量是副产物——别盯 KB 数，跑 `verify_report.py` 验门槛。

### 精简版 (Condensed)

| # | Section | Requirement |
|---|---------|------------|
| **YAML** | Frontmatter | Same as 全量版 |
| 0 | Meta | Same as 全量版 |
| 1 | Logic Chain | **G1**: ≤100 lines — same structure as 全量版, just fewer detail rows |
| 2 | Danmaku/Comments | **Minimal**: ≤50 words if sparse. Write "数据不足" and move on — do NOT inflate. |
| 3 | Key Insights | **G3 (relaxed)**: ≥2 insights × ≥150 字 |
| 4 | Deep Dive | **G4 (relaxed)**: 2-3 modules max, each ≤300 字 |
| 5 | Highlights | **G5 (relaxed)**: 2-3 quotes |
| 6 | Knowledge Graph | Core concept table only. Skip cultural/meme analysis. |
| 7 | Critical Review & Action | **G7 (full)**: ≥3 价值点 + ≥2 局限 + ≥3 行动项 — 教程最高价值区，不削减 |
| 8 | Appendix | Sources + version, skip extended reading |

**精简版 quality bar: 满足 Depth Quality Gates 精简版列.** Verify with `verify_report.py --mode condensed`. 体量随内容，不设 KB 目标。

**Timestamp formula**: Bilibili `?t={total_seconds}`. `02:30` → 150 seconds → `?t=150` (NOT `?t=230`!).

Full template: `references/output-template.md`

## Phase 4: Save & Cleanup

**🚦 STEP 0 — Depth gate (blocking, run BEFORE saving):**

```bash
# 先把草稿写到 /tmp，验门通过才落库
python3 scripts/verify_report.py /tmp/报告草稿.md            # 全量版
python3 scripts/verify_report.py /tmp/报告草稿.md --mode condensed   # 精简版
```

- ❌ **Any gate FAIL (exit 1) → do NOT save.** Go back, expand the named section (G3/G4/G5/G7), re-run until ✅ OVERALL PASS (exit 0).
- ✅ Gates green → proceed to save below. This is the same rubric as the §3 Depth Quality Gates — the script just enforces it mechanically so a thin report can't slip through.

**Then save:**

- 🚨 **Use terminal `cp`, NOT `write_file`** — `write_file` 在 Obsidian vault 同步目录上可能静默失败（报告成功但文件未落盘）。正确做法：`cp /tmp/报告草稿.md "<vault路径>" && ls -la "<vault路径>" && wc -c "<vault路径>"`。三步验证：cp → ls 确认存在 → wc 确认非空。
- ✅ Save to: `~/Documents/Obsidian/AlexCai/00-Inbox/B站笔记_[主题简述]_YYYYMMDD.md`
- ⚠️ **Filename convention**: follow the vault's CLAUDE.md — for this vault it's `B站笔记_主题简述_YYYYMMDD.md` (NOT `视频解析_...`). Check the target vault's CLAUDE.md for its actual convention.
- ✅ Must include YAML frontmatter（status/type/priority/aliases/tags/created/modified）
- ✅ **Re-run `verify_report.py` on the final saved Obsidian path**, not only on the `/tmp` draft. This catches wrong-path saves, copy/truncation mistakes, and final filename/path issues before reporting success.
- ✅ Clean temp files: `rm -f /tmp/bili_hermes* /tmp/BV* /tmp/cid_* /tmp/报告草稿.md` — do this only after the final saved file has passed verification.
- ❌ Never save to: `~/clawd/00-Inbox/` or vault root

## 🆕 Phase 2: YouTube 评论同步 + WRR 事实核查

**搬运视频评论同步**：
```bash
# 独立使用 YouTube 评论抓取
python3 scripts/fetch_youtube_comments.py <youtube_url或video_id> --limit 50
# 输出：/tmp/{video_id}_youtube_comments.json
```

**🆕 YouTube 视频独立分析入口**（对标 fetch_all，非搬运场景直接分析 YouTube 原片）：
```bash
python3 scripts/fetch_youtube.py <youtube_url或video_id> [--limit 50]
# 采集：yt-dlp --dump-json 元数据 + 字幕(youtube-transcript-api 优先, yt-dlp --write-auto-subs 兜底) + 评论
# 调 video_analysis_engine(platform='youtube') → 输出 /tmp/{video_id}_youtube_report.md
# 走 RESULT_JSON 协议；全程 best-effort 降级（字幕/评论任一失败不阻塞其余）
```

**WRR 事实核查链**：
```bash
# Step 1: 从字幕提取可验证 claim
python3 scripts/fact_check_wrr.py --transcript /tmp/BVxxx_subtitle_official.txt --bvid BVxxx
# 输出：/tmp/{BVxxx}_fact_checks.json

# Step 2: 人工或 WRR 对 claims 逐条核查 → 更新 verdict/sources 字段
# Step 3: 将 fact_checks 结果传入 video_analysis_engine 生成报告 §4 关键声明核查
```

## Script Reference

| Script | Function | Dependency |
|:---|:---|:---|
| `fetch_all.py` ⭐ | One-shot: danmaku + comments + subtitles (dispatches sub-scripts via `/usr/bin/python3`; failures reported, not masked). 🆕 `--report` 追加 Obsidian 报告 | yt-dlp, mlx-whisper/whisper-cli |
| `generate_report.py` 🆕 | 胶水层：fetch_all 结果 → AnalysisInput → 引擎 → Obsidian Markdown（`--bvid`/`--input`/stdin 三入口） | stdlib only |
| `fetch_youtube.py` 🆕 | YouTube 视频独立分析入口（metadata + 字幕 + 评论 → 引擎报告，对标 fetch_all） | yt-dlp, youtube-transcript-api |
| `fetch_danmaku_v2.py` | Danmaku (BV号 direct, BV-prefixed output) | requests |
| `fetch_comments.py` | Comments (top 50 hot) | requests |
| `fetch_subtitle_auto.py` | Subtitles (auto-fallback: official→yt-dlp→whisper.cpp→mlx) | yt-dlp, whisper.cpp, mlx-whisper |
| `fetch_youtube_comments.py` 🆕 | YouTube 评论双路径抓取（yt-dlp → yt-comment-dl fallback） | yt-dlp, yt-comment-dl |\n| `fact_check_wrr.py` 🆕 | WRR 事实核查路由：从字幕提取可验证 claim | stdlib only |\n| `video_analysis_engine.py` 🆕 | 平台无关视频分析引擎骨架（数据类 + 报告渲染） | stdlib only |\n| `bilibili_dm_patch.py` 🆕 | yt-dlp dm_img monkey-patch 412 绕过（移植自 BiliNote） | yt-dlp (optional) |\n| `mlx_transcribe.py` | mlx-whisper Python-API transcription (local snapshot, offline) | mlx-whisper (`/usr/bin/python3`) |
| `release_gate.py` 🆕 | 发布前统一质量入口：fixture quality gate + pytest；真实样片 smoke 需显式 `--real-sample` | stdlib only |
| `verify_report.py` 🆕 | Static Depth-Quality-Gate checker for a report `.md` | stdlib only |
| `transcribe_whisper_cpp.sh` | Audio transcription | whisper-cli, ffmpeg |

> [!note] 解释器要求：弹幕/评论/字幕子脚本需可用的 `requests` + 可用的 `xml/pyexpat`，请用 **`/usr/bin/python3`**（CommandLineTools 3.9 + `~/Library/Python/3.9` user site）运行；本机 homebrew python3.12 的 `pyexpat` 损坏，无法解析弹幕 XML。`fetch_all.py` 已内置该选择。

## Known Limitations

- ⚠️ Official subtitle API requires login (SESSDATA); **preferred path: `yt-dlp --cookies-from-browser chrome`** — single command extracts both official + AI subtitles without API calls (see below)
- ⚠️ Comment API returns max 3-5 hot comments for new videos (<24h)
- ⚠️ whisper.cpp: ~68-85s per 19-minute video (Apple M4 GPU) — now local fallback only when H200 HTTP ASR fails/unavailable
- ⚠️ Fallback chain: official/AI subtitles → PlayURL direct audio → H200 ASR (default) → whisper.cpp → mlx-whisper. **No transcript, no formal full report**: if all subtitle/ASR paths fail, output only a clearly-labeled `预分析_未通过ASR_...` file; do not save it as a normal `B站笔记_...`. Source-gate and single-note-output details: `references/asr-evidence-gates-and-single-note-output-20260630.md`.
- ⚠️ 🆕 **PlayURL 音频抽样下载不要用 `curl --max-filesize`**：`--max-filesize` 会因远端 Content-Length 超限直接退出（不是音频不可下载）。测试片段请用 Range：`-H 'Range: bytes=0-10485759'`；完整转录直接下载低码率 DASH audio，再 ffmpeg 切 5 分钟 chunk → H200 ASR。
- ⚠️ 🆕 **`bilibili_dm_patch.py` 仅对 in-process yt-dlp 生效**：monkey-patch 通过修改 `yt_dlp.extractor.bilibili.BiliBliIE._build_dm_params` 绕过 412，但 `fetch_subtitle_auto.py`/`bili_env.py` 中的 yt-dlp 调用走 `subprocess.run(['yt-dlp', ...])`（CLI 进程），不经过 Python 模块——**dm_patch 对 CLI 调用零效果**。CLI 412 先走 PlayURL API 直连下载音频，再走 H200/local ASR。
- ✅ **Fallback chain is automatic (v2.6.2)** — `fetch_subtitle_auto.py` runs official → yt-dlp subtitles → PlayURL direct audio → H200 ASR → whisper.cpp → mlx-whisper **in-process** and reports the engine that actually succeeded in the `method` field. `fetch_all.py` surfaces failures as `{"status":"failed","returncode":N,"error":...}` (no more silent `null`).
- ⚠️ Multi-video merge: when user provides multiple B站 URLs from the same creator/series, offer to merge into a single unified report. Collect all data first, then interleave analysis with per-video Meta tables.
| **🆕 合并报告特殊技巧**：G4 诊断脚本、§1 flowchart 压缩策略、多视频并行采集模式 → 见 `references/merged-report-tips.md` |
| **🆕 Hermes/飞书配置视频交叉校验**：多 profile、多 gateway、飞书群聊/bot-to-bot 的官方核验点与评论区故障映射 → 见 `references/hermes-feishu-video-crosscheck.md` |
| **🆕 政策/新闻类视频 WRR 事实核查**：公共政策解读类视频的声明提取、WRR 多引擎交叉验证（Brave+Exa）、声明-来源对照表、弹幕众包信号利用 → 见 `references/wrr-fact-check-policy-videos.md` |
- ⚠️ Tutorial/How-to videos <20min: use **精简版** — full 8-section analysis is overkill
- ⚠️ New videos (<24h, <500 views): expect 0-3 comments and 0-10 danmaku. Don't force analysis on empty data.
- ⚠️ 🆕 **Multi-P 视频总时长陷阱**：`x/web-interface/view` API 返回的 `duration` 是所有 Part 的**总和**，不是单 Part 时长。必须分别获取每个 CID 的时长才能判断内容关系。曾出现 P1+P2 双音轨（中配+原声）= 26 分钟但零额外内容的案例——不能凭总时长推测有增补解说，必须全量转录后判断。
- ⚠️ 🆕 **mlx-whisper 不一定预装**：skill 假设 `mlx-whisper` 已安装在 `/usr/bin/python3`，但实际可能缺失。若 `import mlx_whisper` 失败，执行 `pip3 install mlx-whisper`（安装到 `~/Library/Python/3.9/`，~60s）。whisper.cpp 模型文件也可能缺失（需 `ggml-large-v3-turbo.bin`），优先用 mlx-whisper。
- ⚠️ 🆕 **fetch_all 字幕失败不是终点**：即使 `fetch_all.py` 的字幕步骤返回 `status=failed`，先读 trace。当前自动链路会在 PlayURL API 下载音频后优先调用 **H200 ASR**；只有 H200 不通/失败才继续本机 `whisper.cpp` / `/usr/bin/python3 scripts/mlx_transcribe.py ... zh`。不要因为 `python3 -c 'import mlx_whisper'` 失败就误判无法转录。
- ⚠️ 🆕 **转载/搬运视频优先检查原始来源字幕**：如果 B站简介给出 YouTube/原站链接（如 `来源：https://www.youtube.com/watch?...`），且 B站无官方字幕或 yt-dlp 412，先尝试原始来源字幕：`yt-dlp --write-auto-subs --sub-lang 'en.*,zh.*' --skip-download --convert-subs srt -o '/tmp/<topic>' '<原始URL>'`。原始英文字幕通常比中文音频转录更完整；可作为主分析文本，B站 PlayURL+H200/local ASR 转录作为辅助核对。报告 §0/§8 必须明确数据来源差异，避免把 YouTube 字幕误称为 B站字幕。
- 🆕 **YouTube 原视频评论同步（搬运视频）**：当 B站视频标题/简介含 `youtube.com/watch?v=` / `youtu.be/` / 「来源」「搬运」「中配」等关键词时，自动触发 YouTube 原视频评论抓取 → `yt-dlp --write-comments --skip-download -o '/tmp/yt_%(id)s' '<youtube_url>'`。抓取后在 §2.5 Comments Analysis 下增加「YouTube 原视频评论对比」子节。详见 `references/bilinote-cross-reference.md` §3。
- 🆕 **BiliNote / jz-skills 交叉参考**：2026-06-29/30 深度分析了 [JefferyHcool/BiliNote](https://github.com/JefferyHcool/BiliNote) 与旧版 `jz-skills/shared/bilibili-video-analyzer`。结论：BiliNote 提供 Downloader/Transcriber/GPT/NoteGenerator 分层与 RequestChunker/checkpoint 蓝图；旧 skill 提供 Hermes-native RESULT_JSON、真实 home/user-site 兜底、PlayURL direct audio 稳定路径。详见 `references/bilinote-cross-reference.md` 与 `references/bilinote-and-jz-source-absorption-20260630.md`。
- 🆕 **P0 防回归锁定参考**：修改 `fetch_subtitle_auto.py` / `bilibili_dm_patch.py` / `fetch_all.py` 前先读 `references/p0-regression-lock-20260630.md`。其中记录了 PlayURL 逐 P 音频主 fallback、4 个 P0 回归测试、Hermes 复跑命令和 OMP 审核证据。
- 🆕 **内容引擎升级原则**：下一阶段优化重点是分析与内容产出引擎，不是继续堆 fetcher。旧版报告框架是 Alex 蒸馏资产，必须作为基线保留；BiliNote/GitHub 只提供增量增强。见 `references/content-engine-upgrade-principles-20260630.md`。
- 🆕 **P2-A ReportPlan / SectionSpec 源码吸收**：已细读老版 `output-template.md` / `v3-detailed-prompt.md`、BiliNote `note.py` / `request_chunker.py` / prompt 体系，并用 WRR/GitHub 吸收 OpenNote/NoteTaker-py 的 timestamped retrieval / salience-clustering 思路。落地为 `build_report_plan()`，保留老版 §0–§8。见 `references/content-engine-p2-report-plan-source-absorption-20260630.md`。
- 🆕 **P2-B EvidenceMap 归档记录**：Codex 只读审核确认 P2-A 方向正确但未闭环；随后已通过 P2-B1~B5 补齐 `EvidenceMap per SectionSpec`、timestamped quote/citation candidates、plan-aware skeleton 与 Source Appendix 表。见 `references/content-engine-p2-codex-audit-and-evidencemap-next.md`。
- 🆕 **P2-B1 EvidenceMap 三方协作记录**：已用 Codex planning-only → CC/cc-tmux 小包实现 → OMP 独立审核 → Hermes 验证/推送闭环落地。锁定 `EvidenceCandidate` / `EvidenceMap` schema、B站秒数 timestamp URL、无社交数据不伪造 §2/§2.5。见 `references/content-engine-p2b1-evidencemap-triad-20260630.md`。
- 🆕 **P2-B2 render_markdown skeleton 三方协作记录**：`render_markdown()` 现优先读 `report_plan.sections` 输出旧版 `## 0.`–`## 8.` headings，并注入 `evidence_map` anchors；验收口径是 `NO_SECTION_MISSING=1`，不要求 Depth Gates 全 pass（`overall=False` 对 skeleton 是预期）。OMP 若因 markdown/code fence 导致 schema rejected，必须 compact JSON-only 重审后再 accept。见 `references/content-engine-p2b2-render-skeleton-triad-20260630.md`。
- 🆕 **P2-B3 generate_report metadata 三方协作记录**：`generate_report.py::_build_transcript()` 现保留 `end` / `language` / `json_path` / `txt_path` / multi-P `parts/failed_parts`；本轮 OMP 抓到 CC 第一轮自报成功但生产文件未落地的 false positive，验收必须读当前文件+真实跑测。见 `references/content-engine-p2b3-generate-report-metadata-triad-20260630.md`。
- 🆕 **P2-B4 render Source Appendix 三方协作记录**：`render_markdown()` 现于旧版 §0/§8 输出 `### Source Appendix`，从 `evidence_gate.sources.transcript` 暴露 transcript availability/source/language/segments/chars；不依赖 `evidence_map`，无 transcript 时不伪造路径。见 `references/content-engine-p2b4-render-source-appendix-triad-20260630.md`。
- 🆕 **P2-B5 Source Appendix §8 数据源表三方协作记录**：`§0` 保持简洁来源摘要，`§8` 升级为固定 12 列、固定 5 行顺序的数据源表；render 层只读解析 P2-B3 `transcript.source` 编码串，不改变上游 schema，无 transcript 时不伪造路径/multi-P 字段。见 `references/content-engine-p2b5-source-appendix-table-triad-20260630.md`。
- 🆕 **P2-C1 Writer Section Context 三方协作记录**：新增 `build_writer_section_context(report, top_n=5)`，把 `report_plan` / `evidence_map` / P2-B5 Source Appendix 表投影为确定性 writer adapter context；不调用 LLM，不改 `render_markdown()`，不污染 `analyze_video()` payload。OMP 必须走 `call-omp` workflow，裸 `omp -p` 结果不采信。见 `references/content-engine-p2c1-writer-section-context-triad-20260630.md`。
- 🆕 **P2-C2 Highlights Writer 三方协作记录**：首刀正式 writer `write_highlights_section()` 从 `transcript.quote_candidate` 证据渲染 `> "文本" — [时间戳](url)` blockquote，接线到 `_emit_section_skeleton` sid=5；纯确定性、不调用 LLM；`verify_report.measure_g5` 已验证计数正确。见 `references/content-engine-p2c2-highlights-writer-triad-20260630.md`。
- 🆕 **P2-D LLM Writer Pipeline 三方协作记录**：新增可插拔 `WriterProvider = Callable[[str, str], str]`、`write_llm_section()`、`validate_section()`、§3/§4/§7 LLM writer、`cli_writer_provider` / `deepseek_writer_provider`、`generate_report.py --writer-provider none|cli|deepseek` 和 `check_report_coherence()`；默认 `provider=None` 向后兼容，CLI 路径可继承 OMP/调用方模型配置。见 `references/content-engine-p2d-llm-writer-pipeline-triad-20260701.md`。
- 🆕 **P2-E Quality Gate 三方协作记录**：新增 `scripts/run_quality_gate.py`，以 deterministic `fixture_writer_provider` 串起 `fetch_all JSON → generate_report.report_markdown() → verify_report full gates → check_report_coherence()`；默认不联网、不烧 LLM，`--writer-provider cli|deepseek` 保留真实样片 smoke 入口。见 `references/content-engine-p2e-quality-gate-triad-20260702.md`。
- 🆕 **P2-F Real Sample Fallback Guard 记录**：`run_quality_gate.py` 增加 `--fail-on-fallback-warning`，捕获 `generate_report.report_markdown()` 期间的 LLM writer fallback warnings；真实样片 smoke 可在 §3/§4/§7 静默回退 skeleton 时直接 fail，避免“结构通过但质量退化”。见 `references/content-engine-p2f-real-sample-fallback-guard-20260702.md`。
- 🆕 **P3-A Release Gate Runner 记录**：新增 `scripts/release_gate.py` 作为发布前统一入口；默认运行 fixture quality gate + `pytest -q tests --ignore=tests/test_asr_config.py`，真实样片 smoke 通过 `--real-sample ... --real-writer-provider cli|deepseek` 显式启用。注意：这是 engineering gate，不代表可入库发布质量。见 `references/content-engine-p3a-release-gate-runner-20260702.md`。
- 🆕 **P3-B Usage Surface 记录**：新增项目根 `README.md`，把 release gate、real sample smoke、generate/verify 常用命令前置为使用入口；避免质量闸只存在于聊天记录或 reference 中。见 `references/content-engine-p3b-usage-surface-20260702.md`。
- 🆕 **P0/P1 Publishable Gate 记录**：BV1zrTq6sEPB 暴露 `verify_report`/coherence/OMP pass 仍可能放过不可读 skeleton。新增 `scripts/verify_publishable_report.py`、`generate_report.py` 正式 `B站笔记_*.md` 输出 guard、`run_quality_gate.py --publishable`；坏稿 fail、历史优质稿 pass、P2-D 骨架稿 fail。见 `references/content-engine-p01-publishable-gate-20260703.md`。
- 🆕 **DraftReport / PublishedMarkdown 边界记录**：新增 `DraftReport`（non-publishable）、`PublishedMarkdown`（publish gate 成功后才创建）、`render_debug_markdown()` 和 `publish_markdown()`；`generate_report.report_markdown()` 显式走 `analyze_video → build_draft_report → render_debug_markdown`，保留 debug/engineering 输出但不伪装成成品。见 `references/content-engine-draft-report-boundary-20260703.md`。
- 🆕 **DraftReport §1/§5 Deterministic Writer Slice 记录**：`DraftReport.draft_sections` 开始承载 written-but-not-publishable 正文；新增 `write_logic_chain_section()` 产 §1 逻辑链表格，收紧 §5 highlights 截断，`assemble_draft_report_slice()` 只填 §1/§5，不改 legacy renderer。见 `references/content-engine-draft-report-slice-1-5-20260703.md`。
- 🆕 **H200 ASR 与 B站本机 ASR 配置边界**：SURGExZR H200 `/ASR/transcribe` 已实测短音频和约 5 分钟长音频可用，现已作为 `BILI_ASR_PROVIDER=auto` 的默认首选；本机 whisper.cpp / mlx-whisper 保留 fallback。覆盖 H200 地址用 `BILI_ASR_ENDPOINT`，不要用 `BILI_ASR_MODEL_PATH`。参考 `references/h200-asr-vs-bili-asr-20260630.md`。

### 🆕 Audio Download via Bilibili PlayURL API (yt-dlp 412 Bypass)

When `yt-dlp --cookies-from-browser chrome` fails with HTTP 412 (extracts 0 cookies, Chrome not running or cookie DB locked), bypass yt-dlp entirely by using Bilibili's public playurl API + curl:

**Step 1: Get audio stream URLs from playurl API** (no auth needed):

```bash
curl -s 'https://api.bilibili.com/x/player/playurl?bvid={BV}&cid={CID}&qn=80&fnval=16&fourk=1' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  -H 'Referer: https://www.bilibili.com/'
```

Parse `data.dash.audio[]` for stream URLs — pick the highest-bitrate one. If `data.dash` is absent, fall back to `data.durl[0].url` (FLV).

**Step 2: Download audio with curl:**

```bash
curl -sL -o '/tmp/bv_{BV}_audio.m4s' \
  -H 'User-Agent: Mozilla/5.0 ...' \
  -H 'Referer: https://www.bilibili.com/' \
  '<audio_url_from_step_1>'
```

**Step 3: Convert m4s to WAV:**

```bash
ffmpeg -y -i /tmp/bv_{BV}_audio.m4s -ar 16000 -ac 1 /tmp/bv_{BV}_audio.wav
```

Proceed with mlx-whisper transcription as normal. Notes: (a) this method works without any browser login — the playurl API is public; (b) the audio URL is time-limited (~6h), so download immediately after fetching; (c) the BV号 and CID must match — get CID from `x/web-interface/view` API or from `fetch_all.py` output.

### Subtitle Extraction — Verified Method (2026-06-02, double-validated)

When the user has a Bilibili login in Chrome, use `yt-dlp` with browser cookies. This method was verified twice in one session — it works reliably.

**Step 1: Diagnostic — check available subtitles** (always run first):

```bash
yt-dlp --cookies-from-browser chrome --list-subs '<URL>' 2>&1 | tail -10
```

This confirms which subtitle tracks exist (typically: `danmaku xml`, `zh srt`, `ai-zh srt`).

**Step 2: Extract to SRT files** (the reliable path):

```bash
# Allow 90s timeout — Chrome cookie extraction can be slow
yt-dlp --cookies-from-browser chrome \
  --write-subs --sub-lang "zh,ai-zh" \
  --skip-download --convert-subs srt \
  -o '/tmp/bv_hermes' '<URL>'
```

**Step 3: Read the SRT file** with `read_file`:

```bash
read_file /tmp/bv_hermes.ai-zh.srt
```

- `--cookies-from-browser chrome` — reuses user's Bilibili login session
- `--sub-lang "zh,ai-zh"` — requests both official (`zh`) and AI-generated (`ai-zh`) subtitles
- **DO NOT use `--write-auto-subs`** — it silently returns "There are no subtitles" even when `--list-subs` shows `ai-zh`. Use `--write-subs --sub-lang "zh,ai-zh"` instead.
- `--convert-subs srt` — converts to standard SRT format readable by `read_file`
- Output: `/tmp/bv_hermes.zh.srt` (official, ~296 lines) and `/tmp/bv_hermes.ai-zh.srt` (AI CC, ~257 lines for 10-min video, ~1028 lines total with timestamps)
- Timeout: allow **90s** (Chrome cookie extraction can be slow; Bilibili API sometimes delays JSON metadata download)
- Cleanup: `rm -f /tmp/bv_hermes* /tmp/bili_hermes*`

> [!tip] Prefer AI subtitles (`ai-zh`) over official (`zh`) — they're usually more complete and better punctuated. 257 entries for a 10-min video is typical.

**Pitfalls** (2026-06-02 verified across two extraction cycles):

- 🪤 `--write-auto-subs` alone fails with "There are no subtitles for the requested languages" even when `--list-subs` shows `ai-zh`. Use `--write-subs --sub-lang "zh,ai-zh"` instead — it reliably extracts both tracks.
- 🪤 `%(subtitles)j` JSON in `--print after_video` is unreliable — it returned `NA` when SRT files were successfully written to disk. Just use the SRT file path directly.
- 🪤 Browser native `browser_navigate` + JS console extraction is a dead end — Bilibili requires login for subtitle data, and the cookie-based API approach is the only reliable path for subtitle content.

### 🆕 mlx-whisper Transcription (Apple Silicon, Preferred Fallback)

When `yt-dlp` subtitle extraction fails (no `zh` or `ai-zh` tracks available), use mlx-whisper for local transcription. This is ~60s for a 7-minute video on Apple Silicon — faster than whisper.cpp.

**Step 1: Download audio** (run in background, allow 120s):

```bash
yt-dlp --cookies-from-browser chrome \
  -f 'bestaudio[ext=m4a]/bestaudio' \
  --extract-audio --audio-format wav \
  -o '/tmp/bv_audio.wav' '<URL>'
```

**Step 2: Transcribe with mlx-whisper** (run in background, allow 300s):

```python
from mlx_whisper import transcribe
result = transcribe('/tmp/bv_audio.wav',
    path_or_hf_repo='~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/<hash>')
# Write to SRT + plain text
```

**Step 3: Read the transcript:**

```bash
read_file /tmp/bv_transcript.txt
```

- **Always use local cache path** — do NOT pass the HuggingFace repo ID (`mlx-community/whisper-large-v3-turbo-mlx`). The HF API returns 401 even when the model is cached locally. Find the snapshot hash: `ls ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/`
- Pre-installed: `mlx-whisper` Python package (v0.4.3+). No CLI needed — use Python API directly.
- Model: `whisper-large-v3-turbo` (cached at `~/.cache/huggingface/hub/`)
- Output: 264 segments for 7.5-min Chinese video is typical
- Language detection: set `language="zh"` if auto-detect fails, but auto-detect usually works for Chinese content

> [!warning] 🪤 HF repo ID pitfall
> Using `path_or_hf_repo='mlx-community/whisper-large-v3-turbo-mlx'` triggers a HuggingFace 401 Unauthorized error even when the model is already cached locally. **Always resolve to the local snapshot path** — use `ls ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/` to find the hash, then pass the full path.
>
> [!warning] 🪤 mlx_transcribe.py argument format
> `scripts/mlx_transcribe.py` takes **positional arguments only**: `<audio_path> <output_txt_path> [language]`. Named flags like `--language`, `--output-txt`, `--output-srt` are NOT supported and will be silently treated as positional args — `--language` becomes the output filename. The script only produces TXT, not SRT. Usage: `/usr/bin/python3 scripts/mlx_transcribe.py /tmp/audio.wav /tmp/transcript.txt zh`
> Using `path_or_hf_repo='mlx-community/whisper-large-v3-turbo-mlx'` triggers a HuggingFace 401 Unauthorized error even when the model is already cached locally. **Always resolve to the local snapshot path** — use `ls ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/` to find the hash, then pass the full path.

Changelog: `references/changelog.md` — timeout optimization, multi-P video support, BV号 direct access.

## ✅ Verification Checklist

- [ ] Final Obsidian output is **exactly one user-facing note** for one video link: `B站笔记_...md`. Do NOT leave `完整记录稿_...`, `预分析_...`, raw transcript, or accident/intermediate drafts in the vault unless the user explicitly asks for source transcript/audit artifacts.
- [ ] Formal report has a transcript evidence source? 官方字幕 or H200/local ASR path recorded in §0/§8. If not, filename/title/YAML must be `预分析_未通过ASR_...`, not normal `B站笔记_...`.
- [ ] EvidenceSourceGate checked? `report.evidence_gate.can_generate_formal_report` must pass before formal save; `external_research.route` should be `wrr_local` when local WRR exists, otherwise `fallback_search` for configured web/search tools. See `references/video-link-single-artifact-evidence-gate.md` for the single-artifact + evidence-gate workflow.
- [ ] Danmaku file read from RESULT_JSON `path` (v2.4: `/tmp/{BV号}_danmaku.json`, BV-prefixed)?
- [ ] Subtitles extracted via `yt-dlp --cookies-from-browser chrome` first (not whisper unless cookie method failed)?
- [ ] Subtitle step: if status `failed`, checked the `error` field (e.g. 412 → cookies) before manual fallback?
- [ ] If yt-dlp subtitles unavailable, mlx-whisper used with local cache path (not HF repo ID)?
- [ ] 🆕 For technical/news videos about external products/APIs/frameworks/papers, official/first-source claims cross-checked and a 事实对照/data-source note added?
- [ ] 🆕 For policy/news commentary videos with verifiable claims, WRR fact-check triggered (Brave+Exa dual-engine, grounding mode)? Source Map table in §8 with per-claim verdict (✅/🟡/🔴)?
- [ ] Output mode selected? (全量版 or 精简版 — user chose explicitly?)
- [ ] 🆕 Multi-video merge: per-video Meta tables + interleaved analysis?
- [ ] YAML frontmatter present? (status/type/priority/aliases/tags/created/modified)
- [ ] Timestamp links use correct `?t={seconds}` formula (NOT `?t=minutes*100+seconds`)?
- [ ] **Depth Quality Gates pass?** Run `python3 scripts/verify_report.py <报告.md>` (全量版) or `--mode condensed` (精简版) — G1/G3/G4/G5/G7 all ✅?
- [ ] 全量版: all 8 sections present, G3 (≥3×200字) + G4 (≥3×500字) + G5 (≥5) + G7 (≥3+2+3) met?
- [ ] 精简版: sections 2/4/5/6 condensed, G7 kept full (≥3+2+3)?
- [ ] Dominant entities scanned? (tools/APIs/characters referenced in ≥3 sections → extra Deep Dive module?)
- [ ] Sparse danmaku/comments handled with ≤50 words, not inflated into full analysis?
- [ ] Output saved to Obsidian `00-Inbox/` using terminal `cp` (NOT `write_file`) + verified with `ls -la` and `wc -c`?
- [ ] Temporary files cleaned from `/tmp/`?

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: bilibili-video-analyzer" && git push`
