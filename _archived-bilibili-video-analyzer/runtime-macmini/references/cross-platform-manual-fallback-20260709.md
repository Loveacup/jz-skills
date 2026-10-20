# 跨平台搬运/中配视频手动回退工作流（2026-07-09）

当 `fetch_all.py --report` / `generate_report.py` 在搬运/中配视频上因 YouTube 评论抓取或 CLI writer 超时而失败时的手动 fallback 路径。

## 触发场景

- `fetch_all.py <BV> --report` 卡在“扫描简介中的 YouTube 链接...” / `fetch_youtube_comments.py` 超过 600s 无返回。
- `fetch_all.py <BV>` 同样卡在 YouTube 评论步骤，即使不加 `--report` 也超时。
- `generate_report.py --input <fetch_all.json> --writer-provider cli` 超过 300s 无输出，进程冻结。

以上情况多发生在 YouTube 评论/字幕服务或 CLI writer 调用外部 LLM 时网络/响应延迟高的情况下。

## 手动回退步骤

1. **分段获取 B站数据**（避开 YouTube 评论步骤）

   ```bash
   python3 scripts/fetch_subtitle_auto.py <BV号>
   python3 scripts/fetch_danmaku_v2.py <BV号> 1000 --stratify
   python3 scripts/fetch_comments.py <BV号> --count 150 --strategy mixed
   ```

   这三步通常不依赖 YouTube，能稳定拿到 B站字幕、弹幕、评论。

2. **获取 YouTube 原片字幕**

   先检查可用字幕：

   ```bash
   yt-dlp --list-subs '<youtube_url>'
   ```

   若有人工字幕，优先用 `--write-subs --sub-lang "zh,en,ai-zh"`；若只有自动字幕，用：

   ```bash
   yt-dlp --write-auto-subs --sub-lang 'en' --skip-download --convert-subs srt \
     -o '/tmp/{BV号}_yt' '<youtube_url>'
   ```

   输出 `/tmp/{BV号}_yt.en.srt`。

3. **清理 YouTube 自动字幕**

   YouTube 自动生成的 SRT 存在特殊结构：每个句子片段通常被重复 3 次（时间块重叠），导致直接转文本会得到大量重复。清理方式：

   - 按 `start` 时间去重：同一 start 时间保留最长文本。
   - 对连续重复文本进行 rolling-window 去重（检测 5-15 词重复）。
   - 按 25-30s 合并成段落，得到干净的英文原片 transcript。

   最终产物应作为**主分析源**，因为 YouTube 原片字幕比 B站中配 ASR 更完整、术语更准确。

4. **单独快速抓取 YouTube 评论**（限制数量，避免超时）

   ```bash
   python3 scripts/fetch_youtube_comments.py '<youtube_url>' --limit 20
   ```

   如果仍超时，可再降到 `--limit 10` 或 `--limit 5`，或放弃 YouTube 评论，改用 WRR 搜索 YouTube 视频相关讨论。

5. **手工编写 8-section 报告**

   - 以 YouTube 原片字幕为**主分析源**。
   - 以 B站 H200 ASR 中配字幕作为**中文表达和术语交叉核对**。
   - 在 §0 和 §8 明确说明两种数据源及其差异。
   - 在 §4 增加“B站中配 vs YouTube 原片”模块，说明术语、完整性、社区反馈差异。
   - 对 YouTube 原片可验证声明（如 Comfy Cloud MCP 能力、定价、版本）用官方/一手资料做 WRR grounding 核查。

6. **质量门与落库**

   - 先用 `scripts/verify_report.py` 校验全量/精简版质量门。
   - 通过后用 `cp` 而非 `write_file` 保存到 Obsidian vault。
   - 保存后再次 `verify_report.py` 复验最终路径。

## 注意事项

- **术语识别偏差**：中配 H200 ASR 常把 ComfyUI 识别为“Confi UI”、把 Claude 识别为其他近似音。必须在 §8 附录中提供“术语对照表”。
- **时间戳差异**：H200 ASR 通常无精确逐句时间戳，YouTube 自动字幕时间戳较准确。报告中的 `[mm:ss]` 链接应以 YouTube 原片字幕为准。
- **评论缺失**：B站评论为 0 时，YouTube 评论成为唯一的社区反馈来源，需在 §2.5 明确说明样本来源。
- **数据隐私**：YouTube 原片字幕和 B站 H200 ASR 转录可能涉及第三方版权，临时文件用完后应及时清理。
