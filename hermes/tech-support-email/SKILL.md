---
name: tech-support-email
description: "Use when drafting a technical support email to a SaaS/API vendor about a service outage, data loss, or bug. Covers the full workflow: deep-dive investigation → config audit against official docs → multi-angle testing → evidence gathering → tone-calibrated bilingual (CN/EN) email drafting. Triggers on: 写技术支持邮件, 给XX发邮件, support email, 报bug给, 联系技术支持, vendor outage email, draft support ticket. DO NOT use for internal team emails, customer success outreach, or non-technical correspondence."
version: 1.1.0
author: Hermes Agent + Alex
license: MIT
metadata:
  hermes:
    tags: [support, email, vendor-communication, debugging, bilingual, governance, evidence-pipeline]
    related_skills: [web-research-router, grill-with-docs, surge-gateway]
    upstream_inspirations:
      - "support-to-repro-pack (mshs01156) — structured evidence pipeline: facts → timeline → report"
      - "debug-runbook (UnCooe) — evidence-based decision engine with confidence scoring"
      - "customer-support (priyanshu9888) — tiered communication with vendor-type tone matrix"
---

# Tech Support Email — Investigation-First Vendor Communication

Write a technical support email that gets results. The core principle: **investigate BEFORE you write**. A well-researched email with hard evidence gets faster resolution than a vague complaint.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|---|---|
| "I already know the problem, I'll just write it" | Without systematic investigation, you'll make claims you can't back up. The vendor will ask for evidence you don't have. |
| "It's just an email, I don't need a workflow" | A sloppy email delays resolution by days. A well-structured one with evidence often gets fixed same-day. |
| "I'll just describe the symptoms" | Vendors need config details, timelines, and diagnostic evidence to skip the back-and-forth. |
| "The tone doesn't matter, they have to help me" | You're asking for help, even if you paid. An accusatory email goes to the bottom of the queue. |

## 🔀 Decision Tree

```
Need to contact a SaaS/API vendor about an issue?
├── YES → This skill
│   ├── Step 1: Investigate (gather symptoms, timeline, logs)
│   ├── Step 2: Audit (cross-reference config against official docs)
│   ├── Step 3: Multi-angle test (endpoints, regions, edge cases)
│   ├── Step 4: Gather hard evidence (headers, traces, error codes)
│   ├── Step 5: Draft email (soft tone, evidence as clues)
│   └── Step 6: Review (delete demands, check bilingual consistency)
└── NO → Internal communication? → Don't load this skill
```

---

## Step 1: Deep-Dive Investigation

Before writing a single word of the email, gather:

### 1a. Symptom Catalog
- What exactly is broken? Be specific — "Memories gone" not "it's broken"
- Which pools/endpoints/features are affected? Which are NOT?
- When did it start? When was it last working?

### 1b. Timeline Construction
Build a precise timeline from logs. Every entry needs: timestamp, event, latency/size.

```
❌ BAD: "It's been slow for days"
✅ GOOD: "May 31 23:03: store 2.92s (normal) → Jun 1 07:08: timeout 5.26s → 08:25: all endpoints 404"
```

**Key pattern to watch for**: healthy → degraded → dead. This proves it's not a sudden crash but a cascade.

### 1c. Log Evidence
Extract actual log lines, not summaries. Include:
- Error messages verbatim
- Latency measurements
- HTTP status codes
- Session IDs for traceability

---

## Step 2: Configuration Audit

**Cross-reference EVERY config key against the vendor's official integration docs.** Use `web-research-router` to fetch the docs page, then build a comparison table.

| Setting | Docs Default | Our Value | Verdict |
|---------|-------------|-----------|---------|
| ... | ... | ... | ✅/⚠️ |

This serves two purposes:
1. **Proves you did your homework** — vendor can skip the "check your config" step
2. **Eliminates client-side as root cause** — focuses them on server-side

Document any minor deviations (custom tags, shared profiles) but explicitly note they cannot cause the observed symptoms.

---

## Step 3: Multi-Angle Testing

Don't test from one path. Test from multiple:

### 3a. API Endpoints
Test ALL relevant endpoints — not just the one you use:
- `/health` — is the entire API down or just specific paths?
- Main site vs API subdomain — is it the whole service or just the API?
- Different HTTP methods (GET vs POST) — does the edge process requests?

### 3b. Geographic Regions (if applicable)
Use proxy/VPN exits to test from different regions. Different CF edges returning the same error = global outage, not regional.

| Exit region | Edge hit | Result |
|------------|----------|--------|
| 🇭🇰 Hong Kong | HKG | 404 |
| 🇺🇸 Los Angeles | LAX | 404 |

### 3c. Response Headers
Capture full response headers. Key signals:
- `Server-Timing: cfOrigin;dur=0` → CDN edge can't reach origin
- `CF-RAY: ...-XXX` → which edge handled the request
- `Server: cloudflare` vs `Server: nginx` → is CDN up but origin down?

---

## Step 4: Hard Evidence Gathering

The goal: find evidence that is **independently verifiable** by the vendor's own infrastructure team.

**Gold-standard evidence:**
- `cfOrigin;dur=0` — CDN spent zero ms talking to origin (proves origin is down, not client)
- Different CF edges all returning same error (proves global, not regional)
- POST returning 400 while GET returns 404 (proves edge processes requests, origin unreachable)
- Main site 200 while API subdomain 404 (proves CDN healthy, API-specific outage)

**Silver-standard evidence:**
- Agent log timestamps with latency degradation curve
- API test results from multiple timepoints

**Bronze-standard evidence:**
- User observations and screenshots
- Symptom descriptions without measurements
- Single-region test results

---

## Step 4b: Evidence Sufficiency Gate ⚠️ DO NOT SKIP

Before moving to draft, run this gate. If any rule fires ❌, go back and gather more evidence.

| Rule | Check | Gate |
|------|-------|------|
| **Multi-region** | Tested from ≥2 distinct geographic regions? | ✅ ≥2 / ❌ <2 |
| **Multi-endpoint** | Tested ≥3 different API endpoints (including `/health`)? | ✅ ≥3 / ❌ <3 |
| **Header capture** | Captured full response headers (not just status code)? | ✅ Yes / ❌ No |
| **Config audit** | Cross-referenced ≥1 official doc page against local config? | ✅ Yes / ❌ No |
| **Timeline** | Have ≥5 timepoints with latency/size data from actual logs? | ✅ Yes / ❌ No |
| **Degradation pattern** | Can describe a clear healthy → degraded → dead curve? | ✅ Yes / ❌ No |
| **Differential** | Tested at least one thing that WORKS (e.g. main site vs API)? | ✅ Yes / ❌ No |

**All 7 gates must pass before drafting.** A weak email with insufficient evidence wastes everyone's time — the vendor will ask for exactly what these gates check.

---

## Step 4c: Vendor Tier Tone Matrix

Different vendors need different tones. The same evidence presented differently gets different response speeds.

| Vendor Type | Tone | Example Opening | Urgency Signal | Evidence Style |
|-------------|------|-----------------|----------------|----------------|
| **SaaS Startup** (< 20 people) | Casual, collaborative | "Hope you're doing well! Ran into something weird..." | "when you get a chance" | Share as debugging clues |
| **API/Platform Vendor** (Stripe, CF, Vercel) | Technical, evidence-forward | "Writing about an issue with the API — gathered some diagnostics" | "this has been a bit challenging for my workflow" | Lead with config audit + headers |
| **Enterprise Vendor** (AWS, Azure, GCP) | Formal, SLA-referenced | "I'm experiencing a service disruption affecting [resource]" | Reference case/ ticket number if exists | Structured, with account ID + affected resources |
| **Open Source Maintainer** | Appreciative, PR-ready | "Love the project! Hit an issue and dug into it..." | None — appreciation only | Include repro steps + potential fix hints |

**Anti-pattern**: Using enterprise tone with a startup ("per our SLA...") → sounds entitled. Using casual tone with enterprise ("hey folks!") → gets ignored.

When unsure, default to **API/Platform Vendor** tone — it's the safest middle ground.

---

## Step 5: Draft the Email

### 5a. Tone Calibration ⚠️ CRITICAL

**You are asking for help, even if you paid.** The email should read like a collaborative debugging session, not a support ticket.

| DON'T write | DO write |
|---|---|
| "This is broken. Fix it." | "I ran into an issue, hoping you could help me understand" |
| "Your migration corrupted my data" | "I'm guessing something might have gone sideways during the migration" |
| "This is blocking production — urgent!" | "It's been a bit challenging for my daily workflow" |
| "Here's proof it's your fault" | "I noticed something that might be a useful clue" |
| "Zero misconfigurations on my end" | "I double-checked against the docs and everything looks correct on my end" |

### 5b. Structure

1. **Warm opening** — "Hope you're doing well!"
2. **Symptom summary** — 2-3 sentences, specific pools/features
3. **Account context** — email, plan tier
4. **Impact (soft)** — "has been a bit challenging" not "blocking production"
5. **Questions (2 max)** — what to investigate, rough timeline
6. **Diagnostic appendix** — config, timeline, multi-region tests, hard evidence
7. **Gracious closing** — "no rush, I know these things can be fiddly"

### 5c. What to DELETE

- ❌ "Do you have a backup?" — implies they might have lost your data permanently; adds tension
- ❌ "This is urgent" / "blocking production" — goes without saying; soft "a bit challenging" works better
- ❌ Accusatory language — "you broke", "your bug", "fix this"
- ❌ Demands for compensation or SLA invocation — save for follow-up if needed

### 5d. Bilingual Consistency

If writing in both English and Chinese, ensure:
- Same structure, same evidence, same tone in both versions
- Chinese version should be independently readable, not a translation artifact
- Cultural calibration: Chinese "完全不急" maps to English "no rush at all"

---

## Step 6: Pre-Send Review

- [ ] Did I gather actual log evidence (not summaries)?
- [ ] Did I audit config against official docs?
- [ ] Did I test from multiple endpoints/regions?
- [ ] Did all 7 Evidence Sufficiency Gates pass?
- [ ] Is hard evidence included (headers, multi-edge results)?
- [ ] Did I select the correct Vendor Tier tone from the matrix?
- [ ] Is the tone soft and collaborative?
- [ ] Did I delete backup questions and demands?
- [ ] Are both language versions consistent?

---

## Case Study: Supermemory Pro Upgrade Memory Wipe

See `references/case-study-supermemory.md` for the full investigation → email pipeline that this skill is based on. Key highlights:

- **Investigation**: 4-hour deep dive across 3 log files, 5 proxy regions, 3 API endpoints
- **Critical evidence**: `cfOrigin;dur=0` + HKG/LAX multi-edge 404 = global origin outage
- **Config audit**: 12 settings cross-referenced against official Hermes integration docs → zero misconfigs
- **Email**: 203 lines, soft tone, deleted backup question per user feedback
- **Outcome**: Pending vendor response

---

## ✅ Verification Checklist (RUN BEFORE SENDING)

- [ ] Did I investigate BEFORE writing (Steps 1-4 complete)?
- [ ] Is hard evidence included (headers, multi-edge tests, config audit)?
- [ ] Is the tone soft ("hoping you could help" not "fix this")?
- [ ] Did I delete backup questions and accusatory language?
- [ ] Are both language versions consistent (if bilingual)?

**If any box is unchecked, go back.**

---

> 📋 Changelog: `references/changelog.md`
> 🔄 Deployment & Sync: this skill is deployed to `jz-skills/hermes/tech-support-email/` and synced to `~/.hermes/skills/hermes/tech-support-email/`
