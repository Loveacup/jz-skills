# Verify 证据纪律

单一职责 = ④Verify 步骤的证据标准、夹逼放行、反幻觉门、软硬失败与心跳。

## 证据阶梯（OMP）

从低到高，验收档越高越往上爬：

| 层级 | 名称 | OMP 机制 | 示例 |
|---|---|---|---|
| ① parse | 静态解析 | `lsp diagnostics` 0 error、config/schema validate | 类型无错误、配置格式合法 |
| ② resolve | 引用完整性 | `lsp references`/依赖 resolve、`grep` 旧符号归零 | 重命名无遗漏、导入路径可解析 |
| ③ live | 运行时实证 | `eval`/`bash` 真跑命令 exit 0、`browser` E2E、`debug` 断点取值 | 测试通过、页面可交互、变量值正确 |

- L0/L1：至少爬到 ①。
- L2：必须爬到 ②。
- L3/full-auto：强制爬到 ③（外加 claimcheck）。

> `omp bench --runs 1` 可作为 CLI 级 live 探针例子。标记 `unverified — confirm first`（OMP CLI 子命令，非本 skill 工具），生产先用 `eval`/`bash`/`browser`/`debug`/`lsp` 等已确认机制。

## 夹逼放行第三态

终态不可观测/强制成本过高时，沿阶梯爬到可行上限，用**两端夹逼**替代直接观察：
- 配置端证开关接对（parse 层）
- 运行端证候选真活（live 层以可观测代理证）

**必须满足**：
1. 缺口写残留留账（明确标注「未终验，夹逼放行」）
2. 论断降格标注（前瞻/未终验）
3. 缺一退回沉默即失败

夹逼 ≠ inference-based approval——有证据锚的两端夹逼，不是推理猜测。

## claimcheck 反幻觉门

- 每条 verdict **必须**附可定位证据锚（`file:line` / exit code / 日志行 / `agent://<id>`）
- 无锚或锚不可达 → 判不通过，打回
- 整轮不可锚率 > 40% → 本轮作废重跑
- **无人值守强制开**

示例：

```text
✅ PASS: verifyArtifact('./dist/app.js') → exit 0 [eval js, line 12]
✅ PASS: lsp diagnostics → 0 errors [lsp, src/app.ts]
❌ FAIL: "should be fast" → 无可定位证据锚，打回
```

## 软/硬失败两态 + 心跳

| 态 | 定义 | 动作 |
|---|---|---|
| 硬失败 | regen 达 3（`gates.mjs counter`） | 停升级，输出审计报告，升级人工 |
| 软失败 | 超时/崩溃/部分产出 | 降级放行 + 标低置信度 + 不阻塞下游 + 可降档；绝不静默当通过 |
| 沉默即失败 | 约定时间无 turn-done | 判卡死→重派 |

**心跳纪律**：
- executor 每阶段发 `irc` 进度
- `2×心跳间隔` 无更新 = 判卡死 → 重派
- 硬上限：`task.maxRuntimeMs`
