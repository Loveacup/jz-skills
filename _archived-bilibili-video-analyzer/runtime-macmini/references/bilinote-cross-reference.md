# BiliNote 交叉参考 · 可借鉴的技术模式

> 2026-06-29 深度分析 [JefferyHcool/BiliNote](https://github.com/JefferyHcool/BiliNote) 后的技术吸收笔记。
> BiliNote 是 Full-Stack AI 视频笔记工具（FastAPI + React + Tauri），我方是 CLI skill。
> 两者定位不同，但 BiliNote 在 B站 数据采集层有几个我们可直接吸收的模式。

---

## 1. yt-dlp dm_img 绕过补丁（🔴 最高优先）

### 问题

2026-06 起 B站 `x/player/wbi/playurl` 网关要求浏览器指纹参数：
`dm_img_list` / `dm_img_str` / `dm_cover_img_str` / `dm_img_inter` / `web_location`。
yt-dlp 当前版本不发送这些参数 → HTTP 412 → 下载失败。

我们目前的 fallback 是 PlayURL API → ffmpeg 转 WAV → mlx-whisper 转录，**成本高（~60s/视频）**。

### BiliNote 解法

`backend/app/downloaders/bilibili_dm_patch.py` — monkey-patch yt-dlp 的 `BilibiliBaseIE._download_playinfo`：

```python
def build_dm_img_params() -> dict:
    return {
        'web_location': 1550101,
        'dm_img_list': '[]',
        'dm_img_str': base64.b64encode(
            ''.join(random.choices(string.printable, k=random.randint(16, 64))).encode()
        )[:-2].decode(),
        'dm_cover_img_str': base64.b64encode(
            ''.join(random.choices(string.printable, k=random.randint(32, 128))).encode()
        )[:-2].decode(),
        'dm_img_inter': '{"ds":[],"wh":[6093,6631,31],"of":[430,760,380]}',
    }

def apply_bilibili_dm_img_patch() -> bool:
    """在 wbi 签名前注入 dm_img 参数。幂等、防御式。"""
    from yt_dlp.extractor.bilibili import BilibiliBaseIE
    original = BilibiliBaseIE._download_playinfo
    if getattr(original, '_bili_dm_patched', False):
        return True

    def _patched(self, bvid, cid, headers=None, query=None):
        merged_query = {**build_dm_img_params(), **(query or {})}
        return original(self, bvid, cid, headers=headers, query=merged_query)

    _patched._bili_dm_patched = True
    BilibiliBaseIE._download_playinfo = _patched
    return True
```

**关键细节**：
- 必须在 wbi 签名**之前**注入（签名覆盖 query params）
- `dm_img_str` 和 `dm_cover_img_str` 用随机 base64 字符串（模拟浏览器指纹）
- 幂等设计：多次调用只 patch 一次
- 防御式：import 失败不崩溃，只 log warning

### 对我方的建议

在 `fetch_all.py` 或 `fetch_subtitle_auto.py` 启动时调用 `apply_bilibili_dm_img_patch()`。
约 40 行代码，零依赖，可大幅减少 whisper fallback 的使用频率。

---

## 2. B站直连 Player API 字幕抓取（替代 yt-dlp 方案）

### 问题

我们依赖 `yt-dlp --cookies-from-browser chrome` 提取字幕，失败点：
- Chrome cookie 提取失败（DB 锁定 → 0 cookies）
- 多 P 视频 SRT 覆盖（CQI P0 已记录）
- 需要 Chrome 在运行中

### BiliNote 解法

`backend/app/downloaders/bilibili_subtitle.py` — 直接调 B站公开 API：

```
1. extract_video_id(URL) → BV号
2. GET /x/web-interface/view?bvid=... → cid（支持 p 参数分 P）
3. GET /x/player/wbi/v2?bvid=...&cid=... → 字幕轨列表
4. 优先级排序：人工中文(type=1,ai_type=0) > AI中文 > 任意非空
5. GET subtitle_url（B站已签好 auth_key）→ JSON body → TranscriptResult
```

**优势**：
- 不需要 yt-dlp，不需要下载音视频
- 零临时文件（字幕直接解析 JSON，不写 SRT）
- 无多 P 覆盖问题（分 P 取不同 cid）
- 轻量：3 次 HTTP 请求，<3 秒
- AI 字幕需要 SESSDATA cookie；人工字幕公开可用

**浏览器插件版**（`BillNote_extension/src/logic/bilibili-subtitle.ts`）：
- 在浏览器环境里 `fetch` 自动带 .bilibili.com cookie
- 用户无需手动配置 SESSDATA
- 与后端 Python 版行为完全对齐

### 对我方的建议

在 `fetch_subtitle_auto.py` 中把这个作为**第一优先路径**：
1. 直接 API → 成功则返回
2. yt-dlp cookie → 成功则返回
3. yt-dlp + dm_img patch → 成功则返回
4. PlayURL + mlx-whisper（当前最重 fallback）

---

## 3. YouTube 原视频评论同步（用户明确需求）

### 问题

B站搬运/中配视频的评论区常冷清（0-3 条），但 YouTube 原视频评论区有实质讨论。
用户要求："评论最好能同步 youtube 原视频"（CQI P2-3）。

### BiliNote 架构参考

BiliNote 的跨平台设计：
- `Downloader` 基类：`download()` / `download_video()` / `download_subtitles()`
- 各平台独立实现：`BilibiliDownloader` / `YoutubeDownloader` / `DouyinDownloader` / `KuaishouDownloader`
- YouTube 路径：`YoutubeDownloader.download_subtitles()` 走 `YouTubeSubtitleFetcher`（InnerTube API 直拉）

虽然 BiliNote 也没有 YouTube 评论抓取，但其跨平台下载器抽象提供了清晰的扩展点。

### 实现方案

当 B站视频简介含 `youtube.com/watch?v=...` 或 `youtu.be/...` 时：

```bash
# 方案 A：yt-dlp --write-comments
yt-dlp --write-comments --skip-download -o '/tmp/yt_%(id)s' '<youtube_url>'
# → 输出 /tmp/yt_<video_id>.info.json（含 comments 字段）

# 方案 B：YouTube Data API（需要 API key，限额度）
# 不推荐，yt-dlp 足够
```

**提取评论后的处理**：
- Phase 1 数据采集：新增可选步骤 "YouTube 原视频评论"
- Phase 2 分析：在 §2.5 Comments Analysis 下增加"跨平台评论对比"子节
- 报告 §0 Meta：注明数据来源差异

### 触发条件

B站视频标题/简介含以下任一关键词时自动触发：
- `youtube.com/watch?v=`
- `youtu.be/`
- 「来源」「原视频」「搬运」「转载」「中配」「中文配音」

---

## 4. 其他可借鉴的模式

### 4.1 RequestChunker 长文本分块

BiliNote 的 `request_chunker.py` 实现了自适应分块：
- 二分搜索找最优切割点（`_split_segment_to_fit`）
- token 预算感知（`max_bytes`）
- 图片 URL 均匀分配算法

**适用场景**：超长视频（>1.5h）转录文本超出 LLM 上下文时。

### 4.2 Cookie 持久化（Netscape 格式）

BiliNote 的 `CookieConfigManager` 将 B站 cookie 写入 Netscape 格式文件：
```python
# .bilibili.com  TRUE  /  FALSE  0  SESSDATA  <value>
```
yt-dlp 通过 `cookiefile` 参数读取，比 `--cookies-from-browser chrome` 更稳定（不依赖 Chrome 状态）。

### 4.3 原子状态文件写入

```python
temp_file = status_file.with_suffix('.tmp')
with temp_file.open('w') as f:
    json.dump(data, f)
temp_file.replace(status_file)  # 原子 rename
```

比直接写入更安全（防止写入中断导致文件损坏）。

### 4.4 笔记风格系统

BiliNote 有 9 种风格：精简/详细/学术/教程/小红书/生活向/任务导向/商业/会议纪要。
其中「教程笔记」风格值得我方增加——教程视频更适合 step-by-step + code block 格式。

---

## 5. 我方独有优势（BiliNote 没有的）

| 能力 | 说明 |
|:---|:---|
| Depth Quality Gates | verify_report.py 硬闸门，G1/G3/G4/G5/G7 定量门槛 |
| 弹幕情绪分析 | 6 类情绪量化 + 文化梗识别 |
| 三层剖析 | Explicit / Implicit / Meta-narrative |
| 实体检测 → 自动 Deep Dive | Phase 2 跨段落实体扫描 |
| 批判审视（G7） | 价值点+局限+行动项 |
| 多视频合并 | 同系列/同 UP 主统一报告 |
| Obsidian 原生集成 | YAML frontmatter + vault 路径约定 |
