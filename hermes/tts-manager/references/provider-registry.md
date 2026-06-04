# Provider Registry

Update this file whenever TTS provider status, default/fallback policy, benchmark, known issue, or voice recommendation changes.

## Current Policy

- **Default Hermes TTS:** CosyVoice (Fun-CosyVoice3-0.5B) via H200 server.
- **Fallback (same profile):** Edge TTS (`zh-CN-XiaoxiaoNeural`) — kept configured; used if H200/CosyVoice is unreachable.
- **Legacy local provider:** Qwen3-TTS 0.6B CustomVoice — retained as experiment only; not used in production.
- **Default switching rule:** Do not switch `tts.provider` without explicit user approval.
- **Voice selection rule:** Default voice is `AlexCai` (user's own voice clone). CosyVoice registration API supports custom voices via 3-shot enrollment (audio + text + speaker ID).
- **Delivery rule:** For voice tests, send individual audio files directly unless the user asks for a bundle.

## Providers

### CosyVoice (Fun-CosyVoice3-0.5B) — H200 Server — DEFAULT

- **Role:** Default Hermes TTS (migrated from Edge TTS 2026-06-02).
- **Backend:** Fun-CosyVoice3-0.5B on H200 GPU, reachable via `http://<internal IP redacted>:8088/CosyVoice`.
- **Integration:** Hermes command provider — wrapper script at `~/.hermes/scripts/cosyvoice-tts.sh`. Config pattern:
  ```yaml
  tts:
    provider: cosyvoice
    cosyvoice:
      type: command
      command: bash ~/.hermes/scripts/cosyvoice-tts.sh {input_path} {voice} {output_path}
      voice: AlexCai
      timeout: 30
  ```
- **Latency:** RTF 0.33–0.55 (well below real-time; ~1.4s for 14-char Chinese).
- **Voices:** 9 registered speakers including custom `AlexCai` voice clone. See `references/cosyvoice-h200.md` for full voice list, registration API, and wrapper script details.
- **Cost:** Zero (local GPU inference, no API key).
- **Strengths:** Custom voice cloning (~6s reference audio), zero API cost, internal network, no artifacts, OGG output (Telegram-native), solid Chinese prosody.
- **Weaknesses:** Requires H200 server running + Surge tunnel to <internal IP redacted>/24 subnet; ~1s slower than Edge TTS; command provider has no built-in fallback chain.
- **Quality:** Excellent Chinese; voice clone fidelity depends on reference audio quality (see §Voice Cloning Quality below).
- **Current verdict:** Default for all Hermes profiles. 18/18 profiles configured.

### Edge TTS — Fallback

- **Role:** Fallback TTS when CosyVoice/H200 is unreachable.
- **Cost:** Free / no API key.
- **Strengths:** Fast, stable, independent.
- **Current status:** Kept configured on all profiles but not default.

### Qwen3-TTS 12Hz 0.6B CustomVoice — Deprecated

- **Role:** Deprecated. Previously local fallback; superseded by CosyVoice (H200) which delivers better quality with no artifacts.
- **Model:** `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` plus tokenizer.
- **Retained for:** experimental/historical reference only. Not used in any production Hermes profile.
- **Known quality issue (historical):** Start-of-audio artifacts required trim 500ms + 300ms fade-in post-processing.
- **Current verdict:** Deprecated. Use CosyVoice for all TTS needs.

## Voice Cloning Quality (CosyVoice)

**Critical rule for reference audio:** Natural conversational speech works. Formal/播音腔 ruins the clone.

| Reference Style | Result |
|---|---|
| "我刚吃完饭，今天那个回锅肉还挺下饭的，你吃了没？" (casual) | ✅ Natural, relaxed, authentic |
| "大家好，我是Alex，很高兴用这种方式和你交流…" (formal intro) | ❌ Stiff, 播音腔, unnatural |

**Rules for reference audio:**
- 4-8 seconds, no background noise, 16kHz mono WAV
- Use everyday conversational content (meal talk, casual chat) — NOT self-introductions, NOT reading aloud
- **Act like you're sending a voice message to a friend, not recording for a system**
- If user complains about stiffness → re-clone with casual reference audio immediately
- Delete old speaker before re-registering with same `spk_id`

## Benchmark Log

### 2026-06-01 — Qwen3-TTS 0.6B local fallback smoke/benchmark

## Voice Cloning Quality (CosyVoice)

**Critical rule for reference audio:** Natural conversational speech works. Formal/播音腔 ruins the clone.

| Reference Style | Result |
|---|---|
| "我刚吃完饭，今天那个回锅肉还挺下饭的，你吃了没？" (casual) | ✅ Natural, relaxed, authentic |
| "大家好，我是Alex，很高兴用这种方式和你交流…" (formal intro) | ❌ Stiff, 播音腔, unnatural |

**Rules for reference audio:**
- 4-8 seconds, no background noise, 16kHz mono WAV
- Use everyday conversational content (meal talk, casual chat) — NOT self-introductions, NOT reading aloud
- **Act like you're sending a voice message to a friend, not recording for a system**
- If user complains about stiffness → re-clone with casual reference audio immediately
- Delete old speaker before re-registering with same `spk_id`

## Update Rules

When adding or changing a provider entry:
1. Include role: default, fallback, experiment, deprecated.
2. Include exact provider ID/model ID if public; redact local usernames, tokens, and private hosts.
3. Include latency/resource measurements only if backed by actual runs.
4. Include quality blockers in plain language.
5. Update `references/changelog.md` with the same date.
