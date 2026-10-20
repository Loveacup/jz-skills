# Bilibili fetch → Writer 交接检查

## 适用场景

`fetch_all.py` 已成功取得 H200 / Whisper 转录，但随后使用 `generate_report.py --bvid BV...` 时，Writer 却显示 `has_transcript=false`、标题/作者为空，或生成骨架稿。

## 根因

`fetch_all.py` 可能把转录保存到 skill 的 `.p6r-cache/{BV}_subtitle_whisper.txt`；而 `generate_report.py --bvid` 的重建路径只查 `/tmp/{BV}_subtitle_whisper.txt`。仅凭 `fetch_all` stdout 显示字幕成功，不代表 `--bvid` 重建时已经接收到字幕。

## 稳妥交接

优先保留并通过 `--input` 传入完整的 `fetch_all` RESULT_JSON，使 `subtitle.txt_path` 原样进入 Writer。

若只能使用 `--bvid`：

1. 检查 fetch 结果里的 `subtitle.txt_path`。
2. 将该文件复制到 `/tmp/{BV}_subtitle_whisper.txt`（复制，不移动，不覆盖正式资产）。
3. 再运行 `generate_report.py --bvid ... --writer-provider cli`。
4. 从 Writer 的 RESULT_JSON 核验：
   - `has_transcript=true`
   - `duration_seconds > 0`
   - `claim_bundle_stats.claims_count > 0`
   - 正式输出路径已写入

## 发布后人工 QA

发布门通过仍不等于知识资产可用。必须打开最终 Markdown，至少检查：

- 标题和作者不是空值；
- YAML 符合当前 Vault 的 `AGENTS.md`，而不是 skill 内旧目录/旧标签示例；
- 不暴露 `/tmp/`、本地模型路径或私有端点；
- 删除 `_目的：..._` 等模板指令残留；
- 知识图谱不是无语义的词项共现链；
- 评论/弹幕样本稀疏时明确写数据边界；
- 行动项具体、可验证，不是 `_暂无可抽取行动项_`；
- 最后重新运行 `verify_report.py` 与 `verify_publishable_report.py`。

## 判断信号

若首次正式生成同时出现“缺少必需章节”“§1 missing”“claims_count=0”“字幕不可用”，先怀疑证据交接，不要靠切换 depth profile 重试掩盖根因。