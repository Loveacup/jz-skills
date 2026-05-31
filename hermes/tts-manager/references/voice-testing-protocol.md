# Voice Testing Protocol

Use this reference when generating or evaluating TTS voice samples.

## Default Report Fields

For each sample, record:

- provider
- model
- speaker / voice ID
- language
- exact input text
- output path
- sample rate
- audio duration
- generation time / RTF when available
- subjective notes: start noise, truncation, clipping, pronunciation, emotion, prosody

## Sample Text Guidance

### Chinese Short

Prefer a natural opening. Avoid ultra-short hard starts such as only `父皇` if testing first-token stability.

Example:

```text
请听这段音色测试：父皇，这是中文日常回复样本，语气自然、清晰、稳定。
```

### Chinese Medium

```text
父皇，这是中等长度的中文语音测试。孤会检查它的起音是否干净，句子之间是否自然停顿，长一点的内容是否仍然清晰稳定。
```

### English

```text
Your Majesty, this is an English voice sample. The goal is to test clarity, pacing, pronunciation, and whether the opening contains any click or noise artifact.
```

## Artifact Triage Workflow

When the user reports start noise:

1. Re-list the exact text that produced the audio.
2. Confirm whether the symptom is truncation, click/pop, hiss, model babble, or pronunciation issue.
3. Inspect first 50/200/500 ms with RMS and peak measurements.
4. Generate controlled variants:
   - original
   - lead silence only
   - fade-in only
   - trim 250 ms + fade
   - trim 500 ms + fade
   - neutral prefix + trim prefix
5. Send individual files directly for listening. Use zip only if the user asks for a bundle.
6. If variants fail, record it as provider/model quality issue in `provider-registry.md`.

## File Delivery Rule

For Telegram/audio UX:
- Directly attach the 1–5 most relevant audio files with `MEDIA:/absolute/path.wav`.
- Do not send only a zip for listening tests unless the user explicitly asks for a bundle.
- Include exact sample text in the message or a nearby summary file.

## Sanitization Rule

Before committing test notes to GitHub:
- Replace `/Users/<name>/` with `~/`.
- Replace private external disk labels with `/Volumes/<external-disk>/` unless the label is intentionally public.
- Never commit API keys, auth tokens, private chat IDs, or user-specific voice cloning samples.
