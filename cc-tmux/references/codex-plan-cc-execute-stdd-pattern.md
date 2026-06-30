# Codex plans → CC executes → Hermes audits (STDD slice pattern)

Use when a project/user explicitly wants role separation:

```text
Codex = planning lane
CC = execution lane
Hermes = audit / coordination / closeout
```

## Session-derived pattern

1. Hermes asks Codex for a **planning-only** STDD slice plan.
   - Prompt must say: do not modify files.
   - Ask for: target files, schema/API, RED-first tests, exact verification commands, risks, and what to delegate to CC.
2. Hermes audits Codex's plan.
   - Tighten boundaries: files not to touch, runtime not to register, routes not to advertise, secrets not to read.
   - Codex output is a draft, not evidence.
3. Hermes sends CC a bounded execution package.
   - Include hard constraints, TDD/RED-GREEN requirements, verification commands, and final output contract.
4. Hermes monitors CC and handles residual input safely.
   - If CC leaves a next-step suggestion in the prompt such as `Now do Slice 2 ...`, do **not** press Enter.
   - Try non-executing clear attempts (`C-u`, `Escape C-u`, `C-c`) if safe; if they fail, preserve the session and ask/record before killing.
5. Hermes audits from disk.
   - Re-run tests and syntax checks.
   - Confirm forbidden files were not touched.
   - Review diff and update Obsidian/qmd/Git only after evidence.
   - If the repo has an embedded project contract/roadmap snapshot (`AGENTS.md`, `README.md`, in-repo docs), check it for drift against the Obsidian/spec authority before closeout. In the agent-hub OMP slices, CC correctly updated code but the repo `AGENTS.md` roadmap still lagged at Slice 1 until Hermes audited and synchronized it.
6. For multi-slice feature work, keep the slice boundary explicit in both code and docs.
   - Do not let CC carry a residual prompt like `proceed to Slice N+1` or `commit this` forward; kill/finish the session after verification and start the next slice from a new Codex plan.
   - When Codex planning wanders into qmd/broad repository discovery and times out, retry with a shorter “use known context, do not inspect files” prompt rather than widening scope.

## Good Codex planning prompt

```text
You are planning only. Do not modify files. Read <specs> and current code. Produce a concise STDD execution plan for <slice>. Include target files, proposed schema/API, tests to write first, exact commands to verify, risks, and what should be delegated to CC for execution. Output Markdown only.
```

## Good CC execution package clauses

- Do not commit/push/rebase/install dependencies.
- Do not read secrets or environment-specific private directories unless explicitly in scope.
- Do not modify runtime routing or registration before the slice that owns it.
- Write tests first and show RED before implementation where feasible.
- Report changed files, RED/GREEN evidence, verification commands/exit codes, and residual risks.

## Verification checklist

- [ ] Codex produced plan only; no file writes.
- [ ] Hermes audited plan and added boundaries.
- [ ] CC stayed inside target files.
- [ ] Hermes re-ran tests.
- [ ] No self-report was used as final proof.
- [ ] Residual prompt input was not executed accidentally.
