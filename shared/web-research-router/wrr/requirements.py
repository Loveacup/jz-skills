"""引擎需求元数据（P1）。

声明式引擎依赖清单，用于：
- 测试：验证 ENGINE_REQUIREMENTS 与实际注册引擎无漂移
- 文档：自动生成 .env.example 模板
- 未来：自动化部署脚本可消费此元数据

设计约束：
- 纯数据结构，无业务逻辑
- 引擎 health_check 实现不依赖此文件（避免循环依赖）
- 测试验证一致性：每个注册引擎必须在此声明，tier 必须匹配
"""
from typing import Dict, Any, List


# ── 引擎需求元数据 ──────────────────────────────────────────────────
ENGINE_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    # Tier 0: 无本地配置要求
    "academic": {
        "tier": 0,
        "env": [],
        "env_optional": ["PAPER_SEARCH_MCP_URL"],
        "commands": [],
        "endpoints": [
            "https://api.openalex.org/works",
            "https://api.semanticscholar.org/graph/v1/paper/search",
            "http://export.arxiv.org/api/query",
        ],
        "description": "学术搜索（OpenAlex + Semantic Scholar + arXiv；可选 paper-search-mcp）",
    },

    # Tier 1: API key/token 要求
    "exa": {
        "tier": 1,
        "env": ["EXA_API_KEY"],
        "commands": [],
        "endpoints": [],
        "description": "Exa AI 搜索引擎",
    },
    "brave": {
        "tier": 1,
        "env_any": ["BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY"],
        "commands": [],
        "endpoints": [],
        "description": "Brave Search API（主用或备用 key）",
    },
    "github": {
        "tier": 1,
        "env": ["GITHUB_TOKEN"],
        "commands": [],
        "endpoints": [],
        "description": "GitHub 仓库搜索",
    },
    "skill": {
        "tier": 1,
        "env": ["GITHUB_TOKEN"],
        "commands": [],
        "endpoints": [
            "https://api.github.com/search/code (path:**/SKILL.md)",
            "https://api.github.com/repos/vercel-labs/skills (主信源)",
        ],
        "description": "Skill Discovery（GitHub code search；主信源 vercel-labs/skills + Agent-Reach/last30days 等）",
    },

    # Tier 2: 本地服务/CLI 要求
    "searxng": {
        "tier": 2,
        "env": ["SEARXNG_URL"],
        "commands": [],
        "endpoints": ["SEARXNG_URL"],
        "description": "SearXNG 本地实例",
        "example_env": {
            "SEARXNG_URL": "http://127.0.0.1:32080",
        },
    },
    "community": {
        "tier": 2,
        "env": [],
        "commands": ["opencli"],
        "endpoints": [],
        "description": "社区搜索（OpenCLI/Agent-Reach + last30days）",
        "optional_commands": ["python3"],
        "optional_paths": [
            "~/code/last30days-skill/skills/last30days/scripts/last30days.py",
            "~/code/last30days-skill-cn/skills/last30days/scripts/last30days.py",
        ],
        "external_repos": [
            "https://github.com/Panniantong/Agent-Reach",
            "https://github.com/mvanhorn/last30days-skill",
            "https://github.com/Jesseovo/last30days-skill-cn",
        ],
    },

    # ── 本地搜索层（v5.2）─────────────────────────────────────────────
    # Tier 1: 依赖 Hermes 运行时注入的内置 tool（CLI/CI 环境降级）
    "local_supermemory": {
        "tier": 1,
        "env": [],
        "commands": [],
        "endpoints": [],
        "hermes_tools": ["supermemory_search"],
        "description": "本地长期记忆（Hermes supermemory_search tool；非 Hermes 环境降级）",
    },
    "local_session": {
        "tier": 1,
        "env": [],
        "commands": [],
        "endpoints": [],
        "hermes_tools": ["session_search"],
        "description": "历史对话检索（Hermes session_search tool；非 Hermes 环境降级）",
    },
    # Tier 2: 本地 CLI / 文件系统
    "local_qmd": {
        "tier": 2,
        "env": [],
        "env_optional": ["QMD_BIN"],
        "commands": ["qmd"],
        "endpoints": [],
        "description": "Obsidian/QMD 全文索引（qmd CLI；缺失则 doctor fail）",
    },
    "local_obsidian": {
        "tier": 2,
        "env": [],
        "env_optional": ["WRR_OBSIDIAN_VAULTS"],
        "commands": [],
        "endpoints": [],
        "description": "Obsidian vault 文件扫描（仅 *.md，限流；需 WRR_OBSIDIAN_VAULTS）",
        "example_env": {
            "WRR_OBSIDIAN_VAULTS": "/path/to/vault1:/path/to/vault2",
        },
    },
}


def get_all_env_keys() -> List[str]:
    """返回所有必需环境变量 key（展开 env_any）。"""
    keys = []
    for req in ENGINE_REQUIREMENTS.values():
        keys.extend(req.get("env", []))
        keys.extend(req.get("env_any", []))
    return sorted(set(keys))


def get_all_commands() -> List[str]:
    """返回所有必需命令。"""
    commands = []
    for req in ENGINE_REQUIREMENTS.values():
        commands.extend(req.get("commands", []))
    return sorted(set(commands))
