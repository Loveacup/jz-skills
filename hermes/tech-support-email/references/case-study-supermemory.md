# Case Study: Supermemory Pro Upgrade — Memory Graph Wipe

> Full investigation → email pipeline that formed the basis of the `tech-support-email` skill.

## Problem

After upgrading Supermemory from Free to Pro plan, all three memory pools (`hermes-cabinet`, `hermes`, `sm_project_cli`) lost their memory graphs. Only raw documents survived — memories, memory links, and memory states were gone.

## Investigation Pipeline

### Phase 1: Symptom Gathering (15 min)
- User reports: "付费之后记忆图谱只剩文档" (after paying, memory graph only shows documents)
- Confirmed: all 3 pools affected, account-level, not container-specific
- Last known good state: May 31 23:03 UTC

### Phase 2: Log Deep-Dive (30 min)
- Extracted timeline from 3 log files (`agent.log`, `errors.log`, `gateway.log`)
- Discovered the degradation curve: healthy (2.92s) → timeout (5.26s) → degraded (4.20s) → 404
- Key finding: Pro upgrade happened May 31, but API stayed healthy for 10 hours before degrading

### Phase 3: Config Audit (20 min)
- Fetched official docs: `supermemory.ai/docs/integrations/hermes`
- Cross-referenced 12 config keys against our `supermemory.json` + `config.yaml`
- Result: zero misconfigurations. Only minor deviation: custom `container_tag: hermes-cabinet` (supported)

### Phase 4: Multi-Angle Testing (30 min)
- Tested 3 API endpoints + main site
- Tested from 5 geographic regions via Surge proxy exits
- **Critical finding**: HKG and LAX (different CF edges) both returned 404 → global origin outage
- Captured transient `cfOrigin;dur=0` header → CF spent zero ms communicating with origin
- POST returning 400 proved CF edge processes requests; origin is unreachable

### Phase 5: Email Drafting (3 iterations)
- v1: Technical but accusatory tone ("definitively proves", "zero misconfigurations")
- v2: User feedback → soften tone ("I was hoping you could help")
- v3: User feedback → delete backup question, add multi-region test results

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Deleted "do you have a backup?" question | User explicitly requested removal — adds tension, implies permanent data loss |
| Used "cfOrigin;dur=0" as primary evidence | Independently verifiable by vendor's own CF dashboard |
| Tested from 5 proxy regions | Proved global outage vs. regional issue |
| Soft tone throughout | "Hoping you could help" not "fix this" — vendor relationship matters |
| Bilingual (CN/EN) | Vendor is English-speaking; user reviews in Chinese |

## Email Structure (Final)

```
1. Warm opening
2. Symptom summary (3-pool table)
3. Account context
4. Soft impact statement
5. 2 questions (not 3)
6. Diagnostic appendix:
   - Config (12-key audit table)
   - Timeline (log-verified, 13 entries)
   - Multi-region API tests (5 regions)
   - CF header evidence (cfOrigin;dur=0)
7. Gracious closing
```

## Outcome

Pending vendor response. Email sent ~203 lines, bilingual, with hard evidence.

## Lessons for the Skill

1. **Investigate first, write second** — the 4-hour investigation made the email persuasive
2. **Hard evidence beats descriptions** — `cfOrigin;dur=0` is more convincing than "the API is down"
3. **Multi-angle testing matters** — one region's 404 could be regional; 3 regions' 404 is global
4. **Tone is everything** — even with ironclad evidence, soft tone gets faster response
5. **Delete what adds tension** — backup questions, urgency demands, accusatory language
6. **Config audit is a trust-builder** — "I checked my end, it's not me" saves the vendor's first response cycle
