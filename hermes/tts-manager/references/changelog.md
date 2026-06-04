# Changelog

## 2026-06-02 — CosyVoice migration complete

**Default TTS changed from Edge TTS → CosyVoice (H200).**

- Evaluated H200 TTS (CosyVoice) and ASR services. CosyVoice passed all benchmarks: RTF 0.33-0.55, clean output, voice cloning works.
- Registered custom voice `AlexCai` on CosyVoice. First attempt was too 播音腔 (used formal self-intro as reference). Re-cloned with casual conversational reference ("回锅肉" sentence) — much more natural.
- Created Hermes command provider wrapper: `~/.hermes/scripts/cosyvoice-tts.sh` (pure bash + curl).
- Migrated TTS default on all 18 Hermes profiles + main config. Set Edge TTS as fallback.
- Restarted all 3 gateways (default, cron-worker, regent). All verified running.
- ASR also migrated from Groq Whisper → H200 ASR (command provider: `curl | jq -r '.text'`). All 19 profiles configured. Groq retained as manual fallback (`hermes config set stt.provider groq`). Typical latency <1s for Telegram voice messages.
- Added `references/cosyvoice-h200.md` with full API reference, voice list, config pattern, voice cloning quality rules, and troubleshooting.
- Updated `references/provider-registry.md`: CosyVoice now default, Edge downgraded to fallback, Qwen3-TTS 0.6B retired to experiment-only.
- Morning news briefing pipeline tested end-to-end with the new TTS: PDF (716KB) + TTS audio (92s, AlexCai voice).

## 2026-06-01 — Qwen3-TTS local fallback smoke/benchmark

- Initial Qwen3-TTS 0.6B evaluation on Apple Silicon MPS. Too slow for default, artifacts present. Kept as fallback experiment.

## 2026-06-01 — Initial skill creation

- Established provider registry, voice testing protocol, benchmark protocol, and artifact triage workflow.
