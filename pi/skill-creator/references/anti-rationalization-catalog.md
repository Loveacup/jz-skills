# Anti-Rationalization Catalog

Common excuses agents use to skip skills, organized by skill type. Use these as templates when building Red Flags tables.

Loaded on-demand from `skill-authoring/SKILL.md`.

## Search / Research Router Skills

| Excuse | Rebuttal |
|--------|----------|
| "This is a simple query, I'll just use web_search" | web_search is a generic fallback. The router picks the best engine per query type. Even simple factual queries benefit from Tavily (grounding) or Brave (coverage). |
| "I already know the answer" | Training data is stale. Current facts need current search. |
| "I already loaded the skill, that's enough" | Loading ≠ following. Loading tells you WHAT to do; you still need to DO it. |
| "The decision tree is too complicated for this" | It's 4 branches. Takes 5 seconds. |
| "I'll cross-check later" | Cross-checking after the fact is twice the work. Do it in the right order now. |
| "Let me just try a quick search first" | First-search-then-router defeats the purpose. Route first, then search. |

## Code Review Skills

| Excuse | Rebuttal |
|--------|----------|
| "The diff is small, no need" | Small diffs cause the most insidious bugs — no one looks at them carefully. |
| "I already read it while writing" | Reading your own code ≠ reviewing your own code. Confirmation bias is real. |
| "Tests pass so it's fine" | Tests pass for wrong reasons all the time. Review catches that. |
| "This is urgent, I'll review after merging" | Post-merge reviews rarely happen. Review gate is there for a reason. |

## Deployment Skills

| Excuse | Rebuttal |
|--------|----------|
| "Config hasn't changed since last deploy" | Environment state drifts. What worked yesterday may not work today. |
| "This is a minor update, skip the full checklist" | "Minor" is how major incidents happen. The checklist is the same for a reason. |
| "Let me just deploy and verify after" | Post-deploy verification is reactive. Pre-deploy checks prevent incidents. |
| "The last 10 deploys went fine" | Past success ≠ future safety. Each deploy is a new roll of the dice. |

## Data Processing / ETL Skills

| Excuse | Rebuttal |
|--------|----------|
| "I'll validate output later" | Validation deferred is validation skipped. Check now. |
| "The source format looks standard" | "Looks standard" is the #1 cause of silent data corruption. |
| "I can eyeball a few rows" | Eyeballing doesn't catch edge cases, encoding issues, or null patterns. |

## Content Generation Skills

| Excuse | Rebuttal |
|--------|----------|
| "I'll add citations after drafting" | Citations are harder to add retroactively. Capture sources during research. |
| "This output looks fine" | "Looks fine" is not verification. Check against the output contract. |
| "The user can fix formatting themselves" | The skill's job is to produce ready-to-use output. Formatting IS the deliverable. |

## Generic / Multi-Purpose Skills

| Excuse | Rebuttal |
|--------|----------|
| "I don't need to read the full skill" | If you skip sections, you miss edge cases. The skill exists because general knowledge isn't enough. |
| "I've used this skill before, I know it" | Skills get updated. Your memory of it may be stale. Re-read the Red Flags at minimum. |
| "This is an edge case, the skill probably doesn't cover it" | That's when you MOST need the skill. Edge cases are exactly what skills document. |
