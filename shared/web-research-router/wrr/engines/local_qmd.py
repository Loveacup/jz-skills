"""local_qmd 引擎（v5.2，Tier 2）：Obsidian/QMD 全文索引。

数据源：本机 `qmd` CLI（BM25 全文检索）。实测命令：
    qmd search <query> --json -n <limit>
  → JSON 数组 [{docid, score, file, line, title, context, snippet}, ...]
  其中 file 已是 `qmd://<collection>/<path>` 形式，line 为独立字段。

适用查询：项目文档、架构决策、历史报告。优先 CLI（WRR CLI 需独立可运行）。
JSON 解析失败时降级为纯文本最小解析。只实现 search() + health_check()。
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult
from ._local_utils import (run_command, normalize_local_query,
                        LOCAL_FRESHNESS_DEFAULT)


def _qmd_bin() -> str:
    return shutil.which(os.environ.get("QMD_BIN", "qmd")) or ""


class LocalQmdEngine(SearchEngine):
    name = "local_qmd"
    tier = 2

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        qmd = _qmd_bin()
        if not qmd:
            raise EngineError("qmd binary not found")

        limit = min(options.count, config.LOCAL_MAX_RESULTS_PER_ENGINE)
        query = normalize_local_query(options.query)
        try:
            rc, stdout, stderr = await run_command(
                [qmd, "search", query, "--json", "-n", str(limit)],
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise EngineError(f"qmd search timed out >{self.timeout:.1f}s")
        if rc != 0:
            raise EngineError(f"qmd search failed: {stderr[:200]}")

        return self._parse(stdout, limit)

    def _parse(self, stdout: str, limit: int) -> List[SearchResult]:
        """优先 JSON；失败回退纯文本最小解析（P0 兜底）。"""
        rows = self._parse_json(stdout)
        if rows is None:
            return self._parse_text(stdout, limit)

        out: List[SearchResult] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            file = row.get("file") or row.get("path") or ""
            line = row.get("line") or row.get("lineNumber")
            url = file or f"qmd://{row.get('collection', 'default')}"
            if line:
                url = f"{url}#L{line}"
            snippet = (row.get("snippet") or row.get("context")
                       or row.get("text") or "")

            out.append(SearchResult(
                title=str(row.get("title") or file or "QMD result")[:120],
                url=url,
                snippet=str(snippet)[:500],
                highlights=[str(row.get("snippet"))[:300]] if row.get("snippet") else [],
                source_tag="local:qmd",
                freshness_score=LOCAL_FRESHNESS_DEFAULT,
            ))
        return out

    @staticmethod
    def _parse_json(stdout: str):
        try:
            payload = json.loads(stdout or "[]")
        except (json.JSONDecodeError, ValueError):
            return None
        if isinstance(payload, dict):
            return payload.get("results", [])
        if isinstance(payload, list):
            return payload
        return None

    @staticmethod
    def _parse_text(stdout: str, limit: int) -> List[SearchResult]:
        """纯文本兜底：识别 `qmd://...:line` 起始行 + 紧随的 Title 行。"""
        out: List[SearchResult] = []
        lines = (stdout or "").splitlines()
        i = 0
        while i < len(lines) and len(out) < limit:
            line = lines[i].strip()
            if line.startswith("qmd://") or line.startswith("file://"):
                url = line.split(" ")[0]  # 去掉尾部 docid
                if ":" in url.rsplit("/", 1)[-1]:
                    path, _, lno = url.rpartition(":")
                    url = f"{path}#L{lno}" if lno.isdigit() else url
                title = url
                snippet = ""
                if i + 1 < len(lines) and lines[i + 1].strip().lower().startswith("title:"):
                    title = lines[i + 1].split(":", 1)[1].strip()
                out.append(SearchResult(
                    title=title[:120], url=url, snippet=snippet,
                    source_tag="local:qmd",
                    freshness_score=LOCAL_FRESHNESS_DEFAULT))
            i += 1
        return out

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        qmd = _qmd_bin()
        if not qmd:
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary="qmd binary not found",
                requirements=["binary:qmd"],
                repair=["Install qmd (brew install qmd) or set QMD_BIN",
                        "Rerun: wrr-cli.py doctor --engine local_qmd"],
                evidence={"qmd.path": "missing"},
            )
        if not deep:
            return EngineCheckResult(
                engine=self.name, status="ok", tier=self.tier,
                summary="qmd binary found",
                active_backend="qmd-cli",
                evidence={"qmd.path": qmd},
            )
        try:
            rc, stdout, stderr = await run_command([qmd, "status"], timeout=3.0)
        except asyncio.TimeoutError:
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary="qmd status timed out",
                evidence={"qmd.path": qmd, "probe": "timeout"},
            )
        if rc != 0:
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary="qmd status failed",
                evidence={"qmd.path": qmd, "stderr": stderr[:300]},
            )
        # 解析 "Pending: N need embedding" → 索引陈旧 warn
        pending = self._parse_pending(stdout)
        stale = pending > 0
        return EngineCheckResult(
            engine=self.name, status="warn" if stale else "ok", tier=self.tier,
            summary=("qmd index reachable but stale" if stale
                     else "qmd index reachable"),
            active_backend="qmd-cli",
            requirements=["binary:qmd", "qmd index"],
            repair=["Run 'qmd embed' to refresh stale index"] if stale else [],
            evidence={"qmd.path": qmd, "pending_embedding": pending},
        )

    @staticmethod
    def _parse_pending(status_text: str) -> int:
        import re
        m = re.search(r"Pending:\s*(\d+)\s+need embedding", status_text or "")
        return int(m.group(1)) if m else 0
