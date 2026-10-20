# bilibili-video-analyzer 质量优化 workflow：Claim-First 深度升级

Session: 2026-07-05
Context: 用户反馈 v3.0 重构后分析深度退化（从“深度研究”变成“摘要生成器”），要求按质量优先流程出优化方案。

## 1. 诊断方法

当用户说“老版本更好”时，先定位具体好在哪个维度，而不是整体回滚。

| 维度 | 老版本 v2.4.0 特征 | 当前 v3.0 退化表现 |
|------|--------------------|--------------------|
| 输出长度 | 8-section 模板，§3 每个洞察 ≥200 字 | skeleton 占位、节段过短 |
| 观点密度 | 7 步推理链：类型诊断→弹幕→分层→降噪→要素→对比→批判 | prompt 变轻，结构未继承推理 |
| 学习笔记感 | 不是主要特征，更像分析报告 | 摘要化、碎片化 |
| 深度研究 | 每个见解带原理+案例+关联+弹幕反馈 | 缺少 warrant/backing |
| 证据密度 | 每个 insight 关联时间戳/弹幕 | 引用稀疏或缺失 |

老版本 commit: `436b3197`（`3c53411^`），路径 `hermes/bilibili-video-analyzer`。
退化断点: `301ee6b`（render markdown skeleton 引入）。

## 2. 质量优先工作流

用户要求：CodeX 规划 → CC 执行 → OMP 审核 → 我协调验收与文档。

| 阶段 | 工具/角色 | 产出 |
|------|----------|------|
| 规划 | CodeX (read-only planning) | `/tmp/bili_quality_optimization_plan.md` |
| 实现 | CC (cc-tmux) | 6 个 task 包，每包改小范围 |
| 验收 | 我 (Hermes) | 读文件 + git diff + 跑 pytest |
| 审计 | OMP (call-omp) | 结构化 JSON verdict |
| 文档 | 我 + CC | README / SKILL.md / reference |

Task 拆分：
1. RED tests + fixtures
2. Claim/Insight/ClaimBundle dataclasses + pure functions
3. Section QA gate D6-D8 + verify_report G8-G10
4. CLI surface: `--depth-profile`, `--claim-qa-gate`
5. v2.4 prompt restoration + claim context injection
6. README / SKILL.md / reference docs

## 3. 关键设计决策

- **保留代码结构优势**：draft/publishable/Section QA gate 不变。
- **注入 claim-first 结构**：`Claim` 对象显式包含 claim/warrant/grounds/rebuttal/confidence。
- **默认向后兼容**：新 gate 和 CLI 参数默认关闭，现有脚本不带参数时行为不变。
- **样片验证**：真实视频样片必须通过 `verify_report.py` + `check_report_coherence()`。

## 4. 验证命令

```bash
cd /Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py
python3 scripts/run_quality_gate.py --depth-profile claim-first-full --claim-qa-gate ...
python3 scripts/verify_report.py --depth full --claim-first ...
```

## 5. 坑与教训

- 旧版优势来自“重 prompt”，不是代码结构；重构时不能把 prompt 变轻。
- 深度不够不是 prompt 不够长，而是缺少“从证据到结论的受控跳跃”。
- 所有新增 gate 必须默认关闭，否则破坏现有测试和发布流程。
- LLM writer 输出必须经 verify_report 格式校验，fallback 到 skeleton 是允许的但要有 warning。
- CC 完成报告必须复核实际文件和 diff，不能采信自报。
