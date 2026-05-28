---
name: "supermemory-maintenance"
description: "General reference for Supermemory — the long-term memory and context infrastructure for AI agents. Architecture, API, SDK usage, container tags, processing pipeline, and troubleshooting. Covers concepts, quickstart, and operational patterns."
version: 3
created: "2026-05-28"
updated: "2026-05-29"
source: "https://supermemory.ai/docs/intro"
---

# Supermemory 通用参考

> State-of-the-art memory & context infrastructure for AI agents. 原文：[docs](https://supermemory.ai/docs/intro)

---

## 一、是什么

Supermemory 是 AI agent 的长期/短期记忆和上下文基础设施。#1 on LongMemEval, LoCoMo, ConvoMem 三大基准。提供完整上下文栈：

- **Agent memory** — 从对话中自动学习、提取事实、构建用户画像
- **Content extraction** — 支持 PDF/网页/图片/视频等多种格式
- **Managed RAG** — 语义搜索 + 混合检索
- **Connectors** — 自动同步外部数据源

---

## 二、核心架构：Document → Memory

Supermemory 不是文件存储，是**活的知识图谱**。

```
Documents (原始输入)    →   Processing Pipeline   →   Memories (知识单元)
PDF / 网页 / 文本            队列→提取→分块→嵌入→索引      语义片段，可搜索，有关系
```

### Document（文档）
原始材料：上传的 PDF、保存的网页、粘贴的文本、图片、视频

### Memory（记忆）
Supermemory 处理后的知识单元：
- 语义分块，嵌入向量化
- 通过关系连接（Updates / Extends / Derives）
- 动态更新

> 上传 50 页 PDF → 拆成数百条互联记忆，每条理解上下文和关系。

---

## 三、记忆关系

| 关系 | 含义 | 示例 |
|------|------|------|
| **Updates** | 新信息**替换**旧信息 | "你在 Supermemory 工作"→"你升任 CMO" |
| **Extends** | 新信息**丰富**已有记忆 | 角色信息 + 具体工作内容 |
| **Derives** | 从模式中**推理**出新知 | "Dhravya 是创始人"+"在 Supermemory 工作"→推断关系 |

系统用 `isLatest` 标记最新版本，搜索自动返回当前信息。

---

## 四、处理管线

| 阶段 | 说明 |
|------|------|
| `queued` | 等待处理 |
| `extracting` | 内容提取中 |
| `chunking` | 创建记忆片段 |
| `embedding` | 生成向量 |
| `indexing` | 建立关系 |
| `done` / `dreaming` | 完全可搜索 |

> 大文件耗时：100 页 PDF ~1-2分钟，1 小时视频 ~5-10分钟。小文本 3-8 秒。

---

## 五、SDK 快速上手

**安装**：
```bash
pip install supermemory
export SUPERMEMORY_API_KEY="sm_x...from supermemory import Supermemory

client = Supermemory()

# 1. 获取画像 + 相关记忆
profile = client.profile(container_tag="user-id", q="user's last message")
context = "\n".join(profile.profile.static + profile.profile.dynamic)

# 2. 注入 LLM
messages = [{"role": "system", "content": f"User context:\n{context}"}, ...]

# 3. 存储对话
client.add(content="conversation text", container_tag="user-id")
```

---

## 六、关键 API

| 操作 | SDK | 说明 |
|------|-----|------|
| 添加文档 | `client.documents.add(content, container_tags=[...])` | 原始内容 |
| 添加对话 | `client.add(content, container_tag=...)` | 自动提取记忆 |
| 语义搜索 | `client.search.memories(q, container_tag, limit, search_mode)` | hybrid / memories / documents |
| 获取画像 | `client.profile(container_tag, q)` | static + dynamic facts |
| 列出文档 | `client.documents.list(limit)` | 含 `dreaming_status` |
| 获取单文档 | `client.documents.get(id)` | 含完整 `content` |
| 删除记忆 | `client.memories.forget(id, container_tag)` | 按 ID 删除 |

### 搜索模式
- `hybrid`（默认）— 混合检索
- `memories` — 仅记忆对象
- `documents` — 仅文档对象

---

## 七、Container Tags（多租户/过滤）

`container_tag` 是 Supermemory 的数据隔离机制——类似"记忆池"。

- 不同 agent/profile 用不同 tag 隔离记忆
- `client.profile(container_tag=...)` 只召回该池的画像
- 搜索也限定 `container_tag`

**本环境配置**：
| Profile | Container Tag |
|---------|---------------|
| default（小黄） | `hermes` |
| regent（太子） | `hermes-cabinet` |
| pi（Windows） | `Pi`, `sm_project_cli` |

---

## 八、Hermes 内置工具

Hermes Supermemory provider 注册 4 个工具：

| 工具 | 对应 SDK |
|------|----------|
| `supermemory_store` | `client.documents.add()` |
| `supermemory_search` | `client.search.memories()` |
| `supermemory_profile` | `client.profile()` |
| `supermemory_forget` | `client.memories.forget()` |

配置：`~/.hermes/profiles/<profile>/supermemory.json`

---

## 九、常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| store 返回 ID 但搜索 content 空 | 文档还在 dreaming（索引中） | 等 3-8 秒后重试 |
| profile static_count=0 | 新容器无积累 | 正常，dynamic 会先有数据 |
| 403 | container tag 未授权 | 检查 API key 权限或换 tag |
| search 返回 unrelated | 查询太短或 search_mode 不对 | 用更具体的 query 或切换 search_mode |
| 写入慢 | 大量文档同时写入 | 分批，每批 ≤10 条 |
| forget 404 | memory ID 是 doc_id 不是 mem_id | 用 search 找到正确 ID 再删 |

---

## 十、文档索引

完整文档树：https://supermemory.ai/docs/llms.txt
关键页面：
- 概览：https://supermemory.ai/docs/intro
- 快速开始：https://supermemory.ai/docs/quickstart
- 工作原理：https://supermemory.ai/docs/how-supermemory-works
- 图记忆：https://supermemory.ai/docs/graph-memory
- API 参考：https://supermemory.ai/api-reference
- Dashboard：https://app.supermemory.ai

---

*来源：https://supermemory.ai/docs 官方文档，整理于 2026-05-29*
