"""Skill 发现引擎（v5.0，D3）。复用共享 GitHubClient，零自造认证/httpx。

主力检索：code search ``path:**/SKILL.md`` 定位 SKILL.md → 反推 (repo, skill 子目录)
→ contents API 取 SKILL.md 内容（base64 解码）→ 解析 YAML frontmatter
→ **无 name 或无 description 即丢弃**（区分"真 skill" vs"恰好有 SKILL.md"）
→ 单 skill 级活跃度（``subdir_commit_count(path=子目录)``，解"大包整体≠单 skill"难点）
→ 评分 → 排序。

双层评分（STDD §5.2）：
  - 包级（仓库出处先验，按唯一 repo 缓存抓 /repos）：
        bundle = 0.30*stars + 0.25*recency + 0.25*community_activity + 0.20*license
    取不到 repo 元数据（client 无 get_repo / 失败）→ 中性先验，不丢结果（graceful）。
  - 单 skill 级（对齐研究报告 §4，权重 config.SKILL_SCORE_WEIGHTS）：
        per_skill = 0.40*子目录活跃度(log 压缩) + 0.35*frontmatter 完整度 + 0.25*工程化
  - 合成：final = (0.5 + 0.5*bundle) * per_skill（包级当先验加权，单 skill 主导）。

输出 SearchResult：title=name；url 直指子目录 ``tree/HEAD/<dir>``；
snippet=description 截断 + 质量信号 + Hermes 兼容标记（name+desc+type+version 齐=✓，
缺 type/version=⚠needs-default）。各 skill 探测**独立失败**互不影响。
"""
from __future__ import annotations

import asyncio
import base64
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult
from ._github_client import GitHubClient

_Scored = Tuple[float, SearchResult]


# ── 纯函数：frontmatter 解析 / 真伪判定（单测可直接调用）────────────────
def parse_frontmatter(md_text: str) -> Optional[Dict[str, Any]]:
    """解析 Markdown 顶部 ``---...---`` YAML frontmatter。

    首行须为 ``---``，需有闭合 ``---``/``...``；yaml 解析失败或结果非 dict → None。
    """
    if not md_text:
        return None
    text = md_text.lstrip("﻿")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def is_true_skill(fm: Optional[Dict[str, Any]]) -> bool:
    """真 skill = frontmatter 含非空 name + description（否则只是恰好有 SKILL.md）。"""
    if not isinstance(fm, dict):
        return False
    name = str(fm.get("name") or "").strip()
    desc = str(fm.get("description") or "").strip()
    return bool(name and desc)


# ── 纯函数：单 skill 评分 ────────────────────────────────────────────
def _activity_score(commits_90d: Optional[int]) -> float:
    """子目录活跃度：90 天提交数对数压缩（~100 commits → 1.0）。"""
    c = commits_90d or 0
    if c <= 0:
        return 0.0
    return min(1.0, math.log10(c + 1) / 2.0)


def _frontmatter_completeness(fm: Optional[Dict[str, Any]]) -> float:
    """完整度：name+description 必备(0.6) + version/license 各 0.15 + 触发词 0.10。"""
    if not isinstance(fm, dict):
        return 0.0
    s = 0.0
    if str(fm.get("name") or "").strip() and str(fm.get("description") or "").strip():
        s += 0.6
    if fm.get("version"):
        s += 0.15
    if fm.get("license"):
        s += 0.15
    if fm.get("triggers") or fm.get("trigger") or fm.get("keywords"):
        s += 0.10
    return min(1.0, s)


def _engineering_score(files_in_dir: Optional[List[str]]) -> float:
    """工程化：子目录含 scripts(0.4) / references(0.3) / 测试(0.3)。"""
    names = [str(f).lower() for f in (files_in_dir or [])]
    s = 0.0
    if any("script" in n for n in names):
        s += 0.4
    if any("reference" in n for n in names):
        s += 0.3
    if any("test" in n for n in names):
        s += 0.3
    return min(1.0, s)


def skill_score(commits_90d: Optional[int], fm: Optional[Dict[str, Any]],
                files_in_dir: Optional[List[str]]) -> float:
    """单 skill 综合分（权重取自 config.SKILL_SCORE_WEIGHTS）。"""
    w_act, w_fm, w_eng = config.SKILL_SCORE_WEIGHTS
    return (w_act * _activity_score(commits_90d)
            + w_fm * _frontmatter_completeness(fm)
            + w_eng * _engineering_score(files_in_dir))


# ── 纯函数：包级评分（STDD §5.2 双层模型上层）──────────────────────────
def _bundle_stars(stars: Optional[int]) -> float:
    """star 对数压缩（~100k stars → 1.0）。"""
    s = stars or 0
    if s <= 0:
        return 0.0
    return min(1.0, math.log10(s + 1) / 5.0)


def _bundle_recency(pushed_at: Optional[str], now: Optional[datetime] = None) -> float:
    """仓库 pushed_at 指数衰减（半衰期 config.SKILL_BUNDLE_RECENCY_HALFLIFE_DAYS）。"""
    if not pushed_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(pushed_at).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    age_days = max((now - dt).total_seconds() / 86400.0, 0.0)
    return 0.5 ** (age_days / config.SKILL_BUNDLE_RECENCY_HALFLIFE_DAYS)


def _bundle_community_activity(forks: Optional[int], subscribers: Optional[int]) -> float:
    """社区活跃度：forks + watchers/subscribers 对数压缩（~1000 → 1.0）。"""
    total = (forks or 0) + (subscribers or 0)
    if total <= 0:
        return 0.0
    return min(1.0, math.log10(total + 1) / 3.0)


def _bundle_license(license_obj: Any) -> float:
    """许可：无=0.0；有但非宽松=0.6；宽松(permissive SPDX)=1.0。"""
    if not isinstance(license_obj, dict):
        return 0.0
    spdx = str(license_obj.get("spdx_id") or license_obj.get("key") or "").lower()
    if not spdx or spdx == "noassertion":
        return 0.0
    return 1.0 if spdx in config.SKILL_PERMISSIVE_LICENSES else 0.6


def bundle_score(repo_meta: Optional[Dict[str, Any]],
                 now: Optional[datetime] = None) -> float:
    """包级综合分（仓库出处先验）。权重 config.SKILL_BUNDLE_WEIGHTS：
    stars 0.30 + recency 0.25 + community_activity 0.25 + license 0.20。

    repo_meta = GitHub /repos/{repo} 响应；None/缺失 → 返回中性先验。
    """
    if not isinstance(repo_meta, dict) or not repo_meta:
        return config.SKILL_BUNDLE_NEUTRAL
    w_s, w_r, w_c, w_l = config.SKILL_BUNDLE_WEIGHTS
    return (w_s * _bundle_stars(repo_meta.get("stargazers_count"))
            + w_r * _bundle_recency(repo_meta.get("pushed_at"), now)
            + w_c * _bundle_community_activity(repo_meta.get("forks_count"),
                                               repo_meta.get("subscribers_count"))
            + w_l * _bundle_license(repo_meta.get("license")))


def combine_scores(per_skill: float, bundle: float) -> float:
    """双层合成：包级当先验加权，单 skill 仍主导。final = (0.5 + 0.5*bundle) * per_skill。

    bundle∈[0,1] → 因子∈[0.5,1.0]；中性 bundle=0.5 → 因子 0.75。
    """
    return (0.5 + 0.5 * max(0.0, min(1.0, bundle))) * per_skill


def hermes_compat(fm: Optional[Dict[str, Any]]) -> str:
    """Hermes 兼容标记：name+desc+type+version 齐 → "✓"，缺 type/version → 需补默认。"""
    if not is_true_skill(fm):
        return "⚠needs-default"
    if fm.get("type") and fm.get("version"):
        return "✓"
    return "⚠needs-default"


# ── 反推子目录 / 排除 / 解码 ─────────────────────────────────────────
def _subdir_from_path(path: str) -> Optional[str]:
    """从 ``a/b/SKILL.md`` 反推 skill 子目录 ``a/b``；根目录 SKILL.md → ""。"""
    if not path or not path.endswith("SKILL.md"):
        return None
    return path[: -len("SKILL.md")].strip("/")


def _is_excluded(subdir: str) -> bool:
    """子目录任一路径段命中 config.SKILL_EXCLUDE_DIRS → 排除（模板/示例等非真 skill）。"""
    segs = [s for s in (subdir or "").lower().split("/") if s]
    for ex in config.SKILL_EXCLUDE_DIRS:
        exs = ex.strip("/").lower()
        if exs and exs in segs:
            return True
    return False


def _decode_content(content: Any) -> Optional[str]:
    """从 contents API 文件 dict（base64）解出文本。"""
    if not isinstance(content, dict):
        return None
    raw = content.get("content")
    if raw is None:
        return None
    if (content.get("encoding") or "base64") == "base64":
        try:
            return base64.b64decode(raw).decode("utf-8", errors="ignore")
        except Exception:
            return None
    return str(raw)


class SkillDiscoveryEngine(SearchEngine):
    name = "skill"
    tier = 1

    def __init__(self, client: Optional[GitHubClient] = None):
        self._client = client or GitHubClient()

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        client = self._client
        q = f"{options.query} {config.SKILL_CODE_SEARCH_PATH}".strip()
        res = await client.code_search(q)
        items = (res or {}).get("items", []) or []

        # ① 反推 (repo, 子目录)，过滤排除目录、去重、限量
        targets: List[Tuple[str, str, str]] = []
        seen = set()
        for it in items:
            repo = (it.get("repository") or {}).get("full_name")
            path = it.get("path") or ""
            subdir = _subdir_from_path(path)
            if not repo or subdir is None or _is_excluded(subdir):
                continue
            key = (repo, subdir)
            if key in seen:
                continue
            seen.add(key)
            targets.append((repo, subdir, path))
            if len(targets) >= config.SKILL_MAX_ENTITIES:
                break

        since = (datetime.now(timezone.utc)
                 - timedelta(days=config.SKILL_ACTIVITY_WINDOW_DAYS)).strftime(
                     "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.now(timezone.utc)

        # ②（包级层）按唯一 repo 抓元数据并算包级先验（缓存，取不到→中性降级）
        unique_repos = {repo for repo, _, _ in targets}
        bundle_scores = await self._fetch_bundles(unique_repos, now)

        # ③ 各 skill 独立探测（解析 + 活跃度 + 单 skill 评分 × 包级先验），失败隔离
        gathered = await asyncio.gather(
            *[self._probe(repo, subdir, path, since, bundle_scores.get(repo))
              for repo, subdir, path in targets],
            return_exceptions=True,
        )
        scored: List[_Scored] = []
        for r in gathered:
            if isinstance(r, Exception) or not r:
                continue
            scored.append(r)
        if not scored:
            raise EngineError("skill: no valid SKILL.md entities found")
        scored.sort(key=lambda t: t[0], reverse=True)
        return [sr for _, sr in scored][:options.count]

    async def _fetch_bundles(self, repos, now) -> Dict[str, float]:
        """对每个唯一 repo 取元数据 → 包级先验。client 无 get_repo 或失败 → 中性降级。

        graceful：包级是先验增强，不应让单 skill 结果因取不到 repo 而消失。
        """
        get_repo = getattr(self._client, "get_repo", None)
        if not callable(get_repo):
            return {r: config.SKILL_BUNDLE_NEUTRAL for r in repos}

        async def one(repo):
            try:
                meta = await get_repo(repo)
                return repo, bundle_score(meta, now)
            except Exception:
                return repo, config.SKILL_BUNDLE_NEUTRAL

        pairs = await asyncio.gather(*[one(r) for r in repos], return_exceptions=True)
        out: Dict[str, float] = {}
        for p in pairs:
            if isinstance(p, Exception):
                continue
            out[p[0]] = p[1]
        for r in repos:
            out.setdefault(r, config.SKILL_BUNDLE_NEUTRAL)
        return out

    async def _probe(self, repo: str, subdir: str, path: str, since: str,
                     bundle: Optional[float] = None) -> Optional[_Scored]:
        client = self._client
        content = await client.get_contents(repo, path)
        md = _decode_content(content)
        fm = parse_frontmatter(md) if md else None
        if not is_true_skill(fm):
            return None                                   # 丢弃非真 skill

        # 工程化信号：列子目录文件（失败则空，不拖垮评分）
        files: List[str] = []
        if subdir:
            try:
                listing = await client.get_contents(repo, subdir)
                if isinstance(listing, list):
                    files = [str(c.get("name") or "") for c in listing
                             if isinstance(c, dict)]
            except Exception:
                files = []

        commits = await client.subdir_commit_count(repo, subdir, since)
        per_skill = skill_score(commits, fm, files)
        if bundle is None:
            bundle = config.SKILL_BUNDLE_NEUTRAL
        sc = combine_scores(per_skill, bundle)         # 双层：包级先验 × 单 skill
        compat = hermes_compat(fm)
        desc = str(fm.get("description") or "")
        url = f"https://github.com/{repo}/tree/HEAD/{subdir}".rstrip("/")
        commits_label = commits if commits is not None else "?"
        snippet = (f"{desc[:160]} · score={sc:.3f} · "
                   f"commits90d={commits_label} · bundle={bundle:.2f} · hermes={compat}")
        return (sc, SearchResult(title=str(fm.get("name") or "")[:200],
                                 url=url, snippet=snippet[:500], source_tag="skill"))

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        """检查 GITHUB_TOKEN + 验证 code search 实际可用；标注 skill 信源状态。"""
        import httpx
        token = config.get_env("GITHUB_TOKEN")
        if not token:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="GITHUB_TOKEN not configured",
                details="Skill Discovery uses GitHub code search which requires authentication",
                requirements=["env:GITHUB_TOKEN"],
                repair=[
                    "Set GITHUB_TOKEN in your shell or ~/.hermes/.env:",
                    "  export GITHUB_TOKEN=your_token_here",
                    "Rerun: wrr-cli.py doctor --engine skill",
                ],
                evidence={"env.GITHUB_TOKEN": "missing"},
            )

        # 验证 GitHub code search 实际可用（轻量：只取 1 条 SKILL.md）
        code_search_ok = False
        code_search_detail = ""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.github.com/search/code",
                    params={"q": "path:**/SKILL.md", "per_page": 1},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("total_count", 0)
                code_search_ok = True
                code_search_detail = f"{count} SKILL.md files found"
            elif resp.status_code == 403:
                code_search_detail = f"rate limited ({resp.status_code})"
            else:
                code_search_detail = f"search failed ({resp.status_code})"
        except Exception as e:
            code_search_detail = f"search error: {type(e).__name__}"

        # Vercel skills 信源检查（可选，不影响状态）
        vercel_ok = False
        vercel_detail = ""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.github.com/repos/vercel-labs/skills",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
            if resp.status_code == 200:
                vercel_ok = True
                vercel_detail = "vercel-labs/skills accessible"
            elif resp.status_code == 404:
                vercel_detail = "vercel-labs/skills not found"
            else:
                vercel_detail = f"vercel-labs/skills status {resp.status_code}"
        except Exception:
            vercel_detail = "vercel-labs/skills unreachable"

        if code_search_ok:
            return EngineCheckResult(
                engine=self.name,
                status="ok",
                tier=self.tier,
                summary=f"GitHub code search OK ({code_search_detail})",
                active_backend="github-code-search",
                evidence={
                    "env.GITHUB_TOKEN": "present",
                    "code_search": code_search_detail,
                    "vercel_labs_skills": "accessible" if vercel_ok else vercel_detail,
                },
            )
        else:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary=f"GitHub code search failed: {code_search_detail}",
                details="Token is set but code search is unavailable",
                repair=[
                    "Check GitHub token permissions (requires public_repo scope)",
                    f"GitHub API returned: {code_search_detail}",
                    "Regenerate token at https://github.com/settings/tokens",
                    "Verify network can reach api.github.com",
                ],
                evidence={
                    "env.GITHUB_TOKEN": "present",
                    "code_search": code_search_detail,
                },
            )
