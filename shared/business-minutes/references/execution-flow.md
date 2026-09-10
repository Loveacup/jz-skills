# Execution Flow — 8 phases, two runners

Load when starting a run or when a phase artifact is missing. Every phase ends on a file; the next phase reads only files (never chat history).

## Runners

| Runner | When | Mechanics |
|---|---|---|
| **single-agent** | transcript ≤ 40k chars, Claude Code available | Main agent runs Phases 0/1/2/5/8 itself; Phases 3/4/6/7 via `Task` with `subagent_type="general-purpose"` (needed for MCP access). |
| **relay** | transcript > 40k chars, or coordinator quota is scarce, or Orca + OMP available | Main agent is Leader (writes task packs, dispatches, verifies); each phase runs in a fresh OMP terminal via `orca orchestration dispatch --inject`; all state passes through `work/`. See "Relay task pack" below. |

Both runners obey the same artifacts and the same gate.

## Directory

```text
<run_dir>/
├── input/            transcript(s), ppt, screenshots (read-only)
├── work/             manifest.json, known-facts.json, normalized.md, stats.json,
│                     analysis.json, knowledge-context.json, preprocessed.md,
│                     verified-facts.json, deep-analysis.json, receipts/
└── <minutes>.md      the only deliverable (plus optional PDF)
```

## Phase contracts

### Phase 0 · 材料清点 (main)
- Type every input: `transcript` (txt/srt/md with or without timestamps), `slides`, `screenshot`, `url`, `doc`.
- Record `transcript_chars`, `estimated_minutes` (from last timestamp or chars/220), `has_timestamps`, `has_speaker_labels`.
- Output `work/manifest.json`. Missing transcript → stop and ask.

### Phase 1 · 记忆注入 (main)
- `python3 scripts/memory_reader.py work/normalized.md work/known-facts.json --memory-dir <memory>`（输入用规范化稿；Phase 2 未完成时可先用原始转写）
- known-facts holds: confirmed speakers (name, role, aliases, voiceprint id), projects, prior ASR corrections, user preferences.
- Empty memory is fine; write `"memory_state": "empty"` so later phases don't pretend.

### Phase 2 · 规范化 (scripts)
```bash
python3 scripts/speaker_normalizer.py input/transcript.txt work/normalized.md   # uses known-facts aliases
python3 scripts/rule_based_cleaner.py work/normalized.md work/normalized.md     # crystallized ASR rules
python3 scripts/stat_extractor.py work/normalized.md work/stats.json
```
- Keep timestamps. Never delete lines; cleaning is substitution only.

### Phase 3 · 分析 ∥ 知识增强 (two agents, parallel)
- **scene-analyzer** → `work/analysis.json`: `{scene, sub_type, confidence, participants_guess[], topics[{title, start, end}], decision_signals[], action_signals[]}`. confidence < 0.7 → ask user.
- **knowledge-enricher** → `work/knowledge-context.json`: vault lookups (qmd/Obsidian search; skip if unavailable, say so) **and** external search for every trigger hit (writing-spec.md §3): `{evidence[{claim, url, date, quote, supports}], wikilinks[{name, exists}], unresolved[]}`.

### Phase 4 · 内容处理 (content-processor)
- Input: normalized.md + analysis.json + known-facts.json (prompt header).
- Segment by topic; merge scattered discussion of the same topic; delete filler only; keep `[hh:mm:ss]` on every paragraph; keep verbatim candidate quotes (≤ 60 chars each) tagged `QUOTE`.
- Output `work/preprocessed.md` + `work/entities.json` (every person/company/product/place with first timestamp).

### Phase 5 · 核验门 (main, blocking)
- Cross-check `entities.json` against known-facts: match → confirm; candidate (`张总?`) → show the 3 longest utterances, ask; new → ask for name/role once; mismatch → ask.
- Ask the user **once**, in one message, for all open entities.
- Write `work/verified-facts.json`; apply corrections to preprocessed.md; append new corrections to the note's 订正表 draft.

### Phase 6 · 深度分析 (deep mode only)
- deep-analyst → `work/deep-analysis.json`: tensions, DIKW, strategic alignment, risks. Skip in standard mode.

### Phase 7 · 成文 (agents/minutes-writer.md)
- Reads: preprocessed.md, analysis.json, knowledge-context.json, verified-facts.json, known-facts.json, deep-analysis.json (if any), `references/minutes-template.md`, `references/writing-spec.md`.
- Writes `<minutes>.md` following the template variant for `sub_type`.
- Then run the gate; on FAIL fix and rerun (max 2 rounds), then human QA.

### Phase 8 · 回写 (main)
- `python3 scripts/memory_writer.py work/ <memory>` — reads the phase artifacts in `work/` and updates speakers / sessions / corrections / metrics.
- `python3 scripts/pattern_analyzer.py <memory> work/pattern-candidates.json` → candidates with ≥ 5 occurrences across ≥ 2 sessions become rules for `rule_based_cleaner` (write them to `memory/patterns.json`, type `asr_correction`).
- Update the vault ledger / 项目动态档案 named in the SOP; delete `work/`.

## Relay task pack (OMP / Orca)

One file per phase in `10_任务包/`. Keep every pack self-contained:

```text
# 任务包 P<phase> · <名称>
<protocol>先读 接力协议.md（目录、只读输入、只写指定输出、回执五段、worker_done）。</protocol>
<role>你是 <agent 名>。</role>
<goal>产出 work/<artifact>。</goal>
<inputs>只读：<路径列表>。**禁止整份读入超过 60k 字符的文件**：逐字稿按时间段分段读（sed -n），编码稿按追溯索引定位。</inputs>
<output_schema>… 与 Phase contract 一致 …</output_schema>
<depth>字数/条目下限；每条带 [hh:mm:ss]。</depth>
<boundaries>不联网（除 knowledge-enricher）；不派子代理；不改输入；总时长 ≤ N 分钟。</boundaries>
<self_check>… 与 gates.md 对应项 …</self_check>
```

Leader rules learned the hard way: `python3` + `PYTHONIOENCODING=utf-8` on Windows; write Orca JSON to a file before parsing; one `check --wait` loop at a time; settle a task from its receipt when `worker_done` is lost; a worker that reads a whole 250 KB file will overflow and hang — narrow reads are mandatory.

## Single-agent prompt headers

Every subagent prompt starts with the injected block:

```text
## 已验证事实（来自记忆，必须遵守）
<known-facts.json 摘要：人名/角色/别名、项目名、历史订正>
如转写与上表冲突，以上表为准，并把冲突记入 corrections。
```
