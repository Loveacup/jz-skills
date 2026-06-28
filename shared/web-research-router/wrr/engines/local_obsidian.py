"""local_obsidian 引擎（v5.2，Tier 2）：直接读 Obsidian vault Markdown。

数据源：本地 vault 文件系统（白名单目录，仅 *.md）。
适用：qmd 不可用 / 索引滞后时兜底；frontmatter 精准匹配。
权重低于 qmd（索引兜底定位）。只实现 search() + health_check()。

安全/限流（强约束，见 codex-eval §7）：
  - 只扫 config.obsidian_vault_paths() 配置目录；不做全盘 find。
  - 仅 *.md；不读 .env/secrets/附件/二进制。
  - max files / max bytes / exclude dirs / 扫描超时，防慢查询拖垮 local mode。
"""
from __future__ import annotations

import asyncio
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult
from ._local_utils import (scan_markdown_files, count_markdown_files,
                           read_text_prefix, parse_frontmatter_and_body,
                           score_markdown_match, tokenize)


class LocalObsidianEngine(SearchEngine):
    name = "local_obsidian"
    tier = 2

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        roots = config.obsidian_vault_paths()
        if not roots:
            raise EngineError("no obsidian vault configured (set WRR_OBSIDIAN_VAULTS)")

        query_terms = tokenize(options.query)
        if not query_terms:
            return []
        limit = min(options.count, config.LOCAL_MAX_RESULTS_PER_ENGINE)

        # 扫描 + 评分整体放线程池，并加超时硬上限。
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
