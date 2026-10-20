# P6-R 真实 payload 闭环：H200、稀疏社交与 KG（2026-07-10）

## 触发条件

当 `fetch_all` 实际产出来自 H200 chunked ASR、弹幕/评论稀疏、且需要走正式 `B站笔记_*.md` 发布路径时，不能只信 fixture、publishable summary 或 citation coverage。

## 已验证的根因与处理

1. **H200 chunk TXT 时间丢失**
   - 格式：`## Chunk N [MM:SS]` 后接无行级时间戳正文。
   - `generate_report._parse_txt_subtitle()` 必须把 heading 时间继承给后续正文，跳过 `## P...` / `## Chunk...` 元数据行。
   - 真实报告应出现多个可解析的 timestamp，例如 0/5/10/15/20 分钟；多候选 transcript 全为同一时间不可发布。

2. **零弹幕幻觉**
   - §3 writer 可能为满足格式而杜撰“观众惊叹/共识度高”。
   - 若 `frontmatter.danmaku_count == 0`，writer context 必须明确要求每个 `**弹幕反馈**` 写：`弹幕数据不足，无法判断共识度或典型反应`。
   - `P0_SPARSE_SOCIAL_EVIDENCE` 是 formal gate 的 fail-closed 兜底；prompt 不可替代 gate。

3. **KG 机械残留**
   - 不要让连续中文片段直接成为 entity；会输出句子碎片。
   - KG 自动实体仅保留英文/数字技术术语，中文只保留已知概念/MOC 命中。
   - 行动项只消费显式 `application_candidate`，不要因长转录含“可以/需要”等字就整段摘录。

## 真实样本 QA 顺序

1. 先复跑 formal gate / 全量 tests；
2. 再人眼检查 §3（社交证据）、§5（时间分布）、§6（概念可读性）、§7（稀疏数据边界）；
3. 发现问题先修 producer 或 P0 gate，**不要放宽 gate 或把 candidate 写成 gold**；
4. 只有 reviewer rubric、reviewer/time/verdict、可复跑 input 和 run summary 齐全，才能由 `candidate` 升到 `accepted_gold`。

## 验证锚点

真实 Pi candidate `BV14fTc6TEi5`：H200 ASR → cli writer → formal gate → 人眼 QA。最终候选仅保留在 `/tmp`，未写入 Obsidian、未升级 gold。