# Template vs Command — 描述性标签 vs 指令性约束

> **Execution Lapse case study (2026-05-31): claude-code progress reporting**

## 症状

claude-code skill v3.3.0 的 Progress Reporting 段写了完整的汇报模板（含 worker 树 + emoji + token），但小黄和太子在实际监控 CC 时从不使用该模板格式。搜遍近期会话，0 条实际使用记录。

## 根因：描述性标签被 LLM 解读为「参考示例」

```markdown
<!-- 原写法（无效） -->
**汇报模板：**
```

对 LLM 来说，"模板"是一个**描述性名词**，暗示"这是参考格式，你可以参考但不强制"。agent 内心独白：

> "模板只是个参考，用户只要知道 CC 在干嘛就行，我简短说两句也一样。"

## 修复：三管齐下把「示例」升级为「命令」

### 1. 标签改写 — 描述性 → 指令性

```markdown
<!-- 修复后 -->
**汇报模板（必须严格按此格式，不按模板 = 未完成汇报）：**
```

### 2. Core Rule 绑定格式

```markdown
9. **📡 无条件持续汇报进度** — 每 30-60s polling，沉默 >2min 不可接受。
   **必须使用下方 Progress Reporting 段规定的模板格式**，自由发挥视为未汇报。
```

### 3. 段首 EXECUTION LAPSE 预拦截

```markdown
> ⚠️ **这不是建议，是命令。** 每次 capture-pane 后必须按下方模板汇报。
> 不要简化、不要自由发挥、不要合并多轮为一句话。
```

### 4. Verification Checklist 细化

```markdown
- [ ] Progress：是否严格使用规定的模板格式（含 worker 树 + emoji + token）？
```

## 通用模式

| 检查项 | 描述性（弱） | 指令性（强） |
|--------|:---|:---|
| 标签词 | 模板、示例、参考 | 必须、严格、强制 |
| 绑定点 | 仅在格式段 | Core Rule + 段首 + Checklist |
| 预拦截 | 无 | blockquote 对抗 agent 反驳 |
