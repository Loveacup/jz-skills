# CC Research → STDD → Codex Plan → CC Execute · 6-Phase Pipeline · 2026-06-29

Use when a project needs **research-informed design** before planning and execution. Unlike
`codex-plan-cc-execute-stdd-pattern.md` (which assumes design exists), this pattern starts
with CC agent team doing multi-domain research to feed the STDD control document.

## 6-Phase Flow

```
Phase 1: CC agent team researches N domains in parallel
   ↓ 产出研究报告（多域合并）
Phase 2: CC writes STDD control document + restructures OB docs
   ↓ 产出 STDD 终稿 + 全量文档
Phase 3: Codex plans implementation (15-step RED-first)
   ↓ 产出实施计划
Phase 4: CC agent team executes (RED tests → implementation → regression)
   ↓ 产出代码 + 测试
Phase 5: OMP audits against STDD (criteria × verdict = nit/concern/blocker/pass)
   ↓ 产出审计报告
Phase 6: Hermes verifies (cross-check + tests + GitHub push + OB writeback)
   ↓ 交付完成
```

## Phase 1 Specifics: CC Agent Team Multi-Domain Research

### Task Brief Format

Write a self-contained research brief covering all domains, specify:
- Per-domain focus areas
- Output file path per domain (e.g., `/tmp/cc-output/<session>/domain<N>-<topic>.md`)
- Requirement: all domains merge into one final report

### Agent Team Pattern

CC's `@` agent team spawns one sub-agent per domain:
```
@github-researcher  → domain1-github.md
@community-researcher → domain2-community.md
@academic-researcher → domain3-academic.md
@skill-researcher   → domain4-skill-discovery.md
```

Main agent merges into `/tmp/wrr-research-report.md`.

### Pitfall: Sub-Agent Write Failures

Academic sub-agent ran 11min+ with `write` tool failing silently (file not written to disk).
**Mitigation**: CC main told sub-agent to return raw markdown as message text, then main wrote
the file itself. Timeout: accept 3 out of 4 domains if one sub-agent stalls, note as limitation.

## Phase 2 Specifics: STDD + OB Restructuring

After research report, CC writes:
1. STDD control document (Spec/Design/Task/Delivery) — the design authority
2. Restructure OB documentation directory (6 new v5.0 docs + mark old as historical)

STDD sections: Spec(Why/What/Not) → Design(Mode/Engine/Weights) → Task(File List) → Delivery(Acceptance Criteria) → Execution Route

## Phase 4 Specifics: RED-First Implementation

CC agent team splits into sub-agents per component:
- `@eng-fusion` → _fusion.py + test_fusion.py
- `@eng-academic` → academic.py + test_academic_engine.py
- `@eng-skill` → skill_discovery.py + test_skill_*py
- `@eng-gh-client` → _github_client.py + shared client utilities
- Main → router overhaul + integration

Each sub-agent: write RED tests → confirm fail → implement → confirm pass → return to main.

## Mid-Turn Supplementary Task Injection

When CC main is waiting for a sub-agent (e.g., academic-researcher), you can send a supplementary
research brief to add a new domain **without breaking the session**:

```bash
# Write supplementary brief
write_file /tmp/wrr-skill-discovery-brief.md "新研究域..."

# Send to same CC session mid-turn
cc-send.sh --session <session> --context /tmp/wrr-skill-discovery-brief.md
```

CC picks it up when it resumes from sub-agent wait. Works for: adding domains, sending corrections,
injecting user feedback mid-research.

## Phase 5: OMP Audit

Use **sync shell** mode (async can silently fail with 0-byte raw):

```bash
omp -p --mode json --no-session --max-time 180 \
  --tools "read,grep,glob" --cwd <project> \
  "审计 criteria..." > /tmp/omp-raw.json
```

If `omp-monitor` rejects (OMP text lacks structured verdict JSON), extract manually:

```bash
python3 -c "
import json
with open('/tmp/omp-raw.json') as f:
    lines = f.readlines()[-1000:]
texts = [json.loads(l)['assistantMessageEvent']['delta']
         for l in lines if json.loads(l).get('type')=='message_update'
         and json.loads(l).get('assistantMessageEvent',{}).get('type')=='text_delta']
print(''.join(texts[-3000:]))
"
```

## Phase 6: Hermes Verification

1. Run full test suite: `pytest --cov=wrr --cov-report=term-missing`
2. Run integration tests with live APIs where available
3. Run E2E mode routing tests (classify_intent, MODE_DISPATCH, RRF)
4. Verify contracts (schemas, tools, formatters, v4 router untouched)
5. Syntax check: `python -m compileall wrr/`
6. Push to GitHub (handle monorepo vs standalone repo)
7. Write back OB documentation (update execution status, test counts, audit results)

### Git Push to Monorepo Subdirectory

If the plugin repo (`~/.hermes/plugins/<name>/`) is standalone but the target GitHub
is a monorepo subdirectory (e.g., `jz-skills/shared/<name>/`):

```bash
# Clone monorepo, sync plugin files WITHOUT --delete
git clone <monorepo-url> /tmp/push-target
rsync -av --exclude .git --exclude __pycache__ \
  ~/.hermes/plugins/<name>/ \
  /tmp/push-target/shared/<name>/
cd /tmp/push-target && git add shared/<name>/ && git commit && git push
```

**Do NOT use `--delete`** — it removes files managed by the monorepo (SKILL.md, references/).
