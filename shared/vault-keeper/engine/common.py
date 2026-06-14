"""vault-keeper 共享工具：vault 定位、frontmatter 读写、页面遍历、wikilink 解析、哈希。

控制面引擎的公共底座。所有 engine 模块依赖本文件。
状态全活在 vault 的 Markdown 里——本模块只读写盘上状态，不持有任何运行时记忆。
"""
import os
import re
import glob
import hashlib

try:
    import yaml  # pip install pyyaml（轻量，可接受）
except ImportError:  # 降级：无 pyyaml 时用极简解析器
    yaml = None

# vault 定位：环境变量 $VAULT 优先，否则默认路径
VAULT = os.environ.get("VAULT") or os.path.expanduser("~/Documents/Obsidian/AlexCai")

CORE_DIRS = ["10-Projects", "20-Areas", "30-Resources", "02-Plan&CQI"]
STAGING = "01-Staging"
INBOX = "00-Inbox"
AUDIT = "88-审计"

_FM = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


def vault_path(*parts):
    return os.path.join(VAULT, *parts)


def _mini_yaml(block):
    """无 pyyaml 时的兜底解析（仅支持 key: value 与简单列表）。"""
    out = {}
    for line in block.splitlines():
        m = re.match(r"^(\w[\w_]*):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip(" '\"") for x in v[1:-1].split(",") if x.strip()]
        out[k] = v
    return out


def load(path):
    """返回 (frontmatter:dict, body:str)。无 frontmatter 时 fm 为 {}。"""
    txt = open(path, encoding="utf-8").read()
    m = _FM.match(txt)
    if not m:
        return {}, txt
    raw = m.group(1)
    fm = (yaml.safe_load(raw) if yaml else _mini_yaml(raw)) or {}
    return fm, m.group(2)


def dump(path, fm, body):
    """写回 frontmatter + body。"""
    if yaml:
        head = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    else:
        head = "\n".join(f"{k}: {v}" for k, v in fm.items())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(f"---\n{head}\n---\n{body}")


def iter_pages(dirs=None):
    """遍历 core 区（或指定目录）的所有 .md。"""
    for d in (dirs or CORE_DIRS):
        yield from glob.glob(vault_path(d, "**", "*.md"), recursive=True)


def all_titles():
    """全库 .md 文件名集合（无扩展），用于断链/去重判断。"""
    return {os.path.basename(p)[:-3]
            for p in glob.glob(vault_path("**", "*.md"), recursive=True)}


def wikilinks(body):
    """提取 body 中的 wikilink 目标（去 #锚点与 |别名）。"""
    return [m.strip() for m in re.findall(r"\[\[([^\]\|#]+)", body)]


def sha12(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
