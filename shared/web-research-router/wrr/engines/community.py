"""社区搜索聚合引擎（Phase 1）。

整合 OpenCLI 社区渠道 + last30days 技能，多源并行搜索 → 统一评分 → 去重 → 排序。

源家族：
  - OpenCLI 渠道（agent-reach 复用浏览器登录态）：reddit / twitter / xiaohongshu / v2ex
    调用 `opencli <chan> search <query> -f json --limit N`，返回结构化 JSON 数组。
  - last30days（重型研究 CLI，按需启用）：last30days_en / last30days_cn
    调用 `python3 <last30days.py> --emit json --quick <query>`，解析其 clusters。

评分（与既有引擎一致的三维加权）：
    score = 0.40*engagement + 0.35*recency + 0.25*quality
  - engagement：点赞/分数（对数压缩，按源用不同上限归一）
  - recency   ：时间衰减（≤24h=1.0, 7d=0.7, 30d=0.3, >30d=0）
  - quality   ：评论/互动比例（comments/engagement）

去重：URL 规范化相等 或 标题 Jaccard 相似度 > 阈值。各源**独立失败**互不影响。

注：OpenCLI 渠道是经实测的快速核心；last30days 为重型工具（常超预算被跳过），
默认仅在 site:news.ycombinator.com|zhihu.com|weibo.com 触发或研究意图关键词时启用。
"""
import asyncio
import json
import math
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base import SearchEngine
from . import _fusion
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult

_Scored = Tuple[float, SearchResult]

_L30_EN = os.environ.get("WRR_LAST30DAYS_EN") or os.path.expanduser(
    "~/code/last30days-skill/skills/last30days/scripts/last30days.py")
_L30_CN = os.environ.get("WRR_LAST30DAYS_CN") or os.path.expanduser(
    "~/code/last30days-skill-cn/skills/last30days/scripts/last30days.py")

# 源定义（字段名对齐各 CLI 实测 Output columns）。
COMMUNITY_SOURCES: Dict[str, Dict[str, Any]] = {
    "reddit": {
        "kind": "opencli", "cli": ["opencli", "reddit", "search"],
        "engagement": "score", "comments": "comments", "time": "created_utc",
        "title": "title", "url": "url", "snippet": "selftext", "eng_max": 10000,
    },
    "twitter": {
        "kind": "opencli", "cli": ["opencli", "twitter", "search"],
        "engagement": "likes", "comments": "replies", "time": "created_at",
        "title": "text", "url": "url", "snippet": "text", "eng_max": 10000,
    },
    "xiaohongshu": {
        "kind": "opencli", "cli": ["opencli", "xiaohongshu", "search"],
        "engagement": "likes", "comments": None, "time": "published_at",
        "title": "title", "url": "url", "snippet": "title", "eng_max": 10000,
    },
    "v2ex": {
        "kind": "opencli", "cli": ["opencli", "v2ex", "search"],
        "engagement": "replies", "comments": "replies", "time": "created",
        "title": "title", "url": "url", "snippet": "content", "eng_max": 1000,
    },
    "last30days_en": {
        "kind": "last30days", "cli": ["python3", _L30_EN],
        "engagement": "score", "comments": None, "time": None, "eng_max": 100,
    },
    "last30days_cn": {
        "kind": "last30days", "cli": ["python3", _L30_CN],
        "engagement": "score", "comments": None, "time": None, "eng_max": 100,
    },
}


# ── 评分（纯函数，单测可直接调用）────────────────────────────────────
def _to_int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _parse_time(time_val) -> Optional[datetime]:
    """解析 Unix 秒/毫秒 或 ISO 8601。"""
    if isinstance(time_val, (int, float)) and time_val > 0:
        ts = time_val / 1000 if time_val > 1e11 else time_val
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(time_val, str) and time_val:
        try:
            return datetime.fromisoformat(time_val.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _recency_score(created: Optional[datetime], now: Optional[datetime] = None) -> float:
    """时间衰减：≤24h=1.0, ≤7d=0.7, ≤30d=0.3, 更旧=0；未知时间给中等分 0.5。"""
    if not created:
        return 0.5
    now = now or datetime.now(timezone.utc)
    age_hours = (now - created).total_seconds() / 3600
    if age_hours <= 24:
        return 1.0
    if age_hours <= 168:
        return 0.7
    if age_hours <= 720:
        return 0.3
    return 0.0


def _engagement_score(value: int, max_ref: int = 1000) -> float:
    """参与度对数压缩到 [0,1]。"""
    if value <= 0:
        return 0.0
    return min(1.0, math.log10(1 + value) / math.log10(1 + max_ref))


def _quality_score(comments: int, engagement: int) -> float:
    """质量：评论/互动比例（20% 评论率 → 1.0）。"""
    if engagement <= 0:
        return 0.0
    return min(1.0, (comments / engagement) * 5)


def calculate_score(item: Dict[str, Any], source_config: Dict[str, Any],
                    now: Optional[datetime] = None) -> float:
    """统一三维加权综合分。权重取自 config.COMMUNITY_SCORE_WEIGHTS。"""
    eng = _to_int(item.get(source_config["engagement"], 0))
    cfield = source_config.get("comments")
    com = _to_int(item.get(cfield, 0)) if cfield else 0
    tval = item.get(source_config["time"]) if source_config.get("time") else None
    w_e, w_r, w_q = config.COMMUNITY_SCORE_WEIGHTS
    return (w_e * _engagement_score(eng, source_config.get("eng_max", 1000))
            + w_r * _recency_score(_parse_time(tval), now)
            + w_q * _quality_score(com, eng))


# ── 去重 ─────────────────────────────────────────────────────────────
def _normalize_url(url: str) -> str:
    url = (url or "").lower().strip().rstrip("/")
    url = re.sub(r"[?#].*$", "", url)
    return url


def _similarity(a: str, b: str) -> float:
    """标题 Jaccard 词集相似度（按 \\w+ 分词，忽略标点/emoji，CJK 友好）。"""
    a_set = set(re.findall(r"\w+", (a or "").lower()))
    b_set = set(re.findall(r"\w+", (b or "").lower()))
    if not a_set or not b_set:
        return 0.0
    return len(a_set & b_set) / len(a_set | b_set)


def deduplicate(results: List[SearchResult]) -> List[SearchResult]:
    """去重：URL 规范化相等 或 标题相似度 > 阈值。保留先到者（已按分降序）。"""
    unique: List[SearchResult] = []
    seen_urls = set()
    for r in results:
        nu = _normalize_url(r.url)
        if nu and nu in seen_urls:
            continue
        if any(_similarity(r.title, k.title) > config.COMMUNITY_DEDUP_THRESHOLD
               for k in unique):
            continue
        if nu:
            seen_urls.add(nu)
        unique.append(r)
    return unique


# ── 子进程（集中一处，便于单测 monkeypatch）──────────────────────────
async def _run_cmd(cli: List[str], timeout: float) -> Tuple[Optional[int], str]:
    """运行命令，返回 (returncode, stdout)；超时/异常返回 (None, '').
    
    自动在 PATH 头部注入 ~/.local/bin，确保非交互 shell 能找到 agent-reach/opencli。
    """
    env = os.environ.copy()
    local_bin = os.path.expanduser("~/.local/bin")
    current_path = env.get("PATH", "")
    parts = current_path.split(os.pathsep)
    if local_bin not in parts:
        env["PATH"] = os.pathsep.join([local_bin] + parts)
    else:
        env["PATH"] = current_path
    try:
        proc = await asyncio.create_subprocess_exec(
            *cli, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=env)
    except (FileNotFoundError, OSError):
        return (None, "")
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return (None, "")
    return (proc.returncode, out.decode("utf-8", errors="ignore"))


class CommunityEngine(SearchEngine):
    name = "community"
    tier = 2  # 本地 CLI 依赖

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        sources = self._detect_sources(options.query)
        now = datetime.now(timezone.utc)
        gathered = await asyncio.gather(
            *[self._fetch_source(s, options, now) for s in sources],
            return_exceptions=True,
        )
        merged: List[_Scored] = []
        for res in gathered:
            if isinstance(res, Exception) or not res:
                continue                                  # 各源独立失败
            merged.extend(res)
        if not merged:
            raise EngineError("community: all sources failed or returned no results")
        merged.sort(key=lambda t: t[0], reverse=True)
        deduped = deduplicate([sr for _, sr in merged])
        return deduped[:options.count]

    # ── v5.0：跨子源 RRF 聚合（源内秩 → RRF）+ canonical 去重 ──────────
    async def search_rrf(self, options: SearchOptions) -> List[SearchResult]:
        """v5 聚合：各子源源内排名 → 跨源 RRF（_fusion）→ canonical_url 去重。

        替代 search() 的「线性合并不可比分」做法（研究报告 §2）。源内仍用
        calculate_score 排序，magnitude 不出源；跨源用秩融合，多源命中自动加分。
        """
        sources = self._detect_sources(options.query)
        now = datetime.now(timezone.utc)
        gathered = await asyncio.gather(
            *[self._fetch_source(s, options, now) for s in sources],
            return_exceptions=True,
        )
        per_source: Dict[str, List[SearchResult]] = {}
        for src, res in zip(sources, gathered):
            if isinstance(res, Exception) or not res:
                continue                                  # 各源独立失败隔离
            ranked = sorted(res, key=lambda t: t[0], reverse=True)   # 源内秩
            per_source[src] = [sr for _, sr in ranked]
        if not per_source:
            raise EngineError("community: all sources failed or returned no results")
        fused = _fusion.rrf_fuse(per_source, k=config.RRF_K)
        deduped = _fusion.dedup_cluster([f["doc"] for f in fused],
                                        config.COMMUNITY_DEDUP_THRESHOLD)
        return deduped[:options.count]

    # ── 源选择 ───────────────────────────────────────────────────────
    def _detect_sources(self, query: str) -> List[str]:
        q = (query or "").lower()
        picked: List[str] = []

        def add(s):
            if s not in picked:
                picked.append(s)

        # site: 触发 → 精确子集
        if "site:reddit.com" in q:
            add("reddit")
        if "site:twitter.com" in q or "site:x.com" in q:
            add("twitter")
        if "site:news.ycombinator.com" in q:
            add("last30days_en")
        if "site:zhihu.com" in q or "site:weibo.com" in q:
            add("last30days_cn")
        # 平台关键词
        if any(k in q for k in ("小红书", "xiaohongshu", "xhs")):
            add("xiaohongshu")
        if "v2ex" in q:
            add("v2ex")

        if not picked:
            picked = list(config.COMMUNITY_DEFAULT_SOURCES)

        # 研究意图 / 显式开关 → 追加 last30days 重型源
        research = any(k in q for k in ("trending", "30 days", "30天", "最近", "本周", "this week"))
        if config.COMMUNITY_INCLUDE_LAST30DAYS or research:
            add("last30days_en")
            add("last30days_cn")
        return picked

    # ── 单源抓取（超时 + 异常隔离）───────────────────────────────────
    async def _fetch_source(self, source: str, options, now) -> List[_Scored]:
        cfg = COMMUNITY_SOURCES.get(source)
        if not cfg:
            return []
        try:
            if cfg["kind"] == "opencli":
                items = await self._fetch_opencli(cfg, options)
            else:
                items = await self._fetch_last30days(cfg, options)
        except Exception:
            return []
        out: List[_Scored] = []
        for it in items:
            scored = self._item_to_result(it, source, cfg, now)
            if scored:
                out.append(scored)
        return out

    async def _fetch_opencli(self, cfg, options) -> List[Dict[str, Any]]:
        cli = cfg["cli"] + [options.query, "-f", "json",
                            "--limit", str(min(options.count, 20))]
        rc, out = await _run_cmd(cli, config.COMMUNITY_SOURCE_TIMEOUT)
        if rc != 0 or not out.strip():
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("results") or data.get("items") or []
        return []

    async def _fetch_last30days(self, cfg, options) -> List[Dict[str, Any]]:
        cli = cfg["cli"] + ["--emit", "json", "--quick", options.query]
        rc, out = await _run_cmd(cli, config.COMMUNITY_SOURCE_TIMEOUT)
        if rc != 0 or not out.strip():
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []
        items: List[Dict[str, Any]] = []
        for c in (data.get("clusters") or []):
            ids = c.get("representative_ids") or c.get("candidate_ids") or []
            url = ids[0] if ids else ""
            title = c.get("title") or ""
            if not (title and url):
                continue
            items.append({
                "title": title, "url": url,
                "snippet": "sources: " + ", ".join(c.get("sources") or []),
                "score": c.get("score") or 0,
            })
        return items

    def _item_to_result(self, item, source, cfg, now) -> Optional[_Scored]:
        title = str(item.get(cfg.get("title", "title")) or item.get("title")
                    or item.get("text") or "").strip()
        url = str(item.get(cfg.get("url", "url")) or item.get("url") or "").strip()
        if not title or not url:
            return None
        snippet = str(item.get(cfg.get("snippet", "snippet"))
                      or item.get("selftext") or item.get("text") or "")
        sc = calculate_score(item, cfg, now)
        return (sc, SearchResult(title=title[:200], url=url,
                                 snippet=snippet[:500], source_tag=source))

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        """检查 opencli 是否可用。

        P0 (deep=False): shutil.which 仅检查存在性
        P1 (deep=True): probe_command 执行 --version 验证可用性
        """
        from ._probe import probe_command

        # 快速检查：which
        opencli_path = shutil.which("opencli")
        if not opencli_path:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="opencli command not found",
                details="Community engine requires opencli CLI tool",
                requirements=["command:opencli"],
                repair=[
                    "Install opencli:",
                    "  npm install -g opencli",
                    "Or add opencli to your PATH if already installed",
                    "Verify: which opencli",
                    "Rerun: wrr-cli.py doctor --engine community",
                ],
                evidence={"command.opencli": "missing"},
            )

        # Deep 检查：执行 --version
        if deep:
            probe_result = await probe_command("opencli", ("--version",), timeout=3.0)
            if probe_result.status == "timeout":
                return EngineCheckResult(
                    engine=self.name,
                    status="fail",
                    tier=self.tier,
                    summary="opencli command timeout",
                    details="opencli --version timed out after 3s",
                    requirements=["command:opencli"],
                    repair=[
                        "Check if opencli is working:",
                        "  opencli --version",
                        "Reinstall if needed:",
                        "  npm install -g opencli",
                    ],
                    evidence={"command.opencli": opencli_path, "probe": "timeout"},
                )
            elif probe_result.status in ("broken", "error"):
                return EngineCheckResult(
                    engine=self.name,
                    status="fail",
                    tier=self.tier,
                    summary=f"opencli command {probe_result.status}",
                    details=f"opencli --version failed: {probe_result.error}",
                    requirements=["command:opencli"],
                    repair=[
                        "Check opencli installation:",
                        "  opencli --version",
                        "Reinstall if needed:",
                        "  npm install -g opencli",
                    ],
                    evidence={
                        "command.opencli": opencli_path,
                        "probe": probe_result.status,
                        "exit_code": probe_result.exit_code,
                    },
                )

        # opencli OK，检查 last30days（如果启用）
        details = f"opencli found at: {opencli_path}"
        if config.COMMUNITY_INCLUDE_LAST30DAYS:
            l30_issues = []
            for label, path in [("last30days_en", _L30_EN), ("last30days_cn", _L30_CN)]:
                if not os.path.exists(path):
                    l30_issues.append(f"{label} not found: {path}")
                elif deep:
                    # deep mode: probe 脚本可执行性
                    try:
                        result = await probe_command("python3", (path, "--help"), timeout=5.0)
                        if result.status != "ok":
                            l30_issues.append(f"{label} probe failed: {result.status}")
                        else:
                            details += f", {label} OK"
                    except Exception:
                        l30_issues.append(f"{label}: probe error")

            if l30_issues:
                return EngineCheckResult(
                    engine=self.name,
                    status="warn",
                    tier=self.tier,
                    summary="opencli OK, last30days scripts missing",
                    details="; ".join(l30_issues),
                    requirements=["command:opencli", "script:last30days"],
                    repair=[
                        "Clone last30days skills if needed:",
                        f"  Expected: {_L30_EN}",
                        f"  Expected: {_L30_CN}",
                        "Or set COMMUNITY_INCLUDE_LAST30DAYS=False to disable",
                    ],
                    evidence={"command.opencli": "present", "last30days": "missing"},
                )

        return EngineCheckResult(
            engine=self.name,
            status="ok",
            tier=self.tier,
            summary="opencli available",
            details=details,
            active_backend="opencli",
            evidence={"command.opencli": opencli_path},
        )
