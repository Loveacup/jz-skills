# Changelog

## 2026-06-02 — v0.2.2 patch Qwen artifact fix confirmed

- Corrected stale provider-registry and baseline snapshot entries: Qwen3-TTS 0.6B start-of-audio artifacts ARE fixable with post-processing (trim 500ms + 300ms fade-in, confirmed across 5 Chinese voice samples). Earlier language said "not fully fixed" which was inaccurate after the trim+fade variant was validated.
- No code change; documentation correction only.

## 2026-06-01 — v0.2.2 Speakable text optimizer MVP

- Added deterministic `agent/tts_voice_director/text_optimizer.py` with `SpeakableText` and `optimize_for_tts(...)`.
- `plan_text(..., optimize=True)` now plans spoken segments from optimized text while preserving raw `original_text`; `optimize=False` preserves previous behavior.
- Demo JSON now exposes `spoken_text` and optimizer transformation reason codes, with `--no-optimize` for before/after dry runs.
- Covered Markdown, links, paths, code/JSON/log dense blocks, technical tokens, versions, commit hashes, symbols, and long sentence shaping with regression tests.
- Verification recorded: Voice Director tests `33 passed`; TTS command/provider dispatch/max-length tests `114 passed`; default `tts.provider` remains `edge`.

## 2026-06-01 — v0.2.1 Voice Director MVP sample set

- Generated five Edge TTS review samples for Voice Director scenarios: formal_report, good_news, warning, comfort, and technical_explanation.
- Recorded exact text, sanitized output paths, and durations in `voice-testing-protocol.md`.

## 2026-06-01 — v0.2.0 Voice Director MVP

- Implemented provider-neutral TTS Voice Director MVP under `agent/tts_voice_director/`.
- Added schema models for `TTSPlan`, `ProviderManifest`, `VoiceRoute`, and `RoutingMemoryEvent`.
- Added built-in manifests for `edge` and `qwen3_0_6b_local`; Edge remains first-class realtime/default route while Qwen 0.6B stays fallback-only due to no instruction control and known start-artifact risk.
- Added deterministic content planner, manifest-scored extensible router, Edge SSML compiler, structured JSONL memory event writer, and Supermemory payload helper.
- Added safe dry-run demo: `scripts/tts_voice_director_demo.py`; it does not call live synthesis by default and does not change `tts.provider`.
- Updated `voice-director-architecture.md` with module paths, manifest/adapter contract, and memory event shape.

## 2026-06-01 — v0.1.0 Base Skill

- Created `tts-manager` as the base Hermes TTS aggregation skill.
- Captured current default/fallback policy: Edge TTS remains default; Qwen3-TTS 0.6B CustomVoice is fallback only.
- Added provider registry and voice testing protocol.
- Recorded current Qwen3-TTS local findings in sanitized form:
  - float32 MPS works;
  - float16 MPS failed during prior testing;
  - cold command invocation is too slow for default live replies;
  - start-of-audio artifacts remain a quality blocker.
