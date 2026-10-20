# S8 Research Release Acceptance Record

Scope: acceptance of the S8 research scheduler / release fixture lane for
video-analysis-engine, based solely on locally verified evidence.

## Decision

S8 is **accepted for release** on the strength of the deterministic offline
fixture research lane and the sparse no-research / no-network lane. Acceptance
covers the fixture-driven research path and its P0 gates only. It does **not**
cover a real network research provider, which remains unimplemented and
unverified.

## Accepted Evidence

All items below were run and observed locally.

- **Full test suite:** `716 passed`.
- **Release gate:** `python3.12 scripts/release_gate.py --skip-pytest --json`
  reports top-level `"passed": true`.
- **Full offline fixture research lane:** fixture quality gate PASS with
  `"validated_evidence_count": 14`, `"capability_available": true`; all research
  P0 gates pass (e.g. `P0_RESEARCH_CONFLICT` pass, per-section
  `evidence-grounded` passed).
- **Sparse lane:** runs with no research and no network; research reported as
  unavailable (`"validated_evidence_count": 0`, `"research_gate_passed": null`),
  which is the expected fail-closed state for this lane.
- **Diagnostic archive:** the fixture research run writes to a private local
  path, `/tmp/video-analysis-engine-release-gate/research`, used for diagnostics
  only.

## Evidence Policy

- Only facts observed from local execution are admitted as acceptance evidence.
- The private diagnostic archive is a diagnostic artifact. Its **contents and
  path are never to be treated as a public artifact** and must not be published,
  redistributed, or cited as a deliverable.
- OMP RPC output is **not** acceptance evidence. It exhibited runaway behavior
  and scope misclassification, so it is excluded from the evidence base entirely.

## Exclusions and Limitations

- **Not an OMP approval.** This record is a local acceptance record only; it does
  not constitute or imply OMP approval or sign-off.
- **Real network research provider:** unimplemented and unverified. Any
  network-backed research path is out of scope for this acceptance.
- **OMP RPC output excluded:** disregarded due to runaway output and scope
  misclassification.
- **Private archive is not public:** the archive at
  `/tmp/video-analysis-engine-release-gate/research` is private diagnostic
  state, not a public artifact.
