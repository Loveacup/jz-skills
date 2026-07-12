#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
platform_router.py — V4 平台路由（STDD D18 接口收窄 + 确定性路由）。

职责边界
--------
- **PlatformAdapter 只暴露 `can_handle()` 与 `collect()`**（D18）。下载器、授权
  浏览器、ASR、评论采集器都是 Adapter 私有依赖，不进入公共接口。
- **Router 只做识别与派发**，不做采集、不联网。支持 Bilibili / YouTube / Douyin
  的 URL 与分享文本识别。
- **零匹配 / 多匹配都是明确错误**，绝不做「猜平台」fallback。

本模块不含任何具体 Adapter 实现（Bilibili 在 V4-A2、YouTube 在 V4-C、Douyin 在
V4-D 分别接入）。A1 只锁定接口与路由不变量。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Protocol, Tuple, Union, runtime_checkable

from evidence_contract import EvidenceBundle

# ---------------------------------------------------------------------------
# 输入 / 选项
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceInput:
    """用户提供的原始来源：一条 URL 或一段分享文本。"""

    raw: str
    hint: str = ""  # 可选平台提示，仅用于消歧，不覆盖识别结果


@dataclass(frozen=True)
class CollectOptions:
    """采集选项；凭据和平台私有配置必须由 Adapter 内部依赖提供。"""

    want_transcript: bool = True
    want_audience: bool = True
    timeout_s: float = 60.0


SourceLike = Union[str, SourceInput]


def _raw_text(source: SourceLike) -> str:
    if isinstance(source, SourceInput):
        return source.raw
    return str(source)


# ---------------------------------------------------------------------------
# Adapter 接口（D18：只有 can_handle / collect）
# ---------------------------------------------------------------------------

@runtime_checkable
class PlatformAdapter(Protocol):
    platform: str
    adapter_version: str

    def can_handle(self, source: SourceInput) -> bool: ...

    def collect(self, source: SourceInput, options: CollectOptions) -> EvidenceBundle: ...


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class RouteError(Exception):
    """路由失败基类。"""


class NoPlatformMatched(RouteError):
    """URL / 分享文本未命中任何受支持平台。"""


class MultiplePlatformsMatched(RouteError):
    """来源同时命中多个平台，拒绝猜测。"""


class NoAdapterMatched(RouteError):
    """没有 Adapter 声明能处理该来源。"""


class MultipleAdaptersMatched(RouteError):
    """多个 Adapter 同时声明能处理，拒绝猜测。"""


# ---------------------------------------------------------------------------
# 平台识别（URL / 分享文本）
# ---------------------------------------------------------------------------

# 说明：模式面向公开 URL 结构与分享短链域名，不解析任何私有签名参数。
PLATFORM_PATTERNS: Mapping[str, Tuple[re.Pattern, ...]] = {
    "bilibili": (
        re.compile(r"bilibili\.com/video/(?:BV[0-9A-Za-z]{10}|av\d+)", re.I),
        re.compile(r"\bb23\.tv/[0-9A-Za-z]+", re.I),
        re.compile(r"\bBV[0-9A-Za-z]{10}\b"),
    ),
    "youtube": (
        re.compile(r"youtube\.com/watch\?[^ ]*\bv=[0-9A-Za-z_-]{11}", re.I),
        re.compile(r"youtube\.com/shorts/[0-9A-Za-z_-]{11}", re.I),
        re.compile(r"youtu\.be/[0-9A-Za-z_-]{11}", re.I),
    ),
    "douyin": (
        re.compile(r"\bv\.douyin\.com/[0-9A-Za-z]+", re.I),
        re.compile(r"(?:www\.)?douyin\.com/video/\d+", re.I),
        re.compile(r"iesdouyin\.com/", re.I),
    ),
}

SUPPORTED_PLATFORMS: Tuple[str, ...] = tuple(PLATFORM_PATTERNS.keys())


def detect_platforms(source: SourceLike) -> Tuple[str, ...]:
    """返回所有命中的平台名（去重、按 SUPPORTED_PLATFORMS 顺序，确定性）。"""
    text = _raw_text(source)
    hits: List[str] = []
    for platform, patterns in PLATFORM_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            hits.append(platform)
    return tuple(hits)


def identify_platform(source: SourceLike) -> str:
    """
    识别唯一平台。零命中 -> NoPlatformMatched；多命中 -> MultiplePlatformsMatched。
    不做任何猜测式 fallback。
    """
    hits = detect_platforms(source)
    if not hits:
        raise NoPlatformMatched(f"来源未命中任何受支持平台: {_raw_text(source)!r}")
    if len(hits) > 1:
        raise MultiplePlatformsMatched(
            f"来源同时命中多个平台 {hits}，拒绝猜测: {_raw_text(source)!r}"
        )
    return hits[0]


# ---------------------------------------------------------------------------
# Adapter 级路由
# ---------------------------------------------------------------------------

class PlatformRouter:
    """按 Adapter.can_handle() 确定性派发；零 / 多匹配均为明确错误。"""

    def __init__(self, adapters: Iterable[PlatformAdapter]):
        self._adapters: Tuple[PlatformAdapter, ...] = tuple(adapters)

    @property
    def adapters(self) -> Tuple[PlatformAdapter, ...]:
        return self._adapters

    def route(self, source: SourceLike) -> PlatformAdapter:
        src = source if isinstance(source, SourceInput) else SourceInput(raw=str(source))
        matches: List[PlatformAdapter] = [a for a in self._adapters if a.can_handle(src)]
        if not matches:
            raise NoAdapterMatched(f"没有 Adapter 能处理来源: {src.raw!r}")
        if len(matches) > 1:
            names = tuple(getattr(a, "platform", repr(a)) for a in matches)
            raise MultipleAdaptersMatched(
                f"多个 Adapter 同时匹配 {names}，拒绝猜测: {src.raw!r}"
            )
        return matches[0]

    def collect(self, source: SourceLike, options: CollectOptions) -> EvidenceBundle:
        src = source if isinstance(source, SourceInput) else SourceInput(raw=str(source))
        return self.route(src).collect(src, options)


__all__ = [
    "SourceInput",
    "CollectOptions",
    "PlatformAdapter",
    "RouteError",
    "NoPlatformMatched",
    "MultiplePlatformsMatched",
    "NoAdapterMatched",
    "MultipleAdaptersMatched",
    "PLATFORM_PATTERNS",
    "SUPPORTED_PLATFORMS",
    "detect_platforms",
    "identify_platform",
    "PlatformRouter",
]
