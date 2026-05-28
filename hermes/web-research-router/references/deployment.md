# Deployment & Sync · 部署与同步

After ANY update to this skill:

1. Sync to ALL Hermes profiles (dynamic discovery):
   ```bash
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/research/web-research-router
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/web-research-router-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/research/web-research-router "$dst"
   done
   ```
2. Update Obsidian doc: `00-Inbox/工具制作_Hermes检索总控与GitHub源码探索_三省六部体系_20260526.md`
   （v3.1.0 增量：SearXNG MCP 整合，作为多引擎广扫的默认起手）
3. `qmd update`
4. Spot-check 2-3 profiles for SKILL.md presence。可 `grep -l "v3.1\|SearXNG" ~/.hermes/profiles/*/skills/research/web-research-router/SKILL.md` 快速验证 v3.1.0 已传播。

## v3.7.0 前置依赖（Exa + Brave + Tavily 主力）

部署到任何 profile 前确认：

- Exa MCP server 在线，`EXA_API_KEY` 已配置（主力 #1，9/9）。
- Brave MCP server 在线，`BRAVE_API_KEY` 已配置（主力 #2，9/9，免费 2000 次/月）。
- Tavily MCP server 在线，`TAVILY_API_KEY` 已配置（深度调研专用，8/9，免费 1000 次/月）。
- SearXNG 实例存活（仅作 `web_url_read` 抓取通道 + 最后兜底搜索；不依赖 SearXNG search 主路径）。
- 验证：`hermes mcp list` 应见 exa/brave/tavily/searxng 四行；`curl -s http://127.0.0.1:32080/ | head -5` 确认 SearXNG 首页。
- 完整 MCP config snippet + `.env` 模板见 SKILL.md `⚙️ MCP Configuration & Deployment` 章节。

## v3.1.0 前置依赖（SearXNG MCP）

部署到任何 profile 前确认：

- SearXNG 本地实例运行中：`curl -s http://127.0.0.1:32080/` 应返回 SearXNG 首页 HTML。
- MCP 服务 `mcp-searxng` 在该 profile 的 gateway 配置中已启用，工具 `mcp_searxng_searxng_web_search` 与 `mcp_searxng_web_url_read` 在 `hermes mcp test searxng` 输出中可见。
- 若 SearXNG 不可达，本 skill 仍能回退到 Exa/Tavily/Brave 单引擎链路——但 SKILL.md 中"默认起手"假设会失效，需在 session 内显式声明跳过 SearXNG 步骤。
