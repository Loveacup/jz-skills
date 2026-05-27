# Skill Evolution Research Notes (2026-05)

Condensed from SkillEvolver (arXiv:2605.10500) and EmbodiSkill (arXiv:2605.10332), both published 2026-05-11.

## SkillEvolver: Skill Learning as a Meta-Skill

**Authors:** Genrui Zhang, Erle Zhu, Jinfeng Zhou, Caiyan Jia, Hongning Wang (Tsinghua + Beijing Jiaotong)
**Code:** https://github.com/Skill-Evolve/meta-skill

**Core claim:** A single meta-skill can iteratively author, deploy, and refine domain skills — targeting skill prose + code, not model weights.

### Key mechanisms

1. **Deployment-grounded refinement.** Learning signal comes from failures of ANOTHER agent using the skill, not self-reflection. Candidates are deployed to fresh "Domain-Skill Agents" and the meta-skill observes their failures.

2. **Strategy-diversified exploration.** K=4 distinct high-level strategies per iteration (different libraries, algorithm families), not token-level variations.

3. **Independent Auditor.** Catches: (a) overfit — skill works on training tasks but fails generalization; (b) leakage — skill exploits task-specific shortcuts; (c) **silent-bypass** — skill appears valid in content but is never invoked at runtime.

4. **Meta-skill as just another skill.** Loaded through the same interface by any protocol-compliant CLI-agent (Claude Code, Codex, etc.).

### Results
- SkillsBench (83 tasks, 15+ domains): 56.8% vs 43.6% (curated human) vs 29.9% (no-skill)
- KernelBench (GPU kernel optimization): mean speedup 1.16→1.51x

### Key quotes

> "The meta-skill refines only after deploying the learnt skill, such that the learning signal comes from failures another agent encounters while using it – not from exploratory traces alone."

> "Silent-bypass mode in which a skill appears valid in content but is never invoked at runtime."

---

## EmbodiSkill: Skill-Aware Reflection for Self-Evolving Embodied Agents

**Authors:** Ruofei Ju (NJU), Xinrui Wang (HUST), et al. — NJU + HUST + USTC + MSR + AIR Tsinghua

**Core claim:** In embodied environments, task failure ≠ skill failure. Must distinguish skill defects from execution lapses.

### Key mechanisms

1. **Four-type failure classification:**
   - 🔍 DISCOVERY: skill missing content → add to body
   - ⚡ OPTIMIZATION: valid but suboptimal → revise specific rule
   - 🐛 SKILL DEFECT: wrong/incomplete/underspecified → correct implicated rule
   - 🏃 EXECUTION LAPSE: skill is correct but agent didn't follow → do NOT change body, add to appendix

2. **Skill Appendix (S_app).** Separate from skill body (S_body). Execution-lapse evidence goes into appendix as emphasis markers, preserving valid skill content. Appendix does not introduce new rules — only highlights existing content.

3. **Targeted revision.** Only change skill content IMPLICATED by evidence. Skill content not referenced by any reflection → left untouched.

4. **Accumulate then revise.** Collect B reflections (typ. B=3-5) before consolidating. Consolidation merges overlapping signals, removes redundant ones, resolves conflicts.

5. **Skill-Aware Evolution Spiral.** Closed loop: skill → task execution → trajectory → reflection → revised skill → ... Each evolution step produces skill S^(n+1) = (S_body^(n+1), S_app^(n+1)).

### Results
- ALFWorld: frozen Qwen3.5-27B executor → 93.28% success, +31.58% over GPT-5.2 direct, +25.01% over G-Memory
- Ablation: skill-aware reflection → +19.04% relative improvement over skill-unaware variant
- EmbodiedBench-Habitat: 52.33% (best), EmbodiedBench-Navigation: 61.33% (best)

### Key quotes

> "A failed task execution may reflect not only incorrect skill content, but also an execution lapse in which the agent fails to follow valid guidance."

> "Skill-aware reflection uses the trajectory to examine the current skill and determine which skill content should be added, optimized, corrected, or preserved."

---

## Cross-paper synthesis

| Principle | SkillEvolver | EmbodiSkill |
|:---|:---|:---|
| Deployment > self-review | ✅ Fresh agent as signal source | ✅ Trajectory-grounded evidence |
| Failure ≠ skill bug | — | ✅ Execution Lapse classification |
| Targeted > whole-skill revision | — | ✅ Only implicated content changed |
| Accumulate before revising | — | ✅ B=3-5 reflection buffer |
| Independent audit | ✅ Fresh-agent overfit audit | — |
| Silent-bypass detection | ✅ Key innovation | — |
| Skill appendix | — | ✅ S_app separation |

### Implication for skill-authoring v3.0

Both papers independently converge on the same insight: **static, self-reviewed skills are unreliable. Skills must evolve from deployment-grounded signals, with failure classification separating skill defects from execution lapses.** v3.0 adopted: deployment-grounded audit (Step 9), 4-type failure classification (Step 9a), targeted revision with accumulation (Step 10), silent-bypass detection (7th scoring dimension).
