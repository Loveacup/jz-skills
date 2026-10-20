from video_analysis_engine import WRITER_PROMPTS, build_typed_writer_section_contexts


def _prompt(section):
    spec = WRITER_PROMPTS[section]
    return spec["system"] + "\n" + spec["user"]


def test_section3_prompt_requires_exactly_three_bounded_insights():
    prompt = _prompt("3")
    assert "恰好 3 个洞察" in prompt
    assert "每个洞察正文 350–700 个中文字符" in prompt
    assert "无弹幕时省略该字段" in prompt
    assert "3-5 个洞察" not in prompt


def test_section4_prompt_requires_exactly_three_bounded_modules():
    prompt = _prompt("4")
    assert "恰好 3 个模块" in prompt
    assert "每个模块正文 700–1800 个中文字符" in prompt
    assert "**显性叙事**" in prompt
    assert "**隐性机制**" in prompt
    assert "**元叙事**" in prompt
    assert "3-5 个模块" not in prompt


def test_section7_prompt_is_bounded_and_forbids_placeholders():
    prompt = _prompt("7")
    assert "恰好 3 个独特价值点" in prompt
    assert "恰好 2 个局限" in prompt
    assert "恰好 3 个可行动项" in prompt
    assert "全节不超过 3500 个中文字符" in prompt
    assert "禁止输出 placeholder、E_placeholder" in prompt
    assert "弹幕数据不足声明只写一次" in prompt


def test_zero_danmaku_writer_context_omits_repeated_feedback_fields():
    report = {
        "frontmatter": {"danmaku_count": 0},
        "report_plan": {
            "sections": [{
                "id": "3", "title": "核心洞察", "purpose": "提炼洞察",
                "quality_gate": "", "min_items": 3, "min_words_per_item": 200,
            }]
        },
        "evidence_map": {"by_section": {"3": []}},
    }
    contexts = build_typed_writer_section_contexts(report)
    assert len(contexts) == 1
    contract = contexts[0].claim_context or ""
    assert "无弹幕时省略" in contract
    assert "每个 `**弹幕反馈**：` 字段必须原样包含" not in contract
