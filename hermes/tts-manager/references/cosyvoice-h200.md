# CosyVoice H200 — Voice List & API Reference

> 2026-06-02 — 9 speakers registered, Fun-CosyVoice3-0.5B on H200 × Studio.

## Base URL

```
http://<internal IP redacted>:8088/CosyVoice
```

## Registered Speakers (9)

| # | Speaker ID | Type | Notes |
|---|---|---|---|
| 1 | `测试音色` | Default | Test voice |
| 2 | `tutu` | Default | Female, playful |
| 3 | `女主播` | Default | Female, broadcast-style |
| 4 | `大炮` | Default | Male, deep |
| 5 | `早妹妹` | Default | Female, youthful |
| 6 | `小新` | Default | Male, young |
| 7 | `老板讲故事` | Default | Male, storytelling |
| 8 | `怡宝` | Default | Female, warm |
| 9 | `AlexCai` | Custom | Alex voice clone (re-registered 2026-06-02 with casual audio) |

## API Reference

### Health Check
```bash
curl -s http://<internal IP redacted>:8088/CosyVoice/health
# → {"status":"ok","model_dir":"/share/LLM_models/pretrained_models/Fun-CosyVoice3-0.5B"}
```

### List Speakers
```bash
curl -s http://<internal IP redacted>:8088/CosyVoice/v1/speakers
```

### Register New Voice
```bash
curl -X POST http://<internal IP redacted>:8088/CosyVoice/v1/speakers \
  -F "spk_id=<name>" \
  -F "prompt_text=<exact text of reference audio>" \
  -F "prompt_wav=@/path/to/reference.wav"
```

Requirements: 16kHz mono WAV, 4–8 seconds, clean audio.

### Delete Voice
```bash
curl -X DELETE http://<internal IP redacted>:8088/CosyVoice/v1/speakers/<name>
```

### Synthesize Speech
```bash
curl -X POST http://<internal IP redacted>:8088/CosyVoice/v1/tts \
  -F "text=<text to speak>" \
  -F "spk_id=AlexCai" \
  --output output.ogg
```

Output: OGG Opus, 24kHz mono.

## Hermes Wrapper Script

`~/.hermes/scripts/cosyvoice-tts.sh` — Bash wrapper invoked as Hermes command provider:

```bash
bash ~/.hermes/scripts/cosyvoice-tts.sh {input_path} {voice} {output_path}
```

Reads text from `{input_path}`, calls CosyVoice API with `{voice}` speaker, saves OGG to `{output_path}`.

## Voice Cloning Quality Rule

| Good Reference | Bad Reference |
|---|---|
| "我刚吃完饭，今天那个回锅肉还挺下饭的，你吃了没？" | "大家好，我是Alex，很高兴用这种方式和你交流…" |
| Casual, conversational, ~6s | Formal, broadcast tone, self-introduction |
| ✅ Natural clone | ❌ Stiff, 播音腔 |

**Rule:** Use casual conversational content for reference audio. If user complains about stiffness, re-clone immediately with casual audio.
