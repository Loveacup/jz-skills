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
- 第一条观点引用 [E1]，这是一条包含足够字数的测试观点内容
- 第二条观点引用 [E2]，这是另一条包含足够字数的测试观点内容
- 第三条观点引用 [E3]，这是第三条包含足够字数的测试观点内容
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
- 观点一 [E1]：包含足够的中文字符以满足最低词数要求确保通过验证
- 观点二 [E2]：包含足够的中文字符以满足最低词数要求确保通过验证
- 观点三 [E3]：包含足够的中文字符以满足最低词数要求确保通过验证
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
    result = WriterResult(section_id="3", content=content)
    context = make_section_context(min_items=3, min_words_per_item=20)

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
    result = WriterResult(section_id="3", content=content)
    context = make_section_context(min_items=3, min_words_per_item=20)

    validated = validate_section(result, context)

    assert validated.validation_passed is False
    assert any("词数不足" in e for e in validated.validation_errors)


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
