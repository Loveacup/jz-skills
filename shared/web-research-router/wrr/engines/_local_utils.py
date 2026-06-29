"""本地搜索层共享工具（v5.2）。

4 个本地引擎（local_supermemory / local_session / local_qmd / local_obsidian）共用：
  - Hermes tool resolver  —— Tier 1 引擎（supermemory/session）依赖 Hermes 运行时注入的
    tool callable；CLI/CI 环境为空 → 引擎清晰降级（health_check fail/warn，search 抛 EngineError）。
  - subprocess 封装        —— Tier 2 qmd 引擎调用本机 CLI，带超时 + kill。
  - markdown 扫描/评分     —— Tier 2 obsidian 引擎只扫白名单目录 *.md，限流（max files/bytes/exclude）。
  - 行数据归一            —— 把 Hermes tool 的多形态返回（dict/list/对象）统一成 row list。

纯工具，零网络副作用；CLI 环境下 import 安全。
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ══════════════════════════════════════════════════════════════════════
# Hermes tool resolver
# ══════════════════════════════════════════════════════════════════════
# Hermes 运行时在加载插件后把内置 tool（supermemory_search / session_search）
# 注册进此表；普通 Python 进程（wrr-cli / pytest）下保持为空，引擎据此降级。
_HERMES_TOOLS: Dict[str, Callable] = {}


def register_hermes_tool(name: str, fn: Callable) -> None:
    """Hermes 运行时注入一个本地工具 callable。"""
    _HERMES_TOOLS[name] = fn


def clear_hermes_tools() -> None:
    """清空注入表（测试用）。"""
    _HERMES_TOOLS.clear()


def resolve_hermes_tool(name: str) -> Optional[Callable]:
    """解析 Hermes 内置工具 callable。未注入（如 CLI 环境）→ None。
    
    优先查 _HERMES_TOOLS（显式注入），回退查 Hermes 全局工具注册表（运行时自动发现）。
    """
    fn = _HERMES_TOOLS.get(name)
    if fn is not None:
        return fn
    # 回退：尝试从 Hermes 全局工具注册表获取 handler
    try:
        from tools.registry import registry
        entry = registry.get_entry(name)
        if entry is not None and entry.handler is not None:
            return entry.handler
    except Exception:
        pass
    return None


async def call_tool(tool: Callable, **kwargs) -> Any:
    """调用 Hermes tool，兼容同步 / 异步实现。"""
    res = tool(**kwargs)
    if asyncio.iscoroutine(res):
        return await res
    return res


async def call_tool_with_retry(
    tool: Callable, timeout: float = 5.0, retries: int = 1, **kwargs
) -> Any:
    """带超时 + 重试的 tool 调用。超时时重试 ≤retries 次，仍失败则抛 TimeoutError。

    用于本地引擎（supermemory/session）在 Hermes tool 间歇超时时自动恢复，
    避免静默跳过导致结果丢失。
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            coro = call_tool(tool, **kwargs)
            if asyncio.iscoroutine(coro):
                return await asyncio.wait_for(coro, timeout=timeout)
            return coro
        except asyncio.TimeoutError as e:
            last_error = e
        except Exception as e:
            # 非超时错误直接抛出，不重试
            raise
    raise asyncio.TimeoutError(
        f"tool call timed out after {retries+1} attempts ({timeout}s each)"
    ) from last_error


def extract_rows(raw: Any) -> List[Any]:
    """把 Hermes tool 的多形态返回归一成 row 列表。

    支持：list / dict(results|items|memories|data) / 带 .results 属性的对象 / None。
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("results", "items", "memories", "messages", "data"):
            val = raw.get(key)
            if isinstance(val, list):
                return val
        return []
    rows = getattr(raw, "results", None)
    if isinstance(rows, list):
        return rows
    return []


def normalize_local_query(query: str) -> str:
    """本地查询归一：去首尾空白、折叠内部空白。"""
    return re.sub(r"\s+", " ", (query or "").strip())


# ══════════════════════════════════════════════════════════════════════
# subprocess（qmd CLI）
# ══════════════════════════════════════════════════════════════════════
async def run_command(args: List[str], timeout: float) -> Tuple[int, str, str]:
    """异步执行命令，带超时 + 超时 kill。返回 (returncode, stdout, stderr)。

    超时抛 asyncio.TimeoutError（调用方负责转 EngineError / 标记 doctor）。
    """
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
        raise
    return (proc.returncode,
            (stdout or b"").decode("utf-8", "replace"),
            (stderr or b"").decode("utf-8", "replace"))


# ══════════════════════════════════════════════════════════════════════
# Markdown 扫描 / frontmatter / 评分（obsidian 引擎）
# ══════════════════════════════════════════════════════════════════════
_CJK = r"一-鿿"


def tokenize(query: str) -> List[str]:
    """查询分词：英文/数字词 + 连续 CJK 短语。用于 markdown 相关性匹配。"""
    q = (query or "").lower()
    terms = re.findall(r"[a-z0-9]+", q)
    terms += re.findall(rf"[{_CJK}]+", q)
    # 英文丢 1 字符噪音（a/of…）；CJK 短语保留
    return [t for t in terms if len(t) >= 2 or re.match(rf"[{_CJK}]", t)]


def scan_markdown_files(roots: List[Path], max_files: int,
                        exclude_dirs: Tuple[str, ...]) -> List[Path]:
    """遍历 root 下 *.md（跳过 exclude_dirs），上限 max_files 防全盘扫描失控。"""
    out: List[Path] = []
    excl = set(exclude_dirs)
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # 原地裁剪 exclude 目录（os.walk 不再下钻）
            dirnames[:] = [d for d in dirnames if d not in excl and not d.startswith(".")]
            for fn in filenames:
                if fn.endswith(".md"):
                    out.append(Path(dirpath) / fn)
                    if len(out) >= max_files:
                        return out
    return out


def count_markdown_files(roots: List[Path], max_files: int = 1000) -> int:
    """统计可达 *.md 数量（doctor 抽样用，限上限避免慢）。"""
    return len(scan_markdown_files(roots, max_files, (".git", ".obsidian", ".trash")))


def read_text_prefix(path: Path, max_bytes: int) -> str:
    """读取文件前 max_bytes 字节并解码（防大文件吃内存）。失败返回空串。"""
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", "replace")
    except OSError:
        return ""


def parse_frontmatter_and_body(text: str) -> Tuple[Dict[str, Any], str]:
    """解析 YAML frontmatter（极简，零依赖）。无 frontmatter → ({}, text)。

    支持 `key: value` 与紧随其后的 `- item` 列表（aliases/tags 常见）。
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].strip("\n")
    body = text[end + 4:]
    fm: Dict[str, Any] = {}
    current: Optional[str] = None
    for line in block.splitlines():
        list_item = re.match(r"^\s*-\s+(.*)$", line)
        if list_item and current is not None:
            if not isinstance(fm.get(current), list):
                fm[current] = []
            fm[current].append(list_item.group(1).strip().strip('"').strip("'"))
            continue
        kv = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            current = key
            fm[key] = val if val else []
    return fm, body


def _flatten_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: List[str] = []
        for v in value:
            out.extend(_flatten_strings(v))
        return out
    if isinstance(value, dict):
        return _flatten_strings(list(value.values()))
    return []


def score_markdown_match(query_terms: List[str], frontmatter: Dict[str, Any],
                         body: str, filename: str) -> Tuple[float, Optional[int], str]:
    """对单个 markdown 文件打相关性分。

    权重：文件名命中 3 / frontmatter 命中 2 / 正文命中 1。
    返回 (score, 首个命中行号 1-based, snippet)。score==0 表示不相关。
    """
    if not query_terms:
        return 0.0, None, ""
    fname_lower = filename.lower()
    fm_text = " ".join(_flatten_strings(frontmatter)).lower() if frontmatter else ""
    body_lower = body.lower()

    score = 0.0
    for t in query_terms:
        if t in fname_lower:
            score += 3.0
        if fm_text and t in fm_text:
            score += 2.0
        if t in body_lower:
            score += 1.0
    if score <= 0:
        return 0.0, None, ""

    line_no, snippet = _first_match_line(body, query_terms)
    return score, line_no, snippet


def _first_match_line(body: str, query_terms: List[str]) -> Tuple[Optional[int], str]:
    """返回正文首个命中任一 term 的行号（1-based）与该行文本。"""
    for idx, line in enumerate(body.splitlines(), start=1):
        low = line.lower()
        if any(t in low for t in query_terms):
            return idx, line.strip()
    return None, body.strip().splitlines()[0] if body.strip() else ""


# ══════════════════════════════════════════════════════════════════════
# v5.3 时效感知（简化版：本地结果统一降权，不提取时间戳）
# ══════════════════════════════════════════════════════════════════════

# 本地引擎结果在 RRF 融合时的衰减因子
# 0.7 = 本地信息确定性低于公网，但不完全否定
LOCAL_FRESHNESS_DEFAULT = 0.7


def freshness_score(source_ts: float = 0.0) -> float:
    """v5.3 简化版：本地=0.7，公网=1.0。
    
    不再按 age 阶梯计算——OMP 审计发现 supermemory 无时间戳导致
    矛盾。改为统一降权：本地数据天然比公网信息陈旧，直接乘 0.7。
    """
    if source_ts <= 0:
        return LOCAL_FRESHNESS_DEFAULT
    return 1.0  # 有时间戳 = 公网/精确源
