# 2026-06-30 PlayURL / Multi-P / ASR 配置锁定

## 适用场景

维护 `bilibili-video-analyzer` 的字幕/转写链路、B站 412 fallback、多 P 转录、ASR 模型选择时先读本文件。

## 锁定结论

B站无字幕视频主 fallback 固定为：

```text
Player API / WBI 字幕
→ yt-dlp 字幕 best-effort
→ PlayURL API 逐 P 直拉 DASH audio
→ H200 ASR（默认） / whisper / mlx-whisper 转录
→ yt-dlp 音频最后兜底
```

关键纠正：不要把 B站 412 默认归因为 cookie。BiliNote 的 `dm_img` patch 对 **in-process yt-dlp** 有价值，但 Hermes runtime 调 CLI 时不保护该路径。旧版 `jz-skills/shared/bilibili-video-analyzer` 的 PlayURL 直拉音频才是稳定 runtime fallback。

## 实测锚点

- 视频：`BV1MPjr6zEa8`，短链 `https://b23.tv/ua4UFbg`
- 结构：P1【双语】+ P2【纯享】
- 实测：PlayURL 逐 P 下载成功，`mlx-whisper` 合并转录成功
- 合并文件保留 `## P1` / `## P2` 标题

## 防回归测试锚点

P0 测试已锁定：

- `tests/test_bilibili_dm_patch.py`
- `tests/test_playurl_audio.py`
- `tests/test_multi_p_whisper_merge.py`
- `tests/test_result_json_failure_not_null.py`

验收重点：

- `download_audio(..., cid=P2)` 必须使用传入的 P2 cid，不能被 `get_video_info()` 覆盖回 P1。
- PlayURL 成功时不得触发 `yt-dlp` / `subprocess.run` 兜底。
- 多 P 合并必须保留 `## P1` / `## P2` 可见边界。
- 子步骤失败必须保留结构化 `status=failed` / `returncode` / `error`，不得塌缩为 `None`。

## ASR 模型配置

用户明确纠正：这是 ASR，不是 TTS。ASR 模型需要可配置、可切换。

环境变量接口：

```bash
BILI_ASR_PROVIDER=auto          # auto | h200_asr | whisper_cpp | mlx_whisper
BILI_ASR_ENDPOINT=http://172.16.27.10:8088/ASR/transcribe
BILI_ASR_MODEL=<repo-or-name>
BILI_ASR_MODEL_PATH=<local-path>
BILI_ASR_LANGUAGE=zh            # zh | en | auto
```

行为：

- `auto`：默认 H200 HTTP ASR → VoiceInk/whisper.cpp → mlx-whisper。
- `h200_asr`：只跑 SURGExZR H200 `/ASR/transcribe`，失败不降级本机 ASR。
- `whisper_cpp`：只跑 whisper.cpp，失败不降级 mlx。
- `mlx_whisper`：只跑 mlx-whisper，不触发 whisper.cpp/ffmpeg。
- `BILI_ASR_ENDPOINT` 覆盖默认 H200 ASR URL。
- `BILI_ASR_MODEL_PATH` 覆盖默认本地模型路径。
- `BILI_ASR_MODEL` 透传给 mlx-whisper repo/model。
- `BILI_ASR_LANGUAGE` 同时透传 H200 / whisper.cpp / mlx helper。
- 对外报告不得暴露本地绝对模型路径或内部 endpoint，只记录 engine/model 标识。

P1/P2 测试：`tests/test_asr_config.py`，必须 mock subprocess/filesystem/requests；默认链路还应有短/分钟级 H200 实测锚点。

## 三方执行模式

这类改动的推荐流程：

```text
Codex planning-only
→ CC(cctmux) 实施
→ Hermes 复跑测试和审查 diff
→ OMP 独立审核
→ OB 回写状态
```

注意：未获用户明确授权不得 commit。CC pane 中出现“commit 一下”或“继续更新 SKILL.md”等残留输入时，先清理/停止 session，不要让其自动执行。