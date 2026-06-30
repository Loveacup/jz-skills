# CC 文件幻觉验证模式 · 2026-06-27 实发

## 症状

CC 声称已写入文件（"I've written the report to /tmp/cc-output-xxx/Phase1.md"），但磁盘上文件不存在。CC 可能继续基于"文件已写入"的幻觉推进后续分析。

2026-06-27 实发案例（WRR 自适应改造 Phase 1）：
- CC 声称写入 `/tmp/cc-output-hermes-cc-default-wrr-adaptive-phase1-0627-1638/Phase1_架构讨论稿_v1.md`
- `find /tmp -name "Phase1_架构讨论稿*"` → 无结果
- CC 自曝"工具输出坏了"、"任务没实现"

## 根因

CC 的 Bash/Write 工具在 tmux 环境下间歇性失败（文件系统操作不可靠），但 CC 不自知——它收到工具的"成功"响应（或没有收到错误），继续认为文件已写入。

## 验证铁律

**CC 声称写文件后，必须独立验证磁盘状态。** 不要相信 CC 的"已写入"自报。

```bash
# 方法 1：直接查找声称的文件
find /tmp -name "<filename>" 2>/dev/null

# 方法 2：查找整个输出目录
ls -la /tmp/cc-output-<session>/ 2>/dev/null

# 方法 3：查找最近修改的文件（确认时间窗口）
find /tmp -name "*.md" -mmin -10 2>/dev/null
```

## 应对流程

```
CC 声称完成 → 验证磁盘
  ├── 文件存在 ✓ → 继续审核内容
  └── 文件不存在 ✗ → 立即判定该轮产出不可信
      ├── 选项 A：让 CC 重新写入（可能再次失败）
      ├── 选项 B：换 Sonnet 执行（更机械可靠）
      └── 选项 C：Hermes 直接接管写入（绕过 CC 工具链）
```

## 预防

1. **context 中明确要求**："所有产出必须用 write 工具写入磁盘，写入后我会用 find 验证"
2. **in-turn wait 每轮检查**：长任务中每 5-10 分钟检查一次磁盘产出
3. **磁盘产出阈值告警**：超 20min 无文件产出 → 抓屏诊断 → 准备 C-c

## 与 Pitfall #30 的关系

Pitfall #30（Opus UltraCode 过深思考）和 Pitfall #32（文件幻觉）经常同时触发：
- Opus 深度调研 → 长时间思考 → 工具间歇性失败 → 文件未落盘但 CC 不自知 → 继续基于幻觉推进
- **双重验证**：不仅看 CC 是否"完成"，还要看磁盘是否有文件；不仅看文件是否存在，还要看内容是否正确。
