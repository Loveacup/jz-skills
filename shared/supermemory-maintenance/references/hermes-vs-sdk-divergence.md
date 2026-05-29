# Hermes 内置工具 vs Supermemory SDK 行为差异

> ⚠️ P0 诊断陷阱：SDK 返回 0 ≠ 数据丢失。**只用 Hermes 工具诊断，不用 SDK。**

---

## 实测对比（2026-05-29）

**环境**：同一 API key（`sm_wRr…`）、同一 endpoint（`api.supermemory.ai`）、同一 SDK v3.43.0

| 操作 | Hermes 内置工具 | SDK 直接调用 | 差值 |
|------|:---:|:---:|:---:|
| `search.memories(q="三省六部 治理")` | 3 条，similarity 64-72%，content 有值 | **0 条**（hybrid/memories/documents 全 0） | 100% vs 0% |
| `profile(container_tag="hermes-cabinet")` | 50 dynamic facts | static=0, dynamic=0 | 50 vs 0 |
| `documents.list(limit=200)` | N/A（工具不支持） | 2 条（仅无 tag 测试文档） | — |
| `store(content=...)` | ✓ saved=true, 返回 ID | ✓ documents.add() 也返回 ID | 均正常 |

---

## 根因分析

Hermes 的 `supermemory_*` 工具**不是标准 SDK 的薄封装**。可能的原因（按可能性排序）：

1. **Hermes 自建 HTTP client** — 绕过 SDK，直接调 Supermemory REST API，使用不同的请求头/参数
2. **认证方式不同** — SDK 用 `Authorization: Bearer`，Hermes 可能用 `x-api-key` 或其他 header
3. **API 版本差异** — SDK 调用 v1 endpoint，Hermes 可能调用 v2 或内部 endpoint
4. **内部缓存/代理层** — Hermes 可能通过中间层（如 gateway 内置缓存）访问 Supermemory

> **确认不作为 SDK bug**：已测试三种 `search_mode`（hybrid/memories/documents）、加/不加 `container_tag`、不同 query —— 全部 0 结果。非偶然。

---

## 诊断铁律

```
❌ 错误做法：用 SDK 查 → 0 结果 → "数据丢了！"
✅ 正确做法：用 Hermes supermemory_search 查 → 验证数据存在
```

### 三步自检

```python
# Step 1: Hermes 工具是否正常？
supermemory_search(query="三省六部", limit=3)
# → 有结果 + content 非空 → 正常 ✅

# Step 2: 非要 SDK 验证？（不建议）
from supermemory import Supermemory
c = Supermemory(api_key=key)
c.search.memories(q="三省六部", limit=3)
# → 0 结果 → 别慌，这是已知差异，不是数据丢失 ⚠️

# Step 3: Dashboard 也走 SDK 视角
# Dashboard 显示两个库分离 / 数据空白 → 
# 不一定代表数据丢失，可能是 SDK vs Hermes 工具的数据面分歧
```

---

## 对 Dashboard 的影响

Supermemory Dashboard 很可能也走 SDK/云端 API 路径，与 Hermes 工具数据面不一致。因此：

- **Dashboard 看到两库分离** → 可能是正常的 SDK 视角，不代表实际使用有问题
- **Dashboard 显示数据少** → 同因，Hermes 工具视角可能有更完整的数据
- **判断数据健康度的唯一标准** → `supermemory_search` + `supermemory_profile`（Hermes 工具）

---

## 已知关联问题

- **G4 content 空**：间歇性出现，同一 session 内可能此轮有、下轮空。与本文档描述的"全 0"不同——G4 是部分文档 content 空，本文档是 SDK 全链路 0 结果。
- **Dynamic Dreaming**：可能加剧数据面不一致。官方已确认 Dreaming 为根因，调查中。

---

*实测于 2026-05-29 regent session。SDK v3.43.0, endpoint api.supermemory.ai*
