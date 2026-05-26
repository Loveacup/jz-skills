# Compliance Research: Why Skills Aren't Followed

Academic research supporting compliance-first skill design. Loaded on-demand.

## Key Papers

### 1. "Control Illusion: The Failure of Instruction Hierarchies in Large Language Models"
*AAAI Conference on Artificial Intelligence, 2026*
- **Finding:** system/user prompt separation fails to establish reliable instruction hierarchy
- **Finding:** models exhibit "strong inherent biases toward certain constraint types regardless of priority designation"
- **Finding:** "societal hierarchy framings (authority, expertise, consensus) show stronger influence on model behavior than system/user roles"
- **Implication for skills:** You cannot rely on "this is in a skill so it will be followed." The model defaults to efficient/simple paths regardless of where instructions live.

### 2. "The Compliance Gap: Why AI Systems Promise to Follow Process Instructions but Don't"
*arXiv 2605.01771, 2026*
- **Finding:** Compliance gap is a "structural inevitability" — reward signals + instruction hierarchy + tool affordances create a cascade where models choose shortcuts over procedure
- **Finding:** "When a delegation tool is available, the model has a low-cost shortcut to the high-text-quality output the reward selects for"
- **Finding:** Removing tool affordances closes the gap, but in deployment the affordance IS the point
- **Implication for skills:** Adding "MUST" doesn't solve compliance. You need anti-rationalization (preempt the shortcut reasoning) + structural positioning (put rules where attention lands).

### 3. "GraSP: Graph-Structured Skill Compositions for LLM Agents"
*arXiv 2604.17870, 2026*
- **Finding:** "Cognitive overload" — dumping all skills into prompt burns context without providing an actionable execution path
- **Finding:** Flat execution loses causal structure — a failure at step K in N skills forces O(N) replanning
- **Implication for skills:** Progressive disclosure isn't just about token efficiency — it's about cognitive processing. The agent needs a clear decision tree, not a reference manual.

## Industry Best Practices

### Perplexity: "Designing, Refining, and Maintaining Agent Skills"
- **Key insight:** "The description is the hard part. 'Load when...' (every word costs attention)"
- **Key insight:** "Gotchas are extremely high-value content. Start thin, grow as the agent fails."
- **Key insight:** Write evals BEFORE the skill. Include negative examples and forbidden loads.

### O'Reilly: "Agent Skills Work but the Research Shows Most Teams Are Building Them Wrong"
- **Key insight:** Capability trees > flat lists. Organize skills hierarchically.
- **Key insight:** Skills need lifecycle management — creation is easy, maintenance and retirement are where value lives.

### Addy Osmani: agent-skills
- **Key insight:** "Process, not prose." Skills are workflows agents follow, not reference docs.
- **Key insight:** "Anti-rationalization" — every skill includes a table of common excuses agents use to skip steps with documented counter-arguments.
- **Key insight:** "Verification is non-negotiable." Every skill ends with evidence requirements.

## Our v3.0 Validation

The web-research-router v3.0 restructure validated these findings in practice:

| Finding | v3.0 Implementation | Result |
|---------|-------------------|--------|
| Cognitive overload from 500+ line skills | Compressed to 146 lines + 6 references/ | Decision tree now in attention window |
| Anti-rationalization needed | Added 🚨 Red Flags table (5 excuses + rebuttals) | Agent sees warnings before acting |
| Rule positioning matters | Decision tree moved to top 15% (from line 160) | Critical rules read first |
| Verification checklists improve compliance | Added 7-item self-check at bottom | Agent self-audits before returning |
