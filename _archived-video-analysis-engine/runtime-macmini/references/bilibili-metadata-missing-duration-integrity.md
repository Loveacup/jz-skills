# Bilibili 元数据缺失与时长完整性核验

## 触发

`fetch_all.py` 完成了字幕、评论或弹幕，但聚合 `RESULT_JSON` 的顶层 `info` 为 `null`；Writer 因而缺标题、作者或 `duration_seconds`。同时，H200 ASR 可能成功，却没有可供复核的本地音频资产。

不要把“ASR 非空”当作完整媒体证据，也不要拿评论/弹幕替代元数据。

## 恢复步骤

1. 调用 Bilibili 官方 View API：

```bash
curl --fail --silent --show-error \
  -A 'Mozilla/5.0' \
  'https://api.bilibili.com/x/web-interface/view?bvid=<BVID>' \
  > /tmp/<BVID>_view.json
```

仅从 `data.title`、`data.owner.name`、`data.duration`、目标 `data.pages[]` 补齐身份和声明时长。不要把 API 元数据充当正文论据。

2. 用目标 P 的 `cid` 和公开 PlayURL API 下载低码率 DASH 音频到临时文件，然后用 `ffprobe` 获取实际时长。可复用 `fetch_subtitle_auto.py` 的 `download_audio(bvid, output_path, cid=...)` 与 `check_video_duration()`，以避免手写 Referer、CDN Range fallback 和流选择逻辑。

3. 按 `max(5s, 2%)` 比较 `data.duration` 与 `ffprobe` 时长。超过阈值即 `truncated_media`，阻止正式 Writer；通过后删除仅用于核验的临时音频。

4. 若 ASR 是单段、没有细粒度时间戳，按 `bilibili-single-chunk-asr-salvage.md` 走 condensed 手工重写：承认时码边界，不按文本长度推测时间，不生成伪 `0:00` 链接。

## 验收

- 页面声明时长、实际音频时长、ASR 覆盖状态均已记录；
- 正式笔记只暴露证据方法和边界，不暴露 `/tmp`、`.p6r-cache`、模型或端点路径；
- 最终 Vault 文件仍须跑 `verify_report.py --mode condensed --claim-first` 与 `verify_publishable_report.py`。
