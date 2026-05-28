# Two-Phase Research→Build Pattern

When upgrading a complex skill that needs external reference analysis, split into two independent cc sessions:

## Phase 1: Research (cc agent team, read-only)

**Goal:** Produce an Obsidian research doc. Do NOT modify any skill code.

**Hermes agent pre-work (before launching cc):**
1. `web_search` + GitHub search to identify 3-5 top reference projects
2. Summarize findings — present to user for approval
3. Write task spec to `~/.hermes/tmp/<name>-research-task.md`

**Task spec format:**
```markdown
# Task: <skill> 升级研究

## Phase 1: 参考项目解构（并行 agent team）
克隆 N 个项目到 ~/research-tmp/，每个 worker 负责一个：

### Worker A: <project-name>
- URL: <github-url>
- 关注点：<specific patterns to extract>

### Worker B: ...
### Worker C: ...

### Orchestrator: 基线分析 + 集成方案设计
1. 读当前 skill SKILL.md
2. 读依赖 skill 最新版
3. 分析 gap
4. 等 workers 完成，汇总发现

## Phase 2: 产出研究文档
输出到 Obsidian: 20-Areas/10_AI实践/<skill>_升级研究_{date}.md

## 约束
- 中文为主
- 每个 worker 必须 git clone --depth 1 后 grep 关键模式
- 研究文档 <500 行
- 不要修改任何 skill 代码
```

**cc launch command:**
```
Read <task-spec>. Execute Phase 1: clone N reference projects in parallel, 
then decompose them with agent team. Output research doc to Obsidian. 
Research-only — do NOT modify any skill code.
```

**Common pitfalls in Phase 1:**
- macOS TCC sandbox: `~/Documents/` may be blocked. If cc can't write to Obsidian, tell it to use `/tmp/` instead, then move the file yourself.
- Worker fake-death: if a worker's tokens stall and UI still shows "running" after 2+ min, `ls -la` check if files exist on disk. If yes → tell cc "Worker X is done, files on disk, continue."

---

## Phase 2: Build (cc agent team, write skill files)

**Goal:** Implement the skill update based on the research doc.

**Hermes agent pre-work:**
1. Read the research doc to understand the plan
2. Write build task spec to `~/.hermes/tmp/<name>-vN-task.md`

**Build task spec format:**
```markdown
# Task: <skill> vX → vY 全面升级

## Baseline
- 当前版本 + 路径
- 研究文档路径
- 依赖 skill 路径

## 核心约束
1. 不动已有稳定管线（如渲染/审计）
2. 渐进披露 — 新增进 references/, SKILL.md <X 行
3. 中文为主

## Agent Team 分工

### Worker A: <specific file to write>
产出 + 源项目 + 具体内容要求

### Worker B: ...
### Worker C: ...

### Orchestrator: 主文件更新 + 合规审计
1. 更新 SKILL.md
2. 交叉检查引用
3. 7-dimension compliance audit

## 禁止事项
- 具体的禁改清单
```

**cc launch command:**
```
Read <task-spec>. Execute Phase 1: spawn 3 worker agents in parallel. 
Each writes reference files following the spec. Then orchestrator does 
SKILL.md update + compliance audit. Use agent team.
```

---

## Why Two Phases

| Single phase | Two phase |
|-------------|-----------|
| cc context window inflated with both research + implementation | Each phase fits in one session |
| No user visibility into research findings before build | Research doc in Obsidian → user reviews before committing to build |
| Hard to course-correct mid-build | Build task spec is based on reviewed research |
| Workers waste time re-reading source projects | Phase 1 clones once, Phase 2 references Phase 1 output |

**When NOT to use:** Simple single-file edits, bug fixes, or when the upgrade path is obvious without external research.
