# Dual-Role Review Pattern Reference

## Overview

The dual-role review pattern is a two-pass cached audit inspired by oh-my-hermes's ralplan consensus model (Planner→Architect→Critic), adapted for skill quality review. Unlike single-agent persona-switching (which causes modal confusion), this pattern runs TWO SEQUENTIAL PASSES with prompt caching: Pass 1 (Advocate) establishes the baseline case, Pass 2 (Challenger) adversarially tests it WITH Pass 1 cached, then a synthesis phase reconciles findings.

Why two passes? Single-agent reviews suffer from confirmation bias and miss edge cases. The Advocate pass finds strengths and validates compliance assumptions. The Challenger pass stress-tests those assumptions with adversarial lens (deployment failures, anti-patterns, silent bypasses). Caching Pass 1 gives the Challenger full context without redundant reads.

Why cached? In skill audits (Step 3 progressive disclosure, Step 9 deployment audit), the skill file and references are often 500-2000 tokens. Reading twice without caching burns tokens and time. With caching, Pass 2 references Pass 1 findings at near-zero marginal cost, enabling deeper scrutiny.

When NOT to use: Simple one-off tasks, skills under 50 lines, already-deployed-and-validated skills (compliance score ≥4 on all dimensions), or triage-level quick scans. Use single-pass review for these cases.

This pattern draws from oh-my-hermes's ralplan consensus model (Planner→Architect→Critic) but simplifies it for skill review contexts. Unlike persona-switching approaches that risk modal confusion, this implements **two sequential passes with prompt caching** — Pass 2 reads Pass 1's output from cache, ensuring consistency while enabling adversarial review.

## Pattern Structure

### Pass 1: Advocate Review

**Role**: Validate strengths, confirm compliance, assume good intent.

**Prompt Template**:

```
You are the Advocate reviewer. Your role is to find strengths, validate compliance, and assume good intent.

OBJECTIVE: Audit this skill for compliance and quality, focusing on what works well and where the author made sound decisions.

CONTEXT:
- Skill file: [path]
- Audit type: [Progressive Disclosure Audit / Deployment Audit / Hygiene Triage]
- Compliance target: ≥4 on all 7 dimensions (progressive disclosure, anti-rationalization, rule positioning, description quality, verification, runtime invocation, deployment)

YOUR LENS (Advocate):
1. Assume the author had good reasons for design choices
2. Identify strengths: what compliance mechanisms are already working?
3. Validate structure: does progressive disclosure work as intended?
4. Check positioning: are Red Flags, decision tree, and checklist in the right places?
5. Note defensible tradeoffs: where did the author choose A over B for valid reasons?

OUTPUT FORMAT:
## Advocate Review: [skill-name]

### Strengths
- [Compliance dimension 1]: [what's working well, cite line numbers]
- [Compliance dimension 2]: ...

### Validated Assumptions
- [Assumption 1]: [why it's defensible, evidence]
- [Assumption 2]: ...

### Compliance Snapshot (1-5 scale)
| Dimension | Score | Evidence |
|-----------|:-----:|----------|
| Progressive disclosure | X | [reason] |
| Anti-rationalization | X | [reason] |
| Rule positioning | X | [reason] |
| Description quality | X | [reason] |
| Verification | X | [reason] |
| Runtime invocation | X | [reason] |
| Deployment | X | [reason] |

### Edge Cases to Test
[List 3-5 scenarios the Challenger should stress-test: deployment failures, attention window violations, silent bypasses, anti-pattern risks]

CONSTRAINTS:
- NO destructive criticism in this pass — save that for Challenger
- If something looks wrong, frame it as "edge case to test" not "defect"
- Cite line numbers for all claims
- Complete this review in ≤8 minutes
```

**Output**: Structured findings highlighting what works well, compliance validations, and assumptions that underpin the design.

---

### Pass 2: Challenger Review

**Role**: Adversarially test assumptions, find edge cases, stress test design.

**Prompt Template** (references Pass 1 via cache):

```
You are the Challenger reviewer. Your role is to adversarially test the Advocate's findings and find what breaks.

CONTEXT:
- Skill file: [path] (CACHED from Pass 1)
- Advocate review: [see above, CACHED]
- Your task: Stress-test the Advocate's validated assumptions and edge cases

YOUR LENS (Challenger):
1. Assume the agent will rationalize skipping this skill — does the Red Flags table actually prevent it?
2. Assume critical rules are outside the attention window — does positioning actually work?
3. Simulate deployment failures: what happens if this skill is loaded in a governance chain (multi-profile chain and silently bypassed?
4. Check anti-patterns: does this skill exhibit any catalog failures (see references/anti-rationalization-catalog.md)?
5. Adversarially test compliance scores: if Advocate gave a 4, can you find evidence for a 3?

FOCUS ON ADVOCATE'S EDGE CASES:
[List edge cases from Pass 1]

OUTPUT FORMAT:
## Challenger Review: [skill-name]

### Contested Assumptions
For each Advocate assumption, either AFFIRM (with new evidence) or CONTEST (with failure scenario):

- [Assumption 1]: **AFFIRM** / **CONTEST**
  - Evidence: [deployment scenario / line number / anti-pattern match]
  - Risk if wrong: [what breaks]

### Failure Scenarios Found
[Simulate 3-5 concrete deployment failures: silent bypass, attention window violation, rationalization escape, multi-profile sync failure]

Example:
- **Scenario**: Agent loads this skill in 工部 (executor) profile
- **Failure mode**: Red Flags table at line 45 is outside attention window if the agent is mid-task
- **Evidence**: skill-authoring v3.0 §Critical Rule Positioning requires Red Flags in top 10%
- **Classification**: SKILL DEFECT (SkillEvolver taxonomy)

### Revised Compliance Scores
Only revise scores where you found concrete evidence of lower compliance:

| Dimension | Advocate Score | Challenger Score | Justification |
|-----------|:--------------:|:----------------:|---------------|
| [dimension] | X | Y | [failure scenario / line evidence] |

### Showstoppers
[Critical defects that block deployment — must fix before Step 11]

### Acknowledged Strengths
[What the Advocate got right — don't challenge for the sake of challenging]

CONSTRAINTS:
- NO vague complaints — every criticism must cite line numbers or deployment scenarios
- If you can't find concrete evidence, AFFIRM the Advocate's score
- Use SkillEvolver failure taxonomy: DISCOVERY / OPTIMIZATION / SKILL DEFECT / EXECUTION LAPSE
- Complete this review in ≤10 minutes
```

**Output**: Counter-findings, edge cases, broken assumptions, deployment risks.

---

### Synthesis

## Synthesis: Reconciling Advocate + Challenger

After both passes, the reviewing agent (or skill author) synthesizes findings into actionable revisions.

SYNTHESIS DECISION TREE:

```
For each compliance dimension:
├── Advocate + Challenger AGREE (scores within ±1)?
│   └── Accept consensus score, note supporting evidence from both
├── Advocate + Challenger DISAGREE (scores differ by ≥2)?
│   ├── Does Challenger cite concrete failure scenario?
│   │   YES → Accept Challenger score, add to Priority Fixes
│   │   NO  → Lean toward Advocate, but note the contested assumption
│   └── Is this a showstopper (score <3 on critical dimension)?
│       YES → BLOCK deployment, mandatory fix
│       NO  → Add to revision backlog
└── Advocate flagged "edge case to test" + Challenger AFFIRMED?
    └── Non-blocking, document in references/known-limitations.md
```

OUTPUT FORMAT:

### Final Compliance Scorecard
| Dimension | Consensus | Advocate | Challenger | Deciding Factor |
|-----------|:---------:|:--------:|:----------:|-----------------|
| Progressive disclosure | X | X | X | [reason] |
| ... | ... | ... | ... | ... |

### Priority Fixes (P0 — must fix before deployment)
1. [Showstopper 1]: [specific change required, target line/section]
2. ...

### Revision Backlog (P1 — fix in next iteration)
1. [Non-blocking issue 1]: [recommendation]
2. ...

### Validated Strengths (no changes needed)
- [Strength 1]: [Advocate + Challenger both affirmed]
- ...

### Escalation Criteria
If synthesis cannot resolve a disagreement:
- **Deadlock**: Advocate score 4, Challenger score 2, no concrete failure scenario → Deploy to TEST AGENT (Step 9 deployment-grounded audit) and collect real signals
- **Challenger over-indexed**: If Challenger contests >5 assumptions without citing failure scenarios → Rerun Challenger pass with stricter evidence requirement
- **Advocate under-indexed**: If Advocate gave all 5s but Challenger found 3+ showstoppers → Author had blind spots, trust Challenger

WHEN SYNTHESIS FAILS:
- Trigger Step 9 (Deployment-Grounded Audit) immediately — real deployment signals break ties
- Log the contested dimension in references/compliance-research.md as a scoring calibration case

**Decision Framework**:
- If Advocate and Challenger agree → proceed
- If Challenger finds P0 issues → block and fix
- If they disagree on interpretation → escalate to human judgment
- If Challenger finds only minor issues → document and proceed

## When to Use

- Skill audit after Step 3 (Progressive Disclosure Audit) when SKILL.md is 150-300 lines and has 3+ references files
- Step 9 Deployment Audit when a skill is being deployed to a new agent/profile and compliance must be verified
- Skill hygiene triage when scanning 50+ skills for consolidation, deprecation, or overlap — Advocate finds salvageable content, Challenger finds redundancy
- Post-absorption review (e.g., after absorbing external repo into existing skill) to validate that the integration didn't break compliance
- Multi-profile governance audits (multi-profile where silent bypass risk is high — Challenger simulates cross-profile failure modes
- When a skill has been revised ≥3 times and author suspects rationalization drift — Challenger catches self-review blind spots
- Before creating a references/consolidation-case-study.md for a major skill merge — dual-role review validates the consolidation improved compliance

## When NOT to Use

- Simple skills under 50 lines with no references/ directory — single-pass review is sufficient
- Already-validated skills with compliance scores ≥4.5 on all dimensions and deployment signals from ≥2 agents — no re-audit needed unless materially revised
- Quick triage scans (e.g., scanning 127 skills for obvious deprecation candidates) — use lightweight single-pass filter first, then dual-role for shortlisted skills
- One-off documentation tasks or ad-hoc scripts that will not be reused — these don't need skill-level compliance
- Emergency hotfixes (e.g., fixing a syntax error in a deployed skill) — just patch and deploy, defer full audit to next revision cycle
- First-time skill authors learning the basics — load Anthropic skill-creator first, apply dual-role review after initial draft is complete
- Skills explicitly marked as experimental/alpha (version <1.0.0) and not yet deployed to production profiles

## Failure Modes

### Advocate/Challenger Deadlock

**Symptom**: Advocate scores 4-5 on a dimension, Challenger scores 2-3, but Challenger's evidence is vague or hypothetical (no concrete failure scenario or line citation)

**Resolution**: Synthesis MUST require concrete evidence from Challenger. If Challenger cannot cite deployment failure or anti-pattern match, default to Advocate score but FLAG for Step 9 deployment-grounded audit. Log contested dimension in references/compliance-research.md for calibration.

### Challenger Dominates (Over-Indexing)

**Symptom**: Challenger contests >60% of Advocate assumptions and downgrades ≥5 scores, but most criticisms are theoretical edge cases without deployment evidence

**Resolution**: Rerun Challenger pass with stricter prompt: 'Only contest assumptions if you can cite (1) SkillEvolver failure taxonomy match, (2) line number violating positioning rules, or (3) simulated governance failure.' If still over-contesting, escalate to deployment test — real agent behavior breaks ties.

### Advocate Dominates (Under-Indexing)

**Symptom**: Advocate gives all 4s or 5s, Challenger finds ≥3 showstoppers (Red Flags missing, rules outside attention window, no verification checklist), but synthesis defaults to Advocate because 'no deployment evidence yet'

**Resolution**: Showstoppers are BLOCKING regardless of deployment evidence — these are structural compliance violations per skill-authoring §Steps 4-6. Synthesis must trust Challenger on showstoppers. If in doubt, check skill-authoring references/anti-rationalization-catalog.md for pattern match.

### Attention Window Fatigue

**Symptom**: Challenger pass takes >12 minutes or produces incomplete review (misses obvious issues Advocate flagged as edge cases)

**Resolution**: Skill file + references may exceed Challenger's effective context window. SOLUTION: Split Challenger pass into 2 sub-passes: (2a) Review SKILL.md only, (2b) Review references/ only. Cache both. Common in skills with >5 references files.

### Rationalization Creep in Synthesis

**Symptom**: Synthesis resolves every disagreement in favor of Advocate because 'the author had good reasons' — effectively ignoring Challenger findings

**Resolution**: Synthesis agent is falling into the same trap the skill's Red Flags are meant to prevent. FIX: Reframe synthesis prompt to weight Challenger findings HIGHER when they cite compliance violations (§Steps 4-6) or SkillEvolver failure taxonomy. Advocate finds strengths, Challenger finds risks — risks must be addressed before deployment.

### Cache Miss / Redundant Reads

**Symptom**: Pass 2 re-reads the entire skill file instead of referencing cached Pass 1 output, doubling token cost and time

**Resolution**: Ensure Pass 2 prompt explicitly references 'Pass 1 Advocate Review (CACHED)' and does NOT include a redundant Read tool call for the skill file. If using Claude Code agents, verify prompt caching is enabled in model config. If cache keeps missing, check that Pass 1 output is ≥1024 tokens (caching threshold).


## Implementation Notes

- **Caching**: Pass 2 MUST run immediately after Pass 1 (within cache TTL) to ensure it reads cached Pass 1 output
- **Independence**: Do not allow Pass 1 to see "what Challenger will ask" — this defeats adversarial testing
- **Escalation**: Human review is the tiebreaker, not a third agent role
- **Metrics**: Track Pass 1/Pass 2 disagreement rate — high rate indicates unclear requirements

## Reference Integration

This pattern is referenced by:
- skill-authoring v3.0 Step 3 (Progressive Disclosure Audit)
- skill-authoring v3.0 Step 9 (Deployment Audit)
- skill-hygiene triage workflow

For implementation examples, see the skill-authoring SKILL.md execution sections.

---

*Style conventions from existing references*:
- Triple-backtick code blocks for decision trees, examples, schemas — never indented code
- Bold for critical terms first mention — **Deployment-grounded refinement**, **Silent-bypass**
- Inline code for file paths (`references/modes.md`), commands (`cp -r`), variable names (`$base`)
- H2 for major sections, H3 for subsections within case studies
- Blockquotes for key paper quotes (>) — exactly as written, no paraphrasing
- Emoji + text for section headers (🚨 Red Flags, ✅ Checklist, 🔀 Decision Tree)
- Checkbox lists for checklists — [ ] not - [ ]
- Horizontal rules (---) to separate major sections
- Table alignment: left for text, center for yes/no (✅/❌), right rarely
- arXiv citations in parentheses — (arXiv:2605.10500), not footnotes
- Example blocks labeled with <example> tags when showing literal HEREDOC syntax
- File references as relative paths in tables, absolute paths in inline prose
- Version numbers in headers — v3.0, v2.0, not 'version 3'
- Date format: ISO (2026-05-27) in case studies, natural (2026-05) in summaries
