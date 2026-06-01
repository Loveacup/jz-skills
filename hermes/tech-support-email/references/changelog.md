# Changelog

## v1.1.0 (2026-06-01)

- **Evidence Sufficiency Gate (7 rules)**: Must pass all 7 gates before drafting — multi-region, multi-endpoint, header capture, config audit, timeline, degradation pattern, differential. Inspired by `debug-runbook` (UnCooe).
- **Evidence Type Taxonomy**: GOLD (vendor-verifiable) / SILVER (client-measured) / BRONZE (user-observed). Inspired by `support-to-repro-pack` (mshs01156).
- **Vendor Tier Tone Matrix**: 4 vendor types × calibrated tone/urgency/evidence style. SaaS startup, API/platform, enterprise, open source. Inspired by `customer-support` (priyanshu9888).
- Verification checklist: +2 items (gate check + tier selection)
- Metadata: added `upstream_inspirations` with project credits

## v1.0.0 (2026-06-01)

- Initial release
- 6-step investigation-first workflow: Investigate → Audit → Multi-angle Test → Evidence → Draft → Review
- Case study: Supermemory Pro upgrade memory wipe investigation
- Tone calibration table (what NOT to write vs what TO write)
- Bilingual (CN/EN) consistency guidelines
- Compliance-reviewed: 7-dimension scorecard all ≥4
