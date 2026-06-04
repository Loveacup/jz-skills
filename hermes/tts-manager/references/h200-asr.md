# H200 ASR — Speech-to-Text Reference

> 2026-06-02 — Integrated as Hermes STT default. Groq Whisper kept as manual fallback.

## Endpoint

```
POST http://<internal IP redacted>:8088/ASR/transcribe
Content-Type: multipart/form-data
  file: <audio.wav>
  language: (optional, observed not effective — language auto-detected)
```

Response: `{"text": "transcribed text", "language": "Chinese"}`

N.B. The `language` field in the response is unreliable — always returns "Chinese" regardless of actual audio language. Do not use for downstream logic.

## Hermes Integration

Command provider config (`stt.providers.h200-asr: type: command`):

```yaml
stt:
  enabled: true
  provider: h200-asr
  h200-asr:
    type: command
    command: curl -s -X POST http://<internal IP redacted>:8088/ASR/transcribe -F "file=@{input_path}" | jq -r '.text'
    timeout: 30
    format: txt
```

All 18+ Hermes profiles configured 2026-06-02.

## Fallback

Groq Whisper kept as manual fallback:

```bash
hermes config set stt.provider groq
```

Groq API key intact in `.env`. Supermemory entry: `bipF8W2NDQkSrGjGnDzGYv`.

## Performance (2026-06-02)

| Scenario | Audio Duration | ASR Time | Notes |
|---|---|---|---|
| Chinese short (4s) | 4.0s | 0.49s | Perfect, auto-punctuation |
| Chinese daily (10.8s) | 10.8s | 0.99s | Perfect |
| Chinese long (~12s) | ~12s | 18.3s | Cold start; content correct |
| English short (~4s) | ~4s | 0.22s | Perfect |

**Verdict:** Suitable for real-time Telegram voice transcription (< 1s for typical 10s messages). First long audio after idle has ~18s cold start — subsequent calls stable.

## Health Check

```bash
curl -s http://<internal IP redacted>:8088/ASR/health
# → {"status":"ok","async_task_count":0,"async_task_retention_seconds":86400}
```

## Known Limitations

1. `language` parameter not effective — auto-detection always correct but response field always "Chinese"
2. Cold start on first long audio (~18s) — acceptable; warm calls < 1s
3. No streaming/real-time transcription — batch only
