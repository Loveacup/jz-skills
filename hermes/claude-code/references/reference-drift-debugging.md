# Reference Drift — When SKILL.md Says One Thing and References Say Another

> 2026-06-02 发现：WRR SKILL.md v3.9 已将 SearXNG 降兜底，但 references/research-modes.md 仍写 "SearXNG 默认起手"。

## The Problem

In progressive disclosure skill architectures (SKILL.md → references/ → sub-references/), the more specific files can lag behind the main SKILL.md. When an agent reads the skill, it encounters:

```
SKILL.md:       "SearXNG = 最后兜底"          (correct, v3.9)
research-modes.md: "Step 1: SearXNG 广扫"      (stale, aligned to v3.2)
vertical-domains.md: "News: SearXNG → Brave"  (stale)
fetch-extract-pattern.md: "默认: SearXNG URL Read" (stale)
```

The agent follows the more specific file → uses SearXNG → gets garbage → produces hallucinations.

## Detection

After any major SKILL.md update, grep ALL references for the deprecated pattern:

```bash
grep -r "SearXNG 起手\|SearXNG 广扫\|SearXNG.*默认" references/ \
  | grep -v "仅兜底\|降为\|已损坏\|备胎"
```

## Fix

1. Align ALL references to SKILL.md before deploying
2. Each reference must either: (a) use the new correct pattern, (b) explicitly note the deprecation, or (c) be neutral/agnostic about engine choice
3. After fixing, acceptance test: zero hits on the deprecated pattern (excluding correct "deprecated/fallback" contexts)

## Example from WRR v3.9 Alignment

12 files changed across 3 categories:
- **Engine routing**: research-modes.md (6 changes across 5 modes), vertical-domains.md (9 changes)
- **Extraction**: fetch-extract-pattern.md → Exa Fetch + Tavily Extract 主力
- **Residuals**: deep-research-loop.md, deep-loop-verification-pattern.md, SKILL.md pitfall #7
