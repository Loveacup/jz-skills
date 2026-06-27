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
- `agent/tts_voice_director/text_optimizer.py` — deterministic speakable-text optimizer, `optimize_for_tts(...)`, returning raw/spoken text plus transformation reason codes.
- `agent/tts_voice_director/planner.py` — deterministic content planner, `plan_text(..., optimize=True)`.
- `agent/tts_voice_director/router.py` — provider-extensible manifest-scored router, `route_voice(...)`.
- `agent/tts_voice_director/adapters/edge.py` — Edge SSML compiler, `compile_edge_ssml(...)`.
- `agent/tts_voice_director/memory.py` — JSONL memory writer and Supermemory payload helper.
- `scripts/tts_voice_director_demo.py` — safe dry-run demo; it does not synthesize audio.

## Core pipeline

```text
Text
  -> optimize_for_tts
  -> SpeakableText (spoken_text + transformation reason codes)
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

## Speakable-text optimization

`plan_text(...)` now enables `optimize_for_tts(...)` by default and keeps `optimize=False` for backward compatibility and before/after comparisons. The optimizer is deterministic, provider-neutral, and never uses a network call or model.

The no-fact-invention rule is strict: the optimizer may omit unsuitable artifacts from speech only when it records a reason code and keeps the raw input in `TTSPlan.original_text` plus `metadata.speakable_text.original_text_preview`. It must not add facts, warnings, provider claims, or paths that were not present in the source.

Current transformation categories:

- Markdown cleanup: emphasis, headings, bullets, inline code, links, and table summaries.
- Dense artifacts: long JSON, code fences, stack traces, logs, and `MEDIA:` paths are summarized for speech with warnings when appropriate.
- Technical pronunciation: tokens such as `TTSPlan`, `VoiceRoute`, `qwen3_0_6b_local`, versions, commit hashes, and camel-case names are made speakable.
- Paths and filenames: full local paths are shortened to the filename in spoken text while raw text remains in metadata.
- Symbols and numbers: arrows become “然后”, `%` becomes “百分之”, `RTF 4.7` becomes “实时因子四点七”, and slash alternatives become “或”.
- Sentence shaping: very long Chinese or English sentences receive deterministic breath-break cleanup without rewriting meaning.

Demo JSON exposes top-level `spoken_text` and `optimizer.transformations[].reason` so callers can compare raw versus spoken output.

Verification on 2026-06-01:

- `python -m pytest tests/agent/test_tts_voice_director_*.py -q -o 'addopts='` → `33 passed`
- `python -m pytest tests/tools/test_tts_command_providers.py tests/tools/test_tts_plugin_dispatch.py tests/tools/test_tts_max_text_length.py -q -o 'addopts='` → `114 passed`
- Demo dry-run with optimization rewrites `**完成**：TTSPlan -> VoiceRoute，输出 ~/.hermes/foo.ogg，版本 v0.2.1。` to a spoken form containing `完成：T T S 计划 然后 Voice Route，输出 foo 点 ogg，版本零点二点一。`
- Demo dry-run with `--no-optimize` preserves the raw Markdown/path/token text in segments.
- Default `tts.provider` remained `edge`.

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
