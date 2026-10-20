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
        # 模拟 LLM 返回合法内容（3 条洞察，每条 ≥300 字，含完整结构和引用）
        return """### 💡 洞察 1：图像识别突破
**定义**：深度学习在图像识别领域取得突破性进展，准确率提升显著。

**深度解析**：
原理层：模型架构和训练数据共同决定结果质量，这是深度学习的核心规律。从证据 [E1] 可见，视频中展示的卷积神经网络通过多层特征提取实现了对图像的分层理解，从边缘到纹理再到高级语义概念，这种层次化表征学习正是深度学习优于传统方法的关键。
案例层：视频中具体演示了 ResNet-50 在 ImageNet 数据集上的训练过程，Top-5 准确率达到 92.3%，显著高于传统方法的 70-80%。这个案例清晰地说明了深层网络架构带来的性能提升。
关联层：这一发现与迁移学习、预训练模型等概念密切相关，说明了特征表征的可复用性是深度学习生态系统的基础。

**弹幕反馈**：共鸣型弹幕占主导，典型如"终于懂了为什么要用深层网络"、"原来卷积层是这样提取特征的"，共识度：高。

**推理许可**：当模型架构能够实现分层特征提取，且训练数据覆盖目标分布时，深度学习方法的准确率将显著优于传统方法。

**边界条件**：该主张成立的前提是有足够的训练数据和计算资源；在小样本、低资源场景下，深度学习可能不如传统方法有效。

证据：@[E1] @[E2]

### 💡 洞察 2：数据质量优先
**定义**：数据质量比数据量更重要，这意味着工程投入不能只堆规模，还要关注标注、分布和清洗。

**深度解析**：
原理层：作者通过对比实验强调了数据质量的核心地位。从证据 [E2] 可见，使用 10 万条精标注数据训练的模型，效果优于 100 万条粗标注数据，说明标注质量直接影响模型学习的有效性。这背后的机制是：噪声标注会误导梯度下降方向，而高质量标注能让模型学到真实的数据分布规律。
案例层：视频中展示的数据清洗流程包括去重、异常值检测、标注一致性审查，这些步骤虽然耗时但能显著提升模型性能，是工程实践中不可或缺的环节。
关联层：这一观点与主动学习、少样本学习等研究方向呼应，说明了在数据获取成本高昂的场景下，如何通过提升数据质量来降低总体成本。

**弹幕反馈**：调侃型弹幕如"我司就是堆数据不管质量"、"终于有人说出来了"占比较高，质疑型如"但是清洗数据太耗时"也存在，共识度：中偏高。

**推理许可**：当标注质量显著影响模型学习效果，且数据清洗成本低于大规模数据采集成本时，优先投入数据质量提升是更经济的策略。

**边界条件**：在某些场景下（如自监督学习、大规模预训练），数据量可能比单条数据质量更重要；该主张主要适用于监督学习和标注成本可控的场景。

证据：@[E2]

### 💡 洞察 3：迁移学习降本
**定义**：实验结果表明迁移学习能有效降低训练成本，适合资源受限场景快速复用已有能力。

**深度解析**：
原理层：迁移学习的核心是特征复用。从证据 [E3] 可见，在 ImageNet 预训练的模型可以作为特征提取器，在小数据集上只需微调最后几层就能达到从头训练 80% 的性能，但训练时间和计算资源消耗减少 90% 以上。这种效率提升来自于预训练模型已经学到了通用的视觉特征表征，下游任务只需在此基础上进行微调即可。
案例层：视频中展示了在医疗影像分类任务上的迁移学习实践，仅用 1000 张标注图像就达到了专家级分类准确率，而从头训练需要至少 10000 张图像才能达到相同水平。
关联层：这一发现与少样本学习、元学习等概念相关，说明了知识迁移是人工智能实现高效学习的重要路径。

**弹幕反馈**：共鸣型弹幕如"终于找到省钱的方法了"、"迁移学习真香"占主导，也有质疑型如"迁移学习效果不如从头训练"，共识度：高。

**推理许可**：当预训练模型的数据分布与下游任务数据分布有一定相似性，且下游任务训练数据有限时，迁移学习能够以更低的成本达到接近从头训练的性能。

**边界条件**：该主张的局限在于：如果预训练数据与下游任务数据分布差异过大（如从自然图像迁移到医学影像），迁移学习的效果可能不如从头训练；此外，某些对性能要求极高的场景仍需从头训练以获得最佳效果。

证据：@[E3]
"""

    report = _make_section3_report()
    markdown = render_markdown(report, provider=mock_provider)

    # 验证：不含骨架占位文本
    assert '骨架占位' not in markdown
    assert 'Skeleton' not in markdown

    # 验证：含 LLM 生成的观点文本和完整结构
    assert '深度解析' in markdown
    assert '推理许可' in markdown
    assert '边界条件' in markdown
    assert '证据：@[E1]' in markdown
    assert '证据：@[E2]' in markdown
    assert '证据：@[E3]' in markdown


def test_section3_fallback_on_validation_fail():
    """mock provider 返回不合格内容时，fallback 到骨架占位。"""
    def bad_provider(system: str, user: str) -> str:
        # 返回不合格内容：无引用、条目数不足
        return "这是一段没有引用的文本。"

    report = _make_section3_report()
    markdown = render_markdown(report, provider=bad_provider)

    # 验证：应 fallback 到骨架占位
    assert '骨架占位' in markdown or 'Skeleton' in markdown


def test_section3_meets_min_words():
    """mock provider 返回词数刚好达到验证阈值（100 词）的内容时，不应 fallback。"""
    def mock_provider(system: str, user: str) -> str:
        # 模拟 LLM 返回刚好满足 100 词验证阈值的内容（每个洞察约 110 字）
        return """### 💡 洞察 1：图像识别突破
深度学习在图像识别领域取得突破性进展，准确率提升显著，说明模型结构和训练数据共同决定结果质量。从证据 [E1] 可见，视频中展示的卷积神经网络通过多层特征提取实现了对图像的分层理解，从边缘到纹理再到高级语义概念。这种层次化表征学习正是深度学习优于传统方法的关键所在。

证据：@[E1]

### 💡 洞察 2：数据质量优先
作者强调数据质量比数据量更重要，这意味着工程投入不能只堆规模，还要关注标注、分布和清洗。从证据 [E2] 可见，使用 10 万条精标注数据训练的模型，效果优于 100 万条粗标注数据，说明标注质量直接影响模型学习的有效性。噪声标注会误导梯度下降方向，而高质量标注能让模型学到真实的数据分布规律。

证据：@[E2]

### 💡 洞察 3：迁移学习降本
实验结果表明迁移学习能有效降低训练成本，适合资源受限场景快速复用已有能力。从证据 [E3] 可见，在 ImageNet 预训练的模型可以作为特征提取器，在小数据集上只需微调最后几层就能达到从头训练 80% 的性能，但训练时间和计算资源消耗减少 90% 以上。这种效率提升来自于预训练模型已经学到了通用的视觉特征表征。

证据：@[E3]
"""

    report = _make_section3_report()
    markdown = render_markdown(report, provider=mock_provider)

    # 验证：不含骨架占位文本（词数达标，验证应通过）
    assert '骨架占位' not in markdown
    assert 'Skeleton' not in markdown

    # 验证：包含 3 个洞察标题
    assert '### 💡 洞察 1：' in markdown
    assert '### 💡 洞察 2：' in markdown
    assert '### 💡 洞察 3：' in markdown

    # 验证：包含证据引用
    assert '证据：@[E1]' in markdown
    assert '证据：@[E2]' in markdown
    assert '证据：@[E3]' in markdown


def test_section4_llm_writer():
    """mock provider 返回合法内容时，§4 正文来自 LLM 而非骨架占位。"""
    def mock_provider(system: str, user: str) -> str:
        # 模拟 LLM 返回合法内容（3 条技术点，每条 >15 字，含引用）
        return """### 模块 1：模型架构 [E1]
使用 PyTorch 构建卷积神经网络架构，采用 ResNet-50 作为基础骨干网络，体现了成熟视觉模型的迁移价值。
### 模块 2：数据增强 [E2]
数据增强采用随机裁剪和水平翻转策略，这类方法能提升模型泛化能力，降低训练集偏差影响。
### 模块 3：训练优化 [E3]
优化器选择 AdamW 配合余弦退火学习率调度，使训练过程更稳定，收敛速度也更可控。
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
    """mock provider 连续 3 次返回不合格内容时，fallback 到骨架占位。"""
    call_count = [0]

    def bad_provider(system: str, user: str) -> str:
        call_count[0] += 1
        # 连续返回不合格内容：无引用、条目数不足
        return "这是一段没有引用的技术说明。"

    report = _make_section4_report()
    markdown = render_markdown(report, provider=bad_provider)

    # 验证：LLM 被调用了多次（至少 2 次，因为有 retry 机制）
    assert call_count[0] >= 2, f"Expected ≥2 LLM calls for retry, got {call_count[0]}"

    # 验证：最终仍 fallback 到骨架占位（3 次都失败）
    assert '骨架占位' in markdown or 'Skeleton' in markdown


def test_section4_meets_module_format_on_retry():
    """mock provider 第一次返回不合格，第二次返回合格格式时，不应 fallback。"""
    call_count = [0]

    def retry_provider(system: str, user: str) -> str:
        call_count[0] += 1
        if call_count[0] == 1:
            # 第一次返回：缺少模块标题，应触发 validation 失败
            return "这是一段没有模块标题的技术说明。[E1] [E2]"
        else:
            # 第二次返回：符合格式
            return """### 模块 1：现象拆解
**核心论点**：深度学习模型的性能突破依赖于架构创新和数据质量双重驱动 [E1]。

**论证展开**：
- 前提：从证据 [E1] 可见...
- 推理：...
- 结论：...

证据：@[E1] @[E2]

### 模块 2：机制分析
**核心论点**：数据增强策略通过模拟分布多样性提升泛化能力 [E2]。

**论证展开**：
- 前提：从证据 [E2] 可见...
- 推理：...
- 结论：...

证据：@[E2]

### 模块 3：结构性原因
**核心论点**：优化器选择和学习率调度共同决定收敛稳定性 [E3]。

**论证展开**：
- 前提：从证据 [E3] 可见...
- 推理：...
- 结论：...

证据：@[E3]
"""

    report = _make_section4_report()
    markdown = render_markdown(report, provider=retry_provider)

    # 验证：LLM 被调用了 2 次（第一次失败，第二次成功）
    assert call_count[0] == 2, f"Expected 2 LLM calls (1 fail + 1 success), got {call_count[0]}"

    # 验证：最终输出包含模块标题
    assert '### 模块 1：' in markdown
    assert '### 模块 2：' in markdown
    assert '### 模块 3：' in markdown

    # 验证：不含骨架占位
    assert '骨架占位' not in markdown
    assert 'Skeleton Module' not in markdown


def test_section7_llm_writer():
    """mock provider 返回合法内容时，§7 正文来自 LLM 而非骨架占位。"""
    def mock_provider(system: str, user: str) -> str:
        # 模拟 LLM 返回合法内容（3 条观众反馈，每条 >15 字，含引用）
        return """### 独特价值 [E1]
- 视频讲解清晰易懂，适合初学者快速入门深度学习基础概念。
- 观众能从案例中理解训练流程和模型选择之间的关系。
- 内容把复杂技术压缩成可跟随的学习路径，降低了入门阻力。
### 局限与偏见 [E2]
- 多位观众希望增加实战案例演示，说明纯理论讲解缺少可操作性指导。
- 部分用户质疑数据集选择的代表性，提示结论外推需要谨慎。
### 可行动项 [E3]
- 补充一个最小可运行案例，把模型、数据和评估流程串起来。
- 使用更贴近真实业务场景的数据做一次复现实验。
- 将理论概念整理成检查清单，辅助后续项目落地。
"""

    report = _make_section7_report()
    markdown = render_markdown(report, provider=mock_provider)

    # 验证：不含骨架占位文本
    assert '骨架占位' not in markdown
    assert 'Skeleton' not in markdown

    # 验证：含 LLM 生成的观众讨论点文本
    assert '视频讲解清晰易懂' in markdown
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
