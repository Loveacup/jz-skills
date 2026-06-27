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

## 2026-06-01 Voice Director MVP Edge Sample Set

Purpose: verify that the MVP can produce five reviewable scenario samples while keeping live default provider on Edge.

Common settings:
- provider: `edge`
- model: Edge TTS cloud voice
- speaker / voice ID: current profile default Edge voice
- language: `zh-CN`
- sample rate: provider default; generated as Telegram-compatible `.ogg` voice files
- generation time / RTF: not benchmarked in this sample pass
- subjective note: sample existence verified; detailed human listening review not yet recorded

Samples:

1. formal_report
   - exact input text: `父皇，此案已完成。核心模块已落盘，聚焦测试全部通过，默认语音供应商仍保持 Edge。`
   - output path: `~/.hermes/hermes-agent/tmp/voice_director_samples/formal_report.ogg`
   - duration: 9.22s
2. good_news
   - exact input text: `父皇，好消息：Voice Director 的路由演示已经选中合适音色，文档也已同步入库。`
   - output path: `~/.hermes/hermes-agent/tmp/voice_director_samples/good_news.ogg`
   - duration: 7.73s
3. warning
   - exact input text: `父皇，请留意：本次实现尚未接入生产合成链路，当前只是安全的规划、路由、编译与记忆回写闭环。`
   - output path: `~/.hermes/hermes-agent/tmp/voice_director_samples/warning.ogg`
   - duration: 10.45s
4. comfort
   - exact input text: `父皇不必忧心。默认 TTS 没有被切换，Qwen 本地模型仍只作为后备方案保留。`
   - output path: `~/.hermes/hermes-agent/tmp/voice_director_samples/comfort.ogg`
   - duration: 8.24s
5. technical_explanation
   - exact input text: `技术说明：系统先生成 TTSPlan，再根据 manifest 评分选择 VoiceRoute，最后由 Edge adapter 编译为 SSML 样式文本。`
   - output path: `~/.hermes/hermes-agent/tmp/voice_director_samples/technical_explanation.ogg`
   - duration: 11.67s

## Sanitization Rule

Before committing test notes to GitHub:
- Replace `/Users/<name>/` with `~/`.
- Replace private external disk labels with `/Volumes/<external-disk>/` unless the label is intentionally public.
- Never commit API keys, auth tokens, private chat IDs, or user-specific voice cloning samples.
