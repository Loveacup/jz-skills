---
name: deep-research-agent
description: "Use when performing deep research and knowledge synthesis — multi-source web/academic search, hierarchical task graphs, evidence-backed claim verification, structured literature reviews, and long-horizon agentic research for 翰林院 knowledge work. Based on KResearch (KuekHaoYang/KResearch, 336⭐, MIT, any LLM provider) and IterResearch (Chen-GX/IterResearch, 50⭐, ICLR'26, 2048+ tool calls with 40k context). Do NOT use for simple web search (use web-research-router) or for fact-checking single claims (use source-verification)."
version: 1.0.0
author: Hermes Agent (based on KuekHaoYang/KResearch + Chen-GX/IterResearch)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hanlinyuan, research, knowledge-synthesis, academic, deep-research]
    related_skills: [web-research-router, source-verification, arxiv, llm-wiki]
---

# Deep Research Agent — 翰林院深度研究

> Based on KResearch (336⭐, MIT, autonomous multi-source research with inline citations) and IterResearch (50⭐, ICLR'26, Markovian state reconstruction for 2048+ tool calls). Adapted for 三省六部 翰林院 knowledge synthesis work.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just run a few web searches and summarize" | Web search → summarize misses 80% of the value. Deep research requires iterative planning: search → read → extract → verify gaps → search more → synthesize. Each cycle deepens understanding |
| "The LLM can reason from its training data" | Training data is frozen. For current events, recent papers, or domain-specific knowledge, you need live multi-source research with evidence trails |
| "I don't need a task graph for a simple research question" | "Simple" questions often unfold into sub-questions. "Compare GPT-5 and Claude 4" → sub-questions about architecture, benchmarks, pricing, safety. Without a task graph, you miss dimensions |
| "One round of search is enough" | First-round results are surface-level. IterResearch's key insight: multi-turn tool interactions (search→read→analyze→search deeper) with Markovian state reconstruction achieve 2048+ tool calls without context explosion |

## When to Use

- Writing comprehensive research reports on complex topics
- Conducting structured literature reviews (academic papers across Google Scholar/arXiv/Semantic Scholar)
- Comparing technologies/products with multi-dimensional analysis
- Investigating "what happened and why" questions requiring multi-source triangulation
- Building knowledge bases from unstructured web/academic sources

## Architecture

```
Research Question
       │
       ▼
┌─ Hierarchical Task Graph ──────────────────────┐
│                                                 │
│  Sub-task 1: Search        Sub-task 2: Analyze  │
│  (Google/Bing/Scholar)     (extract claims)     │
│       │                         │               │
│       ▼                         ▼               │
│  Sub-task 3: Verify         Sub-task 4: Gap     │
│  (cross-ref sources)        (identify missing)  │
│       │                         │               │
│       └───────┬─────────────────┘               │
│               ▼                                 │
│  Sub-task 5: Synthesize (structure + citations) │
│               │                                 │
└───────────────┼─────────────────────────────────┘
                ▼
        Structured Report
        (every claim → inline citation)
```

## Core Capabilities

### 1. Hierarchical Task Graph

The agent decomposes research questions into a DAG:

```yaml
# Auto-generated task graph for "Compare GPT-5 and Claude 4"
tasks:
  - id: search-gpt5
    type: search
    query: "GPT-5 architecture benchmarks 2025 2026"
    dependencies: []
  - id: search-claude4
    type: search
    query: "Claude 4 architecture benchmarks 2025 2026"
    dependencies: []
  - id: extract-claims
    type: analysis
    dependencies: [search-gpt5, search-claude4]
  - id: identify-gaps
    type: gap-analysis
    dependencies: [extract-claims]
  - id: fill-gaps
    type: search
    query: "from gap analysis"
    dependencies: [identify-gaps]
  - id: synthesize
    type: synthesis
    dependencies: [extract-claims, fill-gaps]
```

### 2. Evidence-Backed Synthesis

Every factual claim links to its source:

```markdown
## Performance Comparison

GPT-5 achieves 92.3% on MMLU-Pro [1], while Claude 4 reaches 94.1% [2].
However, on coding benchmarks, GPT-5 leads with 88.7 on SWE-bench [3]
compared to Claude 4's 85.2 [4].

The key architectural difference: GPT-5 uses a sparse mixture-of-experts
with 1.2T active parameters [1, §3.2], while Claude 4 employs a dense
transformer with constitutional RLHF alignment [2, §4.1].

## References
[1] OpenAI. "GPT-5 Technical Report." arXiv:2503.xxxxx, Mar 2025.
[2] Anthropic. "Claude 4 Model Card." anthropic.com, Apr 2025.
[3] SWE-bench Leaderboard. swebench.com, accessed May 2026.
[4] Aider LLM Leaderboard. aider.chat, accessed May 2026.
```

### 3. Iterative Deepening (IterResearch Pattern)

Markovian state reconstruction enables 2048+ tool calls without context explosion:

```
Turn 1: Search "GPT-5" → 10 results → Read 3 → Extract 15 claims
Turn 2: Gap detected: missing pricing → Search "GPT-5 pricing" → Read 2
Turn 3: Contradiction found: benchmark scores differ → Verify with primary source
...
Turn 50: All claims verified, gaps filled → Synthesize final report

Total: 50 turns, 2,048 tool calls, 40k context window maintained throughout
```

### 4. Structured Literature Review (deep-researcher pattern)

```bash
# Search 100 papers, enrich with OpenAlex metadata, synthesize by theme
hermes research literature-review \
  --query "multi-agent reinforcement learning with LLMs" \
  --papers 100 \
  --source google-scholar \
  --enrich openalex \
  --output lit-review.md

# Output: papers categorized by theme, cross-category patterns, BibTeX
```

### 5. Multi-Source Triangulation

```bash
hermes research verify-claim \
  --claim "GPT-5 costs $0.02 per 1K input tokens" \
  --min-sources 3 \
  --confidence-threshold 0.90

# Output:
# Source 1: OpenAI pricing page → $0.015/1K (conflict)
# Source 2: TechCrunch article → $0.02/1K (agrees with claim)
# Source 3: Reddit r/MachineLearning → "≈$0.0175" (ambiguous)
# Verdict: UNVERIFIED (conflicting official source vs secondary sources)
# Confidence: 0.65 — recommend checking official pricing page directly
```

## Quick Start

```bash
# KResearch (any LLM provider)
git clone https://github.com/KuekHaoYang/KResearch
cd KResearch && pip install -r requirements.txt
python main.py --query "Your research question"

# IterResearch (ICLR'26)
git clone https://github.com/Chen-GX/IterResearch
pip install iterresearch
iterresearch run --query "Research question" --max-turns 50
```

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [KResearch](https://github.com/KuekHaoYang/KResearch) | 336 | MIT | Autonomous, any LLM, inline citations |
| [IterResearch](https://github.com/Chen-GX/IterResearch) | 50 | Apache 2.0 | ICLR'26, 2048+ calls/40k context |
| [deep-researcher](https://github.com/jackswl/deep-researcher) | 103 | MIT | Google Scholar + OpenAlex + local LLM |
| [StepDeepResearch](https://github.com/stepfun-ai/StepDeepResearch) | 545 | Apache 2.0 | Hierarchical planning + evidence graph |

## Common Pitfalls

- **Single-source bias**: First Google result isn't authoritative. Always triangulate with ≥3 independent sources.
- **Citation hallucination**: LLMs generate plausible-looking but non-existent references. Every citation MUST be verified against the actual source.
- **Over-researching**: More turns ≠ better results. Set a quality threshold: "stop when all claims have ≥2 sources and no gaps remain."

---

## ✅ Verification Checklist (RUN BEFORE DELIVERING RESEARCH)

- [ ] Did I decompose the question into a task graph (not a linear search→summarize)?
- [ ] Does every factual claim in the report have an inline citation to a verified source?
- [ ] Did I detect and fill knowledge gaps (IterResearch pattern: search→gap→search deeper)?
- [ ] Did I triangulate key claims across ≥3 independent sources?
- [ ] Did I verify that all citations resolve to actual, accessible sources (no hallucinated refs)?
- [ ] Did I produce BibTeX/CSV output alongside the markdown report?

**If any box is unchecked, go back.**
