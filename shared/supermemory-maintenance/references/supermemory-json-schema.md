# supermemory.json 配置模板

> Hermes Supermemory provider 的 profile-to-container_tag 映射文件。
> 缺失时 `supermemory_store` 静默写入错误池，导致迁移记忆与自然记忆分裂。

---

## 文件位置

两处均有效（Hermes 按优先级读取）：

1. **全局**（推荐）：`~/.hermes/supermemory.json` — 集中管理所有 profile
2. **Per-profile**：`~/.hermes/profiles/<profile>/supermemory.json` — 单 profile 覆盖

---

## 线上真实 schema（以此为准）

线上 `~/.hermes/supermemory.json` 极简——每个 profile 只有一个 `container_tag`：

```json
{
  "profiles": {
    "default":     { "container_tag": "hermes" },
    "cron-worker": { "container_tag": "hermes" },
    "regent":      { "container_tag": "hermes-cabinet" },
    "auditor":     { "container_tag": "hermes-cabinet" }
  }
}
```

- 私域池 `hermes`：`default`（小黄）、`cron-worker`
- 共享池 `hermes-cabinet`：`regent`（太子）、`auditor` 等 cabinet profile
- 文件里可能还残留 16 个三省六部 dept 条目（gongbu/shangshu/...）——**无害但已无对应 profile**，三省六部架构已退役。线上实际 profile：`regent / auditor / cron-worker / lane-en|zh|tech|mixed / publisher`。

---

## ⚠️ 历史设计字段（v2.0 设计稿，从未进入线上）

v2.0 设计文档曾规划 `search_policy` / `cross_pool_read` / `visibility` / 16-profile department 矩阵 / LRU lmdb 缓存等。**这些从未落到线上 `supermemory.json`**，诊断时不要去找它们。仅作历史参考：

```json
// ❌ 设计稿形态，线上不存在
{ "profiles": { "regent": {
    "container_tag": "hermes-cabinet",
    "search_policy": "global",     // 设计稿，未落地
    "cross_pool_read": true        // 设计稿，未落地
}}}
```

完整历史设计见 Obsidian `[[Supermemory记忆架构_Hermes]]`（v2.0）。

---

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `container_tag` | string | **唯一线上有效字段**。Supermemory container tag，决定写入/搜索的记忆池。**必须与迁移时使用的 tag 一致** |
| ~~`search_policy`~~ | — | 历史设计稿，线上无 |
| ~~`cross_pool_read`~~ | — | 历史设计稿，线上无 |

---

## 诊断：验证配置是否生效

```bash
# 1. 检查文件存在
cat ~/.hermes/supermemory.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d.get('profiles',{}).keys()))"

# 2. 写入测试记忆
# 在 agent session 中调用 supermemory_store
# → supermemory_store(content="CONFIG-TEST: {unique_phrase}")

# 3. 搜索验证
# → supermemory_search(query="{unique_phrase}")
# 若能命中且 content 非空 → 配置生效
# 若命中但 content 空 → G4 间歇性问题（索引延迟/API 版本不兼容）
# 若无法命中 → container_tag 映射错误，仍写入错误池
```

---

## 已知问题

- `hermes memory status` 可能报 API key ✗（假阴性），即使工具实际可用。不以此为准——直接调 `supermemory_search` 验证。
- 创建/修改 `supermemory.json` 后无需重启 Hermes——下次 `supermemory_store` 调用时自动读取新配置。
