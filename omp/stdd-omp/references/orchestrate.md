# orchestrate.mjs 使用手册

`scripts/orchestrate.mjs` 是按需的 STDD-OMP 集成诊断脚本，不是每个任务的强制入口。

## 何时运行

仅在以下情况运行只读 status：

- 首次接入或新 session 需要 gate/agent/hook/Advisor 等可执行集成；
- OMP/skill 版本变化；
- 安装路径、gate、agent 或集成报错；
- L2/L3 准备启用隔离、异步或独立 auditor。

当前 session 内的简单 L1 直接进入四步循环。

## 只读路径

```bash
node scripts/orchestrate.mjs --text
node scripts/orchestrate.mjs
```

可选远程版本检查会访问配置的仓库源：

```bash
node scripts/orchestrate.mjs --repo Loveacup/jz-skills
```

未明确需要版本检查时不要附 `--repo`。

## 写入路径与授权

以下命令会计划或执行安装，不得由 status 结果自动触发：

```bash
node scripts/orchestrate.mjs --install --dry-run
node scripts/orchestrate.mjs --install
node scripts/orchestrate.mjs --install --force
```

- `--install`、`--force`、升级、改配置、登录和凭据操作均需要对应明确授权。
- Full-auto 或普通任务授权不隐含这些权限。
- `--force` 可能覆盖现有文件，应作为单独的高风险动作。

## 当前职责

| 函数 | 用途 |
|---|---|
| `detect()` | 检测 opt-in hook、自定义 auditor 与 native agent 根目录 |
| `readLocalVersion()` | 读取 `references/VERSION` |
| `checkRemote(repo)` | 检查显式配置的远程版本 |
| `planActions(status)` | 生成建议，不执行授权 |
| `installHook({force})` | 安装 hook（写入） |
| `installAuditor({force})` | 安装自定义 auditor（写入） |
| `run({githubRepo})` | 汇总检测与可选版本检查 |

动态导入只在当前 runtime 已确认支持时使用；跨版本主路径是 CLI。

## 退出码语义

退出码描述诊断结果，不是自动安装许可。非零时记录 stderr/状态并按影响处理：

- 与当前 L1 无关：继续 L1，不做安装；
- L2/L3 所需能力缺失：相关能力 BLOCKED；
- runtime error/version drift：报告并在获得授权后修复。

缺少自定义 auditor 不等于没有任何 auditor。先读取当前 runtime roster，按只读审计能力选择；所需 L3 能力确实不存在时才 BLOCKED，不猜固定 agent 名。
