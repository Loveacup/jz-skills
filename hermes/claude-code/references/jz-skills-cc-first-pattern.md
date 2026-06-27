# jz-skills CC-First Design Review Pattern v1.0

> **触发条件：** 在 `~/code/jz-skills/` 做多文件改动、skill 设计、或架构决策时，默认走 CC agent team，不手写 patch。

## 来源

2026-06-03 早新闻 P2 外包 skill 集成 session。Hermes 开始手改 SKILL.md 时用户打断：
- "要调用cc干活啊别自己干"
- "核心设计要让cc审查"

## 模式

```
jz-skills 非简单改动?
├── 单行/单文件小修 → Hermes 自己做（不改接口/不引入新依赖）
└── 多文件/设计/架构 → CC agent team
    ├── Phase 1: 设计审查（先做）
    │   └── CC 读 SKILL.md + references，对照真实 skill 接口验证契约
    │       输出：发现的问题分级（🔴阻塞 🟠隐患 🔵轻微）+ 通过/不通过
    ├── Phase 2: 修复（审查通过后再做）
    │   └── CC 逐项修复，含 sync 映射、版本号、sanitize
    └── Phase 3: 部署验证
        └── CC 部署到目标 profile + 逐项跑验证清单
```

## 为什么 CC 审查有价值

CC agent team (xhigh effort) 能发现 Hermes 漏掉的边界条件：

| 案例 | Hermes 漏了什么 | CC 发现了什么 |
|------|----------------|-------------|
| source-verification 集成 | 假设 skill 存在 | skill 在仓库中完全不存在 |
| tts-manager 集成 | 写了 CosyVoice 私网 IP | 端点不在 SKILL.md 本体，且私网 IP 泄露 |
| de-slop 重写 | 未考虑 verbatim quote 破坏 | citation 锚 `[sN]` 会被改写破坏 |
| aihot 降级 | 以为逻辑完整 | 降级链自语矛盾（回退无对象） |
| sanitize grep | 假设已覆盖 | `192\.168` 模式漏过 `172.16` |

## Context file 模板

```markdown
# 任务标题

## 背景
简要说明要改什么、为什么改。

## Phase 1: 设计审查（先做）
审查以下文件：...

## Phase 2: 执行
具体的修复/创建清单。

## 约束
- workdir: ~/code/jz-skills/
- 不改动...
- 需要改...

## 关键决策
- 用户已决定的方向（CC 不重新质疑）
- 待用户确认的决策点
```

## Effort 选择

jz-skills 多文件/设计审查/架构改动 → `--effort xhigh`
jz-skills skill 撰写/安全审计 → `--effort max`

## 变体：Hermes 主设计 + CC 写配套文件

2026-06-03 早新闻 v4.0。任务拆分模式：
- **Hermes 负责**：写主 SKILL.md（架构决策、格式规范、双模式执行流）
- **CC agent team 负责**：写配套 reference 文件（search-workflow.md 重写、kanban-swarm-workflow.md 新建、tts-script-spec.md 新建）

适用条件：
- 主设计方向已确定（用户批准了设计审查建议）
- 配套文件是「从主设计派生」的规范文档，不含新架构决策
- 多个配套文件需要跨文件参考和对齐（CC agent team 做这个比 Hermes 逐文件 patch 高效）

Context file 要点：
- 写明主 SKILL.md 路径（CC 先读它，保证对齐）
- 每个配套文件的具体要求（是重写还是新建、需要什么内容）
- 相关外部信息直接内联到 context（如 Kanban v0.15 研究笔记摘要），避免 CC 额外搜索
