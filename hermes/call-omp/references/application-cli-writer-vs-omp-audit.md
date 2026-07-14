# Application CLI Writer vs OMP Audit

## Durable distinction

An application option named `writer-provider=cli` does not identify the underlying agent. Inspect the provider factory before choosing a tool workflow. It may resolve to OMP, Codex, Claude Code, or a custom command.

## Correct sequence

1. Read the provider factory and its default command/environment override.
2. Load the skill for the actual underlying CLI.
3. Run the application’s real-sample gate.
4. Treat generated prose as a candidate artifact, not as an independent verdict.
5. Re-run deterministic validators and inspect the rendered artifact directly.
6. If OMP generated the prose, use a separate clean auditor or an evidence-only review for final audit; do not call the same generation turn “independent review.”

## Fail-closed real-sample lesson

A fixture gate can pass while a real accepted sample correctly fails because an evidence locator points to an expired temporary artifact. Preserve this failure. Repair the artifact lifecycle and locator (for example, persistent skill-relative cache locators) rather than weakening required-section, claim-evidence, or section-QA gates.

Before retrying, verify:

- transcript artifact exists;
- locator resolves after a skill rename;
- content hash/provenance still matches;
- formal Writer only receives `ready` evidence;
- degraded output is not mislabeled publishable.
