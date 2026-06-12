# Lane Model Routing — Cheap/Strong 双核分流

> 寄生在 D3 复杂度路由之上，不新增路由维度，只加模型选择。

## 设计原则

1. **D3 寄生**：路由决策仍走 D3 复杂度判定（≤2步→小黄，≥3步→太子）；模型选择是执行层的优化。
2. **默认便宜**：杂活默认走 cheap lane 池，显式 override 才能用强模型。
3. **L0 强制**：cheap lane 产出必经机器校验（schema / git diff / lint），零成本门槛。
4. **L2 抽检**：太子对 cheap lane 产出做 spot-check（D3 已有审查门）。

## 模型池

### Cheap Lane 池（杂活默认）

| Lane | 模型 | 模型 ID | 适用场景 |
|:-----|:-----|:-----|:-----|
| CC | Claude Sonnet 4 | `claude-sonnet-4` | 文档整理、简单修改、格式调整、机械性任务 |
| Codex | GPT-5.3-Codex-Spark | `gpt-5.3-codex-spark` | 单文件/quick PR/bounded、frontmatter 修复、标签规范化 |

### Strong Lane 池（重活 / 显式 override）

| Lane | 模型 | 模型 ID | 适用场景 |
|:-----|:-----|:-----|:-----|
| CC | Claude Opus 4.8 | `claude-opus-4-8` | 多文件架构、复杂重构、代码审查 |
| CC | Claude Fable 5 | `claude-fable-5` | 最高价值/最高风险/关键架构决策 |
| Codex | GPT-5.5 | `gpt-5.5` | 复杂编码、多文件改动、安全审查 |

## 路由决策

```
任务进入 → D3 判定
  ├─ 小黄直接处理 / 简单卡
  │   └─ 需要外部 lane？
  │       ├─ 默认 → cheap lane 池（Sonnet / Spark）
  │       └─ 显式 override → strong lane
  └─ 太子牵头调度 / DAG
      └─ 子任务按需选模型（默认 strong，显式降级可走 cheap）
```

## 显式 Override 机制

Kanban 卡 `metadata.model` 字段：

```yaml
# 默认（不写 = cheap）
metadata:
  model: auto          # 自动走 cheap

# 强制 cheap（显式声明，用于审计）
metadata:
  model: cheap

# 强制 strong（重活 / 关键任务）
metadata:
  model: strong

# 指定具体模型（极少用，仅调试/实验）
metadata:
  model: claude-opus-4-8
```

## L0 机器校验（cheap lane 强制）

cheap lane 产出必须通过以下全部校验才能进入 review：

1. **Schema 校验**：frontmatter YAML 可解析 + 必填字段齐全 + type 在枚举内
2. **Git diff 比对**：`git diff --stat` 确认只改了声明的文件
3. **裸标签检查**：所有 tags 都在允许前缀内
4. **危险操作检测**：diff 中无 `rm -rf` / secret 泄露 / 权限变更

任一失败 → 自动 block，不进入人工审查。

## 成本意识

- Sonnet / Spark 额度充裕 → 杂活默认走 cheap
- 不是"省着用强模型"，而是"把强模型留给真正需要深度推理的任务"
- cheap lane 任务失败不重试 cheap → 记录失败原因 → 由 Hermes 决定是否升级到 strong 重跑
