# Bilibili 媒体时长完整性检查与截断恢复

## 触发信号

采集阶段出现任一情况时启用：

- `yt-dlp` 返回 HTTP 412，但 Bilibili view API、评论或弹幕仍可读；
- `x/web-interface/view` 的 `duration` 与实际下载媒体、浏览器 `<video>.duration` 不一致；
- 弹幕最大时间明显超过媒体时长；
- 视频页面标称完整时长，但公开 playurl 只返回较短 progressive MP4。

## 为什么这是发布阻断项

拿到一个可播放文件或非空 ASR 文本，只证明“有媒体”，不证明“媒体完整”。若元数据标 24:34，而 `ffprobe` 与播放器都只有 11:25，基于该文件生成的报告只能覆盖前半段。不得把 `has_transcript=true`、非空转录或静态门 PASS 写成完整视频分析。

## 三源完整性门

正式 Writer 前至少比较：

1. **权威元数据时长**：`x/web-interface/view?bvid=...` 的 `data.duration`，并记录 title / owner / cid。
2. **实际媒体时长**：下载后用 `ffprobe` 读取；浏览器恢复时同时读取 `<video>.duration`。
3. **内容时间上界**：弹幕最大 `time_sec`、章节/评论中明确时间点（仅作异常检测，不作为事实内容证据）。

建议判定：实际媒体时长与元数据差异超过 `max(5 秒, 2%)`，或弹幕时间上界超过实际媒体时长 30 秒以上，即标记 `truncated_media`，阻断正式发布。

## 412 后的安全恢复顺序

1. 先调用 Bilibili view API确认 bvid/cid/title/owner/duration，元数据不能替代内容证据。
2. 尝试带现代 UA + Bilibili Referer + cookie 的 `yt-dlp`。
3. 若 `yt-dlp` 仍 412，可用公开 `x/player/playurl` / WBI playurl 取得候选媒体；立即下载并 `ffprobe`，不要因 HTTP 200 就认定完整。
4. 检查浏览器实际 `<video>.duration` 与 `currentSrc`；若浏览器也只播放短版本，说明不是单纯下载器故障。
5. 运行 recovery 搜索寻找同一 BV/精确标题的镜像或字幕；只接受可核验的同源完整内容。
6. 若仍截断，进入授权恢复：请求用户在可读取 cookies 的浏览器登录，或提供本地视频文件。不要要求用户交出 cookie/SESSDATA 文本。

## 部分转录的处理边界

- 可以生成**明确标注覆盖区间**的临时摘要，例如“仅覆盖 0:00–11:25”。
- 不写入正式 Obsidian 视频笔记，除非用户明确要求保留部分稿。
- 不使用视频简介、评论或弹幕补写缺失后半段；它们只能用于诊断、受众信号和待核验线索。
- 最终回复应尽早说明：标称时长、实际时长、已完成步骤、阻塞点、是否写入 Vault。用户追问进度时先给这四项，不等全部恢复尝试结束。

## 验收记录

正式发布前在采集日志中保留：

- metadata duration
- ffprobe duration
- browser duration（如使用浏览器恢复）
- danmaku max timestamp（如可用）
- 完整性 verdict：`complete | truncated_media | unknown`

只有 `complete` 才能进入正式 Writer。