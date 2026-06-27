# Cross-Project Architecture Analysis Methodology

> How to systematically dissect an external AI agent skill/project and extract applicable patterns. Used in the AnySearch → WRR analysis (2026-06-07).

## Purpose

When evaluating an external project for WRR integration or design inspiration, use this structured approach to go beyond README-level understanding.

## Four-Stage Method

### 1. Surface Layer (10 min)

**Sources**: README, SKILL.md, repo description, official website, GitHub topics/stars.

**Questions to answer**:
- What does it do? One sentence.
- What's the architecture pattern? (thin client → hosted API? local engine? MCP server?)
- What are the headline features?
- What protocol does it speak? (JSON-RPC? MCP? REST?)

**Output**: 5-bullet summary + architecture diagram (ASCII).

### 2. Source Layer (30 min)

**Sources**: All CLI/script implementations, config files, constants/templates.

**Key checks**:
- Read EVERY runtime implementation (Python/Node/Bash/PS if multi-runtime). Don't assume they're consistent.
- Compare constants across implementations — multi-runtime projects often have drift.
- Trace the actual API call path end-to-end for one command.
- Check for hidden dependencies (env vars, config files, binary requirements).

**Red flags to spot**:
- Domain/feature lists differ between implementations
- Tool/command names differ between implementations
- Some implementations skip features others have
- Bash implementations using grep/sed for JSON parsing
- Hardcoded secrets or cookies in source

### 3. Pattern Extraction Layer (15 min)

**For each design decision, ask**: "Does WRR have this problem? Would this solution work for WRR?"

**Pattern catalog**:

| AnySearch Pattern | WRR Equivalent |
|-------------------|----------------|
| `runtime.conf` cache | Engine status cache (wrr-engine-status.json) |
| `doc` offline command | wrrdoc self-documenting |
| `constants.json` DRY | engine-registry.json |
| Multi-runtime CLI fallback | wrr-fallback.sh (curl-based) |
| Single JSON-RPC endpoint | MCP consolidation / CLI-fication |
| Progressive complexity (Python > Node > Bash) | Capability tiers (Full/Light/Bare) |

**For each pattern**: rate applicability (high/medium/low) + estimate implementation effort.

### 4. Anti-Pattern Extraction Layer (10 min)

**What NOT to do** — just as valuable as what TO do.

- AnySearch: 4 CLIs with 3 different domain lists → anti-pattern for WRR: enforce single source of truth
- AnySearch: Bash grep-based JSON extraction → anti-pattern for WRR: don't compromise robustness for availability
- AnySearch: Node.js hardcoded doc text instead of template → anti-pattern for WRR: always DRY

## Decision Output Format

For each analyzed project, produce:

```
## {Project} Analysis

### What it is / Architecture
{5-bullet summary}

### Patterns to Adopt (ranked by ROI)
1. {pattern} — {WRR application} — {effort: L/M/H}
2. ...

### Anti-Patterns to Avoid
1. {pattern} — {why bad} — {WRR guard}

### Integration Path (if applicable)
- As WRR auxiliary source: Yes/No/Maybe
- Pre-flight check: {command}
- Risk: {what breaks}
```

## User-Facing Output Delivery ★

**The full analysis is for you, not the user.** The user wants a concise takeaway they can react to and discuss — not an exhaustive report to scroll through. After completing all four stages internally, deliver to the user:

1. **One-paragraph summary** — what it is, how it works, 3–5 sentences max
2. **Key mechanisms enumerated** — numbered list, one sentence each
3. **Comparison to our approach** — a few bullet contrasts
4. **Open-ended question** — invite discussion on a specific direction (e.g. "要不要让 regent 自动判断该交给 CC？")

**Anti-pattern**: dumping all four stages verbatim into the chat. The user said "不要发那么长的东西，我看不懂我们讨论一下技术路线" — this is the signal. The detailed analysis exists for you to draw on during the discussion, not to paste wholesale.

## When NOT to Do This

- Skip if the project is clearly a toy (< 10 stars, no recent commits)
- Skip if it solves a problem WRR doesn't have
- Don't re-analyze projects already covered in CQI plan unless new version has major changes
