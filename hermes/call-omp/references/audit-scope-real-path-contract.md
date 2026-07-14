# OMP 审计 scope：结构合法不等于可取证

## 症状

委派包使用：

```json
"scope": {
  "include": ["startup/retry policy"],
  "exclude": ["implementation"]
}
```

`gate-verify` 只验证 `scope` 是对象，因此可能通过；但 OMP 的审计 scope 解析器得不到任何真实 `allowed_paths`，最终只能返回“允许路径为空、无法验证”的 concern。

## 正确合同

独立只读审计也必须给真实路径：

```json
"scope": {
  "allowed_paths": [
    "/absolute/repo/path/module.py",
    "/absolute/repo/path/tests/test_module.py",
    "/tmp/design-evidence.md"
  ],
  "denied_paths": ["/absolute/profile/.env"],
  "cwd": "/absolute/repo/path"
}
```

同时保持：

- `criterion`：非空数组；
- `threshold.round_limit/reject_limit`：number；
- `output.format="json"`；
- `output.evidence_required=true`；
- `bundle_only` 时额外提供 `evidence_bundle.path`。

## 设计审计证据基座

如果审的是尚未实现的设计，而不是 diff：

1. 写一个短 evidence markdown，放官方文档原文摘录、当前源码路径、候选策略和明确非目标；
2. 把 evidence 文件与直接相关源码/测试都列入 `scope.allowed_paths`；
3. 只写语义标签不算 scope；审计者必须能现场读取证据；
4. 若本轮因空 allowed paths concern，应 reject，修 scope 后才算实质性新一轮。

## 裁决

- “无法验证”是审计输入失败，不是代码/设计 blocker；
- 不得 accept，也不得写成 pass；
- 修正为真实 allowed paths 后再审；若仍 tool-loop，则按 raw 熔断与独立 reviewer 降级流程处理。
