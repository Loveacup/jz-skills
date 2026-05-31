---
name: tts-manager
description: "Use when managing, evaluating, configuring, or testing text-to-speech providers for Hermes or local agent workflows. Covers provider registry, fallback policy, voice/sample tests, resource benchmarks, artifact/noise checks, and keeping TTS decisions synchronized into this skill. Triggers on: TTS, text-to-speech, 语音合成, 音色测试, 后备 TTS, Hermes tts provider, edge-tts, Qwen3-TTS, custom voice. DO NOT use for STT/transcription, generic audio editing unrelated to TTS, or model research without a TTS deployment decision."
version: 0.1.0
author: Hermes Agent + Alex
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [tts, hermes, voice, audio, provider-management, fallback]
    related_skills: [hermes-agent, audio-transcriber, voice-to-markdown-workflow]
---

# TTS Manager — Aggregated Text-to-Speech Operations

This is the base skill for managing all Hermes/local TTS providers. Every future TTS adjustment, benchmark, voice choice, wrapper change, or fallback decision must be reflected here or in `references/` before reporting the work complete.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|---|---|
| "It's just a quick voice test" | Voice tests create durable provider decisions; log text, files, artifacts, and verdicts here. |
| "The default provider is obvious" | Hermes profiles may diverge. Always read live `config.yaml` before claiming the active provider. |
| "Generated WAV exists, so it works" | TTS quality includes first-token artifacts, latency, memory, language fit, and delivery behavior. |
| "I'll remember the benchmark" | Benchmarks become stale unless captured in `references/provider-registry.md` with date/context. |

## 🔀 Decision Tree

```
TTS-related request?
├── Hermes config/provider/default/fallback? → Load `hermes-agent`, read live config, then §Provider Ops
├── Voice/sample test?                       → §Voice Test Protocol + references/voice-testing-protocol.md
├── Resource/latency/quality benchmark?      → §Benchmark Protocol + update provider registry
├── New local/API provider integration?      → §Provider Intake + add registry entry
├── Artifact/noise issue?                    → §Artifact Triage
└── Not TTS (STT/transcription/audio editing) → use audio-transcriber or voice-to-markdown-workflow instead
```

## Core Rule: Update This Skill During TTS Work

For every non-trivial TTS change, do all four:
1. Record what changed in `references/changelog.md`.
2. Update `references/provider-registry.md` if provider capability, status, default/fallback policy, or benchmark changed.
3. Save exact sample text and artifact path in `references/voice-testing-protocol.md` or a dated result file if the test matters later.
4. Verify live config/artifacts before reporting success.

## Provider Ops

1. **Read live profile config first** — do not trust memory:
   ```bash
   hermes config path
   hermes config show | grep -A20 '^tts:'
   ```
2. **Identify current default and fallback**:
   - default provider: `tts.provider`
   - custom providers: `tts.providers.<name>`
3. **Do not switch defaults unless the user explicitly asks.** Adding a fallback provider is allowed when requested, but final response must say whether default changed.
4. **For command providers**, verify the command directly with a short text file and read back the produced media path.

## Voice Test Protocol

Minimum sample set:
- One short Chinese sentence with a natural opening.
- One longer Chinese sentence (≥50 Chinese chars).
- If multilingual provider: one English sentence and one native-language sample per claimed language.

Always report:
- speaker / voice ID
- exact input text
- output path
- sample rate + duration
- generation time or RTF if measured
- subjective artifact notes: start noise, clipping, truncation, pronunciation, prosody

Detailed templates live in `references/voice-testing-protocol.md`.

## Benchmark Protocol

For local providers, benchmark at least short/medium/long text. Capture:
- host/device/backend (`cpu`, `mps`, `cuda`, API)
- dtype / precision
- load time vs generation time
- output audio duration
- wall-clock RTF
- peak memory if available
- known blockers (missing acceleration, unsupported dtype, model reload cost)

## Artifact Triage

When the user reports noise, truncation, clicks, or distortion:
1. Confirm exact file and symptom; do not assume.
2. Inspect waveform/RMS/peak in the first 50/200/500 ms.
3. Try post-processing variants separately from generation changes:
   - lead silence
   - fade-in
   - trim+fade
   - regenerate with neutral prefix then trim prefix
4. If post-processing fails, record it as a provider/model quality issue, not a solved wrapper issue.

## References

| File | Use |
|---|---|
| `references/provider-registry.md` | Provider status, default/fallback policy, benchmark log, voice notes |
| `references/voice-testing-protocol.md` | Sample text templates, artifact triage workflow, Telegram delivery rule |
| `references/trigger-tests.md` | Should-trigger / should-not-trigger cases for description changes |
| `references/changelog.md` | Durable TTS management changes |

## Current Baseline Snapshot

See `references/provider-registry.md` for the live registry. Current baseline at creation:
- Hermes default TTS remains Edge TTS.
- Qwen3-TTS 0.6B CustomVoice is installed as a local fallback command provider, not default.
- On Apple Silicon/MPS, Qwen3-TTS 0.6B works in float32; float16 produced invalid probabilities during prior testing.
- Qwen3-TTS 0.6B voice samples showed start-of-audio artifacts that were not fully fixed by silence/fade/trim post-processing.

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I load `hermes-agent` for Hermes TTS config/provider work?
- [ ] Did I read live config or artifact files before stating current status?
- [ ] Did I record exact sample text and output paths for voice tests?
- [ ] Did I update `references/provider-registry.md` or `references/changelog.md` for durable TTS changes?
- [ ] Did I state whether the default provider changed or remained unchanged?
- [ ] Did I verify generated audio files exist before sending/reporting them?

**If any box is unchecked, go back.**
