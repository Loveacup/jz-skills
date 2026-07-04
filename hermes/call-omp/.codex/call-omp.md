# Codex 侧：call-omp 只读冒烟

> Codex CLI 侧的 call-omp 调用片段。语义以 `references/platform-adapters.md`（单一真相源）为准。
> **非安装器、非全平台支持承诺**：只跑一条 mock-only 冷路径冒烟，零 token、不触网、不起 OMP 进程。

## 何时用

在 Codex 环境里想快速确认 call-omp 的「结构关口 + 证据包生成」骨架能跑（不发起真实审计、
不烧 token）时用。要真做 audit/execute → 走 Hermes 侧 4 步热路径（见 `SKILL.md`），本片段不复制它。

## 调用

```bash
# 缺省临时新建被审 repo 与产物目录
scripts/call-omp-smoke.sh --platform codex

# 指定被审 repo 与产物目录
scripts/call-omp-smoke.sh --platform codex --repo /path/to/repo --out /tmp/codex-smoke
```

冒烟做三件本地可验证的事：`--help` 自检 → `gate-verify --mode package` → `omp-bundle-code-audit.sh`。
退出码：`0` 通过 · `3` 参数错误 · `1` 内部步骤失败。

## 不做什么

- 不调用真实 `omp` / `omp-send.sh` / `delegate_task`。
- 不装任何依赖、不改 PATH / 全局配置。
- 通过不代表 Codex 已获得完整 OMP 平台支持——仅代表骨架冷路径可跑。
