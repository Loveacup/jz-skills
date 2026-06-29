"""local_obsidian 引擎（v5.2，Tier 2）：本地 Obsidian vault。

数据源：白名单目录 *.md 文件扫描 + frontmatter 解析 + 相关性评分。
适用查询：「我记得写过 / 笔记里有 / 之前研究过 / vault 里有没有」。
只实现 search() + health_check()；不实现 extract/similar。

降级：vault 目录不存在 → health_check fail、search 抛 EngineError，
由 router gather 隔离，local mode 可用 web 兜底。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult
from ._local_utils import (
    scan_markdown_files, read_text_prefix, parse_frontmatter_and_body,
    score_markdown_match, tokenize, count_markdown_files,
    LOCAL_FRESHNESS_DEFAULT,
)


class LocalObsidianEngine(SearchEngine):
    name = "local_obsidian"
    tier = 2

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        roots = config.obsidian_vault_paths()
        if not roots:
            raise EngineError("No Obsidian vault configured")

        query_terms = tokenize(options.query)
        if not query_terms:
            return []
        limit = min(options.count, config.LOCAL_MAX_RESULTS_PER_ENGINE)

        scored = await asyncio.wait_for(
            asyncio.to_thread(self._scan_and_score, roots, query_terms),
            timeout=self.timeout,
        )
        scored.sort(reverse=True, key=lambda x: x[0])

        out: List[SearchResult] = []
        for score, path, line, snippet, fm in scored[:limit]:
            title = (fm.get("title") if isinstance(fm, dict) else None) or path.stem
            url = f"file://{path}"
            if line:
                url += f"#L{line}"

            out.append(SearchResult(
                title=str(title)[:120],
                url=url,
                snippet=(snippet or "")[:500],
                highlights=[snippet[:300]] if snippet else [],
                source_tag="local:obsidian",
                freshness_score=LOCAL_FRESHNESS_DEFAULT,
            ))
        return out

    def _scan_and_score(self, roots, query_terms):
        candidates = scan_markdown_files(
            roots, config.LOCAL_OBSIDIAN_MAX_FILES,
            config.LOCAL_OBSIDIAN_EXCLUDE_DIRS)
        scored = []
        for path in candidates:
            text = read_text_prefix(path, config.LOCAL_OBSIDIAN_MAX_BYTES)
            if not text:
                continue
            fm, body = parse_frontmatter_and_body(text)
            score, line, snippet = score_markdown_match(
                query_terms, fm, body, path.name)
            if score > 0:
                scored.append((score, path, line, snippet, fm))
        return scored

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        roots = config.obsidian_vault_paths()
        existing = [p for p in roots if p.exists() and p.is_dir()]
        if not existing:
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary="No readable Obsidian vault configured",
                requirements=["env:WRR_OBSIDIAN_VAULTS or default vault path"],
                repair=["Set WRR_OBSIDIAN_VAULTS to one or more vault directories",
                        "  export WRR_OBSIDIAN_VAULTS=/path/to/vault",
                        "Rerun: wrr-cli.py doctor --engine local_obsidian"],
                evidence={"configured_paths": [str(p) for p in roots]},
            )
        if not deep:
            return EngineCheckResult(
                engine=self.name, status="ok", tier=self.tier,
                summary="Obsidian vault path exists",
                active_backend="filesystem",
                evidence={"paths": [str(p) for p in existing]},
            )
        md_count = await asyncio.to_thread(count_markdown_files, existing, 1000)
        return EngineCheckResult(
            engine=self.name, status="ok" if md_count > 0 else "warn", tier=self.tier,
            summary=f"Obsidian vault reachable; markdown files sampled={md_count}",
            active_backend="filesystem",
            evidence={"paths": [str(p) for p in existing], "sample_md_count": md_count},
        )
