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

## Case Study: ECC → Jz-Plugin engineering shell (updated 2026-06-05)

**Context:** ECC is not just a skill checklist repository; it is a cross-harness operator system with manifests, component installation plans, validators, hook definitions, and adapters for multiple AI coding harnesses. For Jz-Plugin, the right comparison target is NOT memory-hub's truth-source kernel, but the engineering shell around it.

**Decision:** Absorb selectively at the P2/P6 engineering-shell layer. Do NOT absorb ECC as a new memory layer, judge layer, or agent-control-plane core.

| ECC Mechanism | Fit? | Jz-Plugin absorption rule |
|:---|:---|:---|
| Cross-harness adapters | ✅ | Use as pattern for `core/` + `adapters/{hermes,claude-code,codex}` separation. Core must not know target-platform paths. |
| `install-plan` / dry-run / apply / repair | ✅ | Add plan-first installer flow: discover → plan → apply → repair. Default to dry-run; apply only after user confirmation. |
| Component manifest | ✅ | Treat manifest as L1 writing discipline/index, not truth. It records component type, source, target harnesses, provenance, and whether it can touch L0. |
| Validators/test matrix | ✅ | High-value absorption: validate manifests, skill frontmatter, logs, hooks, cross-profile writes, and smoke install plans before deployment. |
| Hook organization | ⚠️ | Learn routing/cooldown patterns only. Jz hooks may emit events and trigger audits, but must not auto-resolve, auto-edit skill bodies, or become quality judges. |
| TUI/control plane/auto-dispatch | ⏸️ | Defer. Start with `jz doctor/status/plan/validate`; avoid new orchestration until the log/manual CQI loop is stable. |
| Marketplace-scale command/agent sprawl | ❌ | Reject. Jz should stay narrower and deeper; avoid importing dozens of agents/commands. |

**Rule of thumb:** ECC is useful as an engineering wrapper for Jz-Plugin (`manifest + validator + installer + adapter + repair`), not as a replacement for Jz's existing `append-only JSONL truth source + schema/provenance discipline + CQI judge separation` kernel.

**Recommended first deliverable:** an `ECC → Jz-Plugin 可迁移矩阵` reference or plan with four columns: ECC mechanism, Jz current state, absorb/reject/defer, minimal implementation path.

## Case Study: taste-skill → jz-skills (2026-05-27)

| taste-skill Feature | Fit? | Absorbed as |
|:---|:---|:---|
| Adjustable tuning dials | ✅ | CROSS_CHECK_DEPTH parameter in web-research-router |
| Hard pre-flight check language | ✅ | CHECK: language + "must honestly pass" in all verification checklists |
| Anti-slop rule | ✅ | Added to grill-with-docs Red Flags |
| 8 frontend-specific variants | ❌ | Domain mismatch — we don't do frontend design |
