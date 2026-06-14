---

name: auto-diary
description: |
  自动化日记生成和四层聚合（日/周/月/年）。cron 定时触发：每日日记(23:00)、每周周报(Mon 09:00)、
  每月月报(1号 09:30)、每年年报(1/1 10:00)。采集天气(Open-Meteo)、日历(icalBuddy)、
  AI 对话(Hermes state.db + CC JSONL)、知识库变更(Obsidian vault + jz-skills git commits)、钉钉班级群消息(dingwave 解密本地 DB)，经校验闭环交付。
  支持日历事件回填和日记清理。详见知识库 [[日记系统-三机架构与路线图]]。

  Use when: cron triggers or user manually requests
  生成日记 / 生成周报 / 生成月报 / 生成年报 / diary / weekly / monthly / 补日程 / 整理日记.

  DO NOT use for: general note-taking, non-diary content generation, one-off research.
type: routine
version: 3.8.2
author: Hermes Agent — v3.8.2 跨运行时架构 + Codex v2.1 富提取 · v3.8.1 JSONL 双源修复 · v3.8.0 新增 Codex 会话采集 + 去重 cron ID + 文档漂移修复 · v3.7.0 git diff 扫 vault 删除 + git log 扫 jz-skills 提交 · v3.6.3 pwd.getpwuid() 绕过 cron HOME 污染

---

# Auto-Diary v3.8.0

自动化日记生成 + 四层聚合（日/周/月/年）。Cron 定时触发或手动调用。

> ⚠️ **真实调度状态**（2026-06-04 核实）：**4 个 auto-diary cron 全部存活**。
> 
> | job_id | 任务 | schedule | scheduler | 聚合源 | 状态 |
> |--------|------|----------|-----------|--------|------|
> | `a68f4f81b3ee` | 每日日记草稿 | `0 23 * * *` | cron-worker | 当日 Hermes+CC+Codex+vault+cal | ✅ |
> | `4f5b5607912d` | 每周周报 | `0 9 * * 1` | cron-worker | 上周 7 篇日记 | ✅ |
> | `59a992daaa55` | 每月月报 | `30 9 1 * *` | cron-worker | 当月日记 | ✅ |
> | `b6659cd1c94c` | 每年年报 | `0 10 1 1 * *` | cron-worker | 去年 12 篇月报 | ✅ |
> 
> **聚合金字塔**：日←采集 · 周←日 · 月←日（避开 ISO 周跨月）· 年←月。每个 cron 内置校验闭环。
> 
> **v3.6.0 关键修复**:
> - 🔴 **HERMES_HOME 污染**：`_get_state_dbs()` 改用 `Path.home()/.hermes` 硬编码，不再依赖 `HERMES_HOME` 环境变量。修复 cron-worker profile 下只扫到 cron-worker 自己 state.db、漏掉 regent/default 会话的问题
> - 🔴 **校验脚本假阳性**：新增三问答案深度检查——Q1/Q2/Q3 答案不足 20 字或仅占位符 `(无)` `(待补充)` 即判 FAIL
> - 🔴 **Cron prompt 精简**：去掉内联指令，改为引用 skill，使用绝对路径
> 
> **v3.6.1 修复**:
> - 🔴 **dingwave 超时**：DingTalk 班级群 cron (458bec58ee72) 报 120s timeout。改用 `-export-only -merged-out`，解密完即退出
> 
> **v3.6.2 修复 (2026-06-07)**:
> - 🔴 **管线 stdout 混合文本崩溃**：`dingtalk-media-pipeline.py` 的状态日志和 JSON 数据混在 stdout，monitor 脚本用 `json.loads()` 解析混合文本炸了。`set -euo pipefail` 把非零退出放大成脚本级崩溃。修复：(1) 管线所有状态输出切到 stderr，stdout 只留纯 JSON；(2) monitor 脚本增加 `|| true` 防护 + 从混合文本里智能提取 JSON 数组
>
> **v3.6.3 修复 (2026-06-07)**:
> - 🔴 **Path.home() 被 cron HOME 环境变量污染**：v3.6.0 声称用 `Path.home()` 绕过 HERMES_HOME 污染，但 cron-worker profile 启动时 **同时覆盖 HOME 到 chroot**，`Path.home()` 返回 chroot 路径而非真实 HOME。chroot 内无 state.db、.claude、Documents，导致 Hermes/CC/Vault 三项数据全为 0。这是静默故障——cron status 'ok'，日记文件存在且格式完整，但数据全是空的。修复：`extract_hermes_conversations.py` 和 `collect_data.py` 新增 `_real_home()` 函数，使用 `pwd.getpwuid(os.getuid()).pw_dir` 读系统 passwd 数据库，彻底绕过所有环境变量。验证：6/6 日记从 2920 字节（Hermes=0/CC=0/Vault=0）重写为 7422 字节（Hermes=36/CC=5/Vault=1），校验 PASS。

## 🚨 Red Flags: Don't Skip the Diary Rules

| Excuse | Why it's wrong |
|--------|---------------|
| "I'll just write a quick summary, the user won't notice" | Diary format is strict: 10 sections required. `verify_diary_compliance.py` 强制校验 13 项结构（含三问三条齐全、CC 三组、各体系 info callout、底部 --- 分隔）。Missing = 不合格,必重写。 |
| "The calendar events are empty, I'll skip that section" | Empty calendar ≠ skip. Must write "当日无日历事件" placeholder. |
| "I'll quote the user's exact words, it's more accurate" | 🔴 **Iron rule**: NEVER quote user's raw messages. Summarize. "讨论了视频分析" not "帮我看下这个 bilibili 视频". |
| "Existing content is just a template, I'll overwrite it" | Check existing_content first. If user has written anything, merge — keep user content, fill gaps only. |
| "icalBuddy returned empty, must be a bug" | icalBuddy silently returns empty on calendar name mismatch. Diagnose before assuming no events. |
| "I'll just pick the top 2-3 topics, the rest are noise" | 🔴 **Exhaustive coverage** (v3.0): EVERY topic in `ai_logs.*.topics` must appear in the diary. List all first, cluster by category (📖知识输入/🔍技术调研/📝文档管线 etc.), then write. Cross-check raw session data if overview seems thin. Busy days (10+ streams) → at least 3-4总结项. |
| "🦞 is Claude Code, I'll use that emoji" | 🔴 **🦞 = OpenClaw, NOT Claude Code**. CC has no fixed emoji; diary uses 💻 for CC. Hermes = 🐴. Mixing these up frustrated user. |
| "Callouts look cleaner folded, I'll use `> [!info]-`" | 🔴 **No folding callouts** (v3.0): user rejected `-` suffix. All callouts MUST be expanded — `> [!abstract]`, `> [!info]`, `> [!tip]`, `> [!note]`. Never use `> [!xxx]-`. |
| \"CC sessions are all the same, I'll list them flat\" | 🔴 **CC three-type split** (v3.2): 🤝 Agent Team 协作 / 💻 独立对话 / 🤖 程序调用。Group by type THEN by project, per-project topics. Data in `claude_overview.agent_team`, `.standalone`, `.program_call`. Classification uses CC native metadata (entrypoint + parentUuid), not text matching. |
| \"Codex sessions are all guardian noise, I'll skip them\" | 🔴 **Codex blind spot** (v3.8.0): Codex sessions were completely absent from diaries before v3.8.0. Data source: `~/.codex/state_5.sqlite` → threads table (Unix timestamps) AND `~/.codex/sessions/YYYY/MM/DD/*.jsonl` (v3.8.1 双源). Three-type split: 💻 独立 (vscode) / 🤝 Guardian (subagent) / 🤖 程序 (exec/cli). Guardian 会话虽多是审批 noise，但也有实质性运维会话（如 skill 中心化治理）。不能整体跳过。v3.8.2: 每条独立对话必须有时间、消息数、轮次数、2-4 行具体描述和 🔗 跨运行时联动标注。 |
| \"I'll group all Codex sessions into one summary line\" | 🔴 **Codex 信息过薄** (v3.8.2): 凭记忆写日记导致 Codex 被压缩为一行（如"Agent Skills 自动化 (7)"），丢失 729 消息 19 轮的深度审查会话、8922 消息 96 轮的需求分析会话。正确做法：`extract_codex_conversations.py` v2.1 提取每条会话的消息数/轮次/用户话题/助手行为摘要，逐条展开写。日记格式见 `diary-format.md` v3.3。 |
| \"The AI sections are independent silos\" | 🔴 **跨运行时盲区** (v3.8.2): Hermes、Codex、CC 在同一任务线上协作，但旧格式把它们写成独立段落。v3.8.2 新增 `🔗 跨运行时协作主线` note callout——从三段数据中提取端到端链路（发起方 → 审计/执行 → 交付物），用 `→` 展示。CC 和 Codex 段落内的项目也需标 `🔗` 联动标注。 |
| "Knowledge base changes are independent" | 🔴 **KB ↔ AI linking** (v3.1): Every vault change was produced by an AI session. Cross-reference `vault_changes` paths/titles with session topics. Group by source system (🐴/🏛️/💻). Unreliable matches → mark `(推断)`. |
| "I'll batch-generate all 31 diaries with a Python loop, it'll be fast" | 🔴 **批量生成 = 垃圾** (v3.2): 用户明确拒绝模板填充式批量生成。正确做法：逐条处理，用 cron 输出摘要的叙事做底子，三问必须有洞察力。详见 `references/batch-generation-pitfall.md`。 |
| "I've written diaries before, I know the format — no need to load diary-format.md" | 🔴 **NEVER write from memory** (v3.3): 凭记忆写日记导致 2026-06-02 全月重写——用户发现缺失 info callout、段落合并、三问缩写、CC 未按三组拆分、底部分段拍扁、tip 格式错误。教训：写或重写任何日记之前，**必须** `skill_view(name='auto-diary', file_path='references/diary-format.md')` 加载格式 spec，逐段对照写。记忆不可信。 |
| "The cron job status says 'ok' and diaries are being produced, so it must be working" | 🔴 **Status 'ok' ≠ skill loaded** (v3.5): cron 即使 `skills: []` 空数组也会以 status 'ok' 运行——用自己的裸 prompt 产出退化日记。日记文件存在≠质量合格。症状：CC=0、知识库变更=0、三问空洞、裸模板。**必须用 `cronjob list` 或 `hermes cron list` 确认 `Skills:` 字段非空**。2026-06-02~04 三日日记崩塌根因即此。 |

## 🔀 Decision Tree

```
Trigger received (cron or manual)?
├── Manual "生成日记" / cron daily (23:00) → Workflow A: Daily Diary
├── Manual "生成周报" / cron weekly (Mon 09:00) → Workflow B: Weekly Report
├── Manual "生成月报" / cron monthly (1号 09:30) → Workflow E: Monthly Report
├── Manual "生成年报" / cron yearly (1/1 10:00) → Workflow F: Yearly Report
├── Manual "补日程" / "日历事件没记" → Workflow C: Calendar Backfill
├── Manual "整理日记" / "清理日记" → Workflow D: Diary Cleanup
└── Ambiguous → Ask user which workflow
```

## Workflow A: Daily Diary

1. Determine target date (default today)
2. Run: `python3 {baseDir}/scripts/collect_data.py diary YYYY-MM-DD`
   - Returns: `vault_changes` (find-based), `vault_deletions` (git diff), `jzskills_commits` (git log), plus weather/ai_logs/calendar/dingtalk
3. Check calendar with icalBuddy using calendars `个人1,工作1,Naomi1,Zelda1` (iCloud `<email redacted>`)
4. **🔴 知识库双源** (v3.7.0): 日记的知识库部分必须同时呈现 Obsidian vault 变更（含 `vault_deletions`）和 jz-skills git commits。两者都做 AI 会话关联
5. Read format spec: `{baseDir}/references/diary-format.md`
6. **🔴 Cron health check** (v3.8.0): Run `hermes --profile cron-worker cron list | grep a68f4f81b3ee`. If the daily diary cron job_id is absent from the cron-worker scheduler, note it in the diary's 临时笔记 section and report it in the final response. The config archive at `config/cron-job.json` still holds the correct parameters for reconstruction.
7. Generate diary with 10 sections: 🎯每日总结(三问) → 🌤️概览(weather+mood) → ⏰时间线(calendar) → 🤖AI工作记录（📊全天AI活动概览 callout → 🔗跨运行时协作主线 callout → 🐴助理体系 → 🏛️治理体系 → 🤖Codex → 💻CC） → 📚知识库更新（含 Obsidian vault + jz-skills git commits） → 📅日历事件(detailed table) → 🏠个人生活(placeholder) → ✅待办 → 📝临时笔记 → 💡tip 页脚
   - 🔴 **v3.3 必须 callout**（C1 修复）：`🤖 AI助手工作记录` 章节开头必须先有 `> [!info] 📊 全天AI活动概览` 和 `> [!note] 🔗 跨运行时协作主线` 两个 callout，再接四体系。漏写会被 `verify_diary_compliance.py` 判 FAIL。
8. **CRITICAL 合并安全**: `collect_data.py` 的 `existing_content` 恒为 `null`（已知限制,脚本不读已有日记）。所以写入前**必须先 `Read` 目标日记文件**;若已存在用户手写内容 → 合并,保留用户文字,只填空缺。不可盲目覆盖。
9. **校验闭环**: 写完后运行 `python3 {baseDir}/scripts/verify_diary_compliance.py <写入的文件>`;若 FAIL,对照 `diary-format.md` 逐项重写,直到 PASS 再交付
10. Write to Obsidian vault
11. **日记入记忆** (v3.6): 校验 PASS 且写入 vault 后,把日记写进 supermemory `hermes` 池,让小黄(default profile)能检索每天的日记。
    `~/.hermes/hermes-agent/venv/bin/python {baseDir}/scripts/write_diary_to_supermemory.py <写入的日记文件绝对路径>`
    - ⚠️ **必须用 venv python 绝对路径**(系统 `python3` 缺 supermemory SDK 会 skip)。**不要用 `~/.hermes/...`**——cron-worker profile 下 `~` 会解析到 chroot (`~/.hermes/profiles/cron-worker/home/`)，venv python 根本不存在。必须用 `~/.hermes/hermes-agent/venv/bin/python` 硬编码全路径。
    - 幂等(`custom_id=hermes-diary-<date>`,重跑覆盖不重复)、失败不阻塞交付、走 Surge 代理避开 fake-ip。
    - 这是绕过 memory provider 对 cron session 写入限制(`_write_enabled` 排除 cron)的唯一途径——日记 cron 不会自动 capture。
12. Notify user (cron: via final response; manual: via Telegram)

See `references/diary-format.md` for weather codes, calendar table format, and section templates.

## Workflow B: Weekly Report

> cron `4f5b5607912d`(cron-worker profile)每周一 09:00 自动跑。也可手动(`生成周报`)。
> 🔴 `collect_data.py weekly` **未实现**(返回 not implemented)——直接 Read 日记,不依赖采集脚本。

1. 算上周 ISO 周范围: `python3 -c "import datetime as d; t=d.date.today(); mon=t-d.timedelta(days=t.weekday()+7); sun=mon+d.timedelta(days=6); iso=mon.isocalendar(); print(f'{mon} {sun} {iso[0]}-W{iso[1]:02d}')"`
2. Read 这 7 天日记(`01_日记/YYYY-MM-DD.md`,已归档的在 `归档/YYYY-MM/`)
3. Read: `{baseDir}/references/weekly-format.md`
4. 合并安全:先 Read 目标周报,保留用户手写内容
5. 按 5 维分析生成,写 `02_周报/YYYY-Www周报.md`(ISO week,如 `2026-W22周报.md`)
6. 🔴 校验闭环: `python3 {baseDir}/scripts/verify_report.py <文件>` → FAIL 重写到 PASS

## Workflow E: Monthly Report

> cron `59a992daaa55`(cron-worker profile)每月 1 号 09:30 自动跑。聚合源:**当月日记**(月←日,避开 ISO 周跨月)。

1. 算上月: `python3 -c "import datetime as d; t=d.date.today(); print((t.replace(day=1)-d.timedelta(days=1)).strftime('%Y-%m'))"`
2. Read 该月所有日记(根目录 + `归档/YYYY-MM/`),🔴 直接读日记不依赖采集脚本
3. Read: `{baseDir}/references/monthly-format.md`
4. 合并安全 → 生成 `06_月报/YYYY-MM月报.md`(从每日三问提炼跨日主线,不流水账)
5. 🔴 `verify_report.py <文件>` → PASS 才交付

## Workflow F: Yearly Report

> cron `b6659cd1c94c`(cron-worker profile)每年 1/1 10:00 自动跑。聚合源:**去年 12 篇月报**(年←月,非直读 365 篇日记)。

1. 算去年: `python3 -c "import datetime as d; print(d.date.today().year-1)"`
2. Read 该年所有月报(`06_月报/YYYY-*月报.md`);月报缺失则降级读该月日记并标注
3. Read: `{baseDir}/references/yearly-format.md`
4. 合并安全 → 生成 `07_年报/YYYY年报.md`(主线的主线,不复述月度细节)
5. 🔴 `verify_report.py <文件>` → PASS 才交付

## Workflow C: Calendar Backfill

Trigger: User notices persistent "当日无日历事件" on days that had events.

1. **Diagnose root cause**: `icalBuddy calendars` vs `collect_data.py` `-ic` params
2. Fix script if names mismatched
3. Determine backfill range (typically 3-7 days)
4. Backup diaries → `~/.hermes/backups/diary-calendar-backfill-YYYYMMDD_HHMMSS/`
5. For each day: query icalBuddy, patch calendar section (keep all other sections intact)
6. Skip days that genuinely had no events
7. Remind user of upcoming important events (eventsToday+30)

## Workflow D: Diary Cleanup

| 日历事件回填流程 | `references/calendar-backfill.md` |
| 日记清理启发式 | `references/diary-cleanup-heuristics.md` |
| **🆕 钉钉班级群消息采集 (dingwave 解密)** | `references/dingtalk-class-msgs.md` |
   - Empty/template: backup → delete
   - Sparse: merge by month → `归档/YYYY-MM/碎片日记合并-YYYY-MM.md`
   - Normal: keep
3. Write cleanup report: `日记清理报告-YYYYMMDD.md`
4. Run `qmd update` after cleanup

## Tech Stack

| Tool | Purpose |
|------|---------|
| icalBuddy | Calendar queries (`brew install ical-buddy`) |
| Open-Meteo API | Weather (free, no API key) |
| `state.db` SQLite | Hermes session extraction (see `references/hermes-session-extraction.md`) |
| `~/.claude/projects/*/uuid.jsonl` | Claude Code session extraction (see `references/cc-session-extraction.md`) |
| `find` command | Vault change detection |

Key improvements history: see `CHANGELOG.md` (skill 根目录)。

## Common Pitfalls

| Trap | Consequence |
|------|-------------|
| Quoting user's raw messages in diary | Diary becomes chat log, not personal record |
| Overwriting existing user content | User's personal notes lost |
| Trusting icalBuddy silent empty output | Calendar events silently missing for weeks (see config drift below) |
| **Not checking `existing_content` before writing** | Duplicate or conflicting diary entries |
| **Using `~` paths in shell commands from cron-worker profile** | `~` resolves to the cron-worker chroot (`~/.hermes/profiles/cron-worker/home/`), NOT `~/`. Scripts `obsidian_sync.py`, `collect_data.py`, `verify_diary_compliance.py`, and file reads (`~/Documents/Obsidian/...`) all fail silently. Fix: always use the full absolute path `~/...` in shell commands and `read_file`/`write_file` tool calls. |
| **verify_diary_compliance.py section header spacing** | The regex `r"^## 🤖 AI助手工作记录"` requires exactly `## 🤖 AI助手工作记录` — no space between `AI` and `助手`. Writing `## 🤖 AI 助手工作记录` (with space) or `## 🤖 AI工作记录` (without 助手) both fail validation. Always match the exact header string from `diary-format.md`. |
| Using relative dates without `-nrd` flag | Adjacent-day events bleed into wrong date |
| **Using `Path("~/...")` without `.expanduser()` or `Path.home()`** | `Path("~/Documents/...")` does NOT expand `~` — `find` / `open()` silently fail (0 vault changes). Fix: `Path.home() / "Documents/..."`. Same applies to `str(Path("~/..."))` passed to shell commands. |
| **Reading session JSON files instead of SQLite DB** | JSON session files deprecated May 2026; sessions now in `state.db` SQLite (2026-05-27 fix: `extract_hermes_conversations.py` v2.0 queries `state.db`)
| **CC `message` field type mismatch** | `message` can be `dict` or Python repr `str` — always use `_parse_cc_message()`. Content can be `list` or `str` — use `_extract_cc_text()`. See `references/cc-session-extraction.md`. |
| **Using wrong emoji for CC (🦞)** | 🦞 = OpenClaw. CC uses 💻 in diary. Hermes = 🐴. See Red Flags. |
| **Grouping cron-worker into 治理体系** | cron-worker is 小黄影分身 → 助理体系. Only extract_hermes_conversations.py handles the split correctly (key `"assistant"`, not `"default"`). |
| **Batch-regenerating old diaries with a script** | 🔴 **批量生成 = 垃圾**。用户反馈："不行啊，你批量生成的质量太垃圾了"。必须逐天 LLM 加工，三问要有叙事。详见 `references/batch-generation-pitfall.md`。 |
| **Shortening diaries to "speed up"** | 为了赶进度压缩日记到 900 字符 → 质量崩塌。用户要的是质量不是速度。"不行啊，我们是改了整个逻辑的，llm严格按照一天一天来，所有数据重新读"。宁可慢、要对。 |
| **Keeping zero-data days as separate files** | 全零日（无 Hermes/CC/vault/cal）不创建独立日记。连续多日→合并为一篇时期笔记。低密度日（仅 CC /usage）同理。 |
| **Dumping raw topics into 三问** | 把 `ai_logs.*.topics` 直接贴进"今天我做了什么推动进展的事情"→ "work kanban task t_cf1c6c9b" 这样的内容毫无意义。必须 LLM 加工成可读叙事。 |
| **🔴 Cron 从 scheduler 消失** | **新一级的静默故障** (v3.5.1 发现)：config/cron-job.json 存在但 cron 实体已从 scheduler 删除。hermes cron list 不显示该 job。后果：日记彻底不生成。诊断：对比 hermes cron list 的输出与 config/cron-job.json 中的 job_id。修复：用 config/cron-job.json 的参数重建 cron。运行每日日记时自我检查：如果本次是 cron 触发且对应 job 在 scheduler 中不存在，在 final response 中报告。 |
| 🔴 **Cron skills 数组为空** | **最危险的静默故障** (v3.5 发现)：cron job 的 skills: [] 为空时，cron 仍以 status ok 正常运行——但 agent 收不到 auto-diary skill 的任何指令。日记逐日退化，直到用户发现。诊断：cronjob list 看 Skills 列。修复：cronjob update 挂上 auto-diary skill。四个 cron 都必须挂 skill。 |
| **dingwave 超时 (v3.6.1 修复)** | DingTalk 班级群 cron (458bec58ee72) 报 120s timeout。根因: `dingwave -o` 解密完起 HTTP server 不退→sleep+kill 不生效。v3.6.1 改用 `-export-only -merged-out`，解密完即退出。表变更: `createdAt→created_at`, `content→content_json`, `tbmsg_112→messages`。详见 `references/dingtalk-class-msgs.md`。 |
| **🔴 管线 stdout 混合文本 + set -euo pipefail = 脚本崩溃 (v3.6.2 修复)** | `dingtalk-media-pipeline.py` 的 `print()` 状态日志和 `print(json.dumps())` 数据输出混在 stdout。Monitor 脚本的 `python3 -c "json.loads(...)"` 吃到混合文本抛 JSONDecodeError。`set -euo pipefail` 下非零退出被放大为脚本级 exit 1，cron 报 `Script exited with code 1`。修复：(1) 管线状态输出切 stderr；(2) monitor 脚本加 `\|\| true` + 从混合文本中提取 JSON 数组。 |
| **🔴 HERMES_HOME 污染 (v3.6.0 修复)** | Cron 跑在 cron-worker profile 下时 `HERMES_HOME` 被设为 profile 私有路径。`extract_hermes_conversations.py` 的 `_get_state_dbs()` 使用 `HERMES_HOME` 来找 state.db，导致只扫 cron-worker 自己的会话，regent/default 的全部丢失。CC 和知识库不受影响（用 `Path.home()` 直读）。修复：`_get_state_dbs()` 硬编码 `Path.home()/.hermes`，不再读 `HERMES_HOME` 环境变量。 |
| **🔴 Path.home() 被 cron HOME 环境变量污染 (v3.6.3 修复)** | v3.6.0 的 `Path.home()` 修复是假的——cron-worker profile 启动时 **同时覆盖 HOME** 到 chroot（`~/.hermes/profiles/cron-worker/home/`），所以 `Path.home()` 返回的是 chroot 而非真实 HOME。后果：chroot 里没有 `state.db`、没有 `.claude/projects/`、没有 `Documents/Obsidian/`，导致 Hermes/CC/Vault 三项数据全部为 0。只有天气（curl）和日历（icalBuddy）不受影响。修复：`extract_hermes_conversations.py` 和 `collect_data.py` 都新增 `_real_home()` 函数，使用 `pwd.getpwuid(os.getuid()).pw_dir` 读取系统 passwd 数据库，彻底绕过所有环境变量污染。**这是静默故障——cron 状态 'ok'，日记文件存在且格式完整，但数据全空**。 |
| **🔴 find 扫不到已删除文件 (v3.7.0 修复)** | `scan_vault_changes()` 用 `find -newermt` 扫描文件系统，**已删除的文件对 find 完全不可见**。6/6 的 vault 有 165 个 .md 文件被删除（三省六部退役 + 00-Inbox 清理），但 find 只扫到 1 个修改。修复：新增 `scan_vault_deletions()` 使用 `git -c core.quotepath=false diff --diff-filter=D --name-only HEAD` 检测所有 staged 删除。注意：git 默认 `core.quotepath=true` 会转义中文路径为八进制，必须加 `-c core.quotepath=false`。另外删除操作无法精确日期过滤——返回自上次 commit 以来所有 staged 删除。 |
| **🔴 jz-skills repo 提交未被计入知识库 (v3.7.0 修复)** | 用户的「知识库」不仅包括 Obsidian vault，还包括 `~/code/jz-skills/`（60+ skill 的源码仓库）。6/6 的 jz-skills 有 5 个 commit、71 个文件变更、5,467+ 行新增——这些是实打实的知识产出，但 `collect_data.py` 完全不扫。修复：新增 `scan_jzskills_commits()` 使用 `git log --after/--before` 扫描当日所有 commit，返回 hash + message + file list。 |
| **🔴 Codex JSONL 双源漏扫 (v3.8.1 修复)** | `extract_codex_conversations.py` v1.0 只读 `state_5.sqlite` → threads 表。但 Codex 的会话存储是**双源**：(1) 旧会话在 SQLite threads 表；(2) 近期会话在 `~/.codex/sessions/YYYY/MM/DD/*.jsonl` 和 `~/.codex/archived_sessions/*.jsonl`。6/13 的 14 个 Codex 会话全部在 JSONL 里、SQLite 为 0，导致日记 Codex=0 的静默漏报。v3.8.1 修复：`extract_codex_conversations.py` v2.0 — 三源合并（SQLite + sessions/ JSONL + archived_sessions/ JSONL），thread_id 去重。JSONL 的 session_meta 提供元数据（id/source/cwd/timestamp），第一条真实用户消息（跳过 AGENTS.md 注入和 guardian prompt）作为标题。注意 `base_instructions` 是 dict `{text: ...}` 不是字符串。 |

## ⚠️ Config Drift (Silent Failure)

icalBuddy `-ic "cal1,cal2"` on mismatched names returns empty **without error**. If diary shows persistent "当日无日历事件" but user confirms events exist → run `icalBuddy calendars` and compare with `collect_data.py`. Known migration: iCloud `<email redacted>` added "1" suffix to all calendars.

## ⚠️ Known Limitations

**CC session count inflation**: Observer (Claude-Mem) sessions are tallied in CC counts but produce no meaningful topics — their system prompts are filtered. This means CC `session_count` can overrepresent on days with heavy observer activity. Low priority; acceptable trade-off for now.

**CC 内容展现偏薄** (v3.2 TODO): CC 段落目前只罗列 top-level 主题，没有 per-project 展开。待做：强制每个 CC 项目至少一条概括，和 Hermes 穷举覆盖同等粒度。

**知识库 ↔ AI 会话未关联** (v3.1 TODO): 知识库变更（vault_changes）目前独立展示，未标注是由哪个 AI 会话推动的。待做：在日记写作阶段做语义匹配，标注每个 vault 文件的来源会话。

**Codex 内容展现偏薄** (v3.8.1): Codex session titles 来自 `threads.title` (SQLite) 或 JSONL 第一条用户消息。Guardian 类 session 的 title 通常是 guardian 系统 prompt（"You are judging..."），需要额外从 parent thread 获取真正主题（待做）。Automation 类 session 的标题前缀 "Automation:" 可以识别为定时任务。JSONL 来源的 session 需跳过 AGENTS.md 注入行（`# AGENTS.md instructions` 开头）和 guardian prompt 行（`The following is the Codex agent history` 开头）。

**jz-skills git 扫描** (v3.7.0 已集成): 日记现在同时扫描 Obsidian vault 和 jz-skills git commits，**二者均已集成到 `collect_data.py`**（`scan_jzskills_commits()`）。返回 `jzskills_commits` 数组：hash + message + date + files + file_count。只扫描默认分支（main），不追踪 feature 分支。当日如果 jz-skills 有 commit，日记的 📚 知识库章节必须按来源体系分组展示。详见 `references/jz-skills-git-scanning.md`。

## Output Paths

- Diary: `~/Documents/Obsidian/AlexCai/50-Self/01_日记/YYYY-MM-DD.md`
- Weekly: `~/Documents/Obsidian/AlexCai/50-Self/02_周报/YYYY-Www周报.md`
- Monthly: `~/Documents/Obsidian/AlexCai/50-Self/06_月报/YYYY-MM月报.md`
- Yearly: `~/Documents/Obsidian/AlexCai/50-Self/07_年报/YYYY年报.md`

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Calendar empty | `icalBuddy eventsToday`; check Privacy & Security → Calendar permissions |
| Diary not generated | `hermes cron list` → last_run_at; test `collect_data.py` manually |
| AI logs empty/missing regent | Test: `python3 {baseDir}/scripts/extract_hermes_conversations.py $(date +%Y-%m-%d)` |
| CC logs empty | Check `find ~/.claude/projects/ -name "*.jsonl" -newermt "YYYY-MM-DD"`; verify JSONL files exist for target date |
| Weather fails | `curl -s "https://api.open-meteo.com/v1/forecast?latitude=30.27&longitude=120.16&current_weather=true"` |
| dataless files on read | Trigger Obsidian sync first; fallback to qmd index |
| 🔴 **cron job 从 scheduler 消失** | `hermes cron list --profile cron-worker` 和 `hermes cron list` 中均无 `a68f4f81b3ee`。config 存档 `config/cron-job.json` 仍存在但 cron 实体已丢失。重建：`hermes --profile cron-worker cron create` 并从存档中拷贝参数。 |
| 🔴 **日记质量逐日退化** (CC=0, 知识库=0, 裸模板) | ⭐ **先查 cron skills！** `cronjob list` 和 `hermes --profile cron-worker cron list` 看 Skills 字段是否为空。**再查 HERMES_HOME 污染**：如果只有 cron-worker 会话、regent 全部缺失，是 v3.6 之前的 HERMES_HOME 污染 bug。**再查 Path.home() chroot 污染 (v3.6.3)**：如果 Hermes/CC/Vault 三项全 0 但天气和日历正常，是 HOME 被 cron chroot 覆盖——升级到 v3.6.3 用 pwd.getpwuid() 修复。 |
| 🔴 **vault 变更条目偏少** (find 扫不到已删文件) | `find -newermt` 只扫存在的文件。检查 staged 删除: `git -c core.quotepath=false -C ~/Documents/Obsidian/AlexCai diff --diff-filter=D --name-only HEAD | grep '\.md$'`。v3.7.0 的 `scan_vault_deletions()` 已自动检测。注意：必须加 `-c core.quotepath=false` 否则中文路径被转义导致 grep 失败。 |
| 🔴 **知识库变更条目偏少** (只有 vault，缺 jz-skills commits) | v3.7.0 的 `scan_jzskills_commits()` 已自动扫描。手动检查: `git -C ~/code/jz-skills log --after="DATE" --before="DATE+1" --oneline`。问题通常是 jz-skills repo 不存在或 git 不可用。
| 🔴 **Codex 会话缺失** (v3.8.1 双源) | `collect_data.py` 的 `codex_sessions` 字段为空或全零。v3.8.1 前只读 SQLite。先手动测试: `python3 ~/.hermes/skills/auto-diary/scripts/extract_codex_conversations.py 2026-06-13`。若 SQLite 为 0 但 JSONL 目录有文件（`ls ~/.codex/sessions/YYYY/MM/DD/`），说明是双源漏扫——升级到 v3.8.1。若 SQLite 和 JSONL 都为空，说明当天确实没有 Codex 使用。 |

## ✅ Verification Checklist

Run automated check (v2.0 深度校验,支持单文件): `python3 {baseDir}/scripts/verify_diary_compliance.py <file.md>`
不带参数则校验整个日记目录。校验 13 项结构 + 6 项深度规则(三问三条/CC三组/体系 info callout/底部分隔/速览四要素/禁折叠callout)。退出码非 0 = 有不合格文件。

Manual checklist:

- [ ] Target date confirmed and correct?
- [ ] `collect_data.py` ran successfully (weather + AI logs + CC logs + vault changes)?
- [ ] Calendar queried with correct calendar names (`个人1,工作1,Naomi1,Zelda1`)?
- [ ] If existing_content: user-written sections preserved, only gaps filled?
- [ ] 🔴 NO raw user messages quoted — all AI topics summarized?
- [ ] 🔴 All topics from `ai_logs.*.topics` covered? Busy days (10+ streams) cross-checked against raw sessions?
- [ ] 🔴 Emoji correct? 🐴=助理体系 · 🏛️=治理体系 · 🤖=Codex · 💻=CC · 🦞 NEVER appears?
- [ ] v3.8.0 format: inverted pyramid (三问 at top) / frontmatter / abstract callout / info callouts / --- dividers / tip callout / no folding?
- [ ] Hermes split into 🐴助理体系 and 🏛️治理体系? Profiles correctly assigned?
- [ ] 🤖 Codex section present? Three-type split: 💻独立 / 🤝Guardian / 🤖程序?
- [ ] CC split into 🤝 协作 / 💻 独立 / 🤖 程序 三组? Per-project topics shown? Priority order correct?
- [ ] 📚 知识库按来源体系分组（🐴/🏛️/💻）? 关联标注正确? 不可靠匹配标 `(推断)`?
- [ ] All 10 required sections present? (或直接跑 `verify_diary_compliance.py <file>` 自动校验)
- [ ] File written to correct Obsidian path?
- [ ] User notified (cron: final response; manual: Telegram)?

## ⏰ Cron 配置

Cron job 配置存档于 `config/cron-job.json`，包含完整 prompt + schedule + model。每次更新 prompt 后应同步更新此文件。

- Current: 每天 23:00, cron-worker profile, deepseek-v4-flash
- Job ID: `a68f4f81b3ee`
- **四个 cron 全部在 cron-worker profile**。日记 cron 以 cron-worker 身份运行（独立 gateway `ai.hermes.gateway-cron-worker`）。周/月/年报 cron 在 cron-worker profile scheduler（`hermes --profile cron-worker cron list`）。
- v3.5.1: **🔴 四个 cron 的 skills 必须非空**。2026-06-02~04 日记崩塌根因：skills 空数组导致裸跑。诊断：`cronjob list` 看 Skills 列；修复：`cronjob update`（根可见）/ `hermes --profile cron-worker cron edit --skill auto-diary`（cron-worker）。
- v3.5.1 hotfix: **🔴 每日日记 cron 已从 scheduler 消失**。2026-06-04 发现：`a68f4f81b3ee` 在根和 cron-worker profile 的 scheduler 中均不存在，仅 `config/cron-job.json` 存档残留。这是独立于 empty-skills 的故障模式。对策：每次运行 Workflow A 时先做 cron health check（步骤 5），若缺失则在 final response 中报告。修复：`hermes --profile cron-worker cron create` + 从存档中拷贝参数。
- v3.4 prompt 闭环: 写日记前先 `Read` 已有文件(合并安全) → 写入 → 跑 `verify_diary_compliance.py` → FAIL 则对照 spec 重写直到 PASS → 交付。
- CC 数据真实路径: `ai_logs.claude_overview.{agent_team,standalone,program_call}`(注意 `ai_logs.` 前缀)。

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: auto-diary" && git push`
