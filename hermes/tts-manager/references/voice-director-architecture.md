# TTS Voice Director Architecture

Session learning: content-aware TTS behavior must include voice routing, provider extensibility, and structured memory write-back so future routing improves from feedback. The MVP is implemented as an optional helper package and does **not** change the live default `tts.provider`.

## MVP module paths

Implemented in Hermes Agent under:

- `agent/tts_voice_director/schema.py` — provider-neutral dataclasses:
  - `TTSPlan`
  - `TTSSegment`
  - `VoiceCandidate`
  - `ProviderManifest`
  - `VoiceRoute`
  - `RoutingMemoryEvent`
- `agent/tts_voice_director/manifest_loader.py` — YAML manifest loader:
  - `load_manifest(path)`
  - `load_builtin_manifests()`
- `agent/tts_voice_director/manifests/edge.yaml` — Edge baseline manifest.
- `agent/tts_voice_director/manifests/qwen3_0_6b_local.yaml` — Qwen3-TTS 0.6B local fallback manifest.
- `agent/tts_voice_director/planner.py` — deterministic content planner, `plan_text(...)`.
- `agent/tts_voice_director/router.py` — provider-extensible manifest-scored router, `route_voice(...)`.
- `agent/tts_voice_director/adapters/edge.py` — Edge SSML compiler, `compile_edge_ssml(...)`.
- `agent/tts_voice_director/memory.py` — JSONL memory writer and Supermemory payload helper.
- `scripts/tts_voice_director_demo.py` — safe dry-run demo; it does not synthesize audio.

## Core pipeline

```text
Text
  -> plan_text
  -> TTSPlan
  -> route_voice(manifests)
  -> VoiceRoute
  -> ProviderAdapter compiler
  -> compiled_text / SSML artifact
  -> RoutingMemoryEvent
  -> JSONL and optional Supermemory payload
```

The existing live synthesis dispatcher remains `tools/tts_tool.py::text_to_speech_tool(...)`. Voice Director is not wired into production synthesis by default.

## Provider-neutral schemas

### TTSPlan

Captures what should be said and how it should feel, without naming a provider.

Current MVP fields:

- `version`: schema version, currently `tts_voice_director.v1`
- `original_text`: source text
- `language`: BCP-47-ish language code, default `zh-CN`
- `scenario`: `formal_report`, `good_news`, `warning`, `comfort`, `technical_explanation`, `longform_reading`, `generic`
- `tone`: `calm`, `serious`, `warm`, `excited`, `concerned`, `apologetic`, `neutral`
- `energy`: numeric 0-1 planning signal
- `global_style`: deterministic style label
- `segments[]`: text chunks with `emotion`, `speed`, `pitch`, `pause_after_ms`, and `emphasis[]`
- `metadata`: caller-provided hints such as `requires_instruction_control`

### VoiceRoute

Captures the selected route and why.

Fields:

- `provider`
- `voice`
- `adapter`
- `confidence`
- `fallback_chain[]`: top scored candidates with score and reason codes
- `reason_codes[]`: e.g. `language_match`, `tone_fit`, `realtime_fit`, `prosody_capability_fit`
- `metadata`: score and manifest-type details

### RoutingMemoryEvent

Structured routing outcome event. Local writes are JSONL and default to a profile-safe Hermes path via `get_hermes_dir("memory/tts-routing", "tts-routing-memory")`.

Event shape:

```json
{
  "event_type": "tts_routing_outcome",
  "timestamp": "...",
  "plan": { "scenario": "good_news", "tone": "warm", "language": "zh-CN" },
  "route": { "provider": "edge", "voice": "zh-CN-XiaoyiNeural", "confidence": 0.85 },
  "outcome": "generated",
  "artifact": null,
  "user_feedback": null,
  "score_delta": 0.0,
  "output_path": null
}
```

`supermemory_payload(event)` returns stable keys suitable for write-back:

- `type`
- `scenario`
- `tone`
- `language`
- `provider`
- `voice`
- `confidence`
- `artifact`
- `feedback`
- `outcome`
- `timestamp`
- `score_delta`
- `text_preview`

## Capability manifests

Every provider must declare a manifest. The router reads manifests; it must not special-case future provider names.

MVP manifest contract:

```yaml
provider: edge
adapter: edge_ssml
type: command
languages: [zh-CN, en-US]
capabilities:
  ssml: true
  instruction_control: false
  emotion_control: false
  prosody_control: true
  emphasis: true
  streaming: false
  low_latency: true
constraints:
  max_text_chars: 4000
  artifact_risk: low
routing:
  priority: 100
  stable: true
  realtime_fit: high
voices:
  - id: zh-CN-XiaoxiaoNeural
    language: zh-CN
    tone_fit: [calm, warm, neutral]
    tags: [general, formal_report, comfort]
    artifact_risk: []
```

Current built-ins:

- `edge`: `edge_ssml`, low-latency and low-artifact baseline with Chinese voices `zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`, `zh-CN-XiaoyiNeural`.
- `qwen3_0_6b_local`: `plain_text_command`, fallback priority, no instruction/emotion/prosody control, known `start_noise` artifact risk; voices include `Serena`, `Sofia`, `Vivian`, `Mia`, `Azia`.

## Adapter contract

The MVP keeps provider-specific behavior out of the router. Adapters compile a provider-neutral `TTSPlan` plus `VoiceRoute` into provider input.

Current Edge adapter:

- XML-escapes text.
- Inserts `<break time="...ms"/>` after segments.
- Wraps speed/pitch changes in `<prosody rate="..." pitch="...">`.
- Wraps highlighted text in `<emphasis level="moderate">...` where possible.

Adding a new TTS engine should require:

1. `manifest.yaml`
2. adapter compiler module
3. optional postprocess/sample notes
4. tests for manifest loading, routing, and compilation

If adding a new provider requires modifying core router logic, treat it as an architecture defect.

## Routing score inputs

The MVP scores routes using provider-neutral manifest data:

- language support
- voice tone and scenario tags
- low-latency realtime fit
- artifact risk penalty
- SSML/prosody/instruction capability fit
- manifest routing priority
- optional memory boosts/penalties for known artifacts or approved voices

## Current baseline implications

- Edge remains the low-risk default for fast Telegram output and can receive style via SSML/prosody/breaks.
- Qwen3-TTS 0.6B local fallback is represented in the manifest but remains fallback only; the MVP does not download models or pretend it supports instruction/emotion control.
- Qwen3-TTS 1.7B, IndexTTS2, CosyVoice, Fish Speech, MOSS, and API providers should be added as manifests/adapters rather than new core branches.
