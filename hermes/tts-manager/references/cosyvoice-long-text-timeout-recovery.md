# CosyVoice Long-Text Timeout Recovery

Use when Hermes `text_to_speech` or the CosyVoice wrapper times out on medium/long scripts, but short TTS requests still succeed.

## Diagnostic pattern

1. Health probe with a very short text first:
   ```bash
   curl -sS --connect-timeout 5 --max-time 10 \
     -X POST "http://<cosyvoice-host>:8088/CosyVoice/v1/tts" \
     -F "text=测试" -F "spk_id=AlexCai" \
     -o /tmp/test-tts.mp3 \
     -w "HTTP_CODE:%{http_code} SIZE:%{size_download} TIME:%{time_total}\n"
   ```
2. If this returns `200` with non-zero size, the service is alive. Do **not** conclude the provider is down.
3. Medium/long scripts need a longer request timeout than Hermes' default 30s tool window. Retry the direct API with 60–90s max time.

## Direct generation pattern

```bash
TEXT=$(cat /tmp/tts-script.txt)
curl -sS --connect-timeout 10 --max-time 90 \
  -X POST "http://<cosyvoice-host>:8088/CosyVoice/v1/tts" \
  -F "text=$TEXT" \
  -F "spk_id=AlexCai" \
  --output /path/to/output.mp3
ls -lh /path/to/output.mp3
```

If the API returns OGG while the deliverable expects MP3, convert after verifying the source exists:

```bash
ffmpeg -y -i output.ogg -codec:a libmp3lame -b:a 128k output.mp3
```

## Reporting rule

- Successful direct API generation is a valid fallback after `text_to_speech` timeout.
- If both short probe and long direct request fail, annotate TTS as skipped with evidence; do not silently omit it.
- Do not save a durable claim that the provider is broken; record the observed timeout and the retry/fallback pattern only.
