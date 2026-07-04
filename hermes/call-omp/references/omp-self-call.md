# OMP 自调侧：call-omp 只读冒烟 + 递归护栏

> OMP 自调用（OMP 反过来调 call-omp）的调用片段。语义以 `platform-adapters.md`（单一真相源）为准。
> **非安装器、非全平台支持承诺**：只跑一条 mock-only 冷路径冒烟，零 token、不触网、不起 OMP 进程。

## 为什么要单独一份 + 护栏

OMP 是完整 CLI agent。若让 OMP 自己调 call-omp，而 call-omp 又拉起 OMP，就可能**无限自嵌套**、
烧尽 token。因此 omp-self 视图在冒烟脚本**最外层**内置递归护栏。

## 调用

```bash
scripts/call-omp-smoke.sh --platform omp-self [--repo <dir>] [--out <dir>]
# 首行输出：recursion_guard=armed
```

## 递归护栏语义

`scripts/call-omp-smoke.sh` 脚本级实现（不依赖任何外部编排）：

- `--platform omp-self` → 输出 `recursion_guard=armed`（护栏已武装）；
- 读环境变量 `CALL_OMP_SELF_CALL_DEPTH`：
  - `>=1` → 已在一次自调链内 → 输出 `recursion_guard=tripped depth=N`、**退出码 4**、
    **绝不**跑任何嵌套 agent / OMP 调用；
  - `0` / 未设 → 放行本层（本层本就 mock-only，不会真拉起 OMP）。

即：一旦某条链把 `CALL_OMP_SELF_CALL_DEPTH` 置到 1，后续任何 omp-self 冒烟都在最外层短路，
杜绝自嵌套。

## 不做什么

- 不调用真实 `omp` / `omp-send.sh` / `delegate_task`。
- 不装任何依赖、不改全局配置。
- 通过不代表 OMP 自调已获完整平台支持——仅代表骨架冷路径可跑且护栏就位。
