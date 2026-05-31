# qmd 向量检索 自动部署指南

v3.0 知识增强功能依赖 qmd MCP 服务。当 MCP 服务不可用时，按此指南自动部署。

## 检测 qmd 是否可用

```bash
# 1. 检查 qmd 命令
which qmd 2>/dev/null && echo "OK: qmd 已安装" || echo "MISSING: qmd 未安装"

# 2. 检查 MCP 配置
grep -q '"qmd"' ~/.mcp.json 2>/dev/null && echo "OK: MCP 已配置" || echo "MISSING: MCP 未配置"

# 3. 检查索引状态（需要 qmd 已安装）
qmd status 2>/dev/null | grep -q "obsidian" && echo "OK: obsidian 集合已存在" || echo "MISSING: 需要创建集合"

# 4. 检查 embedding 是否完成
qmd status 2>/dev/null | grep -q "embeddings" && echo "OK: 向量索引存在" || echo "MISSING: 需要运行 qmd embed"
```

## 自动部署流程

按顺序执行，已完成的步骤跳过。

### Step 1: 安装前置依赖

```bash
# Bun（如未安装）
if ! which bun >/dev/null 2>&1; then
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

# Homebrew SQLite（qmd 需要，macOS 自带的不够）
brew list sqlite >/dev/null 2>&1 || brew install sqlite
```

### Step 2: 安装 qmd

```bash
if ! which qmd >/dev/null 2>&1; then
  bun install -g github:tobi/qmd
fi

# 验证
qmd status
```

> 安装时 `Blocked 1 postinstall` 和 Windows 404 警告可安全忽略。

### Step 3: 创建 Collection 并索引

```bash
VAULT="$HOME/Obsidian/AlexCai"

# 创建集合（如不存在）
qmd collection list 2>/dev/null | grep -q "obsidian" || \
  qmd collection add "$VAULT" --name obsidian

# 添加语义描述
qmd context add qmd://obsidian "个人知识库，中文笔记，涵盖工作、学习、阅读等"

# 向量索引（首次约 5-15 分钟，增量更新秒级）
qmd embed
```

### Step 4: 配置 MCP

**关键**: MCP 配置在 `~/.mcp.json`（不是 `~/.claude/settings.json`）。

先读取现有 `~/.mcp.json`，然后在 `mcpServers` 中合并添加 `qmd` 条目（不要覆盖其他 MCP 服务器配置）：

```json
{
  "mcpServers": {
    "qmd": {
      "command": "<QMD_PATH>",
      "args": ["mcp"],
      "env": {
        "QMD_RERANK_MODEL": "hf:gpustack/jina-reranker-v1-tiny-en-GGUF/jina-reranker-v1-tiny-en-FP16.gguf"
      }
    }
  }
}
```

- `<QMD_PATH>`: 运行 `which qmd` 获取绝对路径（通常 `~/.bun/bin/qmd`）
- `QMD_RERANK_MODEL` **必须设置**: 默认 reranker 在 MCP 长连接进程中会挂起，jina-tiny 解决此问题

### Step 5: 验证

部署完成后需要重启 Claude Code。在新会话中测试：

```bash
# CLI 验证
qmd vsearch "项目管理" -c obsidian -n 3
```

MCP 验证：在 Claude Code 中调用 `mcp__qmd__vsearch` 搜索任意关键词。

> 首次 vsearch 会下载 Query Expansion 模型 (~1.28GB)，需等待约 30 秒。后续调用秒级完成。

## MCP 工具速查

| MCP 工具 | 用途 | 中文推荐度 |
|----------|------|-----------|
| `mcp__qmd__vsearch` | 向量语义检索 | **首选** — 中文效果好 |
| `mcp__qmd__search` | BM25 关键词检索 | 中文差 — 仅适合英文/精确匹配 |
| `mcp__qmd__query` | 混合检索 + Reranker | 质量最高但较慢 (3-5s) |
| `mcp__qmd__get` | 按路径获取单文档 | 读取搜索结果全文 |
| `mcp__qmd__multi_get` | 批量获取文档 | 批量读取 |
| `mcp__qmd__status` | 索引状态 | 检查健康状态 |

## 知识增强中的使用策略

knowledge-enricher agent 应按以下优先级搜索用户 Obsidian 知识库，为战略分析补充背景知识和关联洞察：

1. **vsearch** (默认): 对分析主题的关键词执行 `mcp__qmd__vsearch`，collection=obsidian，取 relevance > 0.5
   - 搜索维度：主题关键词、行业术语、相关企业名、历史事件
   - 目标：发现用户已有的相关笔记、历史分析、阅读摘录
2. **get**: 对高相关结果 (relevance > 0.7) 用 `mcp__qmd__get` 读取全文，提取可用于当前分析的事实、数据、观点
3. **query** (仅 deep 模式): 需要最高质量语义匹配时用 `mcp__qmd__query`，适合复杂多维度主题
   - 注意：首次调用可能较慢 (3-5s)

### 战略分析场景的搜索模式

| 分析类型 | 推荐搜索关键词 | 说明 |
|----------|---------------|------|
| 行业分析 (industry) | 行业名+关键企业+技术趋势 | 查找用户对该行业的历史笔记 |
| 现象分析 (phenomenon) | 现象描述+因果关键词+影响范围 | 关联已有的现象观察记录 |
| 企业分析 (enterprise) | 企业名+产品线+竞争对手 | 补充企业相关的背景资料 |
| 趋势分析 (trend) | 趋势关键词+时间跨度+驱动因素 | 对比历史趋势笔记 |
| 比较分析 (comparison) | 比较对象A+比较对象B+对比维度 | 查找已有的对比分析 |
| 探索性分析 (exploratory) | 核心问题+相关领域+假设关键词 | 广泛搜索激发灵感 |

## 索引维护

qmd 的 `update` 和 `embed` 是增量更新，无变化时几乎零开销。

维护方式（已在用户系统配置，此处仅供参考）:
- **Claude Code Hooks**: Write/Edit Obsidian 文件后自动触发 `qmd update && qmd embed`
- **launchd**: 每天凌晨 3 点定时更新 (`com.qmd.update`)
- **手动**: `qmd update && qmd embed`

## 故障排查

| 症状 | 解决方案 |
|------|---------|
| `qmd` 命令不存在 | `export PATH="$HOME/.bun/bin:$PATH"` 或重新安装 |
| MCP 工具不可用 | 检查 `~/.mcp.json` 配置，重启 Claude Code |
| vsearch 返回空 | 运行 `qmd embed` |
| query 超时 | 确认 `QMD_RERANK_MODEL` 设置为 jina-tiny |
| 搜不到中文 | 用 vsearch 而非 search（BM25 不支持中文分词） |
| 首次搜索很慢 | 正常，需加载模型到内存（1-2 分钟），后续快 |
