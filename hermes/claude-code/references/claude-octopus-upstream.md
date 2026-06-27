# Claude Octopus 上游 MCP 工具全览

> 更新：2026-05-31 · 公网 grounding 验证

## 来源

Mintlify 官方文档：https://www.mintlify.com/nyldn/claude-octopus/advanced/mcp-server

## 关键事实

Claude Octopus MCP server 上游注册 **11 个工具**（非 Hermes MCP bridge 暴露的 5 个）：

### 工作流工具 (8)
| Tool | Phase | Parameters |
|------|-------|-----------|
| `octopus_discover` | Probe | `prompt` |
| `octopus_define` | Grasp | `prompt` |
| `octopus_develop` | Tangle | `prompt`, `quality_threshold?` |
| `octopus_deliver` | Ink | `prompt` |
| `octopus_embrace` | All 4 phases | `prompt`, `autonomy?` |
| `octopus_debate` | Debate | `question`, `rounds?`, `style?`, `mode?` |
| `octopus_review` | Review | `target` |
| `octopus_security` | Security | `target` |

### 自省工具 (2)
| Tool | Purpose |
|------|---------|
| `octopus_list_skills` | List all 44 available skills |
| `octopus_status` | Check provider availability |

### IDE 集成工具 (1)
| Tool | Purpose |
|------|---------|
| `octopus_set_editor_context` | Inject editor state |

## 与 Hermes MCP bridge 的关系

Hermes 的 `references/claude-octopus-hermes-mcp.md` 配置注册 5 个工具（`cc`/`cc_reply`/`cc_timeline`/`cc_transcript`/`cc_report`）——这是 Claude Octopus 上游 11 工具的一个**子集映射**，聚焦于只读/内省类操作。上游的 `octopus_develop`、`octopus_deliver` 等写操作工具在 Hermes bridge 配置中未被暴露。

## 对外沟通建议

- ✅ 「Hermes 暴露了 5 个只读接口」
- ✅ 「上游引擎含 11 个工作流工具」
- ❌ 直接列举 5 个 MCP tool 名（内部 API 表面）
