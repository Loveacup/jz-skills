# Correlated Multi-Video Synthesis

Use only when a user explicitly provides a small, related set of video URLs and requests one final synthesis rather than independent notes.

## Invariants

- **One URL = one EvidenceBundle acquisition and validation.** Do not create a combined pseudo-bundle or allow a healthy source to mask a failed source.
- Only bundles with `status: ready` can enter formal synthesis.
- A single final note is allowed; individual final notes are not required and should not be created unless requested.
- This is not a license for playlist, channel, feed, or bulk crawling.

## Procedure

1. **Clarify the output shape.** Distinguish: separate notes, comparative analysis, or one integrated argument. If the user says the videos are related and wants one final artifact, use this flow.
2. **Acquire separately.** For each URL: canonicalize, collect metadata and transcript, validate the evidence contract, record duration, transcript source/hash, and any errors.
3. **Set a hard inclusion gate.** Every source used in the synthesis must be `ready`. A non-ready source must be excluded and named under evidence gaps, or the work must pause for user direction.
4. **Build a source-role map before writing.** Example: Video A provides the conceptual mechanism; Video B supplies the operational/governance consequences. This prevents a report that merely concatenates two summaries.
5. **Ground the shared claims.** Use external research only for material claims that need it. Attribute statements to the relevant video and retain each video’s timestamps.
6. **Write one note.** In §0 or the evidence section, list each source, duration, evidence state, provenance and role. In the body, label cross-source synthesis as interpretation rather than a direct quote from either speaker.
7. **Release once.** Run the normal report/publishability gates on the final note, manually inspect for transcript dumping and source conflation, then refresh and retrieve the note from qmd.

## Common failure modes

| Failure | Correct response |
|---|---|
| “The engine says one video, so reject an explicitly requested two-video synthesis.” | Keep acquisition single-video, then synthesize only ready bundles. |
| “Create two formal notes and a third combined note by default.” | Save only the user-requested final artifact; evidence bundles stay outside the Vault. |
| “Use Video A’s details to fill gaps in Video B.” | Never do this. State the gap or omit the source. |
| “Treat two related videos as a batch-crawling job.” | Keep the source set bounded and user-defined; ask before expanding it. |
| “Quote the combined conclusion as though one author stated it.” | Use per-source timestamps for direct claims and label the integrated model as analysis. |
