# YouTube 无字幕时的分段 ASR 恢复

适用：YouTubeAdapter 返回 `metadata_only`，`yt-dlp --list-subs` 同时确认没有人工字幕和自动字幕，但媒体可完整下载，且需要带时间范围的正式视频笔记。

## 原则

- `metadata_only` 不是可写正式笔记的充分证据；必须恢复完整音频转录并重新建立 `ready` 等价证据。
- 先验证下载音频的 `ffprobe` 时长与视频元数据时长一致（容差按平台/格式判断）。不完整媒体不得用于正式报告。
- 不把单块 ASR 的全文当作带时间戳转录。若 ASR API 只返回 `text`，按固定时长切块转录，时间戳仅标为“段落定位/约 N 分钟边界”。
- 专名易被 ASR 误识别；报告中用外部可核验来源统一影片、人名、术语拼写，并声明该限制。

## 可复现流程

```bash
# 1) 字幕预检：无人工/自动字幕才进入音频恢复
yt-dlp --list-subs "$URL"

# 2) 下载单视频音频并核对完整时长
yt-dlp --no-playlist -f 'bestaudio/best' -x --audio-format m4a -o '/tmp/VIDEO_ID.%(ext)s' "$URL"
ffprobe -v error -show_entries format=duration,size -of json /tmp/VIDEO_ID.m4a

# 3) 每 120 秒切块（无需重编码），逐块调用已配置 ASR
mkdir -p /tmp/VIDEO_ID_chunks
ffmpeg -hide_banner -loglevel error -i /tmp/VIDEO_ID.m4a \
  -f segment -segment_time 120 -c copy /tmp/VIDEO_ID_chunks/chunk_%03d.m4a
for f in /tmp/VIDEO_ID_chunks/chunk_*.m4a; do
  # 调用当前环境配置的 ASR；输出需按块单独保存
  asr-command "$f" > "${f%.m4a}.json"
done
```

## 写作与验收

1. 用 `[00:00]、[02:00]…` 的块起点组织主张证据，禁止伪造秒级引语。
2. 元数据区明确：原平台无字幕、音频完整性已确认、时间戳为分段近似定位。
3. 正式笔记中只保留最终报告；原始音频、分块、ASR JSON 留在临时空间，除非用户明确要求源材料。
4. 在 Writer 前把恢复后的转录、分段和 provenance 写回 EvidenceBundle，状态设为 `ready`；不要只绕过状态检查。
5. 运行报告结构/发布门禁，人工检查专名、时间范围、长转录泄漏和不受支持的事实。
