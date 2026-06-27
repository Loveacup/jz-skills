# Supermemory 多 profile 记忆架构设计

完整设计文档位于 Obsidian vault：
`20-Areas/10_AI实践/三省六部_Hermes/10_制度/Supermemory多 profile 记忆架构设计_v1.1.md`

两个版本：
- v1.0 (1035 lines): 基础架构——container_tag 隔离模型、metadata 分类体系、16 profile 配置矩阵、记忆注入策略、五层角色混淆预防、三阶段实施计划
- v1.1 (1671 lines, 2026-05-29): 新增第 11 章——跨记忆池查询机制，含 SDK API 调研结论、12 场景矩阵收敛至 5 条跨池通道、wrapper 显式跨池策略方案（C→E 渐进）、search_policy schema 扩展、审计日志 JSONL 设计

## 核心设计决策

1. **双池隔离**: `container_tag: "hermes"` (小黄私域) vs `"hermes-cabinet"` (regent + 多 profile 共享)
2. **metadata 强制标注**: 写入时必须带 department/type/ttl/visibility，由 wrapper 自动填充 department
3. **五层角色混淆防御**: 写入约束 → 召回过滤 → prompt 标注 → 行为引导 → 审计抽检
4. **跨池查询走 wrapper**: SDK 不支持 OR 语义的跨池查询，由客户端分次调用 + search_policy 控制
5. **渐进实施**: Phase 1 太子试点 → Phase 2 多 profile 全量 → Phase 3 优化监控 → Phase 4 混合广播写

## SDK 关键约束

- `containerTags` 数组是 AND 语义，非 OR
- API key 层无池级权限控制——全部依赖 wrapper
- `client.add(content, container_tag, metadata)` — content 是 positional，其余是 keyword-only
