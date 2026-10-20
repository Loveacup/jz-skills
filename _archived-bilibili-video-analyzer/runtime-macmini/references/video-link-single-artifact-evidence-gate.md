# Video link workflow: single final artifact + evidence gate

Use when the user sends a Bilibili/YouTube video link and expects a finished analysis稿件.

## Hard contract

- Final Obsidian output is exactly **one** user-facing note per video link: `B站笔记_...md`.
- Do **not** leave `完整记录稿_...`, raw transcript files, `预分析_...`, intermediate drafts, or audit notes in the vault unless the user explicitly asks for process evidence.
- Transcript/ASR artifacts may exist in `/tmp` during processing, but must not be persisted into the vault by default.

## Evidence gate

Formal reports require transcript evidence:

- Official subtitle, or
- H200/local ASR transcript, including long-video chunked ASR.

If transcript evidence is missing:

- Do not save a normal `B站笔记_...`.
- Either keep working on subtitle/audio/ASR recovery, or explicitly output a non-final preanalysis outside the vault if the user wants a partial result.

`verify_report.py` only checks structural depth; it does **not** prove source sufficiency. Formal-save gate must check `report.evidence_gate.can_generate_formal_report`.

## Bilibili audio recovery pattern

- Do not use `curl --max-filesize` as an audio sampling probe; it can abort immediately when remote `Content-Length` is larger than the cap.
- Use HTTP Range for sampling, e.g. `Range: bytes=0-10485759`.
- For ASR, prefer the lowest DASH audio bandwidth; high bitrate is unnecessary and increases failure/cost surface.
- For long audio, split into 5-minute WAV chunks and send each chunk to H200/local ASR, then merge.

## External fact-check / expansion route

EvidenceSourceGate should mark auxiliary research route:

- Local WRR detected → `external_research.route = wrr_local`, mode `grounding`.
- No local WRR → `external_research.route = fallback_search`, using configured web/search tools.

This route is auxiliary; it enriches/fact-checks the report but does not replace the transcript requirement.
