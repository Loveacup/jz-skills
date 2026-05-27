---
name: agent-audit-evaluation
description: "Use when performing independent audit and evaluation of agent execution results — verifying outputs against plans, detecting regressions, checking governance compliance, and producing structured audit reports for 御史台 review. Based on OpenAgentBench (generalaimodels/OpenAgentBench, 1⭐, 7 audit dimensions) and agenteval (agentkitai/agenteval, 1⭐, YAML test suites + statistical regression) patterns. Do NOT use for model benchmarking (see evaluating-llms-harness) or for code linting (see code-review-toolkit)."
version: 1.0.0
author: Hermes Agent (based on generalaimodels/OpenAgentBench + agentkitai/agenteval)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [yushitai, audit, evaluation, regression, compliance, verification]
    related_skills: [three-provinces-constitution, 6m-smoke-test, code-review-toolkit, agent-security-audit]
---

# Agent Audit & Evaluation — 御史台独立稽核

> Based on OpenAgentBench (7 audit dimensions: tool-selection optimality, state-transition correctness, memory hygiene, privilege safety, recovery behavior, grounding faithfulness, multi-agent coordination) and agenteval (YAML test suites, 6 graders, Welch's t-test regression detection). Adapted for 三省六部 御史台 independent audit.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "The output looks reasonable, I'll approve it" | Reasonable ≠ verified. Agents hallucinate facts (planner claimed DeepSeek V4-Pro had "4% hallucination rate" when actual figure was 94%), and reviewers miss errors. 御史台 is the LAST LINE OF DEFENSE before results reach the Emperor |
| "I already ran the verification checklist from the skill" | The skill's own checklist is self-assessment. 御史台's audit is INDEPENDENT verification — reading actual files, checking actual logs, comparing against original plan criteria |
| "It's a small change, no need for full audit" | Even "small" changes can break downstream agents. A single wrong file path in a Kanban summary can stall the entire chain |
| "I'll just re-read the output and trust the agent's summary" | Agent summaries are self-reports, not verified facts. Always check: (1) does the claimed file exist, (2) does its content match the summary, (3) are numbers verifiable against source data |

## When to Use

- Auditing completed Kanban tasks before final delivery to the Emperor
- Verifying that execution artifacts match plan specifications
- Detecting regressions: "did agent behavior change after a config/profile/model update?"
- Compliance auditing: "did the agent follow all governance rules?"
- Cross-referencing facts: "do the numbers in the report match the source data?"

## 御史台 Audit Dimensions

Based on OpenAgentBench's 7-dimension framework:

| Dimension | What to Check | How to Check |
|-----------|--------------|--------------|
| **1. Output Correctness** | Does the artifact match the spec? | Diff plan criteria vs actual output |
| **2. Tool-Selection Optimality** | Did the agent use the right tools? | Check tool call log against task requirements |
| **3. State-Transition Correctness** | Did the Kanban chain follow valid transitions? | Verify card states follow VALID_TRANSITIONS |
| **4. Privilege Safety** | Did the agent access only authorized resources? | Check tool calls against profile permissions |
| **5. Memory Hygiene** | Did the agent avoid memory pollution? | Verify MEMORY writes don't contain task progress |
| **6. Recovery Behavior** | How did the agent handle failures? | Check retry logs, error handling, budget exhaustion |
| **7. Grounding Faithfulness** | Are factual claims backed by sources? | Cross-reference report claims against original data |

## Audit Workflow

### Phase 1: Claim Extraction

Extract every verifiable claim from the agent's output:

```bash
# From artifact: extract factual claims
hermes audit extract-claims \
  --input /path/to/agent-output.md \
  --output /tmp/claims.jsonl

# Claims include: numbers, file paths, status assertions, "X is Y" statements
```

### Phase 2: Evidence Collection

For each claim, collect evidence:

```bash
hermes audit collect-evidence \
  --claims /tmp/claims.jsonl \
  --workspace /path/to/task/workspace \
  --output /tmp/evidence.jsonl
```

Evidence types:
- **File existence**: `ls -la <claimed-path>` — does the file exist?
- **Content match**: `grep` or file comparison — does content match the claim?
- **Source verification**: `web_extract` or re-read original source — do numbers match?
- **Log verification**: Check agent logs — did the claimed action actually execute?

### Phase 3: Compliance Check

Verify against governance rules:

```yaml
# audit-rules.yaml
rules:
  - id: "GO-001"
    description: "尚书省 must be inserted in multi-step chains"
    check: "kanban show <chain> --json | jq '.tasks[] | select(.assignee==\"shangshu\")'"
    severity: critical
  
  - id: "GO-002"
    description: "Planner must write files to persistent workspace"
    check: "ls <workspace>/plan-*.md"
    severity: high
  
  - id: "GO-003"
    description: "No executable trading advice in financial reports"
    check: "grep -cE '买入|卖出|仓位|止损|目标价' <report>"
    severity: critical
```

### Phase 4: Regression Detection

Compare current run against previous baseline:

```bash
hermes audit compare \
  --current /tmp/audit-20260527.json \
  --baseline /tmp/audit-20260520.json \
  --threshold 0.05  # 5% significance level
```

Uses Welch's t-test (from agenteval) for statistical comparison.

### Phase 5: Audit Report

```markdown
# 御史台稽核报告

## 审查对象
- Task: t_abc123
- Agent: engineer
- Plan: plan-v3.md

## 审查维度

| 维度 | 结果 | 证据 |
|------|------|------|
| 1. 输出正确性 | ✅ 通过 | 产出文件存在，内容匹配 spec §3.2 |
| 2. 工具选择 | ✅ 通过 | 使用 write_file + terminal，无越权调用 |
| 3. 状态流转 | ✅ 通过 | todo→ready→running→done，无非法跳转 |
| 4. 权限安全 | ⚠️ MODERATE | 读取了 ~/.hermes/config.yaml（只读，无修改）|
| 5. 记忆卫生 | ✅ 通过 | 未写入 MEMORY |
| 6. 恢复行为 | N/A | 任务一次完成，无失败重试 |
| 7. 事实接地 | ❌ HIGH | 声称"test 14/14 pass"，实际仅 11/14 |

## 阻断项

| # | 严重度 | 维度 | 问题 |
|---|--------|------|------|
| B1 | 🔴 HIGH | 事实接地 | 测试通过数不实 (14 claimed, 11 actual) |

## 裁决

**REJECT** — 1 项 HIGH 阻断，需返修后重审。

**证据路径**: /tmp/audit-evidence/t_abc123/
```

## Quick Start

### Install agenteval

```bash
pip install agenteval
```

### Define an Audit Suite

```yaml
# audit-suites/kanban-chain.yaml
name: "Kanban Chain Compliance Audit"
version: "1.0"
tests:
  - name: "尚书省 inserted in chain"
    description: "Verify shangshu card exists between reviewer and execution"
    type: "kanban-graph"
    check:
      path: "planner → reviewer → shangshu → engineer"
      must_exist: ["shangshu"]
  
  - name: "Artifact files exist"
    description: "All claimed output files exist on disk"
    type: "file-existence"
    paths:
      - "/workspaces/plan.md"
      - "/workspaces/report.md"
  
  - name: "No executable trading advice"
    description: "Financial reports must not contain trading instructions"
    type: "grep-absence"
    files: ["/workspaces/report.md"]
    patterns: ["买入", "卖出", "仓位", "止损", "目标价"]
  
  - name: "Token count within budget"
    description: "Agent did not exceed token budget"
    type: "numeric-range"
    source: "session-logs"
    field: "total_tokens"
    max: 50000

graders:
  - exact-match
  - file-existence
  - grep-absence
  - numeric-range
```

### Run Audit

```bash
# Run audit suite against a completed task
hermes audit run \
  --suite audit-suites/kanban-chain.yaml \
  --task t_abc123 \
  --output /tmp/audit-report.md

# Compare against baseline
hermes audit compare --current t_abc123 --baseline t_abc100
```

## Statistical Regression Detection

When the same task is run multiple times (e.g., morning-news-briefing daily), detect regressions:

```bash
# Collect 3 runs, compare groups
hermes audit compare \
  --group-a t_news_may25,t_news_may26,t_news_may27 \
  --group-b t_news_may20,t_news_may21,t_news_may22 \
  --metric quality_score
```

Uses Welch's t-test (agenteval). Reports:
- Whether the difference is statistically significant (p < 0.05)
- Effect size (Cohen's d)
- Which specific dimensions degraded

## Reference: Upstream Projects

| Project | Stars | License | Key Feature |
|---------|-------|---------|-------------|
| [OpenAgentBench](https://github.com/generalaimodels/OpenAgentBench) | 1 | GPL-3 | 7 audit dimensions, state-machine verification |
| [agenteval](https://github.com/agentkitai/agenteval) | 1 | MIT | YAML test suites, Welch's t-test, 6 graders |
| [AgentBench](https://github.com/THUDM/AgentBench) | 3.4K | Apache 2.0 | 8 environments, comprehensive agent evaluation |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) | 302 | - | ICLR'26: memory-specific evaluation framework |

## 三省六部 Integration

御史台 audit is triggered:
1. **Automatically**: After every 门下终复 APPROVE (pre-delivery gate)
2. **On-demand**: When the Emperor asks "核实一下这个结果"
3. **Periodically**: Weekly audit of all completed chains for systemic issues

```
planner → reviewer → shangshu → [engineer, analyst, ...] → reviewer(final)
                                                              │
                                                    ┌─────────┘
                                                    ▼
                                              御史台 audit ← THIS SKILL
                                                    │
                                              ┌─────┴─────┐
                                          APPROVE      REJECT
                                              │           │
                                          deliver    返修链
```

## Common Pitfalls

- **Auditing summaries instead of artifacts**: Always read the actual output files. Agent summaries omit failures.
- **False positive on P0 items**: Items reported as P0 may have been resolved by parallel workers. Always check actual disk/log state before confirming.
- **Regression baseline drift**: Baselines collected weeks ago may be stale. Rotate baselines every 7 days.
- **Over-auditing**: Not every task needs all 7 dimensions. Classify task risk first: LOW→dimensions 1+5, MEDIUM→1+3+5+7, HIGH→all 7.

---

## ✅ Verification Checklist (RUN BEFORE DELIVERING AUDIT REPORT)

- [ ] Did I read the ACTUAL output files (not just the agent's summary)?
- [ ] Did I cross-reference ≥3 factual claims against source data?
- [ ] Did I check Kanban state transitions against VALID_TRANSITIONS?
- [ ] Did I verify file existence for all claimed artifact paths?
- [ ] Did I classify each finding by severity (CRITICAL/HIGH/MODERATE/LOW)?
- [ ] Did I produce a structured report with evidence paths for every finding?
- [ ] For REJECT verdicts: did I list specific blocking items with exact file:line references?

**If any box is unchecked, go back.**
