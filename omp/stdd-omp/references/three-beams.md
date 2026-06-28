# 三梁项目骨架

三梁是项目的最小可控上下文：梁1 需求、梁2 实现、梁3 控制。

## Context Pyramid

```text
           梁1 需求基准线
          /               \
   梁2 共维实现方式    梁3 agent 执行层
              \         /
            派生路线图
```

- 梁1 决定「做什么、为什么」。
- 梁2 决定「怎么做、影响面」。
- 梁3 决定「怎么切、怎么审、怎么停」。
- 路线图是 梁1/梁2/梁3 的派生投影，不是独立梁。

## 每梁的 OMP 载体

| 梁 | 内容 | OMP 载体 |
|---|---|---|
| 梁1 | 需求、用户、验收、反范围 | `context-files` / `SYSTEM.md` / `assets/three-beams/beam1-requirements.md` |
| 梁2 | 设计决策、依赖、接口、风险 | `assets/three-beams/beam2-implementation.md` / plan |
| 梁3 | 任务切片、审计链、退出条件 | `assets/three-beams/beam3-control.md` / `todo` + `plan` |

## 梁1 灵魂红线

基准线 = 需求 + 可证伪验收口径，缺一不可；退化成愿望清单即失去当尺子资格。

验收契约的 warrant/backing 缺陷分级：
- **缺推理桥**（warrant 弱）→ 补一句即可，便宜。
- **缺背书**（backing 空）→ 需补一整节，贵。
- 返工预算差一个量级——发现 warrant 问题时趁早补。

## 梁2 中枢纪律

- **决策台账**：每个设计决策记录选项、选择、理由与**下游影响**（变更影响矩阵）。
- **源真相路由**：核心数据模型/API/schema 正文留在各设计文档，本中枢只持链接、不复制（只路由 = 单一权威）。
- **派生路线图**：引用不复制——路线图指向三梁，而非在路线图中重述梁内容。

## 防变重护栏

1. **梁1 不变原则**：一次 session 内 梁1 一般不变；若变，必须重走 Accept。
2. **梁2 决策最小化**：不做预测性抽象；每个决策对应一条验收项。
3. **梁3 切片可丢弃**：slice 失败可单独放弃，不影响其他 slice。
4. **同步纪律**：任何变更必须同步回三梁；不能只改代码不改文档。

## 模板使用

- `assets/three-beams/beam1-requirements.md`
- `assets/three-beams/beam2-implementation.md`
- `assets/three-beams/beam3-control.md`

复制到项目目录后按 `source_*` frontmatter 填写来源与状态。

> 注意：模板位于 skill 的 `assets/three-beams/` 目录，引用概念文档是 `references/three-beams.md`，不要混淆。
