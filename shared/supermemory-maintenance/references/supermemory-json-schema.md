# supermemory.json 配置模板

> Hermes Supermemory provider 的 profile-to-container_tag 映射文件。
> 缺失时 `supermemory_store` 静默写入错误池，导致迁移记忆与自然记忆分裂。

---

## 文件位置

两处均有效（Hermes 按优先级读取）：

1. **全局**（推荐）：`~/.hermes/supermemory.json` — 集中管理所有 profile
2. **Per-profile**：`~/.hermes/profiles/<profile>/supermemory.json` — 单 profile 覆盖

---

## 最小配置（单 profile）

```json
{
  "profiles": {
    "regent": {
      "container_tag": "hermes-cabinet",
      "search_policy": "global",
      "cross_pool_read": true
    }
  }
}
```

---

## 完整配置（16 profiles）

```json
{
  "profiles": {
    "regent": {
      "container_tag": "hermes-cabinet",
      "search_policy": "global",
      "cross_pool_read": true
    },
    "default": {
      "container_tag": "hermes",
      "search_policy": "department",
      "cross_pool_read": false
    },
    "auditor": {
      "container_tag": "hermes-cabinet",
      "search_policy": "global",
      "cross_pool_read": true
    },
    "archivist": {
      "container_tag": "hermes-cabinet",
      "search_policy": "global",
      "cross_pool_read": true
    }
  }
}
```

> 注：auditor、archivist 与 regent 共享 `hermes-cabinet` 池 + global 视图。其余部门 profile 使用 `department` 策略，仅读写自身 container_tag。

---

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `container_tag` | string | Supermemory container tag，决定写入/搜索的记忆池。**必须与迁移时使用的 tag 一致** |
| `search_policy` | `"global"` \| `"department"` | global = 可跨池读取；department = 仅读写自身池 |
| `cross_pool_read` | bool | 是否允许读取其他 profile 的记忆池 |

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
