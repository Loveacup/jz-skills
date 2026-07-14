# Bundle-only 审计：scope 与终止处理

## 适用场景
对代码审查、架构评估、或其他只读任务使用 `bundle_only` 模式，且审计者只应读取委派方准备的证据目录。

## 委派包的必要结构
`allowed_paths` / `denied_paths` 必须放在 `scope` 对象内，而不是顶层：

```json
{
  "scope": {
    "domain": "…",
    "focus": "…",
    "allowed_paths": ["/tmp/omp-bundle-example"],
    "denied_paths": ["/repo/.git"]
  },
  "evidence_bundle": {"path": "/tmp/omp-bundle-example"}
}
```

若 scope 为空，OMP 正确的行为是拒绝审计；这不是代码审计 verdict，修正包后可重启一次。

## 运行纪律
1. 先用 `omp-start` gate 验证委派包。
2. 明确要求最终只输出合法 JSON：`{severity, evidence, summary}`。
3. R1 因 scope/schema 失败时，修正包后重试一次；不要把失败当作 pass 或代码问题。
4. 若 R2 在证据包上发生持续工具回合、没有终态 JSON，按“沉默/无产物=失败”终止；记录 `rejected`，不采信 raw 中间内容。
5. 无结构化 verdict 时，改由委派方的独立源码取证和其他审查者结论支撑方案，并在交付中透明说明 OMP 未形成结论。

## 反模式
- 不把 scope 放顶层。
- 不用 raw 输出片段替代正式 verdict。
- 不无限重试；schema/scope 修正最多一次，之后升级人工或换审查路径。
