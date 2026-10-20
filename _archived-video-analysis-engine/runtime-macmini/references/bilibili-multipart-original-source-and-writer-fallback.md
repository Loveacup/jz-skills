# Bilibili 多 P、原始来源与 Writer 降级

## 触发信号

- B 站 view API 的 `pages[]` 出现 `trimmed` / `original_with_subs` 等多 P 版本；
- 视频简介提供 YouTube 原片；
- B 站官方字幕采集卡住，但原片能取得完整自动字幕；
- `generate_report.py --writer-provider cli` 只输出启动行、无 `RESULT_JSON`、无 Markdown 或无可验收错误。

## 先分版本，再采集

1. 用 B 站 view API 记录每个 P 的 `cid`、`part`、`duration`；不要把 BV 总时长当作单个内容的时轴。
2. 若简介指向原片，先取其 metadata 与字幕可用性。只在确认该 P 与原片对应时，才以原片作为内容证据。
3. 用三源完整性门：B 站目标 P 时长、原片 metadata 时长、字幕末段/媒体时长。差异需不超过 `max(5 秒, 2%)`。
4. 正式笔记的 frontmatter 和正文必须标出：采用哪一 P、原片链接、精简版是否被排除。不得混用精简版与原版时间锚点。

## 单 P 拼接与原片对应

单 P 也可能在原教程前添加介绍。必须先顺读完整转录，定位问候、结语、主题重启和示例代码变化；不得只按标题认定来源。

1. 从原声中的独特教程名、示例组合或官方文章名查找原片候选。第三方摘要只提供检索线索。
2. 对候选读取发布频道、标题、发布日期、时长及简介章节。可用：
   ```bash
   yt-dlp --skip-download --no-warnings --socket-timeout 20 --retries 0 \
     --print '%(title)s | %(channel)s | %(upload_date)s | %(duration)s' "$ORIGINAL_URL"
   yt-dlp --skip-download --no-warnings --socket-timeout 20 --retries 0 \
     --print '%(description)s' "$ORIGINAL_URL"
   ```
3. 用工具计算目标 P 总时长减去疑似介绍时长，再与原片时长比较。必须同时核对章节顺序、具体例子与原声内容；时长相等不能单独证明同源。
4. 只有元数据与内容对应、未做音视频比对时，必须写成“内容、顺序和时长相对应”，不得写成逐帧验证。前置介绍的出处和讲者身份必须单独取证，不能由后段频道推定。
5. 正式笔记继续使用目标 P 的时间轴。引用原片时间时必须标出来源；只有确认连续片段及固定偏移后，才能换算时间，不能把固定偏移用于中途剪辑过的片段。

## 原片自动字幕的安全交接

- 保存原始 VTT/SRT，只把去标签、去连续累积重复后的带时间戳片段交给分析器。
- 校验：片段数、字符数、首尾时间、最大终点；字幕末段显著早于目标 P 时长时仍是 partial evidence。
- 评论、弹幕为空时明确写数据边界，不从标题或简介推测受众反馈。

## Writer 失败关闭

`--writer-provider cli` 可能间接调用 OMP。OMP 的受控审计契约不是通用文稿生成通道；不可把无终态、空输出或只有启动行的调用视为生成成功。

1. 先检查产物文件、`RESULT_JSON`、退出码和 Markdown 是否真实存在。
2. 任一缺失即判为 Writer failed；不要用同一路径反复重试，也不要以 skeleton/metadata 填充正式稿。
3. 对单篇正式视频笔记，可降级为人工证据写作：以冻结的时间戳字幕为唯一视频事实底座，明确区分视频主张、外部核对和推断。
4. 必须按入口选定的布局验收。固定章节稿运行 `verify_report.py <report> --mode <selected-mode> --claim-first` 与 `verify_publishable_report.py <report>`，不得默认强制 `full`。`editorial` 稿执行 `references/interview-editorial-workflow.md` 的原命题与正文双向核对，不套用旧固定章节门。两种布局都必须检查 Vault frontmatter、真实双链目标、脚注定义、时间锚范围及私密信息；最后一次内容或日志修正后，再运行 `qmd update && qmd embed` 并检索标题。

## 不要做

- 不要因为 B 站采集器已开始字幕步骤就把它当作 `ready`；停滞不是成功。
- 不要用原片描述、评论、弹幕补齐缺失时段。
- 不要把 OMP 的沉默或部分文本视为可发布 Writer 产物。
