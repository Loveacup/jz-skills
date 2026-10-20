# 跨平台社交指标归一化（real-sample regression）

## 触发场景

Bilibili 搬运视频会经 `youtube-comment-downloader` 注入 `cross_platform.youtube_comments.comments`。该来源的投票数可能是字符串（例如 `"53"`），而其他来源通常给整数。

## 风险

证据候选打分若直接执行 `likes * 0.01`，真实样本会在 `build_evidence_map()` 阶段抛 `TypeError`，使后续 writer、P6 evidence gate 与 publishable gate 都无法运行。不要把它误判成 LLM writer 或发布门失败。

## 处理合同

在**外部数据进入 evidence map 的边界**归一化权重，保持原始 payload 不变：

- 接受 `int` / `float` / 数字字符串 / 含千位逗号字符串；
- `None`、空值、非数字、负数、NaN、正无穷回落为 `0.0`；
- 只用于排序/显著度加权，不把社交 likes 当作事实性证据；
- transcript evidence 仍是 §3/§4 正式 factual support 的基线，跨平台评论只是 audience signal。

## 回归要求

`tests/test_cross_platform_evidence.py` 至少覆盖：

1. 字符串 likes 不会阻断 `build_evidence_map()`；
2. 有效字符串 likes 的候选分数高于无效/缺失 likes；
3. 原有整数 likes 排序保持；
4. 用一份真实 `fetch_all` payload 做 analysis-layer smoke，再触发真实 writer/publishable gate。

## 实样本流程

对于跨平台候选，先执行：`fetch_all → parse RESULT_JSON → transcript file exists/non-empty → build_evidence_map`。只有 analysis-layer 通过后才运行真实 writer；这样能把数据适配 crash 与生成质量问题分开。