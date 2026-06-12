# Adversarial Review Gate — Producer ≠ Reviewer Enforcement

## Problem

D16 architecture review identified: producer (Xiao Huang / Codex worker) and reviewer (Taizi / regent) both run `gpt-5.5`, share the same skill repository, and anchor on the same card payload. Memory-pool isolation prevents session-level context leakage but does NOT prevent systemic confirmation bias.

## Solution: Dual-layer enforcement

### Layer 1 — Adversarial prompt field (always-on, zero-cost)

Every review child card MUST include:

```json
{
  "metadata": {
    "review": {
      "adversarial_prompt": "Before approving, list 3 specific ways this diff/change could be wrong, incomplete, or silently harmful. Then explain why each is or isn't applicable."
    }
  }
}
```

The regent worker MUST:
1. Read and respond to `metadata.review.adversarial_prompt` before calling `kanban_complete`
2. Include the adversarial analysis in the completion summary
3. If the prompt is missing, `kanban_block(review-required: "adversarial_prompt field missing")`

This is a **mechanism-level** fix — it forces counterfactual reasoning regardless of model homogeneity.

### Layer 2 — Heterogeneous verification gate (for critical changes)

For cards that touch system-critical configuration, security boundaries, or lane infrastructure, add a non-optional heterogeneous gate:

```json
{
  "metadata": {
    "review": {
      "heterogeneous_gate": {
        "required": true,
        "reason": "touches system-critical configuration",
        "method": "moa | external-model",
        "model_hint": "claude-opus-4-8"
      }
    }
  }
}
```

Implementation options:
- **MoA (§3.2)**: use `delegate_task` with multiple model backends, require consensus
- **External-model**: spawn a second review card assigned to a profile with a different model, gate on both passing

### Card creation template

When creating a review child card:

```python
kanban_create(
    title="Review: <implementation card title>",
    assignee="regent",
    parents=[implementation_task_id],
    body="Review checklist per cc-lane-dual-substrate-template...",
    metadata={
        "review": {
            "adversarial_prompt": "List 3 ways this change could fail or be wrong, then explain why each is inapplicable or mitigated.",
            "heterogeneous_gate": {
                "required": False,  # set True for critical changes
            }
        }
    }
)
```
