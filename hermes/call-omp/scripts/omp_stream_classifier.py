#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────
# omp_stream_classifier.py —— call-omp P2B S1A · 纯 JSONL 判决流分类器
#
# 【S1A 契约：无运行时接线】本模块是可 import 的纯函数分类器，只对
# 「一条 JSONL 记录」做判决，绝不读环境变量 / 文件系统 / 路径 / 状态 /
# 进程信息，也绝不写文件。不 import os/pathlib/subprocess，不用 open()。
# 仅依赖标准库 json / hashlib / dataclasses / typing。
#
# 判决三态：
#   preserve —— 命中严格白名单（verdict 承载 envelope），重建最小规范 JSON；
#   deny     —— 已知的非 verdict 协议 envelope（session/心跳/思考流/工具流…）；
#   unknown  —— 其余一切（含畸形输入）；按结构是否含终态键判定 terminal_capable。
#
# 【隐私】diagnostic_record 只含固定 9 键，绝不携带原文 / 文本增量 / prompt /
#         工具入参出参 / provider / model / usage / 任意源字段。structure_code 亦
#         只从模块级固定字面量白名单取值，绝不从源字段（role/type/subtype）拷贝。
# ─────────────────────────────────────────────────────────────────
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

# 单条记录的硬上限（含末尾换行），1 MiB 包含边界。
MAX_INPUT_BYTES = 1024 * 1024

# 结构性「终态可能」键集合：JSON 结构中任一对象出现其一即视为 terminal_capable。
# 只看对象的键名，绝不检查标量字符串内容。
TERMINAL_KEYS = frozenset(
    {
        "message",
        "content",
        "text",
        "delta",
        "stopReason",
        "severity",
        "evidence",
        "required_actions",
    }
)

# 已知需 deny 的非 verdict 顶层 envelope 类型。
DENY_TYPES = frozenset(
    {
        "session",
        "ready",
        "agent_start",
        "turn_start",
        "message_start",
        "tool_execution_start",
        "tool_execution_end",
        "usage",
        "heartbeat",
    }
)

# 命中严格白名单的顶层 verdict 类型。
PRESERVE_TYPES = frozenset({"message_end", "message_update", "text_delta", "turn_end"})

# 【隐私】允许进入 diagnostic.type 的「安全协议枚举」——只有被本模块识别、
# 参与判决路由的固定类型才可回填；其余（含攻击者自造的 type 串）一律记 null，
# 绝不把源文本带进 diagnostic 或 reason。
SAFE_TYPES = PRESERVE_TYPES | DENY_TYPES

# 允许进入 diagnostic.subtype 的固定安全码。text_delta 为已声明枚举；
# thinking_*/toolcall_* 归一为固定分类码 reasoning_stream（不回填原始子类型串）。
SUBTYPE_TEXT_DELTA = "text_delta"
SUBTYPE_REASONING = "reasoning_stream"

# 【隐私·S3A/S3C】structure_code 的模块级固定字面量白名单——描述已识别 / 未识别
# envelope 的「安全结构形状」，让诊断聚合能区分各分支（含未知 kind 与未分类 envelope
# 里潜在的 verdict 承载形状），而无需保留任何原文。任何不在此集合内的值（含攻击者自造
# 串）都被 _diag 归零成 null，绝不进入 diagnostic。此字段永不从源字段（role/type/
# subtype/body）拷贝——只从「键的存在性 + 标量 JSON 类型」这类固定结构范畴映射而来。
#
# 【S3C】在既有码之上「附加式」细分两处曾经过粗的桶，绝不改动任何判决 / reason / 既有
# 惰性码：
#   · message_update.ame_unknown_kind.*  —— ame 是对象但 type 不属已识别 kind 时，按
#       string delta / string text / stopReason 存在性细分「潜在 verdict 承载形状」；
#       无任何承载信号仍归基码 message_update.ame_unknown_kind（向后兼容）。
#   · unclassified.*                     —— 顶层 type 未识别（unclassified）时，按顶层挂
#       载的 assistantMessageEvent / message / string delta·text / stopReason 细分；
#       无任何承载信号仍记 null（保持既有语义）。
STRUCTURE_CODES = frozenset(
    {
        "message_end.assistant",
        "message_end.non_assistant",
        "message_end.message_missing",
        "message_end.message_non_object",
        "message_update.ame_missing",
        "message_update.ame_non_object",
        "message_update.text_delta",
        "message_update.reasoning_stream",
        "message_update.ame_unknown_kind",
        # S3C：message_update 未知 kind 下的潜在 verdict 承载形状细分。
        "message_update.ame_unknown_kind.delta_string",
        "message_update.ame_unknown_kind.text_string",
        "message_update.ame_unknown_kind.stop_reason",
        # S3C：未分类顶层 envelope 下的潜在 verdict 承载形状细分。
        "unclassified.assistant_message_event",
        "unclassified.message",
        "unclassified.delta_string",
        "unclassified.text_string",
        "unclassified.stop_reason",
    }
)

# diagnostic_record 的唯一合法键集合（对外契约，测试逐字比对）。
DIAGNOSTIC_KEYS = frozenset(
    {
        "seq",
        "type",
        "subtype",
        "input_bytes",
        "input_sha256",
        "decision",
        "reason",
        "terminal_capable",
        "structure_code",
    }
)


@dataclass(frozen=True)
class Classification:
    decision: str  # "preserve" | "deny" | "unknown"
    verdict_line: Optional[bytes]  # 规范 UTF-8 JSONL（含末尾 \n）或 None
    diagnostic_record: Dict[str, Any]
    terminal_capable: bool


def _canonical(obj: Any) -> bytes:
    """确定性规范 JSONL：键排序 + 紧凑分隔符 + ASCII-safe + 末尾换行。

    ensure_ascii=True 让非 BMP / 孤立代理项等一律转义为 \\uXXXX，故 .encode('utf-8')
    对任何已解析对象都不会抛 UnicodeEncodeError（防御性；正常路径下畸形 Unicode 早已
    在分类器里短路成 unknown，不会走到这里）。ASCII 输出仍是合法 UTF-8 且确定性。
    """
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text.encode("utf-8") + b"\n"


def _has_surrogate(obj: Any) -> bool:
    """迭代扫描所有字符串（键与值）中是否含孤立代理码点 U+D800..U+DFFF。

    json.loads 会把 "\\ud800" 解析成含孤立代理项的 Python str，这种标量无法编码为
    合法 UTF-8。检出即判为畸形 Unicode，保守短路成 unknown。
    """
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            for ch in cur:
                if 0xD800 <= ord(ch) <= 0xDFFF:
                    return True
        elif isinstance(cur, dict):
            for key, val in cur.items():
                stack.append(key)
                stack.append(val)
        elif isinstance(cur, list):
            stack.extend(cur)
    return False


def _terminal_capable(obj: Any) -> bool:
    """迭代扫描结构；任一对象的键命中 TERMINAL_KEYS 即 True。不看标量内容。"""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for key, val in cur.items():
                if key in TERMINAL_KEYS:
                    return True
                stack.append(val)
        elif isinstance(cur, list):
            stack.extend(cur)
    return False


def _content_shape_suffix(d: Dict[str, Any]) -> Optional[str]:
    """【隐私·S3C】从对象的键推出「潜在 verdict 承载内容形状」的固定后缀码。

    只看键的存在性与标量 JSON 类型（string / 非 string），绝不读取任何键值内容，
    故返回值恒为固定字面量后缀或 None，永远不会携带原文。

    优先级（承载「答案文本」的信号最强）：
      string delta  > string text  > stopReason 键存在。
    delta / text 必须是字符串才算「潜在 verdict」（verdict 需承载文本内容）；非字符串
    的 delta / text 不构成潜在 verdict，与「无任何承载键」一并归 None（惰性 / inert）。
    """
    if isinstance(d.get("delta"), str):
        return "delta_string"
    if isinstance(d.get("text"), str):
        return "text_string"
    if "stopReason" in d:
        return "stop_reason"
    return None


def _diag(
    seq: int,
    typ: Optional[str],
    subtype: Optional[str],
    input_bytes: int,
    input_sha256: str,
    decision: str,
    reason: str,
    terminal_capable: bool,
    structure_code: Optional[str] = None,
) -> Dict[str, Any]:
    # 【隐私·S3A】防御性归一：structure_code 只允许模块级白名单字面量；其余（含
    # None 与任何意外串）一律记 null，杜绝源字段经此字段泄漏。
    safe_structure = structure_code if structure_code in STRUCTURE_CODES else None
    return {
        "seq": seq,
        "type": typ,
        "subtype": subtype,
        "input_bytes": input_bytes,
        "input_sha256": input_sha256,
        "decision": decision,
        "reason": reason,
        "terminal_capable": terminal_capable,
        "structure_code": safe_structure,
    }


def _unknown(
    seq: int,
    typ: Optional[str],
    subtype: Optional[str],
    input_bytes: int,
    input_sha256: str,
    reason: str,
    terminal_capable: bool,
    structure_code: Optional[str] = None,
) -> Classification:
    return Classification(
        decision="unknown",
        verdict_line=None,
        diagnostic_record=_diag(
            seq,
            typ,
            subtype,
            input_bytes,
            input_sha256,
            "unknown",
            reason,
            terminal_capable,
            structure_code,
        ),
        terminal_capable=terminal_capable,
    )


def classify_jsonl_line(line_bytes: bytes, sequence: int) -> Classification:
    """对单条 newline-terminated JSONL 记录做判决。永不因畸形输入抛异常。"""
    input_bytes = len(line_bytes)
    input_sha256 = hashlib.sha256(line_bytes).hexdigest()

    # ── 结构性前置校验：任一不满足即 unknown、不产出 verdict、不 terminal_capable ──
    if input_bytes > MAX_INPUT_BYTES:
        return _unknown(sequence, None, None, input_bytes, input_sha256, "oversize", False)
    if not line_bytes.endswith(b"\n"):
        return _unknown(
            sequence, None, None, input_bytes, input_sha256, "no_trailing_newline", False
        )

    payload = line_bytes[:-1]
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return _unknown(sequence, None, None, input_bytes, input_sha256, "invalid_utf8", False)

    try:
        obj = json.loads(text)
    except (ValueError, RecursionError):
        return _unknown(sequence, None, None, input_bytes, input_sha256, "json_error", False)

    if not isinstance(obj, dict):
        return _unknown(sequence, None, None, input_bytes, input_sha256, "non_object", False)

    # 结构一旦解析成对象，terminal_capable 一律按结构扫描确定。
    terminal = _terminal_capable(obj)

    # 【隐私·M2】diagnostic.type 只回填安全协议枚举；攻击者自造的 type 串（不在
    # SAFE_TYPES 内）一律记 null，绝不进入 diagnostic 或 reason。注意：路由仍用 typ，
    # 而不被识别的类型本就应落入 unknown，故置 null 不影响判决正确性。
    raw_type = obj.get("type")
    typ = raw_type if (isinstance(raw_type, str) and raw_type in SAFE_TYPES) else None

    # 【隐私·M2】diagnostic.subtype 只回填固定安全码，绝不回填原始 assistantMessageEvent.type
    # 串（可能被攻击者注入 canary）。未识别子类型 → null。
    subtype: Optional[str] = None
    if typ == "message_update":
        ame = obj.get("assistantMessageEvent")
        if isinstance(ame, dict):
            ame_type = ame.get("type")
            if ame_type == "text_delta":
                subtype = SUBTYPE_TEXT_DELTA
            elif isinstance(ame_type, str) and (
                ame_type.startswith("thinking") or ame_type.startswith("toolcall")
            ):
                subtype = SUBTYPE_REASONING

    # 【M1】任何孤立代理码点（U+D800..U+DFFF）都无法编码为合法 UTF-8：在进入
    # preserve/deny 分类之前保守短路成 unknown，绝不产出 verdict。terminal_capable
    # 仍按已存在的结构键判定。
    if _has_surrogate(obj):
        return _unknown(
            sequence, typ, subtype, input_bytes, input_sha256, "invalid_unicode_scalar", terminal
        )

    def preserve(
        out_obj: Any, reason: str, structure_code: Optional[str] = None
    ) -> Classification:
        return Classification(
            decision="preserve",
            verdict_line=_canonical(out_obj),
            diagnostic_record=_diag(
                sequence,
                typ,
                subtype,
                input_bytes,
                input_sha256,
                "preserve",
                reason,
                terminal,
                structure_code,
            ),
            terminal_capable=terminal,
        )

    def deny(reason: str, structure_code: Optional[str] = None) -> Classification:
        return Classification(
            decision="deny",
            verdict_line=None,
            diagnostic_record=_diag(
                sequence,
                typ,
                subtype,
                input_bytes,
                input_sha256,
                "deny",
                reason,
                terminal,
                structure_code,
            ),
            terminal_capable=terminal,
        )

    def unknown(reason: str, structure_code: Optional[str] = None) -> Classification:
        return _unknown(
            sequence, typ, subtype, input_bytes, input_sha256, reason, terminal, structure_code
        )

    # ── 严格白名单 preserve ──
    if typ == "message_end":
        message = obj.get("message")
        if isinstance(message, dict):
            if message.get("role") == "assistant":
                content_in = message.get("content")
                content_out = []
                if isinstance(content_in, list):
                    for block in content_in:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "text"
                            and isinstance(block.get("text"), str)
                        ):
                            content_out.append({"type": "text", "text": block["text"]})
                return preserve(
                    {
                        "type": "message_end",
                        "message": {"role": "assistant", "content": content_out},
                    },
                    "message_end.assistant",
                    "message_end.assistant",
                )
            # message 是对象但 role 非 assistant（含 role 缺失/非串）→ 结构性 deny。
            # 【S3B】message_end 的 message 已是对象，但 role 不严格等于 "assistant"，
            # 在 preserve 契约下不可能承载 assistant 审计 verdict，故属「已知非 verdict
            # envelope」而非未知形状：判 deny，不产出 verdict。deny 仍保留结构扫描得到的
            # terminal 布尔，但因判决为 deny，绝不参与 terminal-unknown 计数。
            return deny("message_end.non_assistant", "message_end.non_assistant")
        # message 缺失或为 null → 结构码区分，但 reason 沿用既有聚合键（附加式）。
        if message is None:
            return unknown("message_end.non_assistant", "message_end.message_missing")
        # message 存在但非对象（字符串/数字/数组…）。
        return unknown("message_end.non_assistant", "message_end.message_non_object")

    if typ == "message_update":
        ame = obj.get("assistantMessageEvent")
        if isinstance(ame, dict):
            ame_type = ame.get("type")
            if isinstance(ame_type, str) and (
                ame_type.startswith("thinking") or ame_type.startswith("toolcall")
            ):
                return deny("message_update.reasoning_stream", "message_update.reasoning_stream")
            if ame_type == "text_delta":
                val = ame.get("delta")
                if not isinstance(val, str):
                    val = ame.get("text")
                if isinstance(val, str):
                    return preserve(
                        {
                            "type": "message_update",
                            "assistantMessageEvent": {"type": "text_delta", "delta": val},
                        },
                        "message_update.text_delta",
                        "message_update.text_delta",
                    )
                # 结构上仍是 text_delta（只是无字符串增量）→ 结构码归 text_delta。
                return unknown(
                    "message_update.text_delta.no_string_delta", "message_update.text_delta"
                )
            # ame 是对象但 type 不属任一已识别 kind。【S3C】用固定结构后缀码进一步
            # 区分「潜在 verdict 承载形状」（ame 挂着 string delta / string text /
            # stopReason）；无任何承载信号仍归基码 message_update.ame_unknown_kind（惰性，
            # 向后兼容）。判决 / reason / terminal 全不变，仅细化 structure_code。
            base = "message_update.ame_unknown_kind"
            suffix = _content_shape_suffix(ame)
            return unknown(
                "message_update.unrecognized", base + "." + suffix if suffix else base
            )
        # ame 缺失或为 null。
        if ame is None:
            return unknown("message_update.unrecognized", "message_update.ame_missing")
        # ame 存在但非对象。
        return unknown("message_update.unrecognized", "message_update.ame_non_object")

    if typ == "text_delta":
        val = obj.get("text")
        if isinstance(val, str):
            return preserve({"type": "text_delta", "text": val}, "text_delta")
        return unknown("text_delta.no_string_text")

    if typ == "turn_end":
        message = obj.get("message")
        if isinstance(message, dict):
            stop = message.get("stopReason")
            if not isinstance(stop, str):
                stop = None
            return preserve(
                {"type": "turn_end", "message": {"stopReason": stop}}, "turn_end"
            )
        return unknown("turn_end.no_message_object")

    # ── 已知非 verdict envelope → deny ──
    if typ in DENY_TYPES:
        return deny("known_envelope")

    # ── 其余一切 → unknown ──
    # 【S3C】顶层 type 未识别时用固定结构码区分「潜在 verdict 承载形状」的 envelope，
    # 供诊断聚合发现协议漂移（新 verdict 格式潜藏在未知 type 之下）：顶层挂着
    # message_update-form 的 assistantMessageEvent、message_end·turn_end-form 的
    # message、或直接的 string delta·text / stopReason。无任何承载键的惰性 envelope 仍
    # 记 null（附加式，保持既有 unclassified 语义）。判决 / reason 全不变。
    if "assistantMessageEvent" in obj:
        return unknown("unclassified", "unclassified.assistant_message_event")
    if "message" in obj:
        return unknown("unclassified", "unclassified.message")
    suffix = _content_shape_suffix(obj)
    if suffix:
        return unknown("unclassified", "unclassified." + suffix)
    return unknown("unclassified")
