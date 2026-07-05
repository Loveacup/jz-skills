# 跨平台适配器（platform adapters）——单一真相源

> call-omp 的底层脚本（`scripts/*.sh` + `scripts/gate/*.sh`）本身**基质无关**：纯参数进、
> 退出码出、不依赖 Hermes 在线。本文件是 Codex / Claude Code / OMP 自调这三种「派生视图」的
> **中央真相源**——其余三个薄文档（`.codex/call-omp.md`、`references/claude-code-call-omp.md`、
> `references/omp-self-call.md`）只是各平台侧的调用片段，语义一律以本文件为准。

## 这不是什么（non-goals）

- ❌ **不是安装器**：不帮你装 `omp` / `jq` / bash；不改 PATH；不写任何平台的全局配置。
- ❌ **不是"全平台支持"承诺**：只提供**一条 mock-only 冷路径冒烟**（`scripts/call-omp-smoke.sh`），
  验证「结构关口 + 证据包生成」在该基质上能跑。真正的 audit/execute 端到端仍走 Hermes 侧
  4 步工作流（start→send→delegate_task→monitor→finish），本适配层**不复制**那条热路径。
- ❌ **不触网、不烧 token**：冒烟脚本绝不调用真实 `omp` / `omp-send.sh` / `delegate_task`。

## 两类冒烟的严格区分

| | mock-only 冒烟 | 真 token 冒烟 | ACP 真实探针（OD-OMP-1） |
| --- | --- | --- | --- |
| 入口 | `scripts/call-omp-smoke.sh` | `references/omp-shell-smoke-test.md` | `scripts/omp-acp-smoke.sh` |
| 是否起 OMP 进程 | ❌ 永不 | ✅ 真拉起 `omp -p --mode json` | ✅ 真拉起 `omp acp` over stdio |
| 是否烧 token | ❌ 零 | ✅ 真实（provider 计费，kimi-code cost=0 除外） | ⚠️ 可能（最小 prompt，kimi-code cost≈0） |
| 覆盖 | `--help` + `gate-verify --mode package` + `omp-bundle-code-audit.sh` | 真实 audit 端到端 + 验收红线 | ACP 协议兼容性 + 7 文件证据包 |
| 谁跑 | 任意基质、CI、离线均可 | 需 `omp` 已装且配 model | 需 `omp` 已装（未配 model 也能探测） |
| 产物 | gate 校验 + bundle manifest | 完整 state/raw/verdict + 归档 | `summary.json` + 6 个证据文件 |

**本适配层只提供 mock-only 冒烟。** ACP 真实探针（OD-OMP-1）是独立手动工具，产出证据但**不改默认通道**。任何文档都不得宣称 mock-only 冒烟等价于真实平台支持或替代热路径。

## 三种派生视图

三者调用的是**同一个** `scripts/call-omp-smoke.sh`，只是 `--platform` 标签与调用侧文案不同：

| 平台 | 视图文档 | `--platform` | 特殊行为 |
| --- | --- | --- | --- |
| Codex CLI | `.codex/call-omp.md` | `codex` | 无 |
| Claude Code | `references/claude-code-call-omp.md` | `claude-code` | 无 |
| OMP 自调 | `references/omp-self-call.md` | `omp-self` | 输出 `recursion_guard=armed`，武装递归护栏 |

调用形态（三平台一致）：

```bash
scripts/call-omp-smoke.sh --platform <codex|claude-code|omp-self> \
  [--repo <被审 repo，缺省临时新建>] [--out <产物目录，缺省临时>]
```

冒烟做三件事（全部本地可验证、零 agent 调用）：
1. `gate-verify.sh --help` / `omp-bundle-code-audit.sh --help`；
2. `gate-verify.sh --mode package` 校验一个内联最小委派包（结构关口连通性）；
3. `omp-bundle-code-audit.sh` 在 repo 上生成只读证据包（`manifest.json` 等）。

退出码：`0` 通过 · `3` 参数错误 · `4` 递归护栏拒绝 · `1` 内部步骤失败。

## OMP 自调递归护栏（recursion guard）

**问题**：若让 OMP 自己调 call-omp，而 call-omp 又拉起 OMP，就可能无限自嵌套、烧尽 token。

**护栏**（`scripts/call-omp-smoke.sh` 脚本级实现，不依赖任何外部编排）：

- `--platform omp-self` → 输出 `recursion_guard=armed`，声明护栏已武装；
- 读环境变量 `CALL_OMP_SELF_CALL_DEPTH`：
  - `>=1` → 判定已在一次自调链内 → 输出 `recursion_guard=tripped depth=N`、**退出码 4**、
    **绝不**跑任何嵌套 agent / OMP 调用；
  - `0` 或未设 → 放行本层冒烟（本层本就 mock-only，不会真正拉起 OMP）。

> 即便冒烟脚本本身永不起 OMP，护栏仍在脚本级前置——这样将来若把 omp-self 视图接到真实
> 自调路径，深度守卫已经在最外层就位，`depth>=1` 一律短路。

## 清单发现（manifest discovery）

三个平台各靠一份最小 `plugin.json` 发现 call-omp——**只是发现清单，不是安装器、不是完整 skill 包装**：

| 平台 | 清单 | `platform` | 特殊字段 |
| --- | --- | --- | --- |
| Codex CLI | `.codex-plugin/plugin.json` | `codex` | — |
| Claude Code | `.claude-plugin/plugin.json` | `claude-code` | — |
| OMP 自调 | `.omp-plugin/plugin.json` | `omp-self` | `recursion_guard`（提示脚本级深度守卫） |

每份清单同形：`name=call-omp`、`version=0.1.0`、`description`（含 mock-only 冒烟入口）、
`platform`、`skills`（指向父仓库 `../`）、`smoke`（指向 `scripts/call-omp-smoke.sh`）。
各平台读到自己的清单后，即知从哪跑冷路径冒烟（`smoke` 字段），以及 skill 本体在父仓库何处（`skills` 字段）。

自检：`bash scripts/call-omp-check.sh` 校验三份清单**齐全 + 合法 JSON + 均引用冒烟脚本**，
全通过退出 `0`，任一缺失/非法/未引用则非零。此脚本纯本地文件校验——不改 PATH、不写全局配置、不烧 token。

## 与 Hermes 热路径的关系

本适配层与主 4 步工作流是**冷/热两条路**：

- 热路径（真活）：`omp-start.sh → omp-send.sh → delegate_task(acp) → omp-monitor.sh → omp-finish.sh`，见 `SKILL.md`。
- 冷路径（本层）：`call-omp-smoke.sh`，只证明结构关口 + 证据包在某基质上可跑，**不**发起真实审计。

选择：要真审计/执行 → 走热路径；只想在新基质上确认"骨架通不通、会不会烧 token" → 跑本层冒烟。
