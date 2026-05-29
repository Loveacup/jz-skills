# Supermemory 诊断三测协议

> 用于验证 Supermemory 写入→索引→检索全链路是否正常。
> 适用于排查 "search content 空" 类问题，区分"瞬态索引延迟"与"持久性后端故障"。

---

## 前置：查设计文档

在动手诊断前，先读 Obsidian 中的架构设计文档：
- 路径：`20-Areas/10_AI实践/三省六部_Hermes/10_制度/Supermemory三省六部记忆架构设计_v2.0.md`
- 检查：当前部署阶段（Phase 1/2/3）、`supermemory.json` 完整性、LRU 缓存部署状态、已知缺口

---

## 测试 1：写入 → 等索引 → 搜索

```python
# 1. 写入一条独特内容
supermemory_store(content="[PROFILE]-TEST-{SEQ}: {timestamp} diagnostic. {unique phrase}.")

# 2. 等 6 秒（超过 3-8s 标准索引窗口）
sleep 6

# 3. 用独特短语搜索
supermemory_search(query="{unique phrase}", limit=3)
```

**通过标准**：搜索结果 top-1 相似度 > 80% 且 content 非空。

**失败**：如果相似度高但 content 空 → **持久性后端故障**，非索引延迟。

---

## 测试 2：Profile 静态事实积累

```python
supermemory_profile(query="current state")
```

**通过标准**：`static_count > 0`（长期稳定事实已固化）。

**失败**：`static_count=0` 而 `dynamic_count` 持续增长 → 记忆固化管线未工作。

---

## 测试 3：配置完整性

```bash
# 1. 检查 supermemory.json 是否包含当前 profile
cat ~/.hermes/supermemory.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.get('profiles',{}).keys()))"

# 2. 检查 API key 是否完整（非截断）
grep SUPERMEMORY_API_KEY ~/.hermes/profiles/<profile>/.env
# 完整 key 格式: sm_ + ~86 chars，不应含字面量 '...'

# 3. 检查 LRU 缓存是否存在
ls ~/.hermes/cache/<profile>.lmdb 2>/dev/null || echo "CACHE MISSING"
```

---

## 判定矩阵

| 测试1 | 测试2 | 测试3 | 结论 |
|-------|-------|-------|------|
| ✅ | ✅ | ✅ | 全链路正常 |
| ✅ | ❌ | ✅ | 记忆固化管线问题（Supermemory 后端） |
| ❌ | ❌ | ✅ | 索引管线故障（Supermemory 后端，联系官方） |
| ❌ | ❌ | ❌ | 客户端配置问题（先修 config，再重测） |
| ✅ | ❌ | ❌ | 配置不影响写入但影响固化（补配置后观察） |

---

## 差分诊断：自动采集 vs 显式写入

当测试 1 失败（content 空）但 profile 的 `dynamic_count` 在增长时，做差分对比：

```
# 搜索迁移期旧内容 → 预期有 content
supermemory_search(query="迁移 三省六部 governance")

# 搜索今日 store 写入 → 可能空
supermemory_search(query="{今日写入的独特短语}")

# 检查 profile → 自动采集的上下文有 content
supermemory_profile()
```

**判定**：

| 旧迁移记忆 | 今日 store | 自动采集 | 结论 |
|-----------|-----------|---------|------|
| ✅ | ❌ | ✅ | SDK/API 版本不兼容（迁移时 API 正常，后续变更导致新写入异常） |
| ✅ | ✅ | ✅ | 间歇性索引延迟（等更久或 Dashboard 查 dreaming_status） |
| ❌ | ❌ | ✅ | 显式 store 管道全局故障（自动采集走不同路径） |
| ❌ | ❌ | ❌ | Supermemory 全站故障 |

> **2026-05-29 实测**：迁移期旧记忆 15/15 有 content ✅，当日 store 写入 ~40% 空 content，自动采集正常。判定为 **SDK/API 版本不兼容**（时间相关性），联系 Supermemory 官方排查。

---

## 已知局限

### `supermemory_search` 不返回 metadata

Hermes 内置 `supermemory_search` 工具仅返回 `{id, content, similarity}`，不包含 `department`、`type`、`visibility`、`ttl` 等 metadata 字段。按 v2.0 设计 §5.3 需「按部门分组渲染记忆」，当前工具无法支持。

**临时替代**：若需验证 metadata 是否存入，用 Python SDK 直接调 `client.documents.get(id)` 检查完整文档对象。

### 间歇性特征

G4（content 空）非二态，可间歇出现：同一 session 内，一轮 10/10 全有 content，下一轮 2/3 空。判断时需多轮采样，不凭单次通过即宣告修复。

---

*来源：2026-05-29 regent 诊断 session，基于 v2.0 架构设计文档。*
