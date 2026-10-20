# Deterministic Writer Skeleton Rejection

## Trigger

`generate_report.py --writer-provider none` reports a successful Markdown artifact, but the output contains any of:

- `Skeleton` / `_骨架占位`
- `_目的：..._` template instructions
- transcript-sized blockquotes instead of analysis
- empty author/metadata reconstructed from incomplete evidence
- “local WRR detected” or route discovery presented as completed research

## Decision

Treat this as a **failed formal Writer**, not as a draft to polish. Its `status=ok` only proves the deterministic renderer wrote a file.

## Recovery

1. Freeze the validated evidence bundle and any real WRR research artifacts.
2. Write the report manually from evidence; do not reuse the raw transcript blocks.
3. Select `condensed` when the transcript has coarse timing or the video/evidence budget does not justify full-mode density. Do not pad solely to meet full-mode quotas.
4. Keep the deterministic contract required by the selected mode. The publishable gate still requires sections `0, 1, 2, 2.5, 3, 4, 5, 6, 7, 8`; a terse prose paragraph must accompany a table-only §6.
5. Run both `verify_report.py --mode <selected>` and `verify_publishable_report.py` on the final saved Vault path, then refresh qmd after the last edit.

## Evidence boundary

A successful renderer process, an evidence gate, and a nonempty Markdown file do not establish editorial acceptance. Human inspection must reject template residue and unsupported claims before promotion.
