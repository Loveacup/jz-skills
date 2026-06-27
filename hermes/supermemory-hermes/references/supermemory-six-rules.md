# Supermemory 操作六条（太子 2026-05-29 实测总结）

## 一、Hermes 工具 ≠ SDK — 不可混用

| | Hermes 内置工具 | Python SDK |
|:--|:--|:--|
| API | `supermemory_store` / `supermemory_search` / `supermemory_forget` | `supermemory.Client.add()` / `client.search()` |
| 管道 | 走 `/v1/add` 等端点 | 走 SDK 内部管道 |
| 故障表现 | 可能不同 | 可能不同 |

**结论**：两者底层管道不同，混用导致"用 A 写入、用 B 搜不到"。选择一个并坚持。

## 二、两池隔离 — 设计如此

| Profile | 池名 | Wrapper ID |
|:--|:--|:--|
| `default`（小黄） | `hermes` | 2 |
| `regent`（太子）+ 14 multi-agent | `hermes-cabinet` | 3 |

- 两池写入互不干扰——**这是架构决策，不是 bug**
- 跨池查询需 `~/.hermes/scripts/supermemory_crosspool.py` 包装
- 跨池写入通过 wrapper 间接通路

## 三、必查 supermemory.json — 最常见陷阱

**路径**：`~/.hermes/supermemory.json`

**模板字段**：
```json
{
  "wrapper_id": 2,
  "pool_name": "hermes",
  "api_url": "http://..."
}
```

**症状**：wrapper_id 或 pool_name 配错 → 写入返回 ID 但搜索不命中。**每次排查先从这开始。**

## 四、假阴性 — `hermes memory status` 报错可忽略

- 此命令 ping `/health` 端点
- Supermemory 容器可能不暴露此端点或返回格式不匹配
- 报红不代表功能不可用
- **以 `supermemory_search` 实际能否召回为准**

## 五、content 空 — Dynamic Dreaming 后端问题

- 索引管道断裂后（如 2026-05-29 03:00 起），写入返回正常 ID 但搜索不命中
- 根因在 Supermemory 后台的 Dynamic Dreaming 索引服务，非客户端 bug
- Dashboard 检查 `dreaming_status`
- 正常延迟：3-8 秒；断裂时：30+ 秒仍不出现

## 六、日常操作指南

```bash
# 更新 skill
hermes skill reset supermemory-hermes --restore

# 检查两池 wrapper ID
cat ~/.hermes/supermemory.json

# 测试搜索
hermes -p regent memory search "测试"

# 跨池查询
python ~/.hermes/scripts/supermemory_crosspool.py search "关键词" --source hermes --target hermes-cabinet
```
