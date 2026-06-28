# orchestrate.mjs 使用手册

`scripts/orchestrate.mjs` 是 STDD-OMP 的启动自检脚本，**默认只读**，不会修改用户环境。

## 设计原则

- **先检测，后安装**：默认 `status` 模式只收集信息；`--install` 才写文件。
- **不覆盖已有文件**：`--install` 默认跳过已存在的 hook/agent；需要覆盖时加 `--force`。
- **可配置 GitHub 源**：通过 `STDD_OMP_GITHUB_REPO` 或 `--repo` 指定；未配置则跳过版本检查。
- **本地路径优先**：所有存在性判断使用 `os.homedir()` + `path.join`，不依赖 `skill://` URL 解析。

## 主路径：CLI

```bash
node scripts/orchestrate.mjs                         # status only, read-only
node scripts/orchestrate.mjs --repo Loveacup/jz-skills       # include version check
node scripts/orchestrate.mjs --install --dry-run     # preview installs
node scripts/orchestrate.mjs --install               # install missing only
node scripts/orchestrate.mjs --install --force       # install + overwrite
```

## 导出函数（可选，Node 动态导入可用）

在支持本地 `.mjs` 动态导入的环境（如 Node CLI）可用；当前 OMP 内置 Bun eval 对此外部 `.mjs` 动态导入不稳定，因此**主路径应为 CLI**：

```js
const o = await import('file:///path/to/scripts/orchestrate.mjs');
const status = await o.run();
const status = await o.run({ githubRepo: 'Loveacup/jz-skills' });
```

| 函数 | 用途 |
|---|---|
| `detect()` | 检测 hook、auditor、native agent 根目录状态 |
| `readLocalVersion()` | 读取 `references/VERSION` |
| `checkRemote(repo)` | 查询 GitHub latest release（未配置 repo 则跳过） |
| `planActions(status)` | 根据状态生成建议 actions |
| `installHook({force})` | 拷贝 hook 到 native lane |
| `installAuditor({force})` | 拷贝 auditor 到 native lane |
| `run({githubRepo})` | 完整检测 + 版本检查 + actions |

## CLI 用法

```bash
# 只读检测
node scripts/orchestrate.mjs

# 包含 GitHub 版本检查
node scripts/orchestrate.mjs --repo Loveacup/jz-skills

# 查看会安装什么，但不写文件
node scripts/orchestrate.mjs --install --dry-run

# 安装缺失项（不覆盖已有）
node scripts/orchestrate.mjs --install

# 安装并强制覆盖
node scripts/orchestrate.mjs --install --force
```

## 退出码

| 码 | 含义 | 处理建议 |
|---|---|---|
| 0 | 全部正常 / 无需操作 | 直接开始 STDD 微循环 |
| 1 | 运行时错误 | 查看 stderr |
| 2 | 缺少 hook 或 auditor | 运行 `--install` 或手动复制 |
| 3 | 本地版本落后于远程 | 更新 skill 到最新版 |

## 配置 GitHub 仓库源

```bash
# 环境变量
export STDD_OMP_GITHUB_REPO=Loveacup/jz-skills

# 或完整 URL
export STDD_OMP_GITHUB_REPO=https://github.com/Loveacup/jz-skills
```

未配置时，`remote_version` 为 `null`，`sync_status` 为 `unknown`，不会报错。

### Native agent 根目录覆盖

orchestrator 按以下优先级定位 native lane：

```text
PI_CODING_AGENT_DIR
  -> PI_CONFIG_DIR/agent
  -> ~/.omp/agent
```

对应 OMP 的 `PI_CODING_AGENT_DIR` / `PI_CONFIG_DIR` 环境变量，与 profile 隔离一致。

## 典型工作流

```text
1. 触发 stdd-omp
2. 运行 orchestrate.mjs status
3. 解析 actions：
   - install-hook → ask 用户确认 → --install
   - sync-version → 提示更新
   - warning → native_agent_root 为空，或 `--repo`/`STDD_OMP_GITHUB_REPO` 格式无效（默认 ~/.omp/agent/，可被 PI_CODING_AGENT_DIR / PI_CONFIG_DIR 覆盖）
4. auditor 默认使用内置 `reviewer`/`oracle`；可选把 `assets/stdd-auditor.agent.md` 复制到 `~/.omp/agent/agents/stdd-auditor.md` 作为自定义增强
4. 确认安装完成后再进入四步微循环
```

## 与 SKILL.md 的集成

`SKILL.md` 的「强制入口」要求每次触发先运行 orchestrator，根据 `actions` 决定是否进入安装模式，再执行 STDD 微循环。
