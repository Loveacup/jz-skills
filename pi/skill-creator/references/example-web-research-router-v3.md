# Case Study: web-research-router v2.4 → v3.0

A real compliance-first restructure. Loaded on-demand.

## Before (v2.4)

```
web-research-router/SKILL.md
├── 500+ lines
├── YAML frontmatter
├── Overview / search stack
├── When to Use / When Not
├── Research Modes (detailed, ~80 lines)
├── Routing Decision Tree (starts at line 160, ~100 lines)
├── Query Patterns (detailed, ~80 lines)
├── Academic Lane Policy (detailed, ~100 lines)
├── Output Contract / Source Map Schema
├── Deployment & Sync
└── Common Pitfalls (13 items)
```

**Problem:** Agent loaded skill → decision tree at line 160 was outside attention window → defaulted to `web_search` (muscle memory) instead of following router.

## Root Cause Research

- **AAAI 2026:** LLMs have "strong inherent biases toward certain constraint types" — instructions outside attention window are effectively invisible
- **Compliance Gap paper:** Models default to high-reward shortcuts (web_search is fast) over procedural fidelity (router decision tree)
- **O'Reilly:** Capability trees > flat lists; progressive disclosure prevents cognitive overload
- **Addy Osmani:** Anti-rationalization tables preempt agent excuses

## After (v3.0)

```
web-research-router/
├── SKILL.md (146 lines)
│   ├── YAML frontmatter
│   ├── 🚨 Red Flags: DO NOT SKIP THIS ROUTER (5 excuses + rebuttals)
│   ├── 🔀 Routing Decision Tree (4 steps, starts at line ~20)
│   ├── 🧭 Quick Engine Reference table
│   ├── 📋 Output Contract (short)
│   ├── 📦 Reference File Map
│   ├── ⚠️ Common Pitfalls (top 5)
│   ├── ✅ Verification Checklist (7 items)
│   └── Deployment & Sync
└── references/
    ├── research-modes.md (detailed mode instructions)
    ├── query-patterns.md (query examples)
    ├── academic-lane.md (full academic policy)
    ├── common-pitfalls.md (full 13 items)
    ├── tool-names.md (MCP tool names)
    └── source-map-schema.md (JSON schema)
```

## Key Changes

| Change | Why | Impact |
|--------|-----|--------|
| 500 → 146 lines | Reduces cognitive overload | Agent reads entire file, not just top/bottom |
| Red Flags table at top 10% | Preempts "use web_search" muscle memory | Agent sees counter-arguments before acting |
| Decision tree at top 15% | Puts critical rules in attention window | Routing logic processed before tool selection |
| Detailed modes → references/ | Progressive disclosure keeps body lean | Deeper content available on demand, not noise |
| Verification checklist at bottom | Forces self-audit before returning | 7-item check prevents mode/engine mismatches |
| Deployment & Sync embedded | Self-documenting sync | 15 profiles synced without manual commands |

## Lessons Learned

1. **Loading ≠ Following.** Skill loaded into context does not mean the decision tree was processed. Position matters.
2. **Anti-rationalization works.** Explicitly naming the excuses the agent will make (and rebutting them) interrupts the default behavior.
3. **Progressive disclosure is not optional.** 500+ lines as a single blob means the middle 60% is effectively dead content.
4. **Verification checklists close the loop.** Without explicit self-check, the agent has no trigger to verify it followed the routing rules.
5. **Deployment rules in the skill itself.** No external memory needed — the skill knows how to sync itself.
