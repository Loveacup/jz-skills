# Medium bundle, runaway audit: criterion-excerpt fallback

## Observations

Two bounded bundle-only audits still entered tool loops:

### Multi-file code audit

- bundle size: ~188 KB;
- diff: 4,242 lines / ~175 KB;
- six explicit criteria;
- prompt said “do not call tools” and required one JSON object;
- raw output grew to 24,999,344 bytes;
- final state: `stopReason=toolUse`, zero evidence, no valid verdict.

### Single design-document audit

- evidence bundle: ~60 KB;
- one Markdown Spec, 1,070 diff lines;
- five explicit architecture criteria;
- scope allowed only the evidence-bundle directory;
- prompt required one JSON object and forbade additional exploration;
- raw output grew to 33,994,786 bytes in roughly 40 seconds;
- final state: `stopReason=toolUse`, zero evidence, no valid verdict.

Both runs were stopped by the 20 MB fuse, formally rejected, and not interpreted as either a blocker or pass.

The second case proves that neither “one file” nor “60 KB” is a safe complexity proxy. Long design documents create semantic traversal pressure even when their byte size is modest.

## Durable rule

“Small in bytes” is not the same as “small for audit reasoning.” A multi-thousand-line full diff invites exploratory traversal even when the prompt forbids tools.

For medium/large multi-criterion changes, prefer a **criterion-excerpt bundle**:

1. One short source excerpt per criterion, including direct caller/callee contracts.
2. One matching test excerpt per criterion, including negative assertions.
3. Compact command evidence: command, exit code, pass count, and artifact path—not full successful logs.
4. A short file/diff manifest for scope proof; include the full diff only as a secondary appendix when truly needed.
5. Explicitly tell the auditor that supplied excerpts are sufficient and that no repository exploration is required.

For a long design document, use a **two-pass review package** instead of feeding the full Spec as the primary reasoning surface:

1. A clean read-only reviewer reads the whole document and emits at most 3–5 concrete concerns with line evidence.
2. Revise the document.
3. Build one short before/after excerpt per concern, plus the full-document semantic hash and heading manifest.
4. Ask OMP only whether those named concerns are closed; the full document is a secondary read-only appendix, not the primary prompt body.
5. If OMP still crosses the 20 MB fuse without a verdict, reject it and use the clean reviewer closure plus Hermes structural checks. Record that OMP failed; never rewrite the fallback pass as an OMP pass.

## Termination and fallback

- Keep the hard 20 MB fuse even for apparently modest bundles.
- If the first run exceeds the fuse with no legal verdict, reject it formally.
- Do not retry the same bundle by merely increasing timeout or repeating “do not call tools.”
- Fall back to Hermes' independently executed commands plus a clean read-only reviewer that inspects current source/test contracts.
- Record the failed auditor truthfully; the fallback reviewer may pass the code, but does not retroactively make the failed audit a pass.
