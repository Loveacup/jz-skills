"""WRR 配置常量。集中管理 fallback 顺序、超时、预算、引擎参数。

从单文件 __init__.py 搬迁而来（v4.0）。所有 volatile 阈值集中于此，便于调参。
"""
import os
from pathlib import Path
from typing import List, Optional

# ── Fallback 顺序（与历史 extension.ts / v3 __init__.py 一致）─────────────
SEARCH_FALLBACK_ORDER = ("exa", "brave", "github", "community", "searxng")
EXTRACT_FALLBACK_ORDER = ("exa", "brave")   # web_fetch：exa 干净正文 → brave 裸抓取
SIMILAR_PROVIDERS = ("exa",)                 # findSimilar 仅 Exa 支持

# ── 单引擎超时（秒）──────────────────────────────────────────────────
ENGINE_TIMEOUT = {
    "exa": 30.0,
    "brave": 10.0,
    "searxng": 10.0,
    "github": 15.0,
    "community": 15.0,
}
DEFAULT_ENGINE_TIMEOUT = 15.0

# ── 预算：fallback 链总响应上限（秒）──────────────────────────────────
TOTAL_BUDGET_SECONDS = 10.0          # search / similar：交互式，求快
# extract 例外：Exa /contents 正文抽取端点可能慢到接近引擎超时（30s），
# 10s 总预算会把 exa 卡在 timeout 并跳过 brave 兜底（budget exceeded）。
# 给 extract 单独的宽预算：容纳 exa 30s engine timeout + brave 10s 兜底。
EXTRACT_BUDGET_SECONDS = 40.0
OPERATION_BUDGET_SECONDS = {
    "search": TOTAL_BUDGET_SECONDS,
    "similar": TOTAL_BUDGET_SECONDS,
    "extract": EXTRACT_BUDGET_SECONDS,
}

# ── 结果数量 / 字符上限 ──────────────────────────────────────────────
DEFAULT_SEARCH_COUNT = 10
MAX_SEARCH_COUNT = 20
DEFAULT_MAX_CHARACTERS = 5000
MAX_MAX_CHARACTERS = 50000

# ── SearXNG：默认引擎(google/ddg/startpage)已失效，仅 bing/baidu 存活；
#    必须显式 language，否则跨语言噪音（见 references/searxng-engine-diagnostics.md）──
SEARXNG_ENGINES = "bing,baidu"
SEARXNG_LANGUAGE = "zh-CN"

# ── Exa：search 随结果带 highlights（官方推荐），作为 citation 源片段 ──
EXA_SEARCH_TEXT_MAX = 500          # search 结果 snippet 上限
EXA_SEARCH_TYPE = "auto"           # neural / keyword / auto
EXA_WITH_HIGHLIGHTS = True

# ── Exa 模式自动路由（质量优先）──────────────────────────────────────
# 查询分类 → 模式选择
EXA_MODE_ROUTING = {
    "factual": "fast",        # 简单事实查询 → 快速响应
    "standard": "auto",       # 标准搜索 → 自动平衡
    "research": "deep-lite",  # 深度研究 → 深度模式
    "academic": "deep",       # 学术/技术深度 → 最深模式
}

# 查询分类关键词
EXA_ACADEMIC_KEYWORDS = ["论文", "综述", "survey", "methodology", "algorithm",
                       "paper", "arxiv", "doi", "citation", "preprint",
                       "peer review", "literature", "state of the art"]
EXA_RESEARCH_KEYWORDS = ["深度", "详细", "全面", "比较", "对比", "分析", "research", "overview", "comparison",
                         "comprehensive", "analysis", "deep", "in-depth", "compare",
                         "优化", "进展", "演进", "设计", "方案", "架构", "实现", "改进",
                         "vs", "versus", "取舍", "选型", "最佳实践", "最新进展"]
EXA_FACTUAL_KEYWORDS = ["什么时候", "多少", "是谁", "日期", "版本", "release", "launch", "price"]

# 各模式超时（秒）
EXA_MODE_TIMEOUT = {
    "fast": 3.0,
    "auto": 5.0,
    "deep-lite": 8.0,
    "deep": 10.0,
}

# ── GitHub 引擎（P1 轻量版：activity + popularity + freshness）─────────
GITHUB_TRIGGER = "site:github.com"            # 查询命中 → 把 github 提到链首
GITHUB_ACTIVITY_LOOKUP = True                 # True: 并发实测 30 天 commit 速度，失败降级
GITHUB_SCORE_WEIGHTS = (0.40, 0.35, 0.25)     # (activity, popularity, freshness)


def github_triggered(query: str) -> bool:
    """查询是否含 site:github.com（自动触发 github 引擎）。"""
    return GITHUB_TRIGGER in (query or "").lower()


# ── 社区聚合引擎（Phase 1：OpenCLI 渠道 + last30days）─────────────────
COMMUNITY_SCORE_WEIGHTS = (0.40, 0.35, 0.25)   # (engagement, recency, quality)
COMMUNITY_SOURCE_TIMEOUT = 10.0                # 每源超时（秒）
COMMUNITY_TOTAL_TIMEOUT = 15.0                 # 总超时（秒）
COMMUNITY_DEFAULT_SOURCES = ("reddit", "twitter", "xiaohongshu", "v2ex")
COMMUNITY_INCLUDE_LAST30DAYS = False           # 重型源；默认仅 site:hn/zhihu/weibo 或研究关键词时启用
COMMUNITY_DEDUP_THRESHOLD = 0.80               # 标题相似度去重阈值
COMMUNITY_TRIGGER_SITES = ("reddit.com", "news.ycombinator.com", "twitter.com",
                           "x.com", "zhihu.com", "weibo.com")
COMMUNITY_PLATFORM_NAMES = ("reddit", "hacker news", "hackernews", "hn",
                            "twitter", "v2ex", "zhihu", "微博", "weibo",
                            "小红书", "xiaohongshu")


def community_triggered(query: str) -> bool:
    """查询是否含社区站点 site: 过滤、平台名称或实践意图（v5.4 自动触发 community）。"""
    import re
    q = (query or "").lower()
    if any(f"site:{s}" in q for s in COMMUNITY_TRIGGER_SITES):
        return True
    if any(re.search(rf"\b{re.escape(p)}\b", q, flags=re.ASCII) for p in COMMUNITY_PLATFORM_NAMES):
        return True
    # v5.4: 实践意图关键词 → 自动触发社区引擎
    return any(kw.lower() in q for kw in PRACTICAL_KEYWORDS)


USER_AGENT = "wrr-hermes/4.0"

# ── MCP 备份：保留 mcp_* 工具作为备份，默认不自动调用，仅在输出附 hint ──
BACKUP_HINT = (
    "需要更强单引擎能力时可显式调用 MCP 备份工具："
    "mcp_exa_* / mcp_brave_search_* / mcp_tavily_* / mcp_searxng_*"
)


# ══════════════════════════════════════════════════════════════════════
# v5.0 路由：mode 分发 + 触发词提升 + RRF 融合（加法式，不改 v4 fallback）
# 真相源：/tmp/wrr-v5.0-stdd-final.md。STDD §3–§6。
# ══════════════════════════════════════════════════════════════════════

RRF_K = 60                                     # Cormack 2009 默认，业界标准

# 连续时间衰减半衰期 τ（小时），按平台
RECENCY_TAU = {
    "twitter": 12.0, "reddit": 12.0,
    "v2ex": 48.0, "hackernews": 48.0, "last30days_en": 48.0,
    "zhihu": 720.0, "weibo": 48.0, "xiaohongshu": 48.0, "last30days_cn": 720.0,
    "default": 72.0,
}

# 意图分类关键词
RESEARCH_KEYWORDS = EXA_RESEARCH_KEYWORDS
DISCOVERY_KEYWORDS = ["有哪些", "盘点", "趋势", "trending", "探索", "推荐", "找", "best", "top",
                      "有没有", "类似", "替代", "取代", "开源", "project", "projects",
                      "工具", "框架", "库", "平台", "sdk", "插件", "plugin",
                      "list of", "awesome", "curated"]

# 触发词（academic/skill；github/community 已在上方定义）
ACADEMIC_KEYWORDS = EXA_ACADEMIC_KEYWORDS
SKILL_KEYWORDS = ["找 skill", "skill 推荐", "推荐 skill", "skill.md",
                  "agent skill", "find skill"]


def academic_triggered(query: str) -> bool:
    """查询命中学术关键词 → 提升 academic 引擎。"""
    q = (query or "").lower()
    return any(k.lower() in q for k in ACADEMIC_KEYWORDS)


def skill_triggered(query: str) -> bool:
    """查询命中 skill 发现意图 → 提升 skill 引擎。"""
    q = (query or "").lower()
    if "skill" in q and any(t in q for t in ("找", "推荐", "有没有", "find", "recommend", "discover")):
        return True
    return any(k.lower() in q for k in SKILL_KEYWORDS)


# ── 本地搜索层触发词（v5.2）──────────────────────────────────────────
# 分层：memory / notes / session 为强信号；scope 为弱信号（需搭配知识类名词）。
LOCAL_MEMORY_KEYWORDS = ["我之前", "之前我们", "上次", "刚才", "记得我", "我记得",
                         "记忆里", "supermemory", "长期记忆", "偏好"]
LOCAL_NOTES_KEYWORDS = ["查笔记", "我的笔记", "笔记里", "知识库", "obsidian", "vault",
                        "qmd", "文档里", "本地文档", "项目文档", "历史报告", "本地搜索"]
LOCAL_SESSION_KEYWORDS = ["历史对话", "会话记录", "聊天记录", "这次会话",
                          "上个 session", "刚才聊", "之前聊"]
LOCAL_SCOPE_KEYWORDS = ["本地", "我的", "我们讨论过", "之前决定", "以前的结论"]
# scope 弱信号需搭配的知识类名词（避免"本地部署 redis"误伤）
_LOCAL_SCOPE_COMBO = ["笔记", "知识库", "文档", "记忆", "历史", "之前", "决定",
                      "note", "memory", "doc"]

# ── 恢复/存档搜索触发词 ──
RECOVERY_KEYWORDS = ["找不到", "丢失", "删除", "不见了", "recover", "恢复",
                     "找回来", "复原", "找回", "被删", "消失", "404",
                     "已删除", "已移除", "missing", "deleted", "gone"]

# ── 开放式兴趣查询（"今天有啥好玩的"→多源探索）──
BROAD_INTEREST_KEYWORDS = ["今天可能感兴趣", "今天有啥", "今天有什么", "今天热点",
                           "今日资讯", "今日热点", "最近有啥", "有什么新鲜",
                           "interesting today", "what's new", "what's happening"]

# v5.4: 实践意图关键词 — 工具使用/操作指南/推荐类查询自动触发社区引擎
PRACTICAL_KEYWORDS = ["怎么用", "如何使用", "使用方法", "操作指南", "教程", "快捷键",
                      "实战", "实践", "经验", "踩坑", "避坑", "最佳实践",
                      "推荐", "值得", "哪个好", "怎么选",
                      "how to", "guide", "tutorial", "shortcuts", "keybindings",
                      "best practice", "tips", "tricks", "gotchas", "worth it"]


def local_triggered(query: str) -> bool:
    """查询是否应进入 local mode（本地优先）。

    保守策略：强信号（memory/notes/session 关键词）直接命中；弱 scope 词
    （本地/我的）必须搭配知识类名词才触发，否则"本地部署/localhost"误入 local。
    """
    q = (query or "").lower()
    strong = LOCAL_MEMORY_KEYWORDS + LOCAL_NOTES_KEYWORDS + LOCAL_SESSION_KEYWORDS
    if any(k.lower() in q for k in strong):
        return True
    if any(k in q for k in LOCAL_SCOPE_KEYWORDS):
        return any(c in q for c in _LOCAL_SCOPE_COMBO)
    return False


def recovery_triggered(query: str) -> bool:
    """查询是否在寻找丢失/删除/不可达的内容 → recovery mode。"""
    q = (query or "").lower()
    return any(k.lower() in q for k in RECOVERY_KEYWORDS)


def broad_interest_triggered(query: str) -> bool:
    """查询是否为开放式兴趣探索 → broad mode（多源并行）。"""
    q = (query or "").lower()
    return any(k.lower() in q for k in BROAD_INTEREST_KEYWORDS)


def classify_intent(query: str) -> str:
    """查询意图分类，返回 7 mode 之一（v5.2 含 local/broad）。显式 mode 由 router 覆盖。"""
    q = (query or "").lower()
    if recovery_triggered(q):       # recovery 优先（"找不到刚才的文件"）
        return "recovery"
    if local_triggered(q):          # 本地记忆/笔记
        return "local"
    if broad_interest_triggered(q): # 开放式探索 → discovery + platform
        return "broad"
    if community_triggered(q):
        return "platform"
    if academic_triggered(q):
        return "academic"
    if any(k.lower() in q for k in RESEARCH_KEYWORDS):
        return "research"
    if any(k.lower() in q for k in DISCOVERY_KEYWORDS):
        return "discovery"
    return "grounding"


# mode → 基础引擎组合
MODE_DISPATCH = {
    "discovery": ("exa", "brave", "community"),
    "broad":     ("exa", "brave", "community", "searxng"),  # 开放式兴趣 → 多源并行
    "grounding": ("exa", "brave"),
    "research":  ("exa", "brave", "community", "academic"),
    "academic":  ("academic", "exa", "community"),
    "platform":  ("community", "exa", "brave"),
    "recovery":  ("brave", "exa", "searxng"),
    # local（v5.2）：本地 4 引擎在前，exa/brave 在后补位。本地引擎在 CLI 环境
    # 不可用时由 router gather 隔离跳过，正好 web 兜底；本地可用时权重碾压外网。
    "local":     ("local_supermemory", "local_session", "local_qmd",
                  "local_obsidian", "exa", "brave"),
}

# mode → {引擎: RRF 融合权重}（D1/D2 对齐 Alex）
_W_DEFAULT = {"exa": 1.0, "brave": 0.9, "community": 0.30, "academic": 0.30,
              "github": 0.25, "skill": 0.25, "searxng": 0.1}
MODE_WEIGHTS = {
    "discovery": {**_W_DEFAULT, "community": 0.50},
    "grounding": {**_W_DEFAULT, "community": 0.40},
    "research":  {**_W_DEFAULT, "community": 0.35, "academic": 0.30},
    "academic":  {**_W_DEFAULT, "academic": 1.0, "community": 0.25},
    "platform":  {**_W_DEFAULT, "community": 1.0},
    "recovery":  {**_W_DEFAULT},
    # local（v5.2）：本地引擎权重高于外网，外网仅低权补位
    "local":     {**_W_DEFAULT,
                  "local_supermemory": 1.0, "local_session": 0.9,
                  "local_qmd": 0.9, "local_obsidian": 0.8,
                  "exa": 0.3, "brave": 0.3, "community": 0.15},
    # broad（v5.2）：开放式兴趣查询，4 引擎并行，社区权重大
    "broad":     {**_W_DEFAULT, "community": 0.55, "searxng": 0.30},
}


# ── 本地搜索层配置（v5.2）────────────────────────────────────────────
LOCAL_MAX_RESULTS_PER_ENGINE = 10       # 单引擎结果上限（与 count 取 min）
LOCAL_MIN_RESULTS = 3                    # local mode 本地结果充足阈值（P1 web 补位用）

# Obsidian 文件扫描限流（强约束：防全盘 find 拖垮 local mode）
LOCAL_OBSIDIAN_MAX_FILES = 2000         # 单次扫描文件数上限
LOCAL_OBSIDIAN_MAX_BYTES = 65536        # 单文件读取前缀字节上限
LOCAL_OBSIDIAN_EXCLUDE_DIRS = (".git", ".obsidian", "node_modules", ".trash",
                               ".smart-env", "attachments")


def obsidian_vault_paths() -> List[Path]:
    """解析 Obsidian vault 路径列表。

    来源：env WRR_OBSIDIAN_VAULTS（os.pathsep 分隔，支持 ~ 展开）。
    doctor 不假定默认 vault 存在；未配置 → 返回空列表（health_check fail）。
    """
    raw = get_env("WRR_OBSIDIAN_VAULTS")
    if not raw:
        return []
    return [Path(os.path.expanduser(p.strip()))
            for p in raw.split(os.pathsep) if p.strip()]

# 触发词 → 引擎（promote 用）
TRIGGER_ENGINES = (
    ("github", github_triggered),
    ("skill", skill_triggered),
    ("academic", academic_triggered),
    ("community", community_triggered),
)


def mode_engines(mode: str, query: str = "") -> list:
    """返回该 mode 的并行引擎组合 = 基础组合 ∪ 触发提升（去重，保序）。"""
    base = list(MODE_DISPATCH.get(mode, MODE_DISPATCH["grounding"]))
    for name, trig in TRIGGER_ENGINES:
        if trig(query) and name not in base:
            base.append(name)
    return base


# ── 学术引擎（v5.0）──────────────────────────────────────────────────
ACADEMIC_SCORE_WEIGHTS = (0.35, 0.25, 0.20, 0.20)  # velocity/authority/recency/relevance
ACADEMIC_DEFAULT_SOURCES = ("openalex", "semantic_scholar")
ACADEMIC_INCLUDE_ARXIV = False
ACADEMIC_SOURCE_TIMEOUT = 8.0
ACADEMIC_RECENCY_HALFLIFE_DAYS = 365.0
OPENALEX_MAILTO = "anyisouth@gmail.com"
OPENALEX_API = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_API = "http://export.arxiv.org/api/query"

# ── Skill 发现引擎（v5.0）────────────────────────────────────────────
SKILL_CODE_SEARCH_PATH = "path:**/SKILL.md"
SKILL_MAX_ENTITIES = 30
SKILL_ACTIVITY_WINDOW_DAYS = 90
SKILL_EXCLUDE_DIRS = ("template/", "spec/", ".system/", "examples/")
SKILL_SCORE_WEIGHTS = (0.40, 0.35, 0.25)         # 子目录活跃度/frontmatter/工程化
# 包级评分（STDD §5.2 双层模型上层）：stars/recency/community_activity/license
SKILL_BUNDLE_WEIGHTS = (0.30, 0.25, 0.25, 0.20)
SKILL_BUNDLE_NEUTRAL = 0.5                        # 取不到 repo 元数据时的中性先验
SKILL_BUNDLE_RECENCY_HALFLIFE_DAYS = 180.0       # 仓库 pushed_at 衰减半衰期
# 宽松许可（permissive）SPDX 集合：有 license 加分，permissive 再加分
SKILL_PERMISSIVE_LICENSES = ("mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause",
                             "isc", "mpl-2.0", "unlicense", "0bsd", "cc0-1.0")

# ── GitHub v5 评分（加法式：4 维 + maintenance，不改 v4 三维）──────────
GITHUB_SCORE_WEIGHTS_V5 = (0.30, 0.30, 0.20, 0.20)  # activity/popularity/freshness/maintenance
GITHUB_NEGLECT_RATIO = 0.10                      # open_issues/stars >10% → 被忽视


def get_env(key: str) -> Optional[str]:
    """读环境变量。懒加载：插件初始化可能早于 .env 加载，故在 handler 内调用。"""
    return os.environ.get(key)


def budget_for(operation: str) -> float:
    """按操作返回 fallback 链总预算（未知操作回退 TOTAL_BUDGET_SECONDS）。"""
    return OPERATION_BUDGET_SECONDS.get(operation, TOTAL_BUDGET_SECONDS)
