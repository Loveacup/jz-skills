# Cross-Project Evaluation Pattern · 跨项目评估模式

When evaluating an external project for absorption into existing skills, follow this decision tree BEFORE proposing changes.

## Decision Tree

```
External project identified?
├── Step 1: ARCHITECTURE FIT
│   Are the two systems solving the SAME class of problem with SIMILAR architecture?
│   ├── YES → continue to Step 2
│   └── NO → STOP. Different architectures = different optimization surfaces.
│       Example: AnySearch (single API engine) ≠ web-research-router (multi-engine router).
│       AnySearch's runtime.conf caching solves CLI startup overhead; our router's cost is cognitive, not computational.
│
├── Step 2: CAPABILITY MAPPING
│   For each feature, ask: "Does this fill a gap, or does this duplicate existing capability?"
│   ├── Fills gap → candidate for absorption
│   └── Duplicates → STOP. Redundancy adds complexity without value.
│
├── Step 3: ABSORPTION COST
│   What changes are needed to absorb this?
│   ├── SKILL.md change (lines added) → check <300 line budget
│   ├── New reference file (references/) → low cost, good candidate
│   └── New dependency (scripts/tools) → high cost, need strong justification
│
└── Step 4: PRESENT EVALUATION FIRST
    Present the fit/misfit analysis BEFORE proposing implementation.
    User can veto before you invest time in changes.
```

## Case Study: AnySearch → web-research-router (2026-05-27)

| AnySearch Feature | Fit? | Rationale |
|:---|:---|:---|
| runtime.conf caching | ❌ | Different bottleneck: CLI startup vs cognitive decision tree |
| batch search | ❌ | We already have parallel MCP tool calls |
| vertical domain mapping | ✅ | Pure reference knowledge, no architecture change |
| CLI platform detection | ❌ | We use MCP tools, not CLI scripts |
| API key auto-registration | ❌ | We use multiple free engines, not a single paid API |
| doc self-documenting command | ❌ | We already use references/ for progressive disclosure |

**Result:** Absorbed only vertical-domains.md (1 reference file, 0 SKILL.md changes). Rejected 5/6 features.

## Case Study: ECC → jz-skills (2026-05-27)

**Result:** ECC validates our path (SKILL.md + checklist + Red Flags) but doesn't challenge it. No absorption needed — our architecture (multi-profile governance) is intentionally narrower and deeper than ECC's broad marketplace approach.

## Case Study: taste-skill → jz-skills (2026-05-27)

| taste-skill Feature | Fit? | Absorbed as |
|:---|:---|:---|
| Adjustable tuning dials | ✅ | CROSS_CHECK_DEPTH parameter in web-research-router |
| Hard pre-flight check language | ✅ | CHECK: language + "must honestly pass" in all verification checklists |
| Anti-slop rule | ✅ | Added to grill-with-docs Red Flags |
| 8 frontend-specific variants | ❌ | Domain mismatch — we don't do frontend design |
