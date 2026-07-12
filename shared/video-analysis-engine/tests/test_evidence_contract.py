#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_evidence_contract.py — V4-A1 契约 + 路由的 RED-first 合同测试。

覆盖 STDD D1/D8（外部接口统一为 EvidenceBundle）、D18（Adapter 只暴露
can_handle/collect）、D19（四种状态、只有 ready 可发布、预期失败返回状态而非
异常猜测）。此文件先于实现存在，用来钉住契约不变量。
"""

import inspect
from dataclasses import replace

import pytest

import evidence_contract as ec
import platform_router as pr


# ---------------------------------------------------------------------------
# 状态与版本
# ---------------------------------------------------------------------------

def test_schema_version_is_semver_4_x():
    assert ec.EVIDENCE_SCHEMA_VERSION == "4.1.0"


def test_status_set_is_exactly_four():
    assert set(ec.EVIDENCE_STATUSES) == {
        "ready",
        "metadata_only",
        "auth_required",
        "unavailable",
    }


def test_incompatible_major_schema_is_rejected():
    assert ec.schema_compatible("4.0.0") is True
    assert ec.schema_compatible("4.7.3") is True  # minor 只新增可选字段
    assert ec.schema_compatible("5.0.0") is False
    assert ec.schema_compatible("3.9.9") is False
    with pytest.raises(ec.IncompatibleSchemaError):
        ec.check_schema_compatibility("5.0.0")
    with pytest.raises(ec.IncompatibleSchemaError):
        ec.check_schema_compatibility("3.0.0")


# ---------------------------------------------------------------------------
# Bundle builders (测试内小工具)
# ---------------------------------------------------------------------------

def _identity(platform="bilibili"):
    return ec.SourceIdentity(
        platform=platform,
        canonical_id="BV14fTc6TEi5",
        canonical_url="https://www.bilibili.com/video/BV14fTc6TEi5",
    )


def _provenance():
    return ec.Provenance(
        adapter="bilibili",
        adapter_version="4.0.0",
        collected_at="2026-07-11T00:00:00Z",
        source_refs=("cache://BV14fTc6TEi5",),
        hashes={"transcript": "sha256:deadbeef"},
    )


def _transcript():
    return ec.TranscriptEvidence(
        text="第一段确实提出了新论点。",
        language="zh",
        source="official_subtitle",
        content_hash="sha256:deadbeef",
    )


def _ready_bundle():
    return ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="ready",
        identity=_identity(),
        metadata={"title": "示例", "duration_s": 62},
        transcript=_transcript(),
        audience_signals=(),
        provenance=_provenance(),
    )


# ---------------------------------------------------------------------------
# 发布性：只有 ready 可发布
# ---------------------------------------------------------------------------

def test_only_ready_is_publishable():
    assert ec.is_publishable(_ready_bundle()) is True

    for status in ("metadata_only", "auth_required", "unavailable"):
        bundle = ec.EvidenceBundle(
            schema_version=ec.EVIDENCE_SCHEMA_VERSION,
            status=status,
            identity=_identity(),
            metadata={"title": "示例"},
            transcript=None,
            audience_signals=(),
            provenance=_provenance(),
            errors=(
                ec.EvidenceError(
                    code="transcript_unavailable",
                    stage="asr",
                    retryable=False,
                    safe_message="转录不可用",
                ),
            ),
        )
        assert ec.is_publishable(bundle) is False


# ---------------------------------------------------------------------------
# 状态不变量
# ---------------------------------------------------------------------------

def test_transcript_segments_reject_invalid_time_or_empty_text():
    base = _ready_bundle()
    invalid = replace(
        base,
        transcript=replace(
            base.transcript,
            segments=(ec.TranscriptSegmentEvidence(-1.0, 0.0, ""),),
        ),
    )
    with pytest.raises(ec.ContractViolation, match="transcript segment"):
        ec.validate_bundle(invalid)


def test_ready_requires_nonempty_transcript():
    bad = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="ready",
        identity=_identity(),
        metadata={"title": "示例"},
        transcript=None,
        audience_signals=(),
        provenance=_provenance(),
    )
    with pytest.raises(ec.ContractViolation):
        ec.validate_bundle(bad)
    assert ec.is_publishable(bad) is False


def test_metadata_only_requires_metadata_and_explaining_error():
    # 缺解释性错误 -> 违约
    no_error = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="metadata_only",
        identity=_identity(),
        metadata={"title": "示例"},
        transcript=None,
        audience_signals=(),
        provenance=_provenance(),
        errors=(),
    )
    with pytest.raises(ec.ContractViolation):
        ec.validate_bundle(no_error)

    ok = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="metadata_only",
        identity=_identity(),
        metadata={"title": "示例"},
        transcript=None,
        audience_signals=(),
        provenance=_provenance(),
        errors=(
            ec.EvidenceError(
                code="transcript_unavailable",
                stage="asr",
                retryable=True,
                safe_message="字幕缺失，媒体未取得",
            ),
        ),
    )
    ec.validate_bundle(ok)  # 不抛


def test_auth_required_carries_no_transcript_and_not_publishable():
    bundle = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="auth_required",
        identity=_identity(),
        metadata={},
        transcript=_transcript(),  # 违约：不该带 transcript
        audience_signals=(),
        provenance=_provenance(),
        errors=(
            ec.EvidenceError(
                code="auth_required",
                stage="metadata",
                retryable=True,
                safe_message="需要登录",
            ),
        ),
    )
    with pytest.raises(ec.ContractViolation):
        ec.validate_bundle(bundle)


def test_unavailable_forbids_fabricated_transcript():
    bundle = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="unavailable",
        identity=_identity(),
        metadata={},
        transcript=_transcript(),  # 违约：unavailable 不得伪造证据
        audience_signals=(),
        provenance=_provenance(),
        errors=(
            ec.EvidenceError(
                code="media_unavailable",
                stage="media",
                retryable=False,
                safe_message="视频已被删除",
            ),
        ),
    )
    with pytest.raises(ec.ContractViolation):
        ec.validate_bundle(bundle)


def test_error_safe_message_rejects_sensitive_material():
    with pytest.raises(ec.ContractViolation):
        ec.validate_bundle(
            ec.EvidenceBundle(
                schema_version=ec.EVIDENCE_SCHEMA_VERSION,
                status="metadata_only",
                identity=_identity(),
                metadata={"title": "示例"},
                transcript=None,
                audience_signals=(),
                provenance=_provenance(),
                errors=(
                    ec.EvidenceError(
                        code="auth_required",
                        stage="metadata",
                        retryable=True,
                        safe_message="cookie=SESSDATA=xxxx; a_bogus=yyyy",
                    ),
                ),
            )
        )


def test_contract_rejects_unsupported_platform_identity():
    bad = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="ready",
        identity=ec.SourceIdentity("evil", "id", "https://example.com/video"),
        metadata={"title": "示例"},
        transcript=_transcript(),
        audience_signals=(),
        provenance=_provenance(),
    )
    with pytest.raises(ec.ContractViolation, match="platform"):
        ec.validate_bundle(bad)


def test_unavailable_forbids_fabricated_metadata():
    bad = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="unavailable",
        identity=_identity(),
        metadata={"title": "未经证实的标题"},
        transcript=None,
        audience_signals=(),
        provenance=_provenance(),
        errors=(ec.EvidenceError("media_unavailable", "media", False, "视频不可用"),),
    )
    with pytest.raises(ec.ContractViolation, match="metadata"):
        ec.validate_bundle(bad)


def test_metadata_only_requires_media_or_transcript_gap_error():
    bad = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="metadata_only",
        identity=_identity(),
        metadata={"title": "示例"},
        transcript=None,
        audience_signals=(),
        provenance=_provenance(),
        errors=(ec.EvidenceError("audience_unavailable", "audience", False, "评论不可用"),),
    )
    with pytest.raises(ec.ContractViolation, match="媒体/转录"):
        ec.validate_bundle(bad)


@pytest.mark.parametrize(
    "metadata, source_refs",
    [
        ({"raw_response": {"cookie": "secret"}}, ("https://example.com/video",)),
        ({"title": "示例", "authorization": "Bearer secret"}, ("https://example.com/video",)),
        ({"title": "示例"}, ("https://example.com/video?access_token=secret",)),
    ],
)
def test_private_payload_and_credentials_cannot_hide_in_bundle(metadata, source_refs):
    provenance = ec.Provenance(
        adapter="bilibili",
        adapter_version="4.0.0",
        collected_at="2026-07-11T00:00:00Z",
        source_refs=source_refs,
        hashes={"transcript": "sha256:deadbeef"},
    )
    bad = ec.EvidenceBundle(
        schema_version=ec.EVIDENCE_SCHEMA_VERSION,
        status="ready",
        identity=_identity(),
        metadata=metadata,
        transcript=_transcript(),
        audience_signals=(),
        provenance=provenance,
    )
    with pytest.raises(ec.ContractViolation, match="敏感|私有"):
        ec.validate_bundle(bad)


def test_collect_options_has_no_unbounded_private_extras_channel():
    assert "extras" not in pr.CollectOptions.__dataclass_fields__


def test_bundle_with_incompatible_major_is_rejected_by_validate():
    bundle = ec.EvidenceBundle(
        schema_version="5.0.0",
        status="ready",
        identity=_identity(),
        metadata={"title": "示例"},
        transcript=_transcript(),
        audience_signals=(),
        provenance=_provenance(),
    )
    with pytest.raises(ec.IncompatibleSchemaError):
        ec.validate_bundle(bundle)


# ---------------------------------------------------------------------------
# PlatformAdapter 接口收窄（D18）
# ---------------------------------------------------------------------------

def test_platform_adapter_public_interface_is_only_can_handle_collect():
    public = {
        name
        for name, _ in inspect.getmembers(pr.PlatformAdapter, callable)
        if not name.startswith("_")
    }
    assert public == {"can_handle", "collect"}


# ---------------------------------------------------------------------------
# Router：URL / 分享文本识别 + 零匹配 / 多匹配确定性失败
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, platform",
    [
        ("https://www.bilibili.com/video/BV14fTc6TEi5", "bilibili"),
        ("https://b23.tv/abcd12", "bilibili"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
        ("https://www.youtube.com/shorts/abc123DEF45", "youtube"),
        ("https://v.douyin.com/iRxY5abc/", "douyin"),
        (
            "7.99 复制打开抖音，看看【作者的作品】 https://v.douyin.com/iRxY5abc/",
            "douyin",
        ),
    ],
)
def test_router_recognizes_supported_platforms(raw, platform):
    assert pr.identify_platform(raw) == platform


def test_router_zero_match_is_deterministic_error():
    with pytest.raises(pr.NoPlatformMatched):
        pr.identify_platform("https://example.com/not-a-video")


def test_router_multi_match_is_deterministic_error():
    ambiguous = "https://youtu.be/dQw4w9WgXcQ 同时 https://v.douyin.com/iRxYab/"
    with pytest.raises(pr.MultiplePlatformsMatched):
        pr.identify_platform(ambiguous)


# --- adapter 级路由 ---

class _StubAdapter:
    def __init__(self, platform, handles):
        self.platform = platform
        self.adapter_version = "0.0.1"
        self._handles = handles
        self.collected = None

    def can_handle(self, source):
        return self._handles

    def collect(self, source, options):
        self.collected = (source, options)
        return "BUNDLE-" + self.platform


def test_router_single_match_dispatches_collect():
    yes = _StubAdapter("bilibili", True)
    no = _StubAdapter("youtube", False)
    router = pr.PlatformRouter([yes, no])
    src = pr.SourceInput(raw="https://www.bilibili.com/video/BV14fTc6TEi5")
    assert router.route(src) is yes
    out = router.collect(src, pr.CollectOptions())
    assert out == "BUNDLE-bilibili"
    assert yes.collected is not None


def test_router_no_adapter_match_raises():
    router = pr.PlatformRouter([_StubAdapter("bilibili", False)])
    with pytest.raises(pr.NoAdapterMatched):
        router.route(pr.SourceInput(raw="whatever"))


def test_router_multiple_adapters_match_raises():
    router = pr.PlatformRouter(
        [_StubAdapter("bilibili", True), _StubAdapter("douyin", True)]
    )
    with pytest.raises(pr.MultipleAdaptersMatched):
        router.route(pr.SourceInput(raw="whatever"))
