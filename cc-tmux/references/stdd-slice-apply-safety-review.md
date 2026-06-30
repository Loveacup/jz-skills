# STDD slice apply safety review

Session lesson: when using the Codex → CC → Hermes pattern for STDD implementation slices, the auditor must review not only whether tests pass, but whether the write boundary is positively constrained.

## Trigger

Use this checklist when a slice introduces an `apply`, `write`, `render-to-disk`, migration, profile generation, config generation, or any other filesystem-writing engine — even if tests use fake FS only.

## Auditor checklist

Before accepting the CC implementation:

1. **Positive allowlist before fs access**
   - The target path must be checked against a positive scope before `exists`, `stat`, `mkdir`, or `writeFile`.
   - Blocking a few known bad paths (`.env`, `iii/config.yaml`, etc.) is not enough.

2. **Expected basename by kind**
   - Each logical file kind must map to an exact basename, e.g. `config -> config.yml`, `mcp -> mcp.json`, `env_example -> .env.example`.
   - Wrong basename means skip/error before fs access.

3. **Profile/name segment validation**
   - If path scope includes a profile/tenant/agent segment, validate that segment with the existing canonical validator.
   - Do not trust the plan producer to have validated it earlier.

4. **No overwrite by construction**
   - Default dry-run.
   - Require explicit `confirm:true` and non-dry-run.
   - Re-check existence immediately before each write.
   - Use exclusive create semantics where available (`flag: 'wx'`).

5. **Fake FS tests must include hostile targets**
   Add tests for examples like:
   - user home secrets (`~/.ssh/config` or absolute equivalent)
   - application config directories
   - default profile paths when only named profiles are allowed
   - invalid profile names (`Page`, `COM1`, etc.)
   - real `.env`
   - wrong basename
   - `..` traversal

6. **Self-report is not evidence**
   - Re-run the focused test and adjacent regression tests yourself.
   - Review the actual code ordering: static scope gate must happen before any adapter call.

## Good outcome pattern

A safe apply skeleton should have this shape:

```text
validate action kind
validate target path scope and basename
validate profile/tenant segment
reject secret/config/runtime-control targets
resolve content
confirm/dry-run gates
adapter.exists(target) immediately before write
adapter.writeFile(target, content, { flag: 'wx' })
```

Normal conflicts/skips should return structured results rather than throwing. Adapter write failures should be captured as structured errors.
