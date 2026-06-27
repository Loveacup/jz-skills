# Cheap Lane Card 模板

> 用于杂活类 Kanban 卡的 metadata 模板。Hermes 建卡时按此格式填充，外部 CLI lane 读取 `metadata.model` 选择模型。

## 卡片 frontmatter 模板

```yaml
---
title: "<任务简述>"
type: task
status: ready
assignee: codex-lane          # 或 cc-lane
priority: normal
metadata:
  model: cheap                # cheap | strong | auto | <具体模型ID>
  lane: codex                 # codex | cc
  l0_checks:                  # L0 机器校验规格（由 Hermes 填充）
    - schema_validate
    - git_diff_scope
    - naked_tag_scan
  workspace: /tmp/kanban-{task_id}-codex
  timeout: 600                # 秒
  retry: false                # cheap lane 失败不自动重试
tags:
  - type/task
  - lane/cheap
created: <ISO timestamp>
---
```

## 模型选择规则（Hermes 建卡时判断）

| 任务信号 | model 字段 | 说明 |
|:---------|:-----------|:-----|
| 单文件修改 / frontmatter 修复 / 标签规范化 / 模板填充 | `cheap` | 默认走 cheap 池 |
| 多文件 / 架构 / 审查 / 安全相关 | `strong` | 必须走强模型 |
| 不确定 | `auto` | Hermes 按复杂度启发式判断 |
| 调试 / 实验 | `gpt-5.5` 等 | 直接指定模型 ID |

## L0 校验清单（cheap lane worker 执行前注入 context）

```
你在执行前必须确认以下全部为真：
□ 只修改了卡片声明的文件范围
□ 所有 YAML frontmatter 可解析
□ 所有 tags 使用允许前缀
□ diff 中无危险操作（rm -rf / secret 泄露 / 权限变更）
□ 未修改卡片声明范围外的任何文件
```

## 验收回写（Hermes 审查后填写）

```yaml
metadata:
  model: cheap
  l0_result: pass             # pass | fail
  l0_fail_detail: ""          # 若 fail，记录具体失败项
  reviewer: regent            # 审查者
  review_result: pass         # pass | revise | reject
```
