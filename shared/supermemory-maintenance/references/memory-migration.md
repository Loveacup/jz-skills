# Supermemory 迁移实战

> 2026-05-29 从内置 MEMORY → Supermemory 全流程记录

---

## ⚠️ Pool 分裂陷阱（迁移后最常见的静默故障）

**现象**：迁移完成、召回验证通过，但之后日常使用 `supermemory_store` 写入的记忆在 Dashboard 中出现在另一个库。

**根因**：迁移脚本显式指定了 `container_tags=['hermes-cabinet']`，确保写入正确池。但 Hermes 的 `supermemory_store` 工具依赖 `~/.hermes/profiles/<profile>/supermemory.json` 获取 container_tag 映射。若该文件缺失或未配置此 profile，`supermemory_store` 会静默写入**默认/空 tag**——与迁移池分道扬镳。

**检测方法**：
```python
# 写入测试记忆
supermemory_store(content="POOL-TEST: <timestamp>")

# 等 8 秒后搜索
supermemory_search(query="POOL-TEST")

# 若搜不到 → pool 分裂
```

**修复**：为该 profile 创建 `supermemory.json`：
```json
{"container_tag": "hermes-cabinet"}
```

> 缺失此文件时 `supermemory_store` 不会报错——这是最危险的地方。迁移验证通过不代表后续日常写入走同一个池。

---

## 关键发现：Document ID ≠ Memory ID

Supermemory 是两阶段架构，写入和搜索返回**不同的 ID**：

```
documents.add(content) → doc_id (如 qzeEWYzLcGEd...)
    ↓ dreaming 处理
search.memories(q)     → mem_id (如 LDP1Uyhpmqtr...)
```

**陷阱**：`supermemory_forget(id=doc_id)` 会 404，因为 forget 操作的是记忆对象，不是文档对象。必须先用 `search` 找到正确的 `mem_id`。

---

## 批量迁移配方

### 1. 准备：读取所有源数据

从 Hermes 内置 MEMORY 提取全部条目（23 memory + 10 user profile）。

### 2. 批量写入（execute_code + SDK）

```python
from supermemory import Supermemory
c = Supermemory(api_key=key, timeout=10)

for content in all_items:
    c.documents.add(
        content=content,
        container_tags=['hermes-cabinet'],
        metadata={'source': 'memory_migration', 'category': cat, 'migration_date': '...'}
    )
```

每次 `documents.add()` 返回 doc_id，写入成功即返回。

### 3. 等待索引（关键步骤）

文档写入后状态：`status='done'` 但 `dreaming_status='dreaming'`。

> **小文本（<1KB）需 3-8 秒索引。批量写入后等 5 秒再搜。**

检查 dreaming 状态：
```python
single = c.documents.get(id=doc_id)
print(single.dreaming_status)  # 'dreaming' → 还在处理，'done' → 可搜索
```

### 4. 逐类验证

按类别分组查询，确认所有迁移内容可召回：

```python
categories = ['governance', 'user_preference', 'hermes_config', ...]
for cat in categories:
    s = c.search.memories(q=f'{cat} specific query', container_tag='hermes-cabinet', ...)
    # 确认 source=='memory_migration' 的结果存在
```

### 5. 压缩源 MEMORY

迁移验证通过后，压缩内置 MEMORY：
- 删除已迁移的环境/工具细节
- 删除重复/过时条目
- 合并重叠条目
- 保留核心治理规则 + 交互模式
- 添加 Supermemory 引用指针

压缩结果：23 → 15 条，配额从超限 → 96%。

---

## 召回验证清单

| 验证项 | 方法 |
|--------|------|
| 文档存在 | `documents.list(limit=200)` 过滤 `metadata.source` |
| 索引完成 | `documents.get(id).dreaming_status == 'done'` |
| 语义搜索 | `search.memories(q=..., container_tag=...)` 每个类别 ≥1 hit |
| Profile 更新 | `profile(container_tag=...).profile.dynamic` 包含新事实 |
| 独立召回 | 用文档标题前 4 词搜索，确认可命中 |
| **Pool 一致性** | `supermemory_store` 写入测试记忆 → 搜索验证可召回，确认日常写入路径也走同一池 |

---

## 容器配置

| Profile | Container Tag | 用途 |
|---------|---------------|------|
| regent | `hermes-cabinet` | 三省六部共享记忆池 |
| default | `hermes` | 小黄独立池 |
| pi | `Pi`, `sm_project_cli` | Windows 机器 |
