# PlayURL 逐 P 音频直拉 fallback 锁定记录（2026-06-30）

## 触发场景

当 B站视频没有官方/AI 字幕，且 `yt-dlp` CLI 对 B站音频/字幕路径返回 HTTP 412 时，**不要默认诊断为 cookie 问题**。cookie 可以辅助登录态字幕/评论，但不是 412 的通用解药。

## 锁定链路

```text
Player API / WBI 字幕
→ yt-dlp 字幕 best-effort
→ PlayURL API 逐 P 直拉 DASH audio
→ whisper / mlx-whisper 转录
→ yt-dlp 音频最后兜底
```

## 原因

- BiliNote 的 `bilibili_dm_patch.py` monkey-patch 的是 in-process `yt_dlp.extractor.bilibili.BilibiliBaseIE`，对 shell 调用的 `yt-dlp` CLI 不生效。
- 旧版 `jz-skills/shared/bilibili-video-analyzer` 的稳定实践是 PlayURL/DASH audio 直拉，再交给 whisper。
- 实测 `BV1MPjr6zEa8`（Supacode 视频，P1 双语 + P2 纯享）时，cookie 文件存在且新鲜仍可能 412；PlayURL API 逐 P 拉音频成功，并通过 `mlx-whisper` 合并转录。

## 实现要求

- `download_audio(bvid, output_path, cid=None)` 必须尊重传入的 `cid`；多 P 视频不能在函数内部重新取 P1 覆盖 P2。
- 多 P fallback 应遍历 `get_video_info(bvid)['pages']`：
  - 每个 `page.cid` 单独下载音频；
  - 每 P 单独转录；
  - 合并文本必须保留 `## P1` / `## P2` 等可读 heading。
- trace/log 要能看出进入了 PlayURL direct audio 路径，避免未来误判为 cookie/yt-dlp 路径。

## 防回归测试清单

- `tests/test_bilibili_dm_patch.py`：required dm keys、patch 幂等、dm params 在 `_sign_wbi` 前进入 query、caller query 保留；不做网络。
- `tests/test_playurl_audio.py`：`download_audio(..., cid=P2)` 使用 P2 cid，不覆盖为 P1；mock HTTP，不下载真实文件。
- `tests/test_multi_p_whisper_merge.py`：mock 两个 pages、mock download/transcribe，断言合并输出包含 `## P1` / `## P2`。
- `tests/test_result_json_failure_not_null.py`：`fetch_all.process_step` 失败保留 `status=failed` / `returncode` / `error`，不塌缩为 `None/null`。

## 不要照搬

不要把 BiliNote 的 FastAPI/DB/provider 管理搬进 Hermes skill；吸收其模块边界和测试思路即可。Hermes runtime 继续保持脚本化、RESULT_JSON、可诊断 trace。