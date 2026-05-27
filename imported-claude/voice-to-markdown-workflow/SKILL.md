---
name: voice-to-markdown-workflow
description: |
  语音/视频转录文本的智能处理工作流 v6.0。自动识别内容场景并调度专业化Subagent执行多阶段处理。

  Supported scenes: meetings (project sync, product review, brainstorm, BD, collaboration, periodic), learning (lectures, podcasts, courses), conversations (interviews), general.

  v6.0 features: material intake (multi-type input normalization), mandatory memory injection (known-facts.json to all agent prompts), verification gate (ASR entity vs memory cross-check), single-file output default, dependency DAG (writer waits for all predecessors), Foundry-style pattern crystallization (≥3 corrections → auto-write Python script rules).

  Hermes mapping: Claude Code Task → Hermes delegate_task. Use clarify for user confirmation. Use qmd CLI for knowledge retrieval. If qmd unavailable, skip knowledge enhancement (don't block pipeline).

  Trigger: 语音转文档、转录整理、会议记录、项目会议、产品评审、头脑风暴、brainstorm、商务对接、BD会议、播客笔记、讲座笔记、采访整理、voice to markdown、transcription workflow
  DO NOT trigger on: general text editing, non-transcription tasks.
version: 6.0.1
author: Claude Code → Hermes (slimmed v6.0.1)
license: Proprietary
---

# Voice-to-Markdown v6.0.1

Intelligent voice/video transcription processing workflow. Slimmed from 349→~220 lines; execution flow moved to references.

## 8 Core Rules

1. **Scene auto-detect**: scene-analyzer determines meeting/lecture/interview; confidence <0.7 → ask user
2. **Three modes**: Quick (3 agents, 1-2 min), Standard (5 agents, 3-5 min, default), Deep (6 agents, 5-8 min)
3. **Single-file output default**: One integrated file. `--layered` flag enables multi-file output
4. **Material intake (v6.0)**: transcripts, PPT/PPTX, screenshots, URLs, documents → normalized-input.md + manifest.json
5. **Parallel only Phase 3**: scene-analyzer ∥ knowledge-enricher. Everything else serial
6. **Mandatory memory**: known-facts.json injected into every agent prompt header. Update speakers/sessions/corrections/metrics after each run
7. **Mandatory verification gate**: Phase 5 extracts all entities from preprocessed.md, cross-checks against known-facts.json, asks user once for any inconsistencies
8. **Hermes agent dispatch**: All via `delegate_task`. qmd MCP unavailable → skip knowledge enhancement only

## Execution Flow (High Level)

```
Phase 0: Material Intake (main agent) → manifest.json
Phase 1: Memory Injection (main agent) → known-facts.json
Phase 2: Input Normalization (Python scripts) → normalized-input.md
Phase 3: Analysis (parallel) → scene-analyzer ∥ knowledge-enricher(qmd+Exa)
Phase 4: Content Processing (content-processor) → preprocessed.md
Phase 5: Verification Gate (main agent) → ASR entity vs memory cross-check
Phase 6: Deep Analysis (deep-analyst, Deep mode only) → deep-analysis.json
Phase 7: Writing (writer, scene-routed) → output.md
Phase 8: Output + Memory Writeback (main agent) → copy file + update 5 memory files
```

**Full DAG and per-phase details**: see `references/execution-flow.md`

## Scene Routing

| Scene | Writer | Key Features |
|-------|--------|-------------|
| Meeting | meeting-writer | Strategic narrative, DACI decisions, action items |
| Lecture | lecture-writer | Knowledge structure, key concepts, Q&A capture |
| Interview | interview-writer | Q&A preservation, thematic clustering, quotes |
| General | meeting-writer (fallback) | Best-effort structured document |

## Verification Gate (v6.0)

Phase 5, before writer starts:
- Extract all entities from preprocessed.md
- Cross-check against known-facts.json:
  - Voiceprint match (confidence=1.0) → auto-confirm
  - Match → confirm
  - Candidate match (name?) → show speech snippet, ask user
  - Mismatch → ask user
  - New entity → ask user to supplement
- Unknown speaker registration (v6.3): check `*-speaker-embeddings.json` sidecar, register voiceprints
- Output: verified-facts.json; if corrections → update preprocessed.md

## Pattern Crystallization (v6.3)

After each run, check corrections.json for uncrystallized rules:
- Condition: occurrences ≥5 AND ≥2 different sessions
- Satisfied → write to patterns.json (type=asr_correction)
- Mark crystallized=true + crystallized_at timestamp

## Output Strategy

**Default (single file)** : executive summary + full minutes + decisions (DACI) + action items + deep analysis (Deep mode). Filename: `{scene}_{date}.md`

**Layered (`--layered`)**: 5 files — executive-summary.md, full-minutes.md, action-items.md, decision-log.md, deep-analysis.md

## Scripts

| Script | Function |
|--------|----------|
| `input_formatter.py` | Input format normalization |
| `speaker_normalizer.py` | Speaker label normalization |
| `stat_extractor.py` | File statistics extraction |
| `rule_based_cleaner.py` | Rule-based cleaning (crystallized ASR rules) |
| `markdown_formatter.py` | Markdown formatting |
| `circuit_breaker.py` | Circuit breaker + retry + paragraph isolation |
| `semantic_chunker.py` | Semantic chunking (by speaker/topic) |
| `speaker_mapper.py` | Intelligent speaker mapping |
| `quality_scorer.py` | Quantitative quality scoring (A/B/C/D) |
| `progress_reporter.py` | Real-time progress feedback |
| `memory_reader.py` | Read memory and match context |
| `memory_writer.py` | Write processing results to memory |
| `pattern_analyzer.py` | Cross-session pattern analysis |

## References

| File | Content |
|------|---------|
| `references/execution-flow.md` | Full 8-phase execution DAG with per-phase detail |
| `references/user-personas.md` | User personas and output strategies |
| `references/strategic-narrative.md` | Strategic narrative writing guide |
| `references/decision-frameworks.md` | DACI/SPADE frameworks |
| `references/obsidian-format-guide.md` | Obsidian format spec |
| `references/meeting-templates.md` | Meeting templates by sub-type |
| `references/memory-schema.md` | Memory JSON schemas (v6.0) |
| `references/qmd-setup-guide.md` | qmd vector search auto-deployment |

## Verification Checklist

- [ ] Scene auto-detected or confirmed by user?
- [ ] Mode selected (Quick/Standard/Deep)?
- [ ] known-facts.json injected into all agent prompts?
- [ ] Verification gate completed before writer starts?
- [ ] Writer waited for ALL predecessor agents to complete?
- [ ] Memory writeback completed (speakers + sessions + corrections + metrics)?
- [ ] Pattern crystallization check run (≥5 occurrences + ≥2 sessions)?
- [ ] Output file saved to user-specified directory?

*Voice-to-Markdown v6.0.1 — slimmed for Hermes compliance*

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: voice-to-markdown" && git push`
