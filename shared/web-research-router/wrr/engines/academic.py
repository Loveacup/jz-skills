"""学术搜索引擎（v5.0，D2）。

OpenAlex 主力 + Semantic Scholar 引用质量 + arXiv 预印本（默认 lazy），多源并行
→ DOI 优先去重合并 → 统一 academic_score 排序 → SearchResult 输出。骨架对齐
community.py（asyncio.gather + 各源独立失败隔离）。

评分（引擎内部，4 维加权，权重取自 config.ACADEMIC_SCORE_WEIGHTS）：
    academic_score = 0.35*velocity + 0.25*authority + 0.20*recency + 0.20*relevance
  - velocity   ：年均引用对数压缩（citation_velocity）——不用绝对引用数，避免老论文碾压新论文。
  - authority  ：venue 权威 + S2 influentialCitationCount 占比；预印本无 venue → 自然偏低。
  - recency    ：连续时间衰减（_fusion.recency_decay，半衰期 365d）；预印本 ×1.2 boost 封顶 1.0。
  - relevance  ：源返回相关性 rank → 分位。

去重：DOI 优先 → arXiv ID 兜底 → OpenAlex id 兜底 → 标题归一；引用数取 max + 标注来源，
优先 OpenAlex 字段，保留正式版（有 venue）为代表。

HTTP 集中在模块级 async 函数（_fetch_openalex / _fetch_s2 / _fetch_arxiv），便于单测
monkeypatch，零网络。研究依据见 /tmp/wrr-research-report.md §3 与 STDD §5.1。
"""
import asyncio
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .base import SearchEngine
from ._fusion import recency_decay
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult

# 内部统一论文表示（paper_dict）字段：
#   title cited_by_count influential_citations pub_date(datetime|None) is_preprint
#   venue venue_rank doi arxiv_id openalex_id source source_relevance
#   tldr abstract doi_url landing_url [cite_sources]


# ── 小工具 ───────────────────────────────────────────────────────────
def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _parse_date(val) -> Optional[datetime]:
    """解析 'YYYY-MM-DD' / ISO 8601 → aware UTC datetime。"""
    if not val or not isinstance(val, str):
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(val[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _year_date(year) -> Optional[datetime]:
    y = _int(year)
    if y <= 0:
        return None
    return datetime(y, 1, 1, tzinfo=timezone.utc)


def _clean_doi(doi: str) -> str:
    """归一 DOI：剥 https://doi.org/ 前缀、小写。"""
    if not doi:
        return ""
    d = doi.strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def _rank_relevance(idx: int, total: int) -> float:
    """源返回顺序 → 相关性分位（首位最高，末位最低，恒 >0）。"""
    if total <= 0:
        return 0.0
    return (total - idx) / total


def _reconstruct_abstract(inv) -> str:
    """OpenAlex abstract_inverted_index → 还原正文。"""
    if not isinstance(inv, dict) or not inv:
        return ""
    positions: List = []
    for word, idxs in inv.items():
        for i in idxs or []:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


# ── 纯评分函数（单测可直接调用）──────────────────────────────────────
def citation_velocity(cited_by_count: int, age_years: float) -> float:
    """年均引用对数压缩到 [0,1]。~300/yr → 1.0。

    用年均引用而非绝对引用数：老论文引用高但 age 大，velocity 不会碾压新论文。
    """
    age = max(age_years, 0.25)                    # 下界保护，避免极新论文 velocity 爆炸
    velocity = max(cited_by_count, 0) / age
    return min(math.log10(velocity + 1) / 2.5, 1.0)


def academic_score(paper: Dict[str, Any], now: Optional[datetime] = None) -> float:
    """4 维加权综合分。权重取自 config.ACADEMIC_SCORE_WEIGHTS。"""
    now = now or datetime.now(timezone.utc)
    w_v, w_a, w_r, w_rel = config.ACADEMIC_SCORE_WEIGHTS
    pub = paper.get("pub_date")

    # 1. velocity：年均引用对数压缩
    if pub is not None:
        age_years = max((now - pub).days / 365.0, 0.25)
    else:
        age_years = 5.0                           # 未知日期 → 中性偏老
    velocity = citation_velocity(_int(paper.get("cited_by_count")), age_years)

    # 2. authority：venue 权威 + S2 influential 引用占比
    cited = _int(paper.get("cited_by_count"))
    infl = _int(paper.get("influential_citations"))
    infl_ratio = (infl / cited) if cited > 0 else 0.0
    venue_rank = float(paper.get("venue_rank") or 0.0)
    authority = min(0.6 * venue_rank + 0.4 * min(infl_ratio * 3, 1.0), 1.0)

    # 3. recency：连续衰减（半衰期 365d）+ 预印本 boost
    if pub is not None:
        age_hours = max((now - pub).total_seconds() / 3600.0, 0.0)
        recency = recency_decay(age_hours, config.ACADEMIC_RECENCY_HALFLIFE_DAYS * 24.0)
    else:
        recency = 0.5
    if paper.get("is_preprint"):
        recency = min(recency * 1.2, 1.0)

    # 4. relevance：源相关性分位
    relevance = float(paper.get("source_relevance") or 0.0)

    return w_v * velocity + w_a * authority + w_r * recency + w_rel * relevance


# ── 去重（DOI 优先 → arXiv → openalex → 标题）─────────────────────────
def _dedup_key(p: Dict[str, Any]) -> str:
    doi = (p.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    ax = (p.get("arxiv_id") or "").strip().lower()
    if ax:
        return "arxiv:" + ax
    oa = (p.get("openalex_id") or "").strip().lower()
    if oa:
        return "openalex:" + oa
    return "title:" + re.sub(r"\W+", "", (p.get("title") or "").lower())


def _merge_into(base: Dict[str, Any], other: Dict[str, Any]) -> None:
    """引用取 max + 标注来源；优先 OpenAlex 字段；保留正式版（有 venue）为代表。"""
    base["cited_by_count"] = max(_int(base.get("cited_by_count")),
                                 _int(other.get("cited_by_count")))
    base["influential_citations"] = max(_int(base.get("influential_citations")),
                                        _int(other.get("influential_citations")))
    cs = base.setdefault("cite_sources", {})
    if other.get("source"):
        cs[other["source"]] = _int(other.get("cited_by_count"))

    # 缺字段补全（任一源有就补）
    for f in ("tldr", "abstract", "venue", "doi", "doi_url", "landing_url",
              "arxiv_id", "openalex_id", "pub_date"):
        if not base.get(f) and other.get(f):
            base[f] = other[f]

    # 正式版优先：有 venue → 提升权威、视为已发表代表
    if other.get("venue") and not base.get("venue"):
        base["venue"] = other["venue"]
    if other.get("venue"):
        base["venue_rank"] = max(float(base.get("venue_rank") or 0.0),
                                 float(other.get("venue_rank") or 0.0))
    if not other.get("is_preprint"):
        base["is_preprint"] = False

    # OpenAlex 字段优先（日更最快、口径最一致）
    if other.get("source") == "openalex":
        for f in ("doi", "doi_url", "venue", "venue_rank", "pub_date",
                  "openalex_id", "landing_url"):
            if other.get(f):
                base[f] = other[f]
        base["source"] = "openalex"


def dedup_by_doi(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """DOI 优先合并同一篇（arXiv ID/openalex id/标题兜底），保留首见为代表。"""
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for p in papers:
        key = _dedup_key(p)
        if key in merged:
            _merge_into(merged[key], p)
        else:
            rep = dict(p)
            rep["cite_sources"] = {p["source"]: _int(p.get("cited_by_count"))} \
                if p.get("source") else {}
            merged[key] = rep
            order.append(key)
    return [merged[k] for k in order]


# ── 各源解析（纯函数）────────────────────────────────────────────────
def _parse_openalex_work(work: Dict[str, Any], idx: int, total: int) -> Optional[Dict[str, Any]]:
    title = (work.get("title") or work.get("display_name") or "").strip()
    if not title:
        return None
    ids = work.get("ids") or {}
    doi_url = ids.get("doi") or work.get("doi") or ""
    openalex_id = ids.get("openalex") or work.get("id") or ""
    ploc = work.get("primary_location") or {}
    venue = ((ploc.get("source") or {}).get("display_name") or "").strip()
    landing = ploc.get("landing_page_url") or openalex_id or ""
    is_preprint = (work.get("type") or "").lower() == "preprint"
    return {
        "title": title,
        "cited_by_count": _int(work.get("cited_by_count")),
        "influential_citations": 0,
        "pub_date": _parse_date(work.get("publication_date")),
        "is_preprint": is_preprint,
        "venue": venue,
        "venue_rank": 0.0 if (is_preprint or not venue) else 0.5,
        "doi": _clean_doi(doi_url),
        "arxiv_id": "",
        "openalex_id": openalex_id,
        "source": "openalex",
        "source_relevance": _rank_relevance(idx, total),
        "tldr": "",
        "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        "doi_url": doi_url,
        "landing_url": landing,
    }


def _parse_s2_paper(p: Dict[str, Any], idx: int, total: int) -> Optional[Dict[str, Any]]:
    title = (p.get("title") or "").strip()
    if not title:
        return None
    ext = p.get("externalIds") or {}
    doi = _clean_doi(ext.get("DOI") or "")
    arxiv_id = (ext.get("ArXiv") or "").strip()
    venue = (p.get("venue") or "").strip()
    tldr_obj = p.get("tldr") or {}
    tldr = (tldr_obj.get("text") if isinstance(tldr_obj, dict) else "") or ""
    pub_date = _parse_date(p.get("publicationDate")) or _year_date(p.get("year"))
    is_preprint = (not venue) and bool(arxiv_id)
    return {
        "title": title,
        "cited_by_count": _int(p.get("citationCount")),
        "influential_citations": _int(p.get("influentialCitationCount")),
        "pub_date": pub_date,
        "is_preprint": is_preprint,
        "venue": venue,
        "venue_rank": 0.0 if (is_preprint or not venue) else 0.5,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": "",
        "source": "semantic_scholar",
        "source_relevance": _rank_relevance(idx, total),
        "tldr": tldr,
        "abstract": (p.get("abstract") or ""),
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "landing_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
    }


_ATOM = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_arxiv_atom(text: str, count: int) -> List[Dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    entries = root.findall("atom:entry", _ATOM)
    out: List[Dict[str, Any]] = []
    total = len(entries)
    for idx, e in enumerate(entries):
        title = (e.findtext("atom:title", default="", namespaces=_ATOM) or "").strip()
        if not title:
            continue
        url = (e.findtext("atom:id", default="", namespaces=_ATOM) or "").strip()
        arxiv_id = url.rsplit("/abs/", 1)[-1] if "/abs/" in url else ""
        summary = (e.findtext("atom:summary", default="", namespaces=_ATOM) or "").strip()
        pub_date = _parse_date(e.findtext("atom:published", default="", namespaces=_ATOM))
        out.append({
            "title": title,
            "cited_by_count": 0,
            "influential_citations": 0,
            "pub_date": pub_date,
            "is_preprint": True,
            "venue": "",
            "venue_rank": 0.0,
            "doi": "",
            "arxiv_id": arxiv_id,
            "openalex_id": "",
            "source": "arxiv",
            "source_relevance": _rank_relevance(idx, total),
            "tldr": "",
            "abstract": summary,
            "doi_url": "",
            "landing_url": url,
        })
        if len(out) >= count:
            break
    return out


# ── HTTP（模块级，便于单测 monkeypatch）──────────────────────────────
def _per_page(count: int, cap: int) -> int:
    return min(max(count, 1), cap)


async def _fetch_openalex(options: SearchOptions) -> List[Dict[str, Any]]:
    """OpenAlex works 检索 → paper_dict 列表。主力源。"""
    params = {
        "search": options.query,
        "mailto": config.OPENALEX_MAILTO,
        "per_page": _per_page(options.count, 25),
    }
    async with httpx.AsyncClient(timeout=config.ACADEMIC_SOURCE_TIMEOUT) as client:
        r = await client.get(config.OPENALEX_API, params=params)
        r.raise_for_status()
        data = r.json() or {}
    works = data.get("results") or []
    parsed = [_parse_openalex_work(w, i, len(works)) for i, w in enumerate(works)]
    return [p for p in parsed if p]


async def _fetch_s2(options: SearchOptions) -> List[Dict[str, Any]]:
    """Semantic Scholar paper search → paper_dict 列表。引用质量 + tldr 补充。"""
    params = {
        "query": options.query,
        "fields": ("title,abstract,citationCount,influentialCitationCount,"
                   "tldr,externalIds,year,venue,publicationDate"),
        "limit": _per_page(options.count, 25),
    }
    async with httpx.AsyncClient(timeout=config.ACADEMIC_SOURCE_TIMEOUT) as client:
        r = await client.get(config.SEMANTIC_SCHOLAR_API, params=params)
        r.raise_for_status()
        data = r.json() or {}
    papers = data.get("data") or []
    parsed = [_parse_s2_paper(p, i, len(papers)) for i, p in enumerate(papers)]
    return [p for p in parsed if p]


async def _fetch_arxiv(options: SearchOptions) -> List[Dict[str, Any]]:
    """arXiv 预印本（Atom）→ paper_dict 列表。默认 lazy（P2，3s/req 慢）。"""
    params = {
        "search_query": f"all:{options.query}",
        "start": 0,
        "max_results": _per_page(options.count, 15),
    }
    async with httpx.AsyncClient(timeout=config.ACADEMIC_SOURCE_TIMEOUT) as client:
        r = await client.get(config.ARXIV_API, params=params)
        r.raise_for_status()
        text = r.text
    return _parse_arxiv_atom(text, options.count)


# ── 输出映射 ─────────────────────────────────────────────────────────
def _to_result(p: Dict[str, Any]) -> SearchResult:
    cited = _int(p.get("cited_by_count"))
    sig = f"📚{cited}cit"
    infl = _int(p.get("influential_citations"))
    if infl:
        sig += f"（{infl} influential）"
    if p.get("is_preprint"):
        sig += " ·preprint"
    body = (p.get("tldr") or p.get("abstract") or "").strip()
    snippet = (body[:300] + " · " + sig) if body else sig
    venue = (p.get("venue") or "").strip()
    if venue:
        snippet += " · " + venue
    doi = (p.get("doi") or "").strip()
    url = (p.get("doi_url") or (f"https://doi.org/{doi}" if doi else "")
           or p.get("landing_url") or p.get("openalex_id") or "")
    return SearchResult(
        title=(p.get("title") or "").strip() or "(untitled)",
        url=url,
        snippet=snippet,
        source_tag=f"academic:{p.get('source', '')}",
    )


class AcademicEngine(SearchEngine):
    name = "academic"
    tier = 0  # 无本地配置要求

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        now = datetime.now(timezone.utc)
        # 主力 openalex + 补充 s2；arxiv 仅当显式开启（默认 lazy）
        fetchers = [_fetch_openalex(options), _fetch_s2(options)]
        if config.ACADEMIC_INCLUDE_ARXIV:
            fetchers.append(_fetch_arxiv(options))
        gathered = await asyncio.gather(*fetchers, return_exceptions=True)

        papers: List[Dict[str, Any]] = []
        for res in gathered:
            if isinstance(res, Exception) or not res:
                continue                                  # 各源独立失败隔离
            papers.extend(res)
        if not papers:
            raise EngineError("academic: all sources failed or returned no results")

        merged = dedup_by_doi(papers)                     # DOI 优先合并
        scored = sorted(merged, key=lambda p: academic_score(p, now), reverse=True)
        return [_to_result(p) for p in scored[:options.count]]

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        """探测 OpenAlex / Semantic Scholar / arXiv 公开 API 可达性；可选检查 paper-search-mcp。"""
        import httpx
        sources_ok: list[str] = []
        sources_fail: list[str] = []
        details: list[str] = []

        probes = {
            "openalex": "https://api.openalex.org/works?per_page=1",
            "semantic_scholar": "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1",
            "arxiv": "http://export.arxiv.org/api/query?search_query=all:test&max_results=1",
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in probes.items():
                try:
                    resp = await client.get(url)
                    if resp.status_code < 500:
                        sources_ok.append(name)
                    else:
                        sources_fail.append(f"{name}({resp.status_code})")
                except Exception as e:
                    sources_fail.append(f"{name}({type(e).__name__})")

        # paper-search-mcp (optional)
        mcp_url = config.get_env("PAPER_SEARCH_MCP_URL")
        if mcp_url:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"{mcp_url.rstrip('/')}/health")
                if resp.status_code < 500:
                    sources_ok.append("paper-search-mcp")
                else:
                    details.append(f"paper-search-mcp returned {resp.status_code}")
            except Exception:
                details.append("paper-search-mcp configured but unreachable")

        active = "+".join(sources_ok) if sources_ok else "none"
        if not sources_fail and sources_ok:
            return EngineCheckResult(
                engine=self.name,
                status="ok",
                tier=self.tier,
                summary=f"Academic sources OK ({len(sources_ok)}/{len(probes)})",
                active_backend=active,
                evidence={"sources_ok": sources_ok},
            )
        elif sources_ok:
            return EngineCheckResult(
                engine=self.name,
                status="warn",
                tier=self.tier,
                summary=f"Some sources unreachable ({len(sources_ok)}/{len(probes)} ok)",
                details="; ".join(sources_fail + details),
                active_backend=active,
                repair=[
                    "Check network connectivity to academic APIs",
                    "Verify no firewall blocking api.openalex.org / api.semanticscholar.org / export.arxiv.org",
                    "Optional: set PAPER_SEARCH_MCP_URL for MCP-based access",
                ],
                evidence={"sources_ok": sources_ok, "sources_fail": sources_fail},
            )
        else:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="All academic sources unreachable",
                details="; ".join(sources_fail + details),
                repair=[
                    "Check network connectivity",
                    "All sources (api.openalex.org / api.semanticscholar.org / export.arxiv.org) are unreachable",
                    "Verify DNS resolution and firewall rules",
                ],
                evidence={"sources_ok": [], "sources_fail": sources_fail},
            )
