# Execution Flow (Full DAG)

## Phase Dependency Graph

```
Quick:  P0 → P1 → P2 → P3(parallel) → P4 → P5 → P7 → P8
Standard: P0 → P1 → P2 → P3(parallel) → P4 → P5 → P7 → P8
Deep:    P0 → P1 → P2 → P3(parallel) → P4 → P5 → P6 → P7 → P8
```

## Phase Detail

### Phase 0: Material Intake (main agent)
- Identify all input material types
- Preprocess: PPT→md, screenshots→OCR, URLs→structure
- Output: manifest.json

### Phase 1: Memory Injection (main agent)
- Read speakers/projects/patterns/corrections
- Read voiceprints.json → verify speaker list
- Match current session context
- Generate known-facts.json
- Crystallized ASR rules → write to cleaning script params

### Phase 2: Input Normalization (Python scripts)
- input_formatter.py → standard-input.md
- speaker_normalizer.py (inject known-facts)
- rule_based_cleaner.py (with crystallized rules)
- stat_extractor.py → file-stats.json
- Output: normalized-input.md, file-stats.json

### Phase 3: Analysis (2 parallel agents)
- scene-analyzer → analysis.json (both inject known-facts.json)
- knowledge-enricher → knowledge-context.json (qmd+Exa, both inject known-facts.json)

### Phase 4: Content Processing (content-processor agent)
- Dependencies: analysis.json + knowledge-context.json
- Segment by topic + deep de-redundancy + ASR correction
- Output: preprocessed.md

### Phase 5: Verification Gate (main agent)
- Extract all entities from preprocessed.md
- Cross-check against known-facts.json:
  - Voiceprint (confidence=1.0) → auto-confirm
  - Match → confirm
  - Candidate match (name?) → show speech snippet, ask user
  - Mismatch → ask user
  - New entity → ask user to supplement
- Unknown speaker registration (v6.3):
  - Check *-speaker-embeddings.json sidecar
  - For "Speaker N": extract 3 longest speech segments, show to user
  - For "name?" candidate match: ask user to confirm or correct
  - Options: speakers.json unregistered voices + "new person" (ask name) + "skip" (keep sidecar)
  - Confirmed → write to voiceprints.json, update speakers.json + preprocessed.md
- Output: verified-facts.json; if corrections → update preprocessed.md

### Phase 6: Deep Analysis (deep-analyst agent, Deep mode only)
- Dependencies: preprocessed.md + analysis.json + knowledge-context.json + verified-facts.json
- Output: deep-analysis.json

### Phase 7: Writing (writer agent, scene-routed)
- Dependencies: ALL above outputs (MUST all complete before writer starts)
- Scene routing:
  - Meeting → meeting-writer (strategic narrative)
  - Lecture → lecture-writer
  - Interview → interview-writer
- Single integrated output: output.md

### Phase 8: Output + Memory Writeback (main agent)
- Copy output.md to user-specified directory
- Read correction stats (v6.3):
  - Find *-corrections-applied.json
  - Accumulate to corrections.json occurrences
  - Update last_seen date
- Mandatory memory writeback:
  - speakers.json (new speakers/aliases/session_count)
  - sessions.json (current session record)
  - corrections.json (new corrections + counts + application stats)
  - metrics.json (workflow metrics)
  - preferences.json (preference changes)
- Auto crystallization check (v6.3):
  - Iterate corrections.json for uncrystallized rules
  - Condition: occurrences ≥5 AND ≥2 different sessions
  - Satisfied → write to patterns.json (type=asr_correction)
  - Mark crystallized=true + crystallized_at
