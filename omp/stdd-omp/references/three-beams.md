# 三梁项目骨架

三梁是项目的最小可控上下文：L1 需求、L2 实现、L3 控制。

## Context Pyramid

```text
           L1 Requirements
          /               \
    L2 Implementation    L3 Control
              \         /
            派生路线图
```

- L1 决定「做什么、为什么」。
- L2 决定「怎么做、影响面」。
- L3 决定「怎么切、怎么审、怎么停」。
- 路线图是 L1/L2/L3 的派生投影，不是独立梁。

## 每梁的 OMP 载体

| 梁 | 内容 | OMP 载体 |
|---|---|---|
| L1 | 需求、用户、验收、反范围 | `context-files` / `SYSTEM.md` / `assets/three-beams/L1-requirements.md` |
| L2 | 设计决策、依赖、接口、风险 | `assets/three-beams/L2-implementation.md` / plan |
| L3 | 任务切片、审计链、退出条件 | `assets/three-beams/L3-control.md` / `todo` + `plan` |

## 防变重护栏

1. **L1 不变原则**：一次 session 内 L1 一般不变；若变，必须重走 Accept。
2. **L2 决策最小化**：不做预测性抽象；每个决策对应一条验收项。
3. **L3 切片可丢弃**：slice 失败可单独放弃，不影响其他 slice。
4. **同步纪律**：任何变更必须同步回三梁；不能只改代码不改文档。

## 模板使用

- `assets/three-beams/L1-requirements.md`
- `assets/three-beams/L2-implementation.md`
- `assets/three-beams/L3-control.md`

复制到项目目录后按 `source_*` frontmatter 填写来源与状态。

> 注意：模板位于 skill 的 `assets/three-beams/` 目录，引用概念文档是 `references/three-beams.md`，不要混淆。
