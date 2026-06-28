# WRR Changelog

## v4.0.0 (2026-06-28)

### 重构
- 从单文件拆分为结构化包 (`wrr/`)
- 统一 Hermes 单一实现，废弃 PI 双轨支持

### 新增
- Exa 模式自动路由（fast/auto/deep-lite/deep）
- `web_similar` 工具（相似内容查找）
- GitHub 引擎（仓库搜索 + activity/popularity/freshness 三维评分；`site:github.com` 自动触发）
- Community 聚合引擎（OpenCLI reddit/twitter/xhs/v2ex + last30days；engagement/recency/quality 三维评分 + 去重；`SearchResult.source_tag`；社区站点 `site:` 自动触发）
- 完整测试覆盖（93%）

### 改进
- 引擎抽象基类，统一接口
- Fallback 预算控制（search/similar 10s；extract 独立 40s，容纳 Exa /contents 慢响应）
- 降级路径记录（fallback_chain）

## v3.12.2 (历史)
- 多运行时自适应（Hermes/PI/Codex/Claude Code）
- Fallback 链：Exa → Brave → SearXNG

## v1.1.0 (历史)
- Hermes plugin 初始实现
- 单文件结构
