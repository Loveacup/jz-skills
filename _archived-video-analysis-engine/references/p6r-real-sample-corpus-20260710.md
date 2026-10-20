# P6-R 真实样本 corpus 框架（2026-07-10）

## 目标

P6-R 把“真实视频样本验证”从单条、一次性的 `--real-sample` smoke，收敛为一个**可审计、显式执行、不会伪造 gold** 的 corpus 框架。

它解决三件事：

1. 正式 `B站笔记_*.md` 使用 `--writer-provider none` 时，在渲染前 fail fast；不再花完生成成本才因 skeleton 被拒绝。
2. `run_quality_gate.py --publishable` 使用 `evaluate_publishable_report(markdown, report)`，因此 P6-A `P0_CLAIM_EVIDENCE_SCORE`、P6-B1 `P0_VIDEO_EVIDENCE_USAGE`、零弹幕声明 gate `P0_SPARSE_SOCIAL_EVIDENCE` 与时间分辨率 gate `P0_TRANSCRIPT_TIME_RESOLUTION` 进入真实 release 路径。
3. `references/p6r-corpus-manifest.json` 管理 10 条跨题材真实 BVID 候选，但不把旧笔记、fixture 或未复跑结果冒充为 gold。

## 非目标

- 不默认下载 Bilibili 内容；没有 `--execute` 时不读取 sample input、不运行 report renderer、不调用 LLM。
- 不自动把 `qa_passed` 升级为 `accepted_gold`。
- 不因为候选来自旧正式笔记，就假定其当前 pipeline output 已经通过。
- 不把 P6-A/B1 误说成 claim 的语义蕴含或事实真实性判定；P6-B2 仍需 human calibration 后再做。

## Manifest 合同

顶层 `schema_version` 固定为 `1`，每个 sample 必须有：

- `id` / `bvid` / `category`；
- `source_note.path` / `source_note.title`：可追溯候选来自哪一篇 Obsidian 正式笔记；
- `input.fetch_all_json_path` / `cache_status`：本地可复跑输入的状态；
- `run`：本轮运行与 summary 的记录；
- `rubric`：人工审核状态与证据。

初始 manifest 包含 10 条 `candidate`，涵盖技术教程、Agent/架构、商业长访谈、事实核查、文化评论与游戏攻略。它们都明确标记 `cache_status=missing`、未运行、未人工验收。

状态机：

```text
candidate → input_ready → generated → qa_passed | qa_failed
                                      ↓
                                review_pending → accepted_gold | rejected | retired
```

`accepted_gold` 至少需要非空的 `reviewed_by`、`reviewed_at`、`verdict_source`。blocking lane 还要求当前 `fetch_all` input 和运行 summary 文件都存在；`qa_passed` 永远不能单独进入 blocking lane。

### 私有证据缓存

真实 `fetch_all` payload 含转录、评论与运行数据，不写入 Obsidian，也不提交 Git。要把候选升为 gold 时，input 必须位于项目的 `.p6r-cache/`（由 `.gitignore` 排除）；manifest 记录其绝对路径。仓库只提交 manifest 中的 hash/run summary/reviewer verdict 等可审计元数据。若缓存被清理，样本自动降回不可 blocking 的状态，必须重新采集和复跑，不能靠旧口头结果晋升。

## CLI

只检查/列出候选，零执行副作用：

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --corpus-manifest references/p6r-corpus-manifest.json \
  --lane candidates --json
```

查看已获人工验收的 blocking corpus：

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --corpus-manifest references/p6r-corpus-manifest.json \
  --lane blocking --json
```

只有已准备本地 `fetch_all` cache 后，才显式执行；该模式不会自动补下载：

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --corpus-manifest references/p6r-corpus-manifest.json \
  --lane ready --execute \
  --writer-provider cli \
  --publishable --fail-on-fallback-warning \
  --section-qa-gate --claim-qa-gate --json
```

corpus 模式默认 `depth_profile=claim-first-full`，保证 P6-A/B1 会参与 publishable gate；普通单样本 CLI 仍默认 `standard`，维持向后兼容。所有 quality options（fact check、publishable、fallback、section QA、depth profile、claim QA）都会透传到单样本 gate。

## 验证边界

P6-R framework 的验证不等于 10 条样本已成为 gold。当前只能证明：

- manifest 结构、状态机和 provenance 可审计；
- dry-run 不会触发 renderer；
- `--execute` 对缺 cache 样本明确失败并拒绝 auto-download；
- fixture claim-first publishable run 中 P6-A/B1 均 PASS，而既有 skeleton 仍正确阻断正式发布。
- 真实 Pi 候选 `BV14fTc6TEi5` 已完成 H200 ASR → `cli` writer → formal gate → 人眼 QA 的验证闭环；发现并修复字符串 likes、§0/§6 renderer skeleton、H200 chunk timestamp 丢失、零弹幕 hallucination 与 KG 句子碎片。该样本仍是 `candidate`，待独立 reviewer rubric 后才可晋升 gold。

后续要填充 gold corpus，必须按：重新采集 → 使用真实 writer 生成 → machine gates → 人眼 rubric → 明确 reviewer/provenance → 才改为 `accepted_gold`。
