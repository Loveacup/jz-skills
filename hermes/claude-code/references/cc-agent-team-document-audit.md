# CC Agent Team: 文档审计模式

> 2026-05-29 验证有效：A2A 架构讨论文档（1059 行/48KB/15 章）3-lens 审计，Phase 1 完整审计用时 ~5min

## 适用场景

- 大型架构文档/设计文档/技术方案的审阅优化
- 由多个 session 合并成的文档（存在风格断裂/重复/概念漂移）
- 需要多维度审视的内容（重复性、风格一致性、事实准确性）

## 三阶段模式

### Phase 1 — 内容审计（只读，不改文件）

**Agent team 配置**：3 个 lens agent 并行

| Lens | 职责 | 典型 prompt |
|:-----|:-----|:-----------|
| **A: 重复与交叉审计** | 标记所有重复论述、内容交叉、概念被多处定义且不一致的地方 | "Read the full doc. Find all content that appears in multiple places or where the same concept is defined differently across sections. Output: numbered list with section references and severity." |
| **B: 风格与语气审计** | 标记风格断裂点、语气不一致、格式不统一 | "Read the full doc. Find all style/tone/format breaks — sections that read differently from others, inconsistent heading levels, emoji usage patterns, code block styles. Output: numbered list with section references." |
| **C: 事实准确性审计** | 核对 arXiv ID、URL、版本号、端口号等硬事实 | "Read the full doc. Verify all arXiv IDs, URLs, version numbers, port numbers, file paths against known facts. Flag any that look wrong." |

**Leader 职责**：启动后不干预，三份报告齐了再归一合并。合并时按类别分组（重复/概念漂移/风格断裂/事实存疑），每组提炼成用户可快速判断的摘要。

### Phase 2 — 结构重组（等用户批准后改文件）

Phase 1 输出包含**建议的新章节骨架**，用户确认后再进 Phase 2。不要 Phase 1 完成后直接改文件——先展示、等绿灯。

关键决策点（Phase 1→2 的桥梁）：
- 角色称谓统一（中性代号 vs 叙事风格）
- 新骨架结构（几 Part、哪些合并）
- 是否改标题（如加状态标签 `✅ done / 📋 proposal / 🔬 research`）

### Phase 3 — 润色统一

- 统一标题层级、表格、代码块
- 消除语气差异
- 添加交叉引用

## Context 文件模板

```markdown
# CC Agent Team Task: 优化 [文档名]

## 文档路径
`/absolute/path/to/doc.md`

## 文档现状
- [行数/KB/章节数]
- [来源：单 session 还是多 session 合并]
- [已知问题]

## Phase 1 — 内容审计（只读，不改文件）
1. 通读全文
2. 启动 3 个 lens agent 并行审计（重复/风格/事实）
3. 合并三份报告，按类别呈现给用户

## Phase 2 — 结构重组（等用户批准）
4. 提出新骨架
5. 重排章节、合并重复
6. 保留所有关键信息

## Phase 3 — 润色统一
7. 统一格式、消除语气差异、加交叉引用

## 约束
- Phase 1 只读，不要改文件
- 写入前先展示方案
- 使用 agent team（3 lens 并行）
```

## 已验证案例

- **A2A 架构讨论文档**（2026-05-29）：1059 行/48KB，由太子 CC team（修复记录）+ 小黄（Kanban 调研）两个 session 合并。3 lens agent 并行审计（A: 1m10s, B: 1m03s, C: ~2m），Phase 1 总耗时 ~5min。发现了 API Server 重复讨论 3 处、Kanban 协作模式出现 2 处、"旧治理体系 — 3 个不同含义、arXiv ID 5 处存疑。输出建议三 Part 骨架（A2A 修复纪实 / 协作架构调研 / 路线图与提案）。

## 注意事项

- **Phase 1 的 lens agent 是只读的**：在 prompt 中明确 "read-only, no file edits"
- **不要用普通 Task subagent 冒充 team**：CC agent team 有独立机制和 worker 管理
- **Worker 假死检测**：如果某 lens agent token 数 >2min 不变，先 `ls -la` 检查是否已产出文件（见 `worker-stall-detection.md`）
- **Context 清理**：文档审计任务启动前，先用 `/clear` 清空旧 context（大文档 + 旧 context = 极慢）
