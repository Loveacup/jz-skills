---
name: business-minutes
description: >
  Turn a meeting transcript (ASR 逐字稿、录音转写、带时间戳文本) into a publishable business minutes note that passes a fail-closed evidence gate.
  Use when the user asks for 会议纪要、商务拓展纪要、客户交流纪要、需求交流纪要、周例会纪要、BD 会议纪要、合作洽谈纪要、逐字稿转纪要、转录整理.
  Fuses voice-to-markdown-workflow's 8-phase pipeline (memory injection, verification gate, scene writer, correction crystallization) with the vault minutes SOP (external evidence table, decision four-element records, verbatim quotes, ledger update) and video-analysis-engine-style gates (verify_minutes.py).
  DO NOT use for video links (→ video-analysis-engine), lectures/podcasts/interviews (→ voice-to-markdown-workflow), or documents that are not transcripts.
version: 1.0.0
type: routine
license: MIT
metadata:
  hermes:
    tags: [minutes, meeting, transcript, evidence-gate, obsidian]
    related_skills: [voice-to-markdown-workflow, video-analysis-engine, 2pdf, obsidian-md-ac]
---

# Business Minutes — 逐字稿 → 可发布的商务纪要

One transcript in, one minutes note out. Publication is gated: `verify_minutes.py` must exit 0 before the note is called done.

## 🚨 Red Flags

| Excuse the agent will invent | Do this instead |
|---|---|
| "纪要顺手写一下就行，≤3 页" | 纪要是独立交付物，长度由逐字稿决定（G9 字数门）。短稿 = 未完成。 |
| "我读了摘要/基准线，不用再读逐字稿" | 只有逐字稿是事实来源。Phase 2 必须逐段读完转写。 |
| "人名转写不清，先按最像的写" | Phase 5 核验门：和 known-facts 比对，不一致就问用户一次，写进订正表。 |
| "决策写成一句话就够" | 每条决策四要素：内容 / 背景理由 / 预期后果 / 拍板人，带全局编号（G4）。 |
| "行动项没时间就写待定" | 责任人 + 节点 + 证据时间戳缺一即 G5 FAIL；确实未定的进"待确认事项"。 |
| "法规/对接/报价这些外部信息不用查" | 命中触发表就联网，写"外部情报与决策依据"表（G7）。 |
| "脚本过了就是好稿" | 门只证结构与指针完整。人工 QA 清单最后一步必做。 |

## Decision Tree

```text
Input is one transcript (txt/srt/md, ≥ 1 speaker)?
├─ No / it is a video link → video-analysis-engine
├─ Lecture / podcast / interview → voice-to-markdown-workflow
└─ Meeting or business conversation
   ├─ Scene: bd-meeting | requirements-interview | partnership | weekly-sync | general-meeting
   ├─ Mode: standard (default) | deep (adds Phase 6 strategic analysis; use for ≥ 90 min or C-level)
   └─ Runner: single-agent (Claude Code Task subagents) | relay (Orca + OMP file relay, see execution-flow.md)
```

## Pipeline (8 phases; each ends on a checkable artifact)

| Phase | Owner | Output | Done when |
|---|---|---|---|
| 0 材料清点 | main | `work/manifest.json` | every input file typed (transcript/ppt/screenshot/url), transcript chars & duration recorded |
| 1 记忆注入 | main + `scripts/memory_reader.py` | `work/known-facts.json` | speakers / projects / prior corrections loaded; empty memory is allowed but must be stated |
| 2 规范化 | scripts | `work/normalized.md`, `work/stats.json` | `speaker_normalizer` → `rule_based_cleaner` → `stat_extractor` ran without error |
| 3 分析 ∥ 知识增强 | 2 agents | `work/analysis.json`, `work/knowledge-context.json` | scene + sub-type decided; external search done for every hit in the trigger table (writing-spec.md §3) |
| 4 内容处理 | agent | `work/preprocessed.md` | topic-segmented, de-duplicated, every segment keeps `[hh:mm:ss]` anchors; no dialogue dropped |
| 5 核验门 | main | `work/verified-facts.json` + updated preprocessed.md | every person/company/product entity matched to known-facts or confirmed by the user **once** |
| 6 深度分析 (deep) | agent | `work/deep-analysis.json` | tensions, DIKW, strategic alignment |
| 7 成文 | `agents/minutes-writer.md` | `<纪要文件>.md` | template complete (references/minutes-template.md); `verify_minutes.py` exit 0 |
| 8 回写 | main + `scripts/memory_writer.py` | memory updated, ledger/项目档案 updated | corrections ≥5 occurrences across ≥2 sessions crystallized into `rule_based_cleaner` rules |

Full per-phase contract, prompts, and the relay task-pack template: `references/execution-flow.md`.

## The writer's non-negotiables (restated because they fail most)

1. **Evidence pointer on every claim**: decisions, action items and quotes carry `[hh:mm:ss]` from the transcript. No timestamp → not a fact, move it to 待确认.
2. **Decision = four elements + global ID** `YYWnn-Dxx` (ISO week). Action items `YYWnn-Axx`. IDs never reused.
3. **Verbatim quotes** for定调性表述: `> [!quote] 说话人 [hh:mm:ss]` — at least 3 per hour of meeting.
4. **External evidence table**: `证据(URL+日期) → 支撑的决策 ID`. Not found → write "未检索到", never invent.
5. **Correction table回填**: every new mis-transcription goes into the note's 订正表 **and** `memory/corrections.json`.
6. **Narrative before tables**: each topic opens with 背景 → 讨论 → 结论 prose; tables only for decisions, actions, evidence, participants.

## Gate

```bash
python3 scripts/verify_minutes.py <minutes.md> --transcript <transcript.txt> [--mode standard|deep] [--json]
```

G1 frontmatter · G2 参会表 · G3 执行摘要 · G4 决策四要素+ID · G5 行动项责任人+节点+证据 · G6 原话引用数 · G7 外部依据表 · G8 订正表 · G9 字数下限（按逐字稿规模）· G10 无占位符/无转写倾倒。Exit 1 on any FAIL. Definitions and thresholds: `references/gates.md`.

## Deliver

- Obsidian frontmatter per the vault rules (`type: 会议纪要|商务拓展纪要|周例会纪要`, tags with prefixes, `related` wikilinks ≥ 3).
- PDF via `2pdf` with `--theme blue` fixed (dark auto-routing is wrong for business documents).
- Update the ledger/项目档案 the vault SOP names; then delete process files (`work/`) — the note is the only archive.

## ✅ Before returning

- [ ] Did I read the **whole** transcript in Phase 2/4 (not a summary)?
- [ ] Did the verification gate ask the user about every unmatched name **once**, and did I write the answers to the 订正表 + memory?
- [ ] Does `verify_minutes.py` exit 0 with the real transcript passed via `--transcript`?
- [ ] Did I read the final Markdown myself for skeleton residue, repetition, and dumped transcript?
- [ ] Did I update memory (speakers / sessions / corrections) and the ledger?

If any box is empty, go back.

---
> Depth on demand: `references/execution-flow.md` (phases, prompts, relay) · `references/minutes-template.md` (成稿模板 3 变体) · `references/writing-spec.md` (质量红线、触发表、四要素) · `references/gates.md` (G1–G10) · `references/memory-schema.md`.
