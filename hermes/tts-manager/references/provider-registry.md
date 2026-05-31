# Provider Registry

Update this file whenever TTS provider status, default/fallback policy, benchmark, known issue, or voice recommendation changes.

## Current Policy

- **Default Hermes TTS:** Edge TTS.
- **Fallback/local high-quality provider:** Qwen3-TTS 0.6B CustomVoice command provider.
- **Default switching rule:** Do not switch `tts.provider` without explicit user approval.
- **Delivery rule:** For voice tests, send individual audio files directly unless the user asks for a bundle.

## Providers

### Edge TTS

- **Role:** Default fast TTS for routine Hermes voice replies.
- **Cost:** Free / no API key.
- **Strengths:** Fast startup, stable delivery, good enough for short Chinese replies.
- **Weaknesses:** Less expressive/custom than local neural custom-voice models.
- **Current status:** Keep as default until a fallback provider proves low-latency and clean enough.

### Qwen3-TTS 12Hz 0.6B CustomVoice — Local Fallback

- **Role:** Local fallback / manual high-quality experiment, not default.
- **Model:** `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` plus tokenizer.
- **Suggested local root:** `${QWEN3_TTS_HOME:-/Volumes/<external-disk>/agent/qwen3-tts}`.
- **Hermes provider name used in local profile:** `qwen3_0_6b_local`.
- **Backend tested:** Apple Silicon MPS, PyTorch float32.
- **Precision finding:** float32 works; float16 on MPS previously failed with invalid probability/NaN behavior.
- **Install footprint observed:** about 4 GB total including model and venv.
- **Observed resource use:** about 2.6–3.2 GB peak RSS during prior tests.
- **Observed speed:** command cold-start is too slow for default live replies; single loaded process performs better but still slower than Edge.
- **Known quality issue:** start-of-audio artifacts/noise occurred in Chinese voice samples. Lead silence, fade-in, and trim+fade variants did not fully eliminate the perceived noise.
- **Current verdict:** keep as fallback only; not suitable as default Hermes TTS yet.

#### Voice Notes

Chinese voices tested:
- `Vivian` — female, bright; artifact issue still reported.
- `Serena` — female, softer; candidate for Chinese fallback if artifacts are acceptable.
- `Uncle_Fu` — mature male; stronger start artifact in diagnostics.
- `Dylan` — young male; start artifact observed.
- `Eric` — bright male; start artifact observed.

Other voices tested:
- `Ryan`, `Aiden` — English.
- `Ono_Anna` — Japanese.
- `Sohee` — Korean.

## Benchmark Log

### 2026-06-01 — Qwen3-TTS 0.6B local fallback smoke/benchmark

Context:
- Mac Apple Silicon with MPS.
- Model loaded from external disk path (sanitized above).
- Hermes default remained Edge TTS.

Representative results from prior local benchmark:
- Short Chinese text: total around 28 s, audio around 4.3 s, peak RSS around 2.6 GB.
- Medium Chinese text: total around 90 s, audio around 19.2 s, peak RSS around 3.2 GB.
- Long Chinese text: total around 280 s, audio around 44.5 s, peak RSS around 3.1 GB.

Interpretation:
- Works as a local fallback experiment.
- Too slow for default immediate replies when invoked as a cold command provider.
- Quality blocker remains start-of-audio noise/artifact.

## Update Rules

When adding or changing a provider entry:
1. Include role: default, fallback, experiment, deprecated.
2. Include exact provider ID/model ID if public; redact local usernames, tokens, and private hosts.
3. Include latency/resource measurements only if backed by actual runs.
4. Include quality blockers in plain language.
5. Update `references/changelog.md` with the same date.
