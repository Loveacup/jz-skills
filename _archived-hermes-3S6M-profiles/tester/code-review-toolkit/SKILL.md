---
name: code-review-toolkit
description: 刑部代码审查工具集 — 基于 super-linter(10.4K⭐) + roborev(1.2K⭐) + inspect(95%召回) 模式，lint/安全审计/实体级审查
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [tester, code-review, linting, security]
    source: [super-linter/super-linter, roborev-dev/roborev, Ataraxy-Labs/inspect]
---

# 刑部代码审查工具集

参考项目：
- **super-linter/super-linter** (10.4K⭐, Shell) — 多语言 lint 集合，并行运行
- **roborev-dev/roborev** (1.2K⭐, Go) — 持续 AI 代码审查，分析重复/复杂度/重构/死代码/安全
- **Ataraxy-Labs/inspect** (120⭐, Python+Rust) — 实体级审查，tree-sitter 分类变更，95%召回

## 审查层级

### L1: 机械检查（零 LLM）
```bash
# Python lint
ruff check --select E,F,W,B,SIM .
# Shell lint  
shellcheck **/*.sh
# YAML/JSON 验证
yamllint . && jsonlint **/*.json
# 安全扫描
bandit -r . -ll
```

### L2: 结构分析
```bash
# 代码复杂度
radon cc -a -s .
# 重复代码
jscpd .
# 死代码检测
vulture .
```

### L3: AI 审查（实体级）
- 按变更实体（函数/类/结构体）评分风险
- 跨文件依赖图谱分析爆炸半径
- 提交解耦（一个 commit 多个逻辑变更 → 分开审查）

## 审查清单

| 维度 | 检查项 |
|------|--------|
| 正确性 | 逻辑错误、边界条件、空指针 |
| 安全 | 注入、密钥泄露、权限、路径遍历 |
| 性能 | N+1 查询、内存泄漏、不必要分配 |
| 维护性 | 命名、函数长度、圈复杂度、文档 |
| 测试 | 覆盖率、边界用例、mock 质量 |

## 集成到三省六部

刑部 agent 应能：
1. `tester lint <path>` — 机械检查
2. `tester review <commit>` — AI 审查
3. `tester security <path>` — 安全审计
4. 产出稽核报告 → 门下复核
