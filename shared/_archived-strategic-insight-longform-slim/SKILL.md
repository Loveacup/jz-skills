---
name: strategic-insight-longform
description: |
  战略洞察长文工作流 v4.2 — 基于S-T-D立方体+多维分析矩阵+GoT自适应路径优化，将商业现象、行业趋势、企业战略转化为结构化深度洞察报告。

  Three execution modes (default Deep):
  - Deep: 16 Agent + GoT adaptive + CoV anti-hallucination verification, 12-20 min
  - Standard: 9 core Agent, 7-10 min (user must explicitly request)
  - Quick: 5 core Agent, 3-5 min (user must explicitly request)

  Hermes mapping: Claude Code TeamCreate/TaskCreate → delegate_task. Use clarify for user confirmation. Use Exa MCP or web_search for external search. Use qmd CLI for knowledge base. If obsidian-md-ac unavailable, format output manually.

  Trigger: 战略洞察、深度分析、行业研究、趋势研判、现象解构、长文撰写、strategic insight、industry analysis、deep dive、商业洞察、战略报告、全息分析、S-T-D分析
  Quick trigger: 快速分析、简要分析、quick、简版
  Standard trigger: 标准分析、standard、常规分析
  DO NOT trigger on: casual Q&A, simple fact lookup, local file operations.
version: 4.2.1
author: Claude Code → Hermes (slimmed v4.2.1)
license: Proprietary
---

# Strategic Insight Longform v4.2.1

S-T-D Cube + Multi-Dimensional Analysis Matrix + GoT Adaptive Path Optimization.
Slimmed from 513→~250 lines; agent pipeline and roster moved to references.

## Modes

| Mode | Agents | Time | Trigger |
|------|--------|------|---------|
| **Deep** (default) | 16 full + GoT | 12-20 min | Default execution |
| **Standard** | 9 core | 7-10 min | User explicitly requests |
| **Quick** | 5 core | 3-5 min | User explicitly requests |

## Architecture (High Level)

```
Leader (main process)
  ├─ Serial: topic-preprocessor → knowledge-enricher → framework-builder → got-controller(D)
  ├─ Parallel: 3-5 researchers (spatial/temporal/domain/stakeholder/causal)
  ├─ Serial: source-manager(D) → insight-synthesizer → longform-writer → output-finalizer
  │   └─ Stage 6.5: obsidian-md-ac formatting (emoji titles, callouts, Mermaid, YAML)
  ├─ Parallel(D): memory-curator + pattern-crystallizer
  └─ Copy final file to Obsidian inbox
```

**Full 16-agent pipeline**: see `references/agent-pipeline.md`
**Agent roster**: see `references/agent-roster.md`

## Framework Building (Stage 1)

framework-builder selects frameworks via two-tier selection:
1. **3 mandatory frameworks**: S-T-D Cube (always) + analysis_type specific (see `references/framework-library.md` for ~75 frameworks across 10 categories)
2. **3-5 supplementary frameworks**: Auto-recommended by analysis_type

## Knowledge Enhancement (Stage 0.5)

1. **qmd vsearch**: Search Obsidian knowledge base (relevance > 0.5)
2. **Historical analysis**: Match from memory-context.json
3. **Exa multi-layer search**: web_search_exa → company_research_exa → crawling_exa
4. **Degradation**: qmd unavailable → skip vector search; Exa unavailable → fallback to web_search

Output: `knowledge-context.json` for all subsequent agents.

## Output Quality

### insight-synthesizer
- Second-order inference: "What does this lead to?"
- Third-order inference: chain effects
- Cross-dimensional matrix: S*T, S*D, T*D combos
- Counterfactual analysis: "What if X didn't happen / went the opposite way?"

### longform-writer
- No hard word limit → content completeness check
- Chain-of-thought embedded: main CoT (after holographic summary) + per-section callouts
- Source index appendix integrated at end
- Insight hierarchy fidelity: never compress or omit multi-layer inference chains
- Wikilinks naturally embedded from knowledge-context
- Appendices: data summary, causal chain diagram, game matrix, scenario hypothesis, source index

### output-finalizer
- Single file output: `战略洞察-{title}.md`
- Revision loop: score < 4.0 → max 1 revision round
- Argument quality: logical gaps, implicit assumptions, counter-evidence, confidence annotation
- Auto-save to Obsidian inbox

### source-manager (CoV anti-hallucination, Deep only)
- **Layer 1**: Citation completeness — scan all factual claims (target 100% coverage)
- **Layer 2**: Source reachability — crawling_exa check URLs, flag dead links
- **Layer 3**: Cross-validation — 5-10 key claims, web_search_exa for independent confirmation

## Memory System

6 JSON files in `memory/`: topics.json, sources.json, frameworks.json, sessions.json, preferences.json, patterns.json. Schema: `references/memory-schema.md`.

## Learning System

5 pattern types (framework_effectiveness, source_reliability, writing_optimization, analysis_depth, topic_association). Crystallization: confidence ≥0.85 + ≥3 occurrences → auto-activate; 0.70-0.85 → pending; <0.70 → discard. Daily decay 0.01; >30 days unused → auto-degrade.

## Scheduling Rules

All agents dispatched via `delegate_task` (Hermes) or `Task` (Claude Code). Agent `.md` `tools:` lists are documentation only. See `references/agent-pipeline.md` for full dispatch logic.

## References

| File | Content |
|------|---------|
| `references/agent-pipeline.md` | Full 16-agent dispatch pipeline with pseudo-code |
| `references/agent-roster.md` | 16 agent definitions, stages, modes |
| `references/framework-library.md` | ~75 analysis frameworks, 10 categories |
| `references/memory-schema.md` | Memory JSON schemas |
| `references/std-cube-methodology.md` | S-T-D methodology |
| `config.json` | Execution modes, agents, memory, learning, CoT, output, quality thresholds |

## Verification Checklist

- [ ] Mode selected (Deep/Standard/Quick) based on user input?
- [ ] framework-builder selected 3 mandatory + 3-5 supplementary frameworks?
- [ ] All researcher agents completed before insight-synthesizer starts?
- [ ] Source verification (CoV) completed in Deep mode?
- [ ] output-finalizer score ≥4.0? If not, revision loop completed?
- [ ] Final file saved to Obsidian inbox?

*Strategic Insight Longform v4.2.1 — slimmed for Hermes compliance*

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: strategic-insight-longform" && git push`
