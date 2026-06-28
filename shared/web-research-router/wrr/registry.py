"""引擎注册表 + 共享单例。"""
from typing import Dict, List, Optional

from .engines.base import SearchEngine
from .engines.exa import ExaEngine
from .engines.brave import BraveEngine
from .engines.searxng import SearxngEngine
from .engines.github import GitHubEngine
from .engines.community import CommunityEngine
from .engines.academic import AcademicEngine          # v5.0
from .engines.skill_discovery import SkillDiscoveryEngine  # v5.0
from .engines.local_supermemory import LocalSupermemoryEngine  # v5.2
from .engines.local_session import LocalSessionEngine          # v5.2
from .engines.local_qmd import LocalQmdEngine                  # v5.2
from .engines.local_obsidian import LocalObsidianEngine        # v5.2


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: Dict[str, SearchEngine] = {}

    def register(self, engine: SearchEngine) -> None:
        self._engines[engine.name] = engine

    def get(self, name: str) -> Optional[SearchEngine]:
        return self._engines.get(name)

    def names(self) -> List[str]:
        return list(self._engines.keys())

    def all(self) -> List[SearchEngine]:
        """返回所有已注册引擎实例。"""
        return list(self._engines.values())

    def doctor_targets(self) -> List[SearchEngine]:
        """返回 doctor 检查目标引擎列表。"""
        return self.all()


def default_registry() -> EngineRegistry:
    reg = EngineRegistry()
    reg.register(ExaEngine())
    reg.register(BraveEngine())
    reg.register(SearxngEngine())
    reg.register(GitHubEngine())
    reg.register(CommunityEngine())
    reg.register(AcademicEngine())          # v5.0
    reg.register(SkillDiscoveryEngine())    # v5.0
    reg.register(LocalSupermemoryEngine())  # v5.2 本地层
    reg.register(LocalSessionEngine())      # v5.2 本地层
    reg.register(LocalQmdEngine())          # v5.2 本地层
    reg.register(LocalObsidianEngine())     # v5.2 本地层
    return reg


_SHARED: Optional[EngineRegistry] = None


def get_registry() -> EngineRegistry:
    """进程内共享注册表（引擎构造无网络副作用，懒加载即可）。"""
    global _SHARED
    if _SHARED is None:
        _SHARED = default_registry()
    return _SHARED
