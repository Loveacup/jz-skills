"""WRR (Web Research Router) — structured package for the Hermes plugin.

v4.0 重构：从单文件 __init__.py 拆为结构化包。
  config    — 常量、fallback order、timeout、预算
  errors    — 异常层级
  schemas   — Search/Extract/Similar 的 options/result dataclass
  engines/  — SearchEngine 抽象基类 + Exa/Brave/SearXNG 实现
  router    — fallback 路由 + 预算控制（search/extract 共用）
  registry  — 引擎注册表
  formatters— Hermes JSON 输出（success/content/details，含 backup_hint）
  tools/    — handle_web_search / handle_web_fetch / handle_web_similar

外部契约（Hermes 工具 schema、返回 JSON 形状、override=True）保持 v3 兼容。
"""

__version__ = "4.0.0"
