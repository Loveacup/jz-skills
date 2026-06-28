"""SearchEngine 抽象基类。引擎只实现自己支持的能力，其余默认抛 EngineError。"""
from abc import ABC
from typing import List

from .. import config
from ..errors import EngineError
from ..schemas import (SearchOptions, SearchResult, ExtractOptions,
                       ExtractResult, SimilarOptions)


class SearchEngine(ABC):
    name: str = "base"

    @property
    def timeout(self) -> float:
        return config.ENGINE_TIMEOUT.get(self.name, config.DEFAULT_ENGINE_TIMEOUT)

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        raise EngineError(f"{self.name} does not support search")

    async def extract(self, options: ExtractOptions) -> ExtractResult:
        raise EngineError(f"{self.name} does not support extract")

    async def similar(self, options: SimilarOptions) -> List[SearchResult]:
        raise EngineError(f"{self.name} does not support similar")
