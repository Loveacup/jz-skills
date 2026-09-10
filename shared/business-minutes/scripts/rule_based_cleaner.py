# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则化转录文本预清洗脚本
用于在 LLM 处理前进行规则化清洗，节约 token 消耗

功能：
1. 删除语气词和填充词
2. 修正重复词
3. 删除无效确认
4. 标点规范化
5. 去除多余空格

预期压缩率：20-30%
"""

import re
import sys
import json
from pathlib import Path


class TranscriptCleaner:
    """转录文本规则化清洗器"""

    # 中文语气词/填充词
    CHINESE_FILLERS = [
        '嗯', '啊', '呃', '哦', '诶', '唉',
        '那个', '这个', '就是说', '怎么说呢', '对吧', '是吧',
        '然后呢', '所以说', '基本上', '大概', '可能吧', '应该说',
        '其实吧', '就是', '反正', '总之吧', '怎么讲',
    ]

    # 英文语气词/填充词
    ENGLISH_FILLERS = [
        'uh', 'um', 'er', 'ah', 'like', 'you know',
        'I mean', 'sort of', 'kind of', 'basically',
        'actually', 'literally', 'so yeah', 'well',
    ]

    # 无效确认模式
    CONFIRMATION_PATTERNS = [
        r'对对对+',
        r'是是是+',
        r'好的好的+',
        r'嗯嗯嗯+',
        r'ok+\s*ok+',
        r'yes+\s*yes+',
    ]

    def __init__(self):
        self.stats = {
            'original_chars': 0,
            'cleaned_chars': 0,
            'fillers_removed': 0,
            'repetitions_fixed': 0,
            'confirmations_removed': 0,
        }

    def clean(self, text: str) -> str:
        """主清洗函数"""
        self.stats['original_chars'] = len(text)

        # 1. 删除语气词/填充词
        text = self._remove_fillers(text)

        # 2. 删除无效确认
        text = self._remove_confirmations(text)

        # 3. 修正重复词
        text = self._fix_repetitions(text)

        # 4. 标点规范化
        text = self._normalize_punctuation(text)

        # 5. 空格规范化
        text = self._normalize_spaces(text)

        self.stats['cleaned_chars'] = len(text)
        return text

    def _remove_fillers(self, text: str) -> str:
        """删除语气词和填充词"""
        count_before = len(text)

        # 中文语气词（按长度倒序，避免"那个"被"那"替换）
        for filler in sorted(self.CHINESE_FILLERS, key=len, reverse=True):
            text = text.replace(filler, '')

        # 英文语气词（不区分大小写）
        for filler in self.ENGLISH_FILLERS:
            text = re.sub(rf'\b{re.escape(filler)}\b', '', text, flags=re.IGNORECASE)

        self.stats['fillers_removed'] = count_before - len(text)
        return text

    def _remove_confirmations(self, text: str) -> str:
        """删除无效确认"""
        count_before = len(text)

        for pattern in self.CONFIRMATION_PATTERNS:
            text = re.sub(pattern, '', text)

        self.stats['confirmations_removed'] = count_before - len(text)
        return text

    def _fix_repetitions(self, text: str) -> str:
        """修正重复词"""
        count = 0

        # 中文重复（我我我 → 我）
        def replace_chinese_repetition(match):
            nonlocal count
            count += 1
            return match.group(1)

        text = re.sub(r'([\u4e00-\u9fff])\1{2,}', replace_chinese_repetition, text)

        # 英文单词重复（the the → the）
        def replace_english_repetition(match):
            nonlocal count
            count += 1
            return match.group(1)

        text = re.sub(r'\b(\w+)\s+\1\b', replace_english_repetition, text, flags=re.IGNORECASE)

        self.stats['repetitions_fixed'] = count
        return text

    def _normalize_punctuation(self, text: str) -> str:
        """标点规范化"""
        # 多个句号 → 单个句号
        text = re.sub(r'\.{2,}', '。', text)

        # 多个问号/感叹号 → 单个
        text = re.sub(r'\?{2,}', '?', text)
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'。{2,}', '。', text)
        text = re.sub(r'？{2,}', '？', text)
        text = re.sub(r'！{2,}', '！', text)

        # 中英文标点统一（可选）
        # text = text.replace('。', '.').replace('，', ',')

        return text

    def _normalize_spaces(self, text: str) -> str:
        """空格规范化"""
        # 多个空格 → 单个空格
        text = re.sub(r' {2,}', ' ', text)

        # 行首行尾空格
        text = re.sub(r'^ +', '', text, flags=re.MULTILINE)
        text = re.sub(r' +$', '', text, flags=re.MULTILINE)

        # 多个换行 → 双换行（保留分段）
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text

    def get_compression_rate(self) -> float:
        """计算压缩率"""
        if self.stats['original_chars'] == 0:
            return 0.0
        reduction = self.stats['original_chars'] - self.stats['cleaned_chars']
        return reduction / self.stats['original_chars'] * 100


def main():
    """主函数：命令行调用"""
    if len(sys.argv) < 3:
        print("用法: python rule_based_cleaner.py <input_file> <output_file>")
        print("示例: python rule_based_cleaner.py raw-input.md pre-cleaned.md")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    # 读取输入
    print(f"读取文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # 清洗
    print("执行规则化清洗...")
    cleaner = TranscriptCleaner()
    cleaned_text = cleaner.clean(text)

    # 写入输出
    print(f"写入文件: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)

    # 输出统计
    stats = cleaner.stats
    compression_rate = cleaner.get_compression_rate()

    print("\n" + "="*50)
    print("清洗统计:")
    print(f"  原始字符数: {stats['original_chars']:,}")
    print(f"  清洗后字符数: {stats['cleaned_chars']:,}")
    print(f"  删除语气词: {stats['fillers_removed']:,} 字符")
    print(f"  删除无效确认: {stats['confirmations_removed']:,} 字符")
    print(f"  修正重复: {stats['repetitions_fixed']} 处")
    print(f"  压缩率: {compression_rate:.1f}%")
    print("="*50)

    # 生成统计 JSON（供后续 Agent 读取）
    stats_file = output_file.parent / "pre-clean-stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump({
            'compression_rate': compression_rate,
            'original_chars': stats['original_chars'],
            'cleaned_chars': stats['cleaned_chars'],
            'details': stats
        }, f, ensure_ascii=False, indent=2)

    print(f"统计信息已保存到: {stats_file}")


if __name__ == '__main__':
    main()
