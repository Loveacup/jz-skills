# Trigger Tests

Use these cases when changing `description` or the decision tree.

## Should Trigger

1. "测试一下 Qwen3-TTS 的中文音色"
2. "把 Qwen3-TTS 暂时作为后备 tts 使用"
3. "Hermes 当前 TTS provider 是什么？"
4. "edge-tts 和本地 Qwen TTS 哪个适合默认？"
5. "这段语音开头有杂音，帮我排查"
6. "给 Serena/Vivian 生成几条试听音频"
7. "把新的 TTS benchmark 结果记到 skill"
8. "新增一个 command 类型的 Hermes TTS provider"
9. "不要切默认，只作为 fallback"
10. "比较这几个 TTS provider 的延迟和音质"

## Should Not Trigger

1. "把这个会议录音转文字" — use transcription skills.
2. "总结这段音频内容" — use audio/video analysis or transcription.
3. "做一个音乐生成 prompt" — use songwriting/music skills.
4. "修复 MP3 文件元数据" — generic media/file task.
5. "朗读一下这段文字给我听" — simple TTS tool invocation may not need provider management unless quality/config changes are requested.
6. "安装 Hermes gateway" — use hermes-agent.
7. "配置 Whisper STT" — STT, not TTS.
8. "搜索最新 TTS 论文" — use web-research-router/arxiv unless the output is a deployment decision.
