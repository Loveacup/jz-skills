---
name: "supermemory-maintenance"
description: "Reference for Supermemory — the cloud long-term memory infrastructure for AI agents (api.supermemory.ai, NOT self-hosted/Docker). Covers concepts, SDK/API, container tags, processing pipeline, and operational troubleshooting. Two deployments here: (1) Hermes (provider=supermemory, two pools hermes/hermes-cabinet); (2) multi-machine Claude Code/Codex/pi sharing container tag sm_project_cli. Triggers: supermemory, 双池, container tag, sm_project_cli, hermes-cabinet, supermemory_store/search, 记忆故障. DO NOT use for: local Obsidian memory, Hindsight (retired)."
version: 7
created: "2026-05-28"
updated: "2026-06-04"
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
export SUPERMEMORY_API_KEY="sm_xxx"
```

**最小示例**：
```python
from supermemory import Supermemory

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

> ⚠️ **Supermemory 是云服务**（`api.supermemory.ai`）。本环境**无** Docker 自托管、**无** `~/data/supermemory/` 本地存储——任何"容器部署"说法都是误传。

### 本环境的两套独立部署

两套都用同一个 Supermemory 云账号，但 container tag 互不相干：

**① Hermes**（`memory.provider: supermemory`，配置见 §八）

| 池 | Container Tag | 归属 |
|----|---------------|------|
| 私域 | `hermes` | `default`（小黄）、`cron-worker` |
| 共享 | `hermes-cabinet` | `regent`（太子）、`auditor` 等 cabinet profile |

> **三省六部 16-profile 架构已退役**（历史，见 Obsidian `[[Supermemory记忆架构_Hermes]]`）。`~/.hermes/supermemory.json` 里残留的 16 个 dept 条目无害但已无对应 profile。**线上实际 profile**：`regent / auditor / cron-worker / lane-en|zh|tech|mixed / publisher`。

**② 多机 Claude Code / Codex / pi**（supermemory 插件，非 Hermes）

| 端 | 工具 | Container Tag | 来源标记 `sm_source` |
|----|------|---------------|---------------------|
| MacBook CC | claude-supermemory 插件 | `sm_project_cli` | `claude-code-macbook` |
| Mac mini CC | claude-supermemory 插件 | `sm_project_cli` | `claude-code-macmini` |
| Windows pi | `@ramarivera/pi-supermemory` | `sm_project_cli` | `pi-supermemory-pi` |
| 新机 Codex | codex-supermemory | `sm_project_cli` | `codex_*`（默认） |

> 三端共池 + 双向检索 + 来源 filter 区分。要点：来源区分须走 `/v3/documents`（`sm_source` 仅可 filter、GET 不回显）；pi 须统一到 v3（v3/v4 索引割裂）。详见 Obsidian `[[Supermemory多机共池]]`。

---

## 八、Hermes 内置工具

Hermes Supermemory provider 注册 4 个工具：

| 工具 | 对应 SDK |
|------|----------|
| `supermemory_store` | `client.documents.add()` |
| `supermemory_search` | `client.search.memories()` |
| `supermemory_profile` | `client.profile()` |
| `supermemory_forget` | `client.memories.forget()` |

配置路径（优先级从高到低）：
1. Per-profile：`~/.hermes/profiles/<profile>/supermemory.json`
2. 全局：`~/.hermes/supermemory.json`（集中管理所有 profile，推荐）

**线上真实 schema**（简单，只有 `container_tag`）：

```json
{ "profiles": { "regent": { "container_tag": "hermes-cabinet" },
                "default": { "container_tag": "hermes" } } }
```

> ⚠️ v2.0 设计文档里的 `search_policy` / `cross_pool_read` / `visibility` / LRU lmdb 缓存等字段**从未进入线上配置**，是历史设计稿（见 `references/supermemory-json-schema.md` 顶部说明）。诊断时以线上简单 schema 为准。

缺失时 `supermemory_store` 不报错，静默写入默认/空 tag → 迁移记忆与自然记忆分裂。详见 FAQ §9。

---

## 九、常见问题

### 🔴 双池复发：`hermes-cabinet` → `hermes_cabinet`（最高频，已复发 2 次）

**现象**：Supermemory Dashboard 出现下划线变体池 `hermes_cabinet`（UI 可读化显示为 `hermes cabinet`），新写入进了错误池。

**根因**：`plugins/memory/supermemory/__init__.py` 的 `_sanitize_tag()` 用了 deny-by-default 正则 `[^a-zA-Z0-9_]`，把连字符 `-` 转成 `_` → `hermes-cabinet` 变 `hermes_cabinet`。2026-05-30 首发、2026-06-04 因代码回退**复发**。

**修复**（缺一不可）：
```python
# plugins/memory/supermemory/__init__.py — 正则改为保留连字符
re.sub(r"[^a-zA-Z0-9_-]", "_", raw or "")
```
1. 改正则 + 同步更新 `tests/plugins/memory/test_supermemory_provider.py`，跑 `pytest` 应全绿。
2. 本地验证：provider 加载应显示 `Active. Container: hermes-cabinet.`。
3. **必须重启长驻 gateway / worker**（`launchctl kickstart`）——否则旧进程仍持旧代码，新写入继续进错池。
4. 错误池里的旧文档先做 dry-run 清单，迁移/删除须另请旨，不可直接清。

**判定坑**：`container_tag="hermes cabinet"`（带空格）API 返 400，证明空格不是真 tag、只是 Dashboard 显示名；真实错误池是下划线 `hermes_cabinet`。`sm_source` 一类字段同理——只能 filter、GET/search 不回显，"看不到"≠"没存"。

**双写路径陷阱**：Hermes provider 读各 profile 的 `$HERMES_HOME/supermemory.json`，而 launchd 托管的 Event Bridge daemon 读真实 `$HOME` 的 `~/.hermes/supermemory.json`——session 内 `~` ≠ daemon 的 `$HOME`，诊断跨进程问题须两个路径都查。完整审计见 Obsidian `[[Supermemory双池审计]]`。

---

| 现象 | 原因 | 解决 |
|------|------|------|
| store 返回 ID 但搜索 content 空（瞬态） | 文档还在 dreaming（索引中） | 等 3-8 秒后重试 |
| store 返回 ID 但搜索 content 空（**持久**） | 非索引延迟。可能：SDK 版本不兼容、Supermemory 后端 bug（如 2026-05 Dynamic Dreaming）、`supermemory.json` 配置不完整 | ① 跑 `references/diagnostic-protocol.md` 三测协议确认不是客户端问题；② 查 Obsidian `[[Supermemory双池审计]]` / `[[Supermemory记忆架构_Hermes]]`；③ 若排除客户端原因，联系 Supermemory 官方排查后端 |
| profile static_count=0 | 新容器无积累，或记忆固化管线未工作 | 正常初期 dynamic 先有数据；若持续 0 且 dynamic 增长，检查 Supermemory 后端 profile 聚合是否正常 |
| 403 | container tag 未授权 | 检查 API key 权限或换 tag |
| search 返回 unrelated | 查询太短或 search_mode 不对 | 用更具体的 query 或切换 search_mode |
| 写入慢 | 大量文档同时写入 | 分批，每批 ≤10 条 |
| forget 404 | memory ID 是 doc_id 不是 mem_id | 用 search 找到正确 ID 再删 |
| `supermemory_diag.py` 语法错误 | API key 曾暴露，源码被截断损坏 | 修复 `load_api_key()` 函数中损坏的条件行；见 `agent-memory-manager/scripts/supermemory_diag.py` |
| **迁移记忆与自然记忆不在同一库**（Dashboard 看到两个池） | `supermemory.json` 缺失。迁移时显式指定了 container_tags，但 supermemory_store 无配置映射，默认写入错误 tag | ① 创建 supermemory.json（全局 ~/.hermes/ 或 per-profile）；② 写入 container_tag 映射；③ 详见 references/supermemory-json-schema.md；④ 缺失时不报错，静默分裂——最常见陷阱 |
| `hermes memory status` 报 API key ✗ 但工具实际可用 | status check 从 config.yaml 或插件注册表检测 key，而工具（`supermemory_store/search`）从环境变量读；二者路径不同导致假阴性 | 优先级低——只要工具可用就无需修复 status check。验证方法：直接调 `supermemory_search` 看是否返回结果，而非依赖 status 输出 |
| **SDK 直接调用返回 0 结果，Hermes 内置工具正常**（⚠️ P0 诊断陷阱） | Hermes 的 `supermemory_*` 工具**不是标准 SDK 的薄封装**。同一 API key、同一 endpoint `api.supermemory.ai`、同一 SDK v3.43.0，`search.memories()` 三种 search_mode 全返回 0，`profile()` 返回 static=0/dynamic=0。但 Hermes 内置工具正常返回数据。 | **不要用 SDK 诊断 Hermes Supermemory 状态**——SDK 视角和 Hermes 工具视角是两个不同的数据面。诊断时只信 Hermes 工具的输出。Dashboard 显示两个库分离也可能是同一原因：Dashboard 走 SDK/云端视角，与 Hermes 工具数据面不一致。详细对比见 `references/hermes-vs-sdk-divergence.md` |
| **同步 supermemory-maintenance skill 到各 profile** | skill 在 `~/.hermes/skills` 共享池（profile 经 `external_dirs` 共读），更新后需部署到线上各 profile（regent/auditor/cron-worker/lane-*/publisher），否则不生效 | ① `cd ~/code/jz-skills && git add/commit/push`；② `HOME=/Users/alexcai bash deploy/sync-all.sh hermes`；③ 注意 `~` 在 Hermes session 下解析为 profile home，必须加 `HOME=/Users/alexcai` 前缀 |

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

## 参考文件

- `references/memory-migration.md` — 批量迁移配方、Document vs Memory ID 陷阱、召回验证清单
- `references/diagnostic-protocol.md` — 写入→索引→检索三测协议，区分瞬态延迟与持久性后端故障
- `references/supermemory-json-schema.md` — supermemory.json 配置（线上简单 schema vs v2.0 历史设计字段）
- `references/hermes-vs-sdk-divergence.md` — ⚠️ Hermes 内置工具 vs SDK 行为差异（P0 诊断陷阱：SDK 返回 0 ≠ 数据丢失）

### Obsidian 深度文档（macOS 本机）

位于 `~/Documents/Obsidian/AlexCai/20-Areas/40_技术项目/Supermemory/`：

- `[[Supermemory记忆架构_Hermes]]` — Hermes 两池 + 三省六部历史设计（v2.0，含现状校准 banner）
- `[[Supermemory多机共池]]` — 多机 CC/Codex/pi 共池 `sm_project_cli` 来源区分改造 + Codex 接入
- `[[Supermemory双池审计]]` — 🔴 双池 sanitize bug 全审计（常青，故障排查首选）

历史归档（`40-Archives/`）：三省六部碎片合集、v1.1 设计稿、实施日志、Dynamic Dreaming 故障史。
