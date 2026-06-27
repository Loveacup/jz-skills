# Agent Hallucination Patterns (2026-06-04)

## Pattern 1: Described-But-Not-Executed (PDF Rendering)

**Symptom**: Agent claims "PDFs generated at path X/Y.pdf" but files don't exist on disk. Agent described the expected output without running `render-pdfs.py`.

**Root cause**: Agent reads SKILL.md Mode A steps as descriptive, not imperative. When the prompt is "严格按 SKILL.md 执行", agent may interpret this as "summarize what SKILL.md says to do" rather than "execute each step with actual tool calls."

**Detection**: `ls -lh <workspace>/*.pdf` after agent claims delivery. Files absent = hallucination.

**Fix applied**: 
1. Added mechanical verification step: after `render-pdfs.py`, run `ls` to confirm files exist before claiming delivery
2. Noted tension between "skill-driven" (user preference) and "prompt-must-include-tool-calls" (pitfall advice) — this is a design tradeoff, not a bug

**Classification**: EXECUTION LAPSE (skill is correct, agent failed to follow). Per EmbodiSkill: preserve valid content, add emphasis markers.

## Pattern 2: Publisher Port Conflict (Mode B)

**Symptom**: `hermes kanban swarm --synthesizer publisher` crashes 54 times. Root cause: `platforms.api_server.extra.port` defaults to 8460, colliding with default profile's gateway. Each profile needs a unique port.

**Fix**: Set unique port in publisher's config.yaml:
```yaml
platforms:
  api_server:
    extra:
      port: 8461  # must differ from default (8460)
```

**Status**: Documented in SKILL.md Mode B section but fix not yet applied to publisher profile config.

## Design Tension: Skill-Driven vs Prompt-Driven Execution

The user's preference is "让 cron 调用 skill 而不是写死规则" — let skills drive execution, not hardcoded prompts. However, SKILL.md's own pitfalls warn: "Cron prompt 过于依赖 skill 引用 → Agent 不执行."

This session confirmed the tension is real: when the cron prompt was just "严格按 SKILL.md 执行", the agent described steps instead of executing them. But when the prompt had explicit tool-call instructions, it contradicted the "skill-driven" philosophy.

**Resolution path**: Mode B (Kanban Swarm) sidesteps the tension — each lane worker gets focused instructions from its profile config + shared skills, and the synthesizer handles rendering/delivery. Mode A (single-agent Cron) may need a hybrid: minimal prompt + skill, with mechanical verification after key steps.
