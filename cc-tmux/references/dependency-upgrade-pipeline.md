# Dependency Upgrade Pipeline（2026-06-28 · iii-sdk 0.19.x→0.20.0 实战）

> **适用**：agent-hub / worker 依赖升级（iii-sdk、npm package、transitive dep migration）。核心模式：Codex 规划 → npm registry 发现 → CC 执行 → Codex 独立审核 → Hermes 手动修复审核发现。

## 1. 发现阶段（npm registry 调查，写 Codex plan 前）

**不要假设版本存在或 API 兼容**——先查再规划：

```bash
# 1. 检查目标版本是否存在
npm view <pkg> versions --json | grep '"目标版本"'

# 2. 检查依赖变化
npm view <pkg>@<ver> dependencies peerDependencies --json

# 3. 检查 exports 变化（关键：核心 API 是否仍在根导出）
npm view <pkg>@<ver> exports --json

# 4. 必要时 unpack 验证（最高置信度）
cd /tmp && npm pack <pkg>@<ver>
tar -xzf <pkg>-<ver>.tgz
grep -r "关键导出名" package/dist/
```

**关键区分**：SDK package（npm）vs engine binary（独立 CLI）。两者版本号可能不同步：
- npm packages: `iii-sdk`, `@iii-dev/helpers`, `@iii-dev/observability`
- engine binary: `~/.local/bin/iii`（独立安装，不在 npm workspace 内）

## 2. 规划阶段（Codex planning-only）

给 Codex 的 prompt 必须包含：

```markdown
## 需要的信息

1. 当前依赖版本和 import 面：检查所有 `package.json` 中的依赖版本
2. worker 源代码中实际使用的 API（`registerWorker`, `ISdk` 等）
3. config.yaml 中的版本注释
4. 文档中的版本引用

## 输出要求

1. 需要改动的文件清单
2. 兼容性层设计（如创建 `iii-compat.js`）
3. 升级步骤（按 worker 顺序）
4. 回滚方案
5. 验证命令
```

## 3. 执行阶段（CC execution）

CC 任务包必须包含：

```yaml
约束:
  - npm install 在每 worker 目录执行（不是全局）
  - lockfile 会同步更新——这是预期行为
  - 不提交，不改 engine 二进制
  - 兼容性层代码放 iii/workers/shared/
  - 兼容性测试放 iii/workers/shared/test/
```

**常见坑**：
- `npm install` 会连带升级 `^` 范围的其他包（如 `@openai/codex`）→ lockfile diff 超出预期范围
- `lockfileVersion` 可能因 npm 版本不同而变化
- 没有 `node_modules` 的 shared 目录：兼容性测试必须用 injectable loader 模式，不 import 真实 SDK

## 4. 审核阶段（Codex independent audit）

Codex 审核 checklist：

```yaml
客观项:
  - node --test: 全量回归通过
  - git diff: 无意外文件变更
  - npm view: 确认新依赖已安装
  - package-lock.json: 版本号正确

主观项:
  - 兼容性层 API 完整（所有承诺的导出）
  - 兼容性测试覆盖所有导出
  - 文档版本引用一致
  - 无 scope creep（npm install 连带的非目标包升级）
```

**Codex 常见发现**：
1. 缺失关键导出（如 `detectSdkVersion`）
2. lockfile 连带升级非目标包（scope creep）
3. 注释与实际版本不一致（如 config.yaml 写 `v0.20.0` 但 binary 是 `v0.19.7`）

## 5. 修复阶段（Hermes manual fix）

Codex `NEEDS_FIX` 后，**不要自动再调 CC**（Pitfall #37：≤3 轮 × ≤2 次拒绝规则）。

**手动修复条件**：
- 修复范围小（<30 行）
- 位置精确（已知文件和行号）
- 纯代码改动（不涉及 npm install / 文件系统操作）

流程：
1. 读文件确认当前状态
2. `patch` 精确修改
3. 跑测试验证
4. 提交

## 6. 兼容性层设计（iii-compat 模式）

```javascript
// 单点 seam 隔离版本差异
export const SUPPORTED_RANGE = '>=0.19.0 <0.21.0';
export const III_SDK_VERSION = process.env.III_SDK_VERSION || '当前版本';
export async function getRegisterWorker(loader) { /* 版本适配 */ }
export function getEngineUrl(env) { /* env 解析 */ }
export async function detectSdkVersion(cwd) { /* 运行期检测 */ }
export async function createWorker(name, opts) { /* 便利工厂 */ }
```

**未来升级**：改 `SUPPORTED_RANGE` + package.json 版本号 → 跑测试 → 完。API breaking change 时才加适配分支。

## 7. OB 文档同步

升级完成后必须更新：
- `agent-hub 路线图.md`：运维事件区追加升级记录
- `agent-hub 架构设计.md`：版本标注更新
- `iii/config.yaml`：注释区分 SDK vs engine 版本
- `docs/ops/iii-zombie-incidents.md`：记录升级上下文

**关键约定**：如果只升级了 SDK 而 engine binary 未变，config.yaml 注释**必须**写清：
```yaml
# iii worker SDK vX.Y.Z (engine binary still vA.B.C until 修复发布)
```
