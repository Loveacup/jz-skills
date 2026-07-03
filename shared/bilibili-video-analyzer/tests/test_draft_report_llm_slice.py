# -*- coding: utf-8 -*-
"""DraftReport LLM writer slice for §3/§4/§7."""

from video_analysis_engine import assemble_draft_report_slice


def _report_for_llm_slice():
    sections = [
        {"id": "3", "title": "核心洞察", "purpose": "提炼核心观点", "quality_gate": "G3", "min_items": 3, "min_words_per_item": 20},
        {"id": "4", "title": "内容深度拆解", "purpose": "拆解内容模块", "quality_gate": "G4", "min_items": 3, "min_words_per_item": 20},
        {"id": "7", "title": "批判与行动", "purpose": "输出价值局限与行动", "quality_gate": "G7", "min_items": 3, "min_words_per_item": 0},
    ]
    evidence = [
        {"text": "第一条证据说明视频提出了明确问题意识，适合作为核心观点支撑。", "timestamp": "0:10", "source_type": "transcript", "reason": "insight_candidate"},
        {"text": "第二条证据解释了机制和结构关系，适合支撑深度拆解。", "timestamp": "1:20", "source_type": "transcript", "reason": "deep_dive_candidate"},
        {"text": "第三条证据呈现了价值、局限和可行动建议的素材。", "timestamp": "2:30", "source_type": "transcript", "reason": "critical_candidate"},
    ]
    return {
        "frontmatter": {"title": "LLM slice test", "video_id": "BVllmSlice"},
        "report_plan": {"can_generate_formal_report": True, "sections": sections},
        "evidence_map": {
            "by_section": {
                "3": evidence,
                "4": evidence,
                "7": evidence,
            },
            "warnings": [],
        },
        "evidence_gate": {"sources": {"transcript": {"available": True, "source": "h200-asr", "language": "zh", "segments": 3, "chars": 120}}},
    }


class _Provider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, system, user):
        self.calls.append({"system": system, "user": user})
        if not self.responses:
            return "bad"
        return self.responses.pop(0)


def _valid_section3():
    return """### 💡 洞察 1：问题意识 [E1]
第一条洞察正文包含足够中文字符用于验证，并且严格绑定原始证据，不添加外部猜测。
### 💡 洞察 2：机制关系 [E2]
第二条洞察正文包含足够中文字符用于验证，并且说明机制关系来自片段证据。
### 💡 洞察 3：行动启发 [E3]
第三条洞察正文包含足够中文字符用于验证，并且给出有限范围内的行动启发。
"""


def _valid_section4():
    return """### 模块 1：问题提出 [E1]
第一个模块正文包含足够中文字符用于验证，并且只说明原始证据中出现的问题提出路径。
### 模块 2：机制展开 [E2]
第二个模块正文包含足够中文字符用于验证，并且只说明证据中呈现的结构关系。
### 模块 3：结论收束 [E3]
第三个模块正文包含足够中文字符用于验证，并且只说明证据中能支持的收束判断。
"""


def _valid_section7():
    return """### 独特价值 [E1]
- 这条价值判断来自证据本身，说明视频能把问题意识压缩成可讨论框架 [E1]
- 这条价值判断来自证据本身，说明机制关系具有复用价值 [E2]
- 这条价值判断来自证据本身，说明行动建议有明确边界 [E3]
### 局限与偏见 [E2]
- 现有证据只覆盖短片段，不能外推到完整行业结论 [E2]
- 现有证据没有提供反方样本，因此批判必须保持有限 [E3]
### 可行动项 [E3]
- 把问题意识整理成检查清单，再决定是否进入完整写作 [E1]
- 用更多证据补足机制关系，再进入发布稿生成 [E2]
- 保留局限说明，避免把片段观察写成确定结论 [E3]
"""


def test_assemble_draft_report_slice_writes_valid_llm_sections_with_provider():
    provider = _Provider([_valid_section3(), _valid_section4(), _valid_section7()])

    draft = assemble_draft_report_slice(_report_for_llm_slice(), section_ids=("3", "4", "7"), provider=provider)

    assert draft.publishable is False
    assert set(draft.draft_sections) == {"3", "4", "7"}
    assert "### 💡 洞察 1" in draft.draft_sections["3"]
    assert "### 模块 1" in draft.draft_sections["4"]
    assert "### 独特价值" in draft.draft_sections["7"]
    assert len(provider.calls) == 3


def test_assemble_draft_report_slice_bad_provider_degrades_to_placeholder_and_warning():
    provider = _Provider(["不合格输出", "不合格输出", "不合格输出"])

    draft = assemble_draft_report_slice(_report_for_llm_slice(), section_ids=("3", "4", "7"), provider=provider)

    assert set(draft.draft_sections) == {"3", "4", "7"}
    assert all("_骨架占位" in draft.draft_sections[sid] for sid in ("3", "4", "7"))
    assert any("§3 LLM writer validation failed" in warning for warning in draft.warnings)
    assert any("§4 LLM writer validation failed" in warning for warning in draft.warnings)
    assert any("§7 LLM writer validation failed" in warning for warning in draft.warnings)


def test_assemble_draft_report_slice_without_provider_does_not_write_llm_sections():
    draft = assemble_draft_report_slice(_report_for_llm_slice(), section_ids=("3", "4", "7"), provider=None)

    assert draft.draft_sections == {}
