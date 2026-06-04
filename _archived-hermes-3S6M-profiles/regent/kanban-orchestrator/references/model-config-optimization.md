# Model Configuration Optimization — Full-Cycle Workflow

> Session reference: 2026-05-18, v0.4 model config optimization.
> Related: regent-3s6m.md, the model config table.

## When to run this

When any of:
- A new model generation ships (DeepSeek V5, Kimi K3, etc.)
- Current models show auth/exhaustion issues
- The Emperor asks to "check all agent model configs"
- A new provider becomes available in the credential pool

## Step-by-step workflow

### Phase 1: Audit current state
1. Read all profile configs (`~/.hermes/profiles/*/config.yaml`)
2. Check credential pool health (`hermes auth list` or read `auth.json`)
3. Verify provider aliases (e.g., `moonshot` → `kimi-coding` in `auth.py` PROVIDER_ALIASES)
4. Check main config `providers:` section for missing entries

### Phase 2: Market research (parallel web search)
Search for model benchmarks, pricing, capabilities:
- `web_search` for each model family (DeepSeek, Kimi, MiniMax, GPT)
- Key sources: deepseekai.guide, artificialanalysis.ai, tokencost.app, platform docs
- Extract: params, context window, SWE-bench, pricing, hallucination rate, speed

### Phase 3: Match models to roles
Map each ministry's responsibilities to model capabilities:

| Ministry | Needs | Key metric |
|----------|-------|------------|
| planner | Reasoning, planning, speed | AA Intelligence Index, token speed |
| reviewer | Judgment, reliability | agentic coding benchmarks |
| engineer | Coding, tool calling | SWE-bench Verified |
| auditor | Long-context, fact-checking | context window, GDPval-AA |
| archivist | Lightweight file I/O | cheapest capable model |

### Phase 4: Apply constraints
- **Budget model**: subscription users don't care about per-token pricing (except DeepSeek which is cheap anyway)
- **Simplicity**: prefer fewer providers/models — 2 providers + 3 model tiers is ideal
- **Existing auth**: only recommend models whose provider credentials are healthy

### Phase 5: Execute config changes
- Modify each profile's `config.yaml`
- Standardize model naming (e.g., `kimi2.6` → `kimi-k2.6`)
- Verify with `hermes profile list` or direct YAML reading

### Phase 6: 三省六部 governance
For the actual config modification task itself, use the governance system:
- **T1 (planner)**: synthesize research into recommendations
- **T2 (reviewer)**: review and approve/reject
- **T3 (archivist)**: archive final config into knowledge base

Do NOT bypass governance even for seemingly simple config edits — the Emperor invested in the system; use it.

## Anti-patterns

- **Trusting the first research result**: the planner claimed DeepSeek V4-Pro had "幻觉率仅4%" when actual data showed 94%. Always cross-reference benchmark data.
- **Reviewer rubber-stamping**: the reviewer approved without catching the auth error. Reviewers need explicit fact-checking instructions.
- **Regent doing the research themselves**: the Emperor corrected this twice. Even research synthesis tasks should go through planner → reviewer.
