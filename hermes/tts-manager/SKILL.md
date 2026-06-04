---
name: tts-manager
description: "Use when managing, evaluating, configuring, or testing text-to-speech providers for Hermes or local agent workflows. Covers provider registry, fallback policy, voice/sample tests, resource benchmarks, artifact/noise checks, and keeping TTS decisions synchronized into this skill. Triggers on: TTS, text-to-speech, 语音合成, 音色测试, 后备 TTS, Hermes tts provider, edge-tts, CosyVoice, Qwen3-TTS, custom voice. DO NOT use for STT/transcription, generic audio editing unrelated to TTS, or model research without a TTS deployment decision."
version: 0.3.0
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
| "A zip bundle is enough for voice review" | Wrong for Telegram listening tests. Send the most relevant audio files directly with `MEDIA:`; use zip only as optional backup or when requested. |
| "Post-processing made the waveform cleaner, so the issue is solved" | User-perceived noise is authoritative. If the user still hears artifacts, record it as unresolved and try generation-side variants rather than declaring success. |
| "I'll remember the benchmark" | Benchmarks become stale unless captured in `references/provider-registry.md` with date/context. |

## 🔀 Decision Tree

```
TTS-related request?
├── Evaluate new TTS backend vs current?     → §Backend Evaluation Protocol + references/cosyvoice-h200.md (if CosyVoice)
├── Hermes config/provider/default/fallback? → Load `hermes-agent`, read live config, then §Provider Ops
├── Voice/sample test?                       → §Voice Test Protocol + references/voice-testing-protocol.md
├── Resource/latency/quality benchmark?      → §Benchmark Protocol + update provider registry
├── Content-aware tone / voice routing?      → §Voice Director + references/voice-director-architecture.md
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

When delivering samples over Telegram, send individual `MEDIA:/...wav` attachments for the primary choices. Do not make the user open a zip just to audition voices.

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

## Voice Director

When adding content-aware tone, emotion, or voice-routing behavior:
1. Use provider-neutral schemas (`TTSPlan`, `VoiceRoute`, `TTSRoutingMemory`) rather than hard-coding one engine's prompt format.
2. Route voices/providers from declared capability manifests: languages, voices, style controls, streaming, latency, artifact risks, memory/cost, and fallback role.
3. Keep the core router adapter-based. Adding a new provider should require only `manifest.yaml`, `adapter.py`, optional `postprocess.py`, and optional reference notes. If core router code must special-case a provider name, treat it as an architecture defect.
4. Automatically write structured routing outcomes and user feedback so future route scoring can learn from accepted/rejected voices, artifacts, latency, and scenario fit.
5. For MVP or dry-run work, verify the full closed loop without touching live defaults: `plan_text` → `route_voice(load_builtin_manifests())` → adapter compile → routing memory payload → focused tests → demo script with `--no-memory-write`.
6. When producing review samples, generate individual Telegram-compatible files for the main scenarios (`formal_report`, `good_news`, `warning`, `comfort`, `technical_explanation`), verify file existence/duration, and record exact text plus sanitized paths in `references/voice-testing-protocol.md`.

Detailed schema and adapter contract: `references/voice-director-architecture.md`. Sample set protocol: `references/voice-testing-protocol.md`.

## Backend Evaluation Protocol

When comparing current TTS/ASR against a new backend (e.g., local server, new API):

1. **Probe first** — health check all relevant endpoints before discussing migration.
2. **Audition all voices** — generate the same test sentence for every available speaker, send individually via `MEDIA:` for direct comparison.
3. **Benchmark latency** — at minimum short (2 chars) and medium (10+ chars) text. Report RTF.
4. **Echo-test ASR** — generate TTS → convert to 16kHz WAV → send to ASR endpoint. Verify accuracy and measure round-trip time.
5. **Present comparison table** — current vs candidate, with concrete metrics, not vibes.
6. **Let user audition before deciding** — do not switch defaults until the user has heard the samples and explicitly approves.

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
| `references/cosyvoice-h200.md` | CosyVoice API endpoints, voice registration workflow, latency benchmarks, speaker catalog, Hermes command provider config, YAML multi-line pitfall |
| `references/voice-director-architecture.md` | Provider-neutral TTSPlan/VoiceRoute/RoutingMemory schemas, adapter contract, extensible voice routing design |
| `references/voice-testing-protocol.md` | Sample text templates, artifact triage workflow, Telegram delivery rule |
| `references/trigger-tests.md` | Should-trigger / should-not-trigger cases for description changes |
| `references/cosyvoice-h200.md` | CosyVoice voice list, API reference, voice cloning quality rules |
| `references/h200-asr.md` | H200 ASR integration, performance benchmarks, fallback procedure |
| `references/changelog.md` | Durable TTS management changes |

## Scripts

| File | Use |
|---|---|
| `scripts/cosyvoice-tts.sh` | Bash wrapper for Hermes command provider — reads text from file, calls CosyVoice API, saves OGG output |

## Current Baseline Snapshot

See `references/provider-registry.md` for the live registry. Current baseline at 2026-06-02:
- **Default TTS:** CosyVoice (Fun-CosyVoice3-0.5B) on H200 server, via Hermes command provider.
- **Voice:** `AlexCai` — custom voice clone (re-registered with casual reference audio after first attempt was too 播音腔).
- **Wrapper:** `~/.hermes/scripts/cosyvoice-tts.sh` — pure bash + curl, zero deps.
- **Fallback:** Edge TTS (`zh-CN-XiaoxiaoNeural`) kept configured but not default.
- **Latency:** ~1.4s for 14-char Chinese (RTF 0.33–0.41 on H200).
- **Coverage:** All 18 Hermes profiles configured. 3 gateways restarted and verified.
- **Qwen3-TTS 0.6B:** Retired from active use (now experimental-only). Artifacts + slow cold start made it unsuitable vs CosyVoice.
- **Voice cloning quality rule:** Casual conversational reference audio produces natural clones. Formal/self-introduction references produce stiff 播音腔. See `references/cosyvoice-h200.md` for full integration guide.
- **ASR:** Still on Groq Whisper. H200 ASR evaluated and ready for migration, but not yet switched. See `references/cosyvoice-h200.md`.

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I load `hermes-agent` for Hermes TTS config/provider work?
- [ ] Did I read live config or artifact files before stating current status?
- [ ] Did I record exact sample text and output paths for voice tests?
- [ ] For content-aware tone/voice routing, did I keep the design provider-neutral and write/plan structured routing memory?
- [ ] Did I update `references/provider-registry.md` or `references/changelog.md` for durable TTS changes?
- [ ] Did I state whether the default provider changed or remained unchanged?
- [ ] Did I verify generated audio files exist before sending/reporting them?

**If any box is unchecked, go back.**
