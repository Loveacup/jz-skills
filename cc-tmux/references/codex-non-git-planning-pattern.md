# Codex planning-only 在非 git workdir 的用法

> **场景**：Codex planning-only 默认要求工作目录是 git repo。但 OB vault（`~/Documents/Obsidian/AlexCai/...`）+ skill 部署副本（`~/.hermes/skills/*`）+ 临时分析目录通常不是 git repo。
> **风险**：Codex 会因 "not a git repository" 拒绝执行；或虽 workdir 在 git repo 但因 `.obsidian/` / `Library/` 等子目录权限问题拒绝。
> **目的**：固化 `--skip-git-repo-check --sandbox read-only` 双 flag 用法。

## 1. 必加的两个 flag

```bash
codex exec --skip-git-repo-check --sandbox read-only 'prompt'
```

| Flag | 作用 |
|------|------|
| `--skip-git-repo-check` | 跳过「工作目录必须是 git repo」的强制检查 |
| `--sandbox read-only` | 限制 Codex 写权限（即使 planning-only 也要双保险） |

## 2. 适用场景

### 2.1 `~/.hermes/skills/*`（skill 部署目录，非 git repo）

```bash
codex exec --skip-git-repo-check --sandbox read-only '规划 /Users/alexcai/.hermes/skills/apple/mac-doctor/scripts/mac-doctor 的 6 subcommand 设计'
```

### 2.2 `~/Documents/Obsidian/AlexCai/...`（OB vault 是 local git，但常出子目录问题）

```bash
codex exec --skip-git-repo-check --sandbox read-only '规划 mac-doctor 项目的 PRD 文档结构'
```

### 2.3 临时分析目录

```bash
mkdir -p /tmp/cc-analyze && cd /tmp/cc-analyze
codex exec --skip-git-repo-check --sandbox read-only '分析 X 系统架构'
```

## 3. mac-doctor 实战案例

### 3.1 P1-P4 全程使用

```bash
# 每次派 Codex 都用这两个 flag
codex exec --skip-git-repo-check --sandbox read-only '...prompt...'
```

**4 次 Codex 任务**全部成功（每个 15-25min 出 22-33k tokens 的 YAML plan）：

| Phase | Tokens | 耗时 | 输出 slice 数 |
|-------|--------|------|--------------|
| P1 | 22k | ~15min | 6 |
| P2 | 22k | ~15min | 5 |
| P3 | 23k | ~15min | 4 |
| P4 | 33k | ~20min | 6 |

**关键参数**：
- `--skip-git-repo-check` 必加（mac-doctor workdir 在 `~/.hermes/skills/apple/mac-doctor/` 非 git）
- `--sandbox read-only` 必加（planning-only 也要双保险；否则 Codex 可能在 plan 里"顺手" 改文件）
- 不传 `--full-auto` 或 `--yolo`（planning-only 阶段不需要写权限）

### 3.2 Codex 输出格式

```yaml
- id: P1-S1
  objective: ...
  files:
    create: [...]
    modify: [...]
  red_test: |
    def test_...():
        ...
  impl: |
    ...
  verify_cmd: |
    pytest ...
  expected: |
    1 passed
```

每 slice 5 段：objective / files / red_test / impl / verify_cmd + expected。

## 4. 不适用场景

### 4.1 Codex 用于实际写代码

**不推荐**用 `--sandbox read-only` 之外执行模式做工程实现。**正确流程**：
- Codex planning-only（read-only）→ 规划
- CC 实施（Opus 4.8 high effort）→ 写代码
- Hermes 独立验收（pytest + spec 契约脚本）→ 验证

### 4.2 工作目录在 `~/.claude/` 或 Hermes 内部目录

`~/.claude/` 含 Claude Code 自身状态，Codex 读写会污染配置。`--sandbox read-only` 防写，**但 Codex 仍可能用只读工具读这些文件干扰 plan**——最好别让 Codex 直接跑这目录。

### 4.3 大文件目录

`~/Library/` / `~/.cache/` 等大型目录，Codex 容易超时。改用 `references/non-git-codex-planning-before-cc.md` 的"指定 ALLOWED FILES 列表"模式。

## 5. 与 cc-send.sh 的关系

```bash
# 1. Codex planning-only（read-only）
codex exec --skip-git-repo-check --sandbox read-only '规划 mac-doctor P1 preferences.py' > /tmp/codex-p1-plan.yaml
# 2. Hermes 审计 plan → 必要时手动 patch Codex 推断（mac-doctor P1 Q4 等）
# 3. CC 实施
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-send.sh \
  --session hermes-cc-default-mac-doctor-... \
  --context /tmp/cc-p1-context.md
# 4. CC 完成后，Hermes 独立跑 pytest 验收
cd /Users/alexcai/.hermes/skills/apple/mac-doctor && python3 -m pytest tests/test_preferences.py -v
```

**关键边界**：
- Codex = 规划（无副作用）
- CC = 实施（有副作用，已在 Hermes 监控下）
- Hermes = 审计（不修改 CC 产出，独立跑验收命令）

## 6. 沉淀到 SKILL.md

- 新 Pitfall #46 Codex non-git workdir（已在 v1.32+ 加入）
- Codex→CC→Hermes Handoff Pattern 段增"非 git workdir 必须用 `--skip-git-repo-check --sandbox read-only`"

## 7. 关联 reference

- `references/codex-plan-cc-execute-stdd-pattern.md`（完整 STDD 流水线模板）
- `references/non-git-codex-planning-before-cc.md`（已存在的非 git 模式）
- `references/codex-plan-vs-spec-schema-conflict.md`（Codex plan 审计 schema 对齐）
- SKILL.md ⚠️ Pitfalls #37（Codex schema 矛盾）/ #46（non-git workdir）
