---

name: source-verification
description: "Use when fact-checking claims, verifying numbers/dates/names/quotes/sources, checking whether a reference supports a statement, or producing claim-level evidence notes."
type: routine
version: 1.0.0
author: Hermes Agent, adapted from Yuan1z0825/nature-skills for general content workflows
license: see references/upstream.md
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [fact-check, verification, claims, sources]
    related_skills: [content-source-workflow]

---

# Source Verification

## Overview

Verify claims against sources. This generalizes the citation-verification discipline into everyday content work: articles, investment notes, reports, social posts, product claims, biographies, and occasional academic citations.

## Hard Rules

- Do not invent facts, references, quotes, dates, numbers, URLs, DOI/PMID/arXiv IDs.
- A claim is not verified just because it sounds plausible.
- Mark support strength clearly:
  - verified;
  - likely but indirect;
  - partially supported;
  - contradicted;
  - not found / insufficient evidence.
- Prefer primary sources for high-stakes claims.

## Workflow

1. Split text into atomic claims.
2. Prioritize high-risk claims: numbers, dates, named entities, causality, medical/financial/legal claims, privacy/security claims, pricing/limits, and claims about local-only or end-to-end-encrypted processing.
3. Find sources via `content-source-workflow` Step 1 or available web tools.
4. Map each claim to evidence and source quality.
5. Return corrections and safe wording.

## Output Template

For each checked claim:

```text
Claim: ...
Status: verified / partial / contradicted / not found
Evidence: ...
Source: ...
Suggested wording: ...
```

## Verification Checklist

- [ ] High-risk claims prioritized.
- [ ] Evidence linked or quoted.
- [ ] Support strength labeled.
- [ ] Unsafe/unsupported wording corrected.
- [ ] For browser/agent tools, Chrome extensions, MCP servers, or scraping gateways, apply `references/browser-agent-tool-assessment.md` before giving a trust/use recommendation.
- [ ] For AI model/provider comparisons, apply `references/ai-model-comparison.md`: verify exact variants, benchmark conditions, context/output limits, cache pricing, and blended costs before recommending routing.
