#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_writer_integration.py — LLM Writer 集成测试（P2-D2）

测试 deepseek_writer_provider 和 §3 LLM 接入渲染逻辑。
"""

import os
import pytest
from video_analysis_engine import (
    deepseek_writer_provider,
    render_markdown,
)


def test_deepseek_provider_no_key():
    """DEEPSEEK_API_KEY 未设置时应抛出 ValueError。"""
    old_key = os.environ.pop('DEEPSEEK_API_KEY', None)
    try:
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY 环境变量未设置"):
            deepseek_writer_provider("system prompt", "user prompt")
    finally:
        if old_key:
            os.environ['DEEPSEEK_API_KEY'] = old_key


def test_section3_llm_writer():
    """mock provider 返回合法内容时，§3 正文来自 LLM 而非骨架占位。"""
    def mock_provider(system: str, user: str) -> str:
        # 模拟 LLM 返回合法内容（3 条观点，每条 >15 字，含引用）
        return """### 核心洞察

- 观点一：视频展示了深度学习在图像识别领域的突破性进展 [E1]，准确率提升显著
- 观点二：作者强调数据质量比数据量更重要 [E2]，这是训练模型的关键因素
- 观点三：实验结果表明迁移学习能有效降低训练成本 [E3]，适合资源受限场景使用
"""

    report = _make_section3_report()
    markdown = render_markdown(report, provider=mock_provider)

    # 验证：不含骨架占位文本
    assert '骨架占位' not in markdown
    assert 'Skeleton' not in markdown

    # 验证：含 LLM 生成的观点文本
    assert '深度学习在图像识别领域的突破性进展' in markdown
    assert '[E1]' in markdown
    assert '[E2]' in markdown


def test_section3_fallback_on_validation_fail():
    """mock provider 返回不合格内容时，fallback 到骨架占位。"""
    def bad_provider(system: str, user: str) -> str:
        # 返回不合格内容：无引用、条目数不足
        return "这是一段没有引用的文本。"

    report = _make_section3_report()
    markdown = render_markdown(report, provider=bad_provider)

    # 验证：应 fallback 到骨架占位
    assert '骨架占位' in markdown or 'Skeleton' in markdown


def test_section4_llm_writer():
    """mock provider 返回合法内容时，§4 正文来自 LLM 而非骨架占位。"""
    def mock_provider(system: str, user: str) -> str:
        # 模拟 LLM 返回合法内容（3 条技术点，每条 >15 字，含引用）
        return """### 技术方法深度拆解

- 方法一：使用 PyTorch 构建卷积神经网络架构 [E1]，采用 ResNet-50 作为基础骨干网络
- 方法二：数据增强采用随机裁剪和水平翻转策略 [E2]，有效提升模型泛化能力
- 方法三：优化器选择 AdamW 配合余弦退火学习率调度 [E3]，训练过程更稳定收敛更快
"""

    report = _make_section4_report()
    markdown = render_markdown(report, provider=mock_provider)

    # 验证：不含骨架占位文本
    assert '骨架占位' not in markdown
    assert 'Skeleton' not in markdown

    # 验证：含 LLM 生成的技术点文本
    assert 'PyTorch 构建卷积神经网络架构' in markdown
    assert '[E1]' in markdown
    assert '[E2]' in markdown


def test_section4_fallback_on_validation_fail():
    """mock provider 返回不合格内容时，fallback 到骨架占位。"""
    def bad_provider(system: str, user: str) -> str:
        # 返回不合格内容：无引用、条目数不足
        return "这是一段没有引用的技术说明。"

    report = _make_section4_report()
    markdown = render_markdown(report, provider=bad_provider)

    # 验证：应 fallback 到骨架占位
    assert '骨架占位' in markdown or 'Skeleton' in markdown


def test_section7_llm_writer():
    """mock provider 返回合法内容时，§7 正文来自 LLM 而非骨架占位。"""
    def mock_provider(system: str, user: str) -> str:
        # 模拟 LLM 返回合法内容（3 条观众反馈，每条 >15 字，含引用）
        return """### 观众核心讨论点

- 讨论点一：评论区普遍认为视频讲解清晰易懂 [E1]，适合初学者快速入门深度学习基础概念
- 讨论点二：多位观众提出希望增加实战案例演示 [E2]，纯理论讲解缺少可操作性指导
- 讨论点三：部分用户质疑数据集选择的代表性 [E3]，建议使用更贴近真实业务场景的数据
"""

    report = _make_section7_report()
    markdown = render_markdown(report, provider=mock_provider)

    # 验证：不含骨架占位文本
    assert '骨架占位' not in markdown
    assert 'Skeleton' not in markdown

    # 验证：含 LLM 生成的观众讨论点文本
    assert '评论区普遍认为视频讲解清晰易懂' in markdown
    assert '[E1]' in markdown
    assert '[E2]' in markdown


def test_section7_fallback_on_validation_fail():
    """mock provider 返回不合格内容时，fallback 到骨架占位。"""
    def bad_provider(system: str, user: str) -> str:
        # 返回不合格内容：无引用、条目数不足
        return "这是一段没有引用的观众反馈。"

    report = _make_section7_report()
    markdown = render_markdown(report, provider=bad_provider)

    # 验证：应 fallback 到骨架占位
    assert '骨架占位' in markdown or 'Skeleton' in markdown


# ============ 测试辅助函数 ============
def _make_section3_report() -> dict:
    """构造包含 §3 的最小 report 结构。"""
    return {
        'frontmatter': {
            'title': 'Test Video',
            'video_id': 'BV1234567890',
            'created_at': '2026-07-01T00:00:00Z',
        },
        'report_plan': {
            'can_generate_formal_report': True,
            'sections': [
                {
                    'id': '3',
                    'title': '核心洞察',
                    'purpose': '提炼视频核心观点',
                    'quality_gate': '至少 3 条有深度的观点',
                }
            ]
        },
        'evidence_map': {
            'by_section': {
                '3': [
                    {
                        'text': '深度学习在图像识别领域取得突破',
                        'timestamp': '00:05:23',
                        'source_type': 'transcript',
                    },
                    {
                        'text': '数据质量比数据量更重要',
                        'timestamp': '00:12:45',
                        'source_type': 'transcript',
                    },
                    {
                        'text': '迁移学习能有效降低训练成本',
                        'timestamp': '00:18:30',
                        'source_type': 'transcript',
                    },
                ]
            },
            'warnings': []
        },
        'evidence_gate': {
            'sources': {
                'transcript': {
                    'available': True,
                    'source': 'mlx-whisper',
                    'language': 'zh',
                    'segments': 100,
                    'chars': 5000,
                }
            }
        }
    }


def _make_section4_report() -> dict:
    """构造包含 §4 的最小 report 结构。"""
    return {
        'frontmatter': {
            'title': 'Test Video',
            'video_id': 'BV1234567890',
            'created_at': '2026-07-01T00:00:00Z',
        },
        'report_plan': {
            'can_generate_formal_report': True,
            'sections': [
                {
                    'id': '4',
                    'title': '技术方法深度拆解',
                    'purpose': '分析视频中的技术方法和工具使用',
                    'quality_gate': '至少 3 条技术要点',
                }
            ]
        },
        'evidence_map': {
            'by_section': {
                '4': [
                    {
                        'text': '使用 PyTorch 构建卷积神经网络',
                        'timestamp': '00:08:15',
                        'source_type': 'transcript',
                    },
                    {
                        'text': '数据增强采用随机裁剪和水平翻转',
                        'timestamp': '00:15:30',
                        'source_type': 'transcript',
                    },
                    {
                        'text': '优化器选择 AdamW 配合余弦退火',
                        'timestamp': '00:22:45',
                        'source_type': 'transcript',
                    },
                ]
            },
            'warnings': []
        },
        'evidence_gate': {
            'sources': {
                'transcript': {
                    'available': True,
                    'source': 'mlx-whisper',
                    'language': 'zh',
                    'segments': 100,
                    'chars': 5000,
                }
            }
        }
    }


def _make_section7_report() -> dict:
    """构造包含 §7 的最小 report 结构。"""
    return {
        'frontmatter': {
            'title': 'Test Video',
            'video_id': 'BV1234567890',
            'created_at': '2026-07-01T00:00:00Z',
        },
        'report_plan': {
            'can_generate_formal_report': True,
            'sections': [
                {
                    'id': '7',
                    'title': '观众讨论与反馈',
                    'purpose': '整理评论区的核心讨论点和观众反馈',
                    'quality_gate': '至少 3 条有代表性的讨论点',
                }
            ]
        },
        'evidence_map': {
            'by_section': {
                '7': [
                    {
                        'text': '评论区普遍认为视频讲解清晰',
                        'timestamp': None,
                        'source_type': 'comments',
                    },
                    {
                        'text': '多位观众希望增加实战案例',
                        'timestamp': None,
                        'source_type': 'comments',
                    },
                    {
                        'text': '部分用户质疑数据集代表性',
                        'timestamp': None,
                        'source_type': 'comments',
                    },
                ]
            },
            'warnings': []
        },
        'evidence_gate': {
            'sources': {
                'transcript': {
                    'available': True,
                    'source': 'mlx-whisper',
                    'language': 'zh',
                    'segments': 100,
                    'chars': 5000,
                },
                'comments': {
                    'available': True,
                    'count': 50,
                }
            }
        }
    }


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
