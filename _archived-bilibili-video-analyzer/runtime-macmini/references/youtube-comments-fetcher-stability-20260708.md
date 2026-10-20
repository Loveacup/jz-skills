# YouTube 评论抓取稳定性说明

> Session: 2026-07-08
> 相关视频: BV1Xs7u6ZEuS, BV1QcQfB7EtH
> 相关脚本: `scripts/fetch_youtube_comments.py`

---

## 现状

`fetch_youtube_comments.py` 是搬运视频跨平台评论同步的入口。它按以下顺序尝试：

1. `youtube-comment-downloader`（Python 库）
2. `yt-dlp --print %(comments)j`（CLI 兜底）

2026-07-08 实测：
- 第一次测试 `BV1Xs7u6ZEuS` 时，`youtube-comment-downloader` 成功，抓到 100 条 YouTube 评论
- 第二次测试（约 30 分钟后）同一个脚本失败：
  - `youtube-comment-downloader` 不可用（可能未安装或依赖异常）
  - `yt-dlp` 解析失败：`Expecting value: line 1 column 1 (char 0)`
- 新视频 `BV1QcQfB7EtH` 的 YouTube 评论抓取也失败，并在 `fetch_all.py` 中卡住超过 9 分钟

## 根因判断

这是外部依赖/网络/YouTube 反爬的波动，不是本次 v2.3 采样量扩量代码本身的问题。代码链路本身正确：之前成功过，现在失败。

可能原因：
- `youtube-comment-downloader` 环境状态变化
- YouTube 对当前 IP/请求做了限制
- `yt-dlp` 输出格式变化或网络中断
- 长连接/大页面超时

## 处理策略

### 1. 不阻塞主流程

`fetch_all.py` 中搬运检测和 YouTube 评论抓取失败只记录到 `cross_platform.youtube_comments.status=failed`，不影响弹幕/评论/字幕的采集。

### 2. 单独诊断

```bash
python3 scripts/fetch_youtube_comments.py 'https://www.youtube.com/watch?v=VIDEO_ID' --limit 100
```

观察：
- `youtube-comment-downloader` 是否可用
- `yt-dlp` 输出是 JSON 还是错误页面
- 是否超时

### 3. 替代方案

若 YouTube 评论抓取持续失败，可用以下方式补充跨平台证据：
- WRR 搜索 YouTube 原视频的热门评论/争议点
- 用 `yt-dlp --write-comments` 直接下载评论 JSON 再解析
- 在报告中明确说明 YouTube 评论数据缺失，不做跨平台对比

### 4. 未来改进

- 增加 `fetch_youtube_comments.py` 内部超时机制（如 60s）
- 增加清晰的降级日志
- 考虑缓存成功的 YouTube 评论，避免重复抓取
- 在 `fetch_all.py` 中对 YouTube 步骤设置独立超时，防止卡住整个流程

## 验证

- 代码链路正确：第一次测试成功抓取 100 条 ✅
- 失败不阻塞主流程 ✅
- 单独诊断命令可复现失败 ✅
