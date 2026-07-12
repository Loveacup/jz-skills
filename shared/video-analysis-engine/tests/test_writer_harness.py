#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_writer_harness.py — P2-D1 LLM Writer Harness 测试

5 个 RED 测试验证：
1. Provider 注入和调用机制
2. 验证器正面通过
3. 验证器 min_items 失败
4. 验证器 min_words 失败
5. can_generate=False 不调用 provider
"""

from video_analysis_engine import (
    WriterProvider,
    WriterEvidenceCandidate,
    WriterSectionContext,
    WriterResult,
    write_llm_section,
    validate_section,
    build_writer_section_context,
    build_typed_writer_section_contexts,
    make_cli_writer_provider,
    cli_writer_provider,
    write_highlights_section,
)


def make_mock_provider(response: str):
    """创建一个 mock provider，记录调用次数。"""
    calls = []

    def provider(system: str, user: str) -> str:
        calls.append({'system': system, 'user': user})
        return response

    provider.calls = calls
    return provider


def make_section_context(
    section_id: str = "3",
    heading: str = "核心观点",
    purpose: str = "提炼要点",
    quality_gate: str = "每条独立可验证",
    min_items: int = 3,
    min_words_per_item: int = 20,
    evidence_count: int = 3
) -> WriterSectionContext:
    """工厂函数：快速构造测试用 WriterSectionContext。"""
    evidence = [
        WriterEvidenceCandidate(
            index=i,
            text=f"这是第 {i} 条测试证据，包含足够的中文字符以满足词数要求。",
            timestamp=f"00:0{i}:00",
            source="transcript"
        )
        for i in range(1, evidence_count + 1)
    ]

    return WriterSectionContext(
        section_id=section_id,
        heading=heading,
        purpose=purpose,
        quality_gate=quality_gate,
        min_items=min_items,
        min_words_per_item=min_words_per_item,
        evidence=evidence
    )


def test_writer_provider_injection():
    """测试：mock provider 被正确调用，返回结构完整。"""
    mock_response = """
### 💡 洞察 1：第一条观点 [E1]
这是第一条观点正文，包含足够的中文字符以满足最低词数要求确保通过验证。
### 💡 洞察 2：第二条观点 [E2]
这是第二条观点正文，包含足够的中文字符以满足最低词数要求确保通过验证。
### 💡 洞察 3：第三条观点 [E3]
这是第三条观点正文，包含足够的中文字符以满足最低词数要求确保通过验证。
"""
    provider = make_mock_provider(mock_response)
    context = make_section_context()

    result = write_llm_section(context, provider, retries=0)

    assert len(provider.calls) == 1, f"provider 应被调用 1 次，实际 {len(provider.calls)} 次"
    assert result.section_id == "3"
    assert result.content.strip() == mock_response.strip()
    assert result.sources_used == [1, 2, 3]
    assert result.validation_passed is True


def test_validate_section_pass():
    """测试：达标 content → validation_passed=True。"""
    content = """
### 💡 洞察 1：观点一 [E1]
包含足够的中文字符以满足最低词数要求确保通过验证。
### 💡 洞察 2：观点二 [E2]
包含足够的中文字符以满足最低词数要求确保通过验证。
### 💡 洞察 3：观点三 [E3]
包含足够的中文字符以满足最低词数要求确保通过验证。
"""
    result = WriterResult(section_id="3", content=content)
    context = make_section_context(min_items=3, min_words_per_item=20)

    validated = validate_section(result, context)

    assert validated.validation_passed is True, f"应通过验证，错误：{validated.validation_errors}"
    assert len(validated.validation_errors) == 0


def test_validate_section_fail_min_items():
    """测试：item 数不足 → validation error。"""
    content = """
- 观点一 [E1]：包含足够的中文字符以满足最低词数要求确保通过验证
- 观点二 [E2]：包含足够的中文字符以满足最低词数要求确保通过验证
"""
    # 使用 section_id="5" 来测试通用条目验证（§3/§4/§7 有专门格式验证）
    result = WriterResult(section_id="5", content=content)
    context = make_section_context(section_id="5", min_items=3, min_words_per_item=20)

    validated = validate_section(result, context)

    assert validated.validation_passed is False
    assert any("条目数不足" in e for e in validated.validation_errors)


def test_validate_section_fail_min_words():
    """测试：词数不足 → validation error。"""
    content = """
- 短 [E1]
- 也短 [E2]
- 还是短 [E3]
"""
    # 使用 section_id="5" 来测试通用条目验证（§3/§4/§7 有专门格式验证）
    result = WriterResult(section_id="5", content=content)
    context = make_section_context(section_id="5", min_items=3, min_words_per_item=20)

    validated = validate_section(result, context)

    assert validated.validation_passed is False
    assert any("词数不足" in e for e in validated.validation_errors)


def test_validate_section_rejects_heading_only_output():
    """测试：只有标题 + 引用的空结构不能通过验证。"""
    content = """
### ## 4. 内容深度拆解 (Deep Dive)
[E1]
"""
    result = WriterResult(section_id="4", content=content)
    context = make_section_context(section_id="4", min_items=3, min_words_per_item=20)

    validated = validate_section(result, context)

    assert validated.validation_passed is False
    # §4 有专门格式验证，会报"§4 格式不符合 verify_report"而不是通用的"条目数不足"
    assert any("§4 格式不符合 verify_report" in e or "有效正文不足" in e or "条目数不足" in e
               for e in validated.validation_errors)


def test_validate_section_enforces_verify_report_format_for_llm_sections():
    """测试：§3/§4/§7 必须生成 verify_report 可识别的结构。"""
    section3 = WriterResult(section_id="3", content="""
### 洞察一：没有 emoji [E1]
这是一段很长的内容，包含足够多的中文字符来满足最低词数要求，但标题缺少 verify_report 需要的灯泡 emoji。
### 洞察二：没有 emoji [E2]
这是一段很长的内容，包含足够多的中文字符来满足最低词数要求，但标题缺少 verify_report 需要的灯泡 emoji。
### 洞察三：没有 emoji [E3]
这是一段很长的内容，包含足够多的中文字符来满足最低词数要求，但标题缺少 verify_report 需要的灯泡 emoji。
""")
    validated3 = validate_section(section3, make_section_context(section_id="3", min_items=3, min_words_per_item=20))
    assert validated3.validation_passed is False
    assert any("§3" in e and "💡" in e for e in validated3.validation_errors)

    section4 = WriterResult(section_id="4", content="""
### 主题一：错误模块标题 [E1]
这里是一段足够长的中文内容，用来模拟 deep dive 模块，但是标题没有使用 verify_report 需要的 `### 模块 N：` 格式。
### 主题二：错误模块标题 [E2]
这里是一段足够长的中文内容，用来模拟 deep dive 模块，但是标题没有使用 verify_report 需要的 `### 模块 N：` 格式。
### 主题三：错误模块标题 [E3]
这里是一段足够长的中文内容，用来模拟 deep dive 模块，但是标题没有使用 verify_report 需要的 `### 模块 N：` 格式。
""")
    validated4 = validate_section(section4, make_section_context(section_id="4", min_items=3, min_words_per_item=20))
    assert validated4.validation_passed is False
    assert any("§4" in e and "模块 N" in e for e in validated4.validation_errors)

    section7 = WriterResult(section_id="7", content="""
### 价值 [E1]
- 这里是一条足够长的价值判断内容，但是标题关键词不符合旧 gate 的独特价值要求。
### 问题 [E2]
- 这里是一条足够长的问题判断内容，但是标题关键词不符合旧 gate 的局限或偏见要求。
### 建议 [E3]
- 这里是一条足够长的建议内容，但是标题关键词不符合旧 gate 的可行动要求。
""")
    validated7 = validate_section(section7, make_section_context(section_id="7", min_items=3, min_words_per_item=20))
    assert validated7.validation_passed is False
    assert any("§7" in e and "独特价值" in e for e in validated7.validation_errors)


def test_validate_section_enforces_deep_dive_module_min_words():
    """测试：§4 必须按模块正文总字数满足 G4，而不是只看段落条目。"""
    content = """
### 模块 1：太短 [E1]
这是一段只有几十个字的模块正文，虽然有引用，但不满足全量版 G4 的五百字要求。
### 模块 2：足够长 [E2]
这里用一段较长的内容来模拟模块正文，包含足够多的中文字符以避免普通条目验证失败，但是仍然应该由模块级字数检查来裁决是否达到 G4 门槛。
### 模块 3：也足够长 [E3]
这里用另一段较长的内容来模拟模块正文，包含足够多的中文字符以避免普通条目验证失败，但是仍然应该由模块级字数检查来裁决是否达到 G4 门槛。
"""
    result = WriterResult(section_id="4", content=content)
    context = make_section_context(section_id="4", min_items=3, min_words_per_item=500)

    validated = validate_section(result, context)

    assert validated.validation_passed is False
    assert any("模块" in e and "词数不足" in e for e in validated.validation_errors)


def test_no_transcript_block():
    """测试：can_generate=False 场景下，sections 为空列表。"""
    report = {
        'video': {
            'video_id': 'BV1234',
            'title': 'Test',
            'author': 'TestAuthor',
            'duration': 300
        },
        'report_plan': {
            'can_generate_formal_report': False,
            'blocking_reason': 'transcript:empty',
            'sections': []
        },
        'evidence_map': {
            'by_section': {},
            'warnings': []
        },
        'evidence_gate': {
            'sources': {
                'transcript': {
                    'available': False
                }
            }
        }
    }

    writer_ctx = build_writer_section_context(report)

    assert writer_ctx['can_generate_formal_report'] is False
    assert len(writer_ctx['sections']) == 0, "can_generate=False 时 sections 应为空列表"

    typed_sections = build_typed_writer_section_contexts(report)
    assert len(typed_sections) == 0, "typed 版本也应返回空列表"


def test_highlights_writer_splits_long_quote_candidates_to_meet_g5():
    """测试：H200 大段 transcript 也能切出至少 5 个高光 blockquote。"""
    long_text = "。".join([
        "第一段提出一个可引用的问题意识，内容足够长可以作为高光",
        "第二段解释一个关键机制，适合独立作为引用块",
        "第三段给出反直觉结论，能支撑报告的高光时刻",
        "第四段说明商业动机与产品命运之间的关系",
        "第五段总结用户行动启发，适合作为收束引用",
    ]) + "。"
    md = write_highlights_section({
        'quality_gate': 'G5',
        'evidence': [
            {
                'source_type': 'transcript',
                'reason': 'quote_candidate',
                'text': long_text,
                'timestamp': '0:00',
                'url': 'https://www.bilibili.com/video/BVx?t=0',
            }
        ]
    })

    quote_groups = [line for line in md.splitlines() if line.startswith('> ')]
    assert len(quote_groups) >= 5
    assert '第一段提出' in quote_groups[0]
    assert '第五段总结' in md


def test_highlights_writer_filters_title_and_short_fragments():
    """测试：§5 不应把标题行或过短问句当作高光。"""
    md = write_highlights_section({
        'quality_gate': 'G5',
        'evidence': [
            {
                'source_type': 'transcript',
                'reason': 'quote_candidate',
                'text': '## P1 那些因为解决了问题而被停产的产品',
                'timestamp': '0:00',
                'url': 'https://www.bilibili.com/video/BVx?t=0',
            },
            {
                'source_type': 'transcript',
                'reason': 'quote_candidate',
                'text': '那么后来发生了什么？为什么灯泡的质量不仅没有提升，反而开始倒退了？这是一个足够长的解释句，应该保留为高光引用。',
                'timestamp': '0:10',
                'url': 'https://www.bilibili.com/video/BVx?t=10',
            },
            {
                'source_type': 'transcript',
                'reason': 'quote_candidate',
                'text': '它最后去了哪里？这是一段足够长的解释句，应该保留为高光引用。',
                'timestamp': '0:20',
                'url': 'https://www.bilibili.com/video/BVx?t=20',
            }
        ]
    })

    assert '## P1' not in md
    assert '> "那么后来发生了什么？"' not in md
    assert '> "为什么灯泡的质量不仅没有提升，反而开始倒退了？"' not in md
    assert '> "它最后去了哪里？"' not in md
    assert '这是一个足够长的解释句' in md


class _Completed:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_make_cli_writer_provider_invokes_configured_cli(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output, text, timeout):
        calls.append({
            'cmd': cmd,
            'capture_output': capture_output,
            'text': text,
            'timeout': timeout,
        })
        return _Completed(returncode=0, stdout='- 合法输出 [E1]\n', stderr='')

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_run)

    provider = make_cli_writer_provider(command='fake-llm --mode markdown', timeout=7)
    output = provider('SYSTEM', 'USER')

    assert output == '- 合法输出 [E1]'
    assert calls[0]['cmd'][:3] == ['fake-llm', '--mode', 'markdown']
    assert 'SYSTEM' in calls[0]['cmd'][-1]
    assert 'USER' in calls[0]['cmd'][-1]
    assert calls[0]['capture_output'] is True
    assert calls[0]['text'] is True
    assert calls[0]['timeout'] == 7


def test_cli_writer_provider_uses_env_command(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output, text, timeout):
        calls.append(cmd)
        return _Completed(returncode=0, stdout='env output [E1]', stderr='')

    import subprocess
    monkeypatch.setenv('BILI_WRITER_CLI', 'env-llm --fast')
    monkeypatch.setenv('BILI_WRITER_CLI_TIMEOUT', '9')
    monkeypatch.setattr(subprocess, 'run', fake_run)

    assert cli_writer_provider('S', 'U') == 'env output [E1]'
    assert calls[0][:2] == ['env-llm', '--fast']


def test_cli_writer_provider_nonzero_raises(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return _Completed(returncode=2, stdout='', stderr='boom')

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_run)

    provider = make_cli_writer_provider(command='fake-llm')
    try:
        provider('S', 'U')
        assert False, 'expected RuntimeError'
    except RuntimeError as e:
        assert 'boom' in str(e)


def test_cli_writer_provider_empty_output_raises(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return _Completed(returncode=0, stdout='   ', stderr='')

    import subprocess
    monkeypatch.setattr(subprocess, 'run', fake_run)

    provider = make_cli_writer_provider(command='fake-llm')
    try:
        provider('S', 'U')
        assert False, 'expected RuntimeError'
    except RuntimeError as e:
        assert 'empty output' in str(e)
