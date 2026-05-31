# Changelog

## 2026-06-01 — v0.1.0 Base Skill

- Created `tts-manager` as the base Hermes TTS aggregation skill.
- Captured current default/fallback policy: Edge TTS remains default; Qwen3-TTS 0.6B CustomVoice is fallback only.
- Added provider registry and voice testing protocol.
- Recorded current Qwen3-TTS local findings in sanitized form:
  - float32 MPS works;
  - float16 MPS failed during prior testing;
  - cold command invocation is too slow for default live replies;
  - start-of-audio artifacts remain a quality blocker.
