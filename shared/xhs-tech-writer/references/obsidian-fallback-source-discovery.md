# Obsidian Vault 作为备选源发现

> 当 xhs-crawler 因 cookie 过期 / CDP 不可用而无法提取小红书笔记内容时，Obsidian vault 可作为风格提取的备选源。

## 触发条件

以下任一条件满足时执行此流程：
1. `xhs_cloak_extractor.py` 超时（>120s）
2. `xhs_extractor.py` CDP 连接失败（ECONNREFUSED）
3. `parse_xhs_url.py` 返回"页面不见了"（cookie 过期）
4. 用户说"ob 里有/知识库里有"

## 发现流程

### Step 1: 从小红书链接推测关键词

从用户提供的链接标题或描述中提取关键词：
- 例："半年迭代20+版本，我的 Obsidian × Ai方法论" → 关键词：`Obsidian` `Ai方法论` `半年`
- 例："约束即自由：重塑 Ai 协作的 STDD思维方法" → 关键词：`约束即自由` `STDD`

### Step 2: 搜索 Obsidian vault

```bash
# 用 search_files 在 vault 搜关键词
search_files(pattern="Obsidian.*Ai.*方法|STDD|约束即自由", target="content", path="<vault_path>", file_glob="*.md")
```

优先顺序：
1. `00-Inbox/` — 小红书文案常存于此
2. `20-Areas/` — 方法论文档
3. `50-Self/` — 个人笔记

### Step 3: 验证命中文件

找到候选文件后：
- `read_file` 前 20 行确认是否为小红书文案（有 `#小红书笔记` type / 标题匹配 / emoji 分节）
- 不是小红书原文但内容相关（如方法论文档）→ 也可用于风格提取（标题结构、emoji 密度、段落节奏）

### Step 4: 告知用户来源

```
✅ 在 Obsidian 找到原文：`<文件路径>`
从这份文档提取风格特征。
```

## 常见匹配模式

| 小红书标题片段 | Obsidian 文件命名线索 | vault 位置 |
|-------------|---------------------|-----------|
| "Obsidian × Ai方法论" | `Obsidian-x-AI-方法论-精华分享版.md` | `20-Areas/20_Obsidian方法论/` |
| "STDD" / "约束即自由" | `参考资料_非程序员的STDD实践指南.md` | `30-Resources/50_技术与工程/` |
| "Harness Engineering" | `Harness Engineering — 小红书文案.md` | `00-Inbox/` |
| 其他技术内容 | `小红书_*.md` | `00-Inbox/` |

## 局限性

- 不是所有小红书笔记都有 Obsidian 对应文件
- Obsidian 版可能比发布版更长（含被删减内容）
- 如果 vault 中确实没有 → 用通用风格 + 告知用户
