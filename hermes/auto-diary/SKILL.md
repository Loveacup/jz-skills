---
name: auto-diary
description: |
  自动化日记生成和周报汇总。由 cron job 定时触发，采集天气(Open-Meteo)、日历事件(icalBuddy)、
  AI 对话记录(Hermes state.db + Claude Code JSONL)、知识库变更(Obsidian vault)，
  生成 Obsidian 日记并通过 Telegram 通知。
  周报可手动汇总上周日记生成（注：周报无自动 cron，仅手动触发）。支持日历事件回填和日记清理。

  Use when: cron triggers daily diary (23:00), or user manually requests
  生成日记 / 生成周报 / 日记草稿 / weekly report / diary / 补日程 / 整理日记.

  DO NOT use for: general note-taking, non-diary content generation, one-off research.
version: 3.4.0
author: Hermes Agent — v3.4 真实校验闭环 + 修正 section 计数/幽灵周报 cron/合并安全
---

# Auto-Diary v3.4

自动化日记生成和周报汇总。Cron 定时触发或手动调用。

> ⚠️ **真实调度状态**（2026-06-01 核实，勿凭文档假设）：
> 仅【每日日记草稿 23:00】这一个 cron 任务在跑（job `1ca6e7d692fa`）。
> **周报/月报/年报均无 cron，全部手动触发。** 改调度前先 `hermes cron list` 核实。

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
| "CC sessions are all the same, I'll list them flat" | 🔴 **CC three-type split** (v3.2): 🤝 Agent Team 协作 / 💻 独立对话 / 🤖 程序调用。Group by type THEN by project, per-project topics. Data in `claude_overview.agent_team`, `.standalone`, `.program_call`. Classification uses CC native metadata (entrypoint + parentUuid), not text matching. |
| "Knowledge base changes are independent" | 🔴 **KB ↔ AI linking** (v3.1): Every vault change was produced by an AI session. Cross-reference `vault_changes` paths/titles with session topics. Group by source system (🐴/🏛️/💻). Unreliable matches → mark `(推断)`. |
| "I'll batch-generate all 31 diaries with a Python loop, it'll be fast" | 🔴 **批量生成 = 垃圾** (v3.2): 用户明确拒绝模板填充式批量生成。正确做法：逐条处理，用 cron 输出摘要的叙事做底子，三问必须有洞察力。详见 `references/batch-generation-pitfall.md`。 |
| "I've written diaries before, I know the format — no need to load diary-format.md" | 🔴 **NEVER write from memory** (v3.3): 凭记忆写日记导致 2026-06-02 全月重写——用户发现缺失 info callout、段落合并、三问缩写、CC 未按三组拆分、底部分段拍扁、tip 格式错误。教训：写或重写任何日记之前，**必须** `skill_view(name='auto-diary', file_path='references/diary-format.md')` 加载格式 spec，逐段对照写。记忆不可信。 |

## 🔀 Decision Tree

```
Trigger received (cron or manual)?
├── Manual "生成日记" / cron daily → Workflow A: Daily Diary
├── Manual "生成周报" / cron weekly → Workflow B: Weekly Report
├── Manual "补日程" / "日历事件没记" → Workflow C: Calendar Backfill
├── Manual "整理日记" / "清理日记" → Workflow D: Diary Cleanup
└── Ambiguous → Ask user which workflow
```

## Workflow A: Daily Diary

1. Determine target date (default today)
2. Run: `python3 {baseDir}/scripts/collect_data.py diary YYYY-MM-DD`
3. Check calendar with icalBuddy using calendars `个人1,工作1,Naomi1,Zelda1` (iCloud `<email redacted>`)
4. Read format spec: `{baseDir}/references/diary-format.md`
5. Generate diary with 10 sections: 🎯每日总结(三问) → 🌤️概览(weather+mood) → ⏰时间线(calendar) → 🤖AI工作记录 → 📚知识库更新 → 📅日历事件(detailed table) → 🏠个人生活(placeholder) → ✅待办 → 📝临时笔记 → 💡tip 页脚
6. **CRITICAL 合并安全**: `collect_data.py` 的 `existing_content` 恒为 `null`（已知限制,脚本不读已有日记）。所以写入前**必须先 `Read` 目标日记文件**;若已存在用户手写内容 → 合并,保留用户文字,只填空缺。不可盲目覆盖。
7. **校验闭环**: 写完后运行 `python3 {baseDir}/scripts/verify_diary_compliance.py <写入的文件>`;若 FAIL,对照 `diary-format.md` 逐项重写,直到 PASS 再交付
8. Write to Obsidian vault
9. Notify user (cron: via final response; manual: via Telegram)

See `references/diary-format.md` for weather codes, calendar table format, and section templates.

## Workflow B: Weekly Report

> ⚠️ 周报**无自动 cron**,仅手动触发(`生成周报` / `weekly report`)。如需自动化,先建 cron 任务。

1. Calculate Mon-Sun of last week
2. Run: `python3 {baseDir}/scripts/collect_data.py weekly START END`
3. Read: `{baseDir}/references/weekly-format.md`
4. Process diaries across 5 analysis dimensions
5. Write: `02_周报/YYYY-Www周报.md` (ISO week, e.g. `2026-W21周报.md`)

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

1. Scan `50-Self/01_日记/` for empty/template diaries (qmd fallback for dataless files)
2. Rules in `references/diary-cleanup-heuristics.md`:
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
| Not checking `existing_content` before writing | Duplicate or conflicting diary entries |
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

## ⚠️ Config Drift (Silent Failure)

icalBuddy `-ic "cal1,cal2"` on mismatched names returns empty **without error**. If diary shows persistent "当日无日历事件" but user confirms events exist → run `icalBuddy calendars` and compare with `collect_data.py`. Known migration: iCloud `<email redacted>` added "1" suffix to all calendars.

## ⚠️ Known Limitations

**CC session count inflation**: Observer (Claude-Mem) sessions are tallied in CC counts but produce no meaningful topics — their system prompts are filtered. This means CC `session_count` can overrepresent on days with heavy observer activity. Low priority; acceptable trade-off for now.

**CC 内容展现偏薄** (v3.2 TODO): CC 段落目前只罗列 top-level 主题，没有 per-project 展开。待做：强制每个 CC 项目至少一条概括，和 Hermes 穷举覆盖同等粒度。

**知识库 ↔ AI 会话未关联** (v3.1 TODO): 知识库变更（vault_changes）目前独立展示，未标注是由哪个 AI 会话推动的。待做：在日记写作阶段做语义匹配，标注每个 vault 文件的来源会话。

## Output Paths

- Diary: `~/Documents/Obsidian/AlexCai/50-Self/01_日记/YYYY-MM-DD.md`
- Weekly: `~/Documents/Obsidian/AlexCai/50-Self/02_周报/YYYY-Www周报.md`

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Calendar empty | `icalBuddy eventsToday`; check Privacy & Security → Calendar permissions |
| Diary not generated | `hermes cron list` → last_run_at; test `collect_data.py` manually |
| AI logs empty/missing regent | Test: `python3 {baseDir}/scripts/extract_hermes_conversations.py $(date +%Y-%m-%d)` |
| CC logs empty | Check `find ~/.claude/projects/ -name "*.jsonl" -newermt "YYYY-MM-DD"`; verify JSONL files exist for target date |
| Weather fails | `curl -s "https://api.open-meteo.com/v1/forecast?latitude=30.27&longitude=120.16&current_weather=true"` |
| dataless files on read | Trigger Obsidian sync first; fallback to qmd index |

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
- [ ] 🔴 Emoji correct? 🐴=助理体系 · 🏛️=治理体系 · 💻=CC · 🦞 NEVER appears?
- [ ] v3.2 format: inverted pyramid (三问 at top) / frontmatter / abstract callout / info callouts / --- dividers / tip callout / no folding?
- [ ] CC split into 🤝 协作 / 💻 独立 / 🤖 程序 三组? Per-project topics shown? Priority order correct?
- [ ] 📚 知识库按来源体系分组（🐴/🏛️/💻）? 关联标注正确? 不可靠匹配标 `(推断)`?
- [ ] All 10 required sections present? (或直接跑 `verify_diary_compliance.py <file>` 自动校验)
- [ ] File written to correct Obsidian path?
- [ ] User notified (cron: final response; manual: Telegram)?

## ⏰ Cron 配置

Cron job 配置存档于 `config/cron-job.json`，包含完整 prompt + schedule + model。每次更新 prompt 后应同步更新此文件。

- Current: 每天 23:00, cron-worker profile, deepseek-v4-flash
- Job ID: `1ca6e7d692fa`
- **唯一在跑的日记 cron**。周报/月报/年报均无 cron(见 Workflow B 警告)。
- v3.4 prompt 闭环: 写日记前先 `Read` 已有文件(合并安全) → 写入 → 跑 `verify_diary_compliance.py` → FAIL 则对照 spec 重写直到 PASS → 交付。
- CC 数据真实路径: `ai_logs.claude_overview.{agent_team,standalone,program_call}`(注意 `ai_logs.` 前缀)。

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: auto-diary" && git push`
