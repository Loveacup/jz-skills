# business-minutes

逐字稿 → 可发布的商务/会议纪要，带 fail-closed 证据门。

## Why this exists

A 2h49m客户需求交流 produced a 4885-line requirements baseline but a 69-line minutes note, because the minutes were a side product of an assembly agent that never read the transcript. The vault already had a minutes SOP, a strategic-narrative guide and a prompt; `voice-to-markdown-workflow` already had the pipeline (memory, verification gate, scene writer, correction crystallization); `video-analysis-engine` already had evidence gates. None were wired together. This skill wires them.

## What it fuses

| Source | Taken |
|---|---|
| voice-to-markdown-workflow v6.0 | 8-phase DAG, known-facts memory injection, entity verification gate, meeting-writer skeleton, correction crystallization, 6 stdlib scripts |
| Vault 周例会纪要写作规范 + 战略产品会议纪要撰写指南 + 会议纪要v2 | external-evidence table with决策 ID mapping, decision four elements + global IDs, `[!quote]` verbatim rule, 订正表回填, timeline + 思维链, ledger update, 2pdf blue |
| video-analysis-engine v4 | fail-closed publish gate, evidence pointer on every claim, action items must cite evidence, human QA checklist |

## Layout

```text
SKILL.md                 body < 100 lines: red flags, decision tree, 8 phases, gate, checklist
agents/                  minutes-writer.md (new) · red-team-reviewer.md (new) · scene-analyzer / knowledge-enricher / content-processor / deep-analyst (inherited)
references/              execution-flow.md · minutes-template.md · writing-spec.md · gates.md · memory-schema.md · decision-frameworks.md
scripts/                 verify_minutes.py (G1–G10, new) + speaker_normalizer / speaker_mapper / rule_based_cleaner / stat_extractor / memory_reader / memory_writer / pattern_analyzer (inherited, stdlib only)
memory/                  _templates/*.json (personal memory is gitignored)
tests/                   fixtures (synthetic 云帆×青禾 case) + test_verify_minutes.py (10 tests: pass case + one mutation per gate)
config.json
```

## Quick start

```bash
# gate a note against its transcript
python3 scripts/verify_minutes.py 纪要.md --transcript 逐字稿.txt --mode standard

# tests
python3 -m pytest -q tests
```

## Runners

- **single-agent**: Claude Code `Task` subagents per phase (needs `subagent_type="general-purpose"` for MCP).
- **relay**: Orca + OMP file relay for long transcripts or scarce coordinator quota — see `references/execution-flow.md`.

## Status

v1.0.0 — first release. Known limits: gates prove structure and pointer integrity, not truth; scene-analyzer / knowledge-enricher / content-processor prompts are inherited from voice-to-markdown and referenced, not duplicated here.
