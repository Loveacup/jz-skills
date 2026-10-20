# Bounded Research Fixture Scheduling

## Problem

A deterministic fixture provider can emit a primary + independent source for every claim, while `HermesWRRAdapter` enforces one shared `max_sources` cap. With 12 claims and a cap of 20, naïvely emitting two sources per claim consumes 20 slots before tail claims run. Those claims receive zero candidates and the final coverage gate blocks.

A second trap is an arbitrary per-query claim slice (for example `claim_uids[:10]`): even unused budget cannot rescue tail claims that were never bound.

## Contract-correct allocation

1. Enumerate claims in stable plan/query order; deduplicate each `(claim_uid, relation)` emission.
2. **Round 1:** emit exactly one `primary` source for every eligible P0–P3 claim.
3. **Round 2:** emit exactly one `independent` source only for P0/P1 claims, which require two independent publishers by default.
4. Apply the unchanged global source cap over the concatenated rounds.
5. If policy minima themselves exceed the cap, leave the bundle blocked; do not increase the cap or weaken coverage.

## Regression proof

Use a budget-pressure plan with tail P2/P3 claims:

- every tail P2/P3 has at least one bound/validated primary source;
- each P0/P1 still has primary + independent sources in separate publisher groups;
- total emitted candidates never exceeds `max_sources`;
- validator coverage passes only when all required minima fit;
- archive, projection and public-path gates still run against the resulting validated bundle.

## Debugging sequence

When a fixture bundle blocks, inspect in this order:

1. raw `execution.source_count` vs final validated source count;
2. candidate quote rejection reasons (`missing_snapshot`, `quote_not_in_snapshot`, etc.);
3. adapter raw field bridge (`quote_candidates` versus validator-consumed `quotes`);
4. per-claim candidate allocation under the shared source cap;
5. assessment relations, publisher groups and claim-level `required_publisher_count`.

Do not treat a passing archive/projection gate as proof of coverage: those validate transport and referential integrity, not whether every required claim got its policy minimum.