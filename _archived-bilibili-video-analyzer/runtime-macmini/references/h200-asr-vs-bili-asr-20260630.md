# H200 ASR vs Local Bilibili ASR

Session learning from 2026-06-30: SURGExZR H200 exposes a working HTTP ASR gateway and is now the default ASR provider for the Bilibili subtitle fallback layer.

## H200 ASR gateway

- Base URL: `http://172.16.27.10:8088/ASR`
- Health: `GET /ASR/health`
- Transcribe: `POST /ASR/transcribe` with multipart field `file=@audio.wav`
- Observed response fields: `text`, `language`

Hermes STT command shape:

```yaml
stt:
  enabled: true
  provider: h200-asr
  h200-asr:
    command: >-
      curl -sS -X POST http://172.16.27.10:8088/ASR/transcribe
      -F "file=@{input_path}" | jq -r '.text'
    format: txt
```

## Live verification pattern before documenting or relying on it

Do not update docs from stale assumptions. Verify live service first:

1. Hit `/ASR/health`.
2. Transcribe a short audio sample with `timeout >= 120s`.
3. Transcribe a minutes-long sample with `timeout >= 1200s` or a background process.
4. Record HTTP code, elapsed seconds, audio duration/size, response keys, and text excerpt.
5. State exactly what was tested; do not extrapolate minutes-long success to arbitrary 20+ minute stability.

2026-06-30 evidence:

| Scenario | Duration | Size | Elapsed | HTTP | Result |
|---|---:|---:|---:|---:|---|
| Chinese short sample, macOS `say -v Tingting` | 11.57s | 362KB wav | 1.43s | 200 | OK; `text`, `language` |
| Chinese long sample, 18 repeated paragraphs | 309.88s | 9.5MB wav | 20.55s | 200 | OK; 1390 chars |

Long-audio guidance: a ~5 minute file works through the sync endpoint; for 10–20+ minute audio, prefer application-level chunking and merge to avoid proxy/gateway/HTTP long-connection fragility.

## `BILI_ASR_*` provider behavior

`bilibili-video-analyzer` subtitle fallback ASR is controlled by:

```bash
BILI_ASR_PROVIDER=auto|h200_asr|whisper_cpp|mlx_whisper
BILI_ASR_ENDPOINT=http://172.16.27.10:8088/ASR/transcribe
BILI_ASR_MODEL=<repo-or-name>
BILI_ASR_MODEL_PATH=<local-path>
BILI_ASR_LANGUAGE=zh|en|auto
```

As of 2026-06-30, `auto` means:

```text
H200 HTTP ASR → local whisper.cpp → local mlx-whisper
```

Explicit provider semantics remain strict:

- `BILI_ASR_PROVIDER=h200_asr`: only call H200; do not silently fall back to local ASR.
- `BILI_ASR_PROVIDER=whisper_cpp`: only call whisper.cpp.
- `BILI_ASR_PROVIDER=mlx_whisper`: only call mlx-whisper.

Use `BILI_ASR_ENDPOINT` to override the H200 URL. Do **not** put the H200 URL into `BILI_ASR_MODEL_PATH`; that variable is only for local whisper.cpp model files or MLX model refs.

## Privacy note

H200 is LAN/SURGE-local and preferable to public STT APIs for sensitive audio, but audio is still uploaded to a service. Avoid logging raw audio paths, full payloads, or sensitive transcripts in durable docs unless needed for debugging.
