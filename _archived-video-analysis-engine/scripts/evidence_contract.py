#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evidence_contract.py — V4 视频分析引擎的唯一外部证据契约（STDD D1/D8/D19）。

设计立场
--------
- **单一外部接口**：所有平台（Bilibili / YouTube / Douyin）经 Adapter 采集后，
  统一收敛为 `EvidenceBundle`。旧的 `AnalysisInput` 只作为 bundle → legacy core
  的内部迁移视图，不在本模块出现，也不作为公共入口。
- **四状态显式降级**（D19）：`ready | metadata_only | auth_required | unavailable`。
  预期的平台失败以 *状态 + 错误* 返回，而不是靠抛异常让上游猜测。
- **只有 `ready` 可发布**：`is_publishable()` 是 Writer / publish gate 的唯一判据。
- **版本闸**：major 不兼容立即拒绝；minor 只允许新增可选字段。

安全边界（本模块强制）
--------------------
- Adapter 私有原始响应（cookie、a_bogus、平台私有 payload、内部 endpoint）
  **不得**进入 bundle。`EvidenceError.safe_message` 经敏感词校验。
- 本模块不联网、不落盘、不做采集，只定义契约与校验。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

# ---------------------------------------------------------------------------
# 版本
# ---------------------------------------------------------------------------

EVIDENCE_SCHEMA_VERSION = "4.1.0"
SUPPORTED_PLATFORMS: Tuple[str, ...] = ("bilibili", "youtube", "douyin")

# metadata/provenance 中禁止出现的平台私有容器或凭据键。
_PRIVATE_PAYLOAD_KEYS = frozenset(
    {
        "raw_response",
        "raw_payload",
        "cookie",
        "cookies",
        "headers",
        "authorization",
        "token",
        "access_token",
        "refresh_token",
        "sessdata",
        "a_bogus",
        "x-bogus",
    }
)
_CREDENTIAL_ASSIGNMENTS: Tuple[str, ...] = (
    "cookie=",
    "sessdata=",
    "authorization=",
    "bearer ",
    "token=",
    "access_token=",
    "refresh_token=",
    "a_bogus=",
    "x-bogus=",
)
_METADATA_ONLY_GAP_CODES = frozenset(
    {"media_unavailable", "transcript_unavailable", "asr_failed"}
)

# ---------------------------------------------------------------------------
# 状态与枚举（用 tuple 常量而非 Literal 运行时校验）
# ---------------------------------------------------------------------------

EVIDENCE_STATUSES: Tuple[str, ...] = (
    "ready",
    "metadata_only",
    "auth_required",
    "unavailable",
)

ERROR_CODES: Tuple[str, ...] = (
    "unsupported_source",
    "resolve_failed",
    "metadata_failed",
    "auth_required",
    "media_unavailable",
    "transcript_unavailable",
    "asr_failed",
    "audience_unavailable",
    "platform_changed",
)

ERROR_STAGES: Tuple[str, ...] = (
    "route",
    "resolve",
    "metadata",
    "media",
    "asr",
    "audience",
)

# safe_message 里绝不允许出现的敏感材料痕迹（大小写不敏感子串匹配）。
_SENSITIVE_MARKERS: Tuple[str, ...] = (
    "cookie",
    "sessdata",
    "a_bogus",
    "abogus",
    "x-bogus",
    "authorization",
    "bearer ",
    "token=",
    "access_token",
    "set-cookie",
)


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class IncompatibleSchemaError(Exception):
    """schema major 版本与本引擎不兼容。"""


class ContractViolation(Exception):
    """EvidenceBundle 违反状态不变量或安全边界。"""


# ---------------------------------------------------------------------------
# 值对象
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceIdentity:
    """稳定的证据身份：不随采集次数或降级状态漂移。"""

    platform: str
    canonical_id: str
    canonical_url: str


@dataclass(frozen=True)
class TranscriptSegmentEvidence:
    """One public transcript cue with optional end time."""

    start: float
    end: Optional[float]
    text: str


@dataclass(frozen=True)
class TranscriptEvidence:
    """转录证据。`source` 记录来源（official_subtitle / asr / ...），含内容 hash。"""

    text: str
    language: str
    source: str
    content_hash: str
    segments: Tuple[TranscriptSegmentEvidence, ...] = ()


@dataclass(frozen=True)
class AudienceSignal:
    """观众态度信号（评论 / 弹幕聚合后的最小视图，不含平台私有原始字段）。"""

    kind: str
    label: str
    weight: float = 1.0


@dataclass(frozen=True)
class Provenance:
    """采集溯源：adapter、版本、时间、来源引用与内容 hash。"""

    adapter: str
    adapter_version: str
    collected_at: str
    source_refs: Tuple[str, ...] = ()
    hashes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceError:
    """一次预期失败的显式记录（D19：状态优先于异常）。"""

    code: str
    stage: str
    retryable: bool
    safe_message: str


@dataclass(frozen=True)
class FactCheck:
    """可选事实核查结果，最小占位；A1 不强制填充。"""

    claim: str
    verdict: str
    note: str = ""


@dataclass(frozen=True)
class EvidenceBundle:
    """
    V4 唯一外部证据对象。字段顺序即契约核心：
    schema_version / status / identity / metadata / transcript /
    audience_signals / provenance / errors，其余为可选扩展。
    """

    schema_version: str
    status: str
    identity: SourceIdentity
    metadata: Mapping[str, object]
    transcript: Optional[TranscriptEvidence]
    audience_signals: Tuple[AudienceSignal, ...]
    provenance: Provenance
    errors: Tuple[EvidenceError, ...] = ()
    cross_platform: Tuple[SourceIdentity, ...] = ()
    fact_checks: Tuple[FactCheck, ...] = ()


# ---------------------------------------------------------------------------
# 版本兼容
# ---------------------------------------------------------------------------

def _parse_major(version: str) -> int:
    try:
        return int(str(version).split(".", 1)[0])
    except (ValueError, AttributeError, IndexError) as exc:  # pragma: no cover
        raise IncompatibleSchemaError(f"无法解析 schema 版本: {version!r}") from exc


def schema_compatible(version: str) -> bool:
    """major 相同即兼容（minor 只新增可选字段，向后兼容）。"""
    return _parse_major(version) == _parse_major(EVIDENCE_SCHEMA_VERSION)


def check_schema_compatibility(version: str) -> None:
    """major 不兼容立即拒绝。"""
    if not schema_compatible(version):
        raise IncompatibleSchemaError(
            f"schema major 不兼容: 收到 {version!r}，引擎为 {EVIDENCE_SCHEMA_VERSION!r}"
        )


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def _has_transcript(bundle: EvidenceBundle) -> bool:
    return bundle.transcript is not None and bool(bundle.transcript.text.strip())


def _assert_no_private_payload(value: object, path: str) -> None:
    """递归拒绝私有响应容器、凭据键和明显的凭据赋值。"""
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _PRIVATE_PAYLOAD_KEYS:
                raise ContractViolation(f"{path} 含私有或敏感字段 {key!r}")
            _assert_no_private_payload(nested, f"{path}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, nested in enumerate(value):
            _assert_no_private_payload(nested, f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in _CREDENTIAL_ASSIGNMENTS):
            raise ContractViolation(f"{path} 含敏感凭据痕迹")


def _assert_transcript_segments(bundle: EvidenceBundle) -> None:
    transcript = bundle.transcript
    if transcript is None:
        return
    for segment in transcript.segments:
        if not isinstance(segment, TranscriptSegmentEvidence):
            raise ContractViolation("transcript segment 必须为 TranscriptSegmentEvidence")
        if not isinstance(segment.start, (int, float)) or segment.start < 0:
            raise ContractViolation("transcript segment start 必须为非负数")
        if segment.end is not None and (
            not isinstance(segment.end, (int, float)) or segment.end < segment.start
        ):
            raise ContractViolation("transcript segment end 必须为空或不早于 start")
        if not segment.text.strip():
            raise ContractViolation("transcript segment text 不得为空")


def _assert_safe_errors(bundle: EvidenceBundle) -> None:
    for err in bundle.errors:
        if err.code not in ERROR_CODES:
            raise ContractViolation(f"未知 error code: {err.code!r}")
        if err.stage not in ERROR_STAGES:
            raise ContractViolation(f"未知 error stage: {err.stage!r}")
        lowered = err.safe_message.lower()
        for marker in _SENSITIVE_MARKERS:
            if marker in lowered:
                raise ContractViolation(
                    f"safe_message 含敏感材料痕迹 {marker!r}，禁止泄漏认证/私有数据"
                )


def validate_bundle(bundle: EvidenceBundle) -> None:
    """
    校验状态不变量与安全边界，违约抛 ContractViolation；major 不兼容抛
    IncompatibleSchemaError。不做任何 I/O。
    """
    check_schema_compatibility(bundle.schema_version)

    if bundle.status not in EVIDENCE_STATUSES:
        raise ContractViolation(f"未知 status: {bundle.status!r}")

    if not isinstance(bundle.identity, SourceIdentity):
        raise ContractViolation("identity 必须为 SourceIdentity")
    if bundle.identity.platform not in SUPPORTED_PLATFORMS:
        raise ContractViolation(f"identity.platform 不受支持: {bundle.identity.platform!r}")
    if not (bundle.identity.canonical_id and bundle.identity.canonical_url):
        raise ContractViolation("identity 必须有稳定的 canonical_id / canonical_url")

    _assert_safe_errors(bundle)
    _assert_transcript_segments(bundle)
    _assert_no_private_payload(bundle.metadata, "metadata")
    _assert_no_private_payload(bundle.identity.canonical_url, "identity.canonical_url")
    _assert_no_private_payload(bundle.provenance.source_refs, "provenance.source_refs")
    _assert_no_private_payload(bundle.provenance.hashes, "provenance.hashes")

    status = bundle.status
    if status == "ready":
        if not _has_transcript(bundle):
            raise ContractViolation("ready 必须携带非空 transcript")
        if not bundle.provenance.hashes.get("transcript") and not bundle.transcript.content_hash:
            raise ContractViolation("ready 必须携带 transcript hash")
    elif status == "metadata_only":
        if not bundle.metadata:
            raise ContractViolation("metadata_only 必须携带 metadata")
        if not bundle.errors:
            raise ContractViolation("metadata_only 必须用 error 解释缺失的媒体/转录")
        if not any(err.code in _METADATA_ONLY_GAP_CODES for err in bundle.errors):
            raise ContractViolation("metadata_only 必须明确记录媒体/转录缺失原因")
        if bundle.transcript is not None:
            raise ContractViolation("metadata_only 不得携带 transcript")
    elif status == "auth_required":
        if bundle.transcript is not None:
            raise ContractViolation("auth_required 不得携带 transcript")
        if not bundle.errors or not any(err.code == "auth_required" for err in bundle.errors):
            raise ContractViolation("auth_required 必须用 auth_required error 记录鉴权需求")
    elif status == "unavailable":
        if bundle.metadata:
            raise ContractViolation("unavailable 不得伪造 metadata")
        if bundle.transcript is not None:
            raise ContractViolation("unavailable 不得伪造 transcript")
        if bundle.audience_signals:
            raise ContractViolation("unavailable 不得伪造观众态度")
        if not bundle.errors:
            raise ContractViolation("unavailable 必须用 error 说明不可用原因")


def is_publishable(bundle: EvidenceBundle) -> bool:
    """
    Writer / publish gate 的唯一判据：只有 ready 且通过全部契约校验才可发布。
    任何降级状态（metadata_only / auth_required / unavailable）均返回 False。
    """
    if bundle.status != "ready":
        return False
    try:
        validate_bundle(bundle)
    except (ContractViolation, IncompatibleSchemaError):
        return False
    return True


__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "SUPPORTED_PLATFORMS",
    "EVIDENCE_STATUSES",
    "ERROR_CODES",
    "ERROR_STAGES",
    "IncompatibleSchemaError",
    "ContractViolation",
    "SourceIdentity",
    "TranscriptSegmentEvidence",
    "TranscriptEvidence",
    "AudienceSignal",
    "Provenance",
    "EvidenceError",
    "FactCheck",
    "EvidenceBundle",
    "schema_compatible",
    "check_schema_compatibility",
    "validate_bundle",
    "is_publishable",
]
