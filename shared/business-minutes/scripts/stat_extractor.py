# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计信息预提取脚本
提取文件基础统计信息，为 content-analyzer 提供数据支撑

功能：
1. 基础统计（字数、行数、token 估算）
2. 说话人统计（发言次数、字数分布）
3. 关键词频率统计（Top 50）
4. 时间信息提取（如果有时间戳）
5. 情感/语气分析（简单）

预计节约 Token：5-10%（content-analyzer 可直接读取统计）
"""

import re
import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter, defaultdict
from datetime import datetime


class StatExtractor:
    """统计信息提取器"""

    def __init__(self):
        # 常见停用词
        self.stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
            '没有', '看', '好', '自己', '这', '那', '里', '后', '以', '所', '如果',
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
        }

        # 关键词正则模式
        self.keyword_patterns = {
            '时间': r'(\d{1,2}月|\d{1,2}日|今天|明天|后天|下周|上月|明年|\d{4}年)',
            '数字': r'\d+(?:,\d{3})*(?:\.\d+)?',
            '金额': r'(\d+(?:,\d{3})*|\d*\.\d+)\s*元|万元|亿|千|百',
            '百分比': r'\d+(?:\.\d+)?%',
            '电话': r'1[3-9]\d{9}',
            '邮箱': r'\w+@\w+\.\w+',
            '网址': r'https?://\S+',
        }

        # 情感词
        self.sentiment_words = {
            'positive': ['好', '棒', '赞', '满意', '喜欢', '同意', '支持', '开心', '高兴', '优秀', '完美'],
            'negative': ['差', '烂', '不满意', '反对', '不支持', '生气', '愤怒', '失望', '糟糕'],
            'neutral': ['一般', '普通', '还行', '凑合', '马马虎虎']
        }

    def extract_stats(self, input_path: Path, output_path: Path) -> Dict:
        """提取统计信息"""
        # 1. 读取文件
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 2. 基础统计
        basic_stats = self._extract_basic_stats(content)

        # 3. 说话人统计
        speaker_stats = self._extract_speaker_stats(content)

        # 4. 关键词统计
        keyword_stats = self._extract_keyword_stats(content)

        # 5. 时间统计
        time_stats = self._extract_time_stats(content)

        # 6. 情感统计
        sentiment_stats = self._extract_sentiment_stats(content)

        # 7. 合并所有统计
        all_stats = {
            'basic': basic_stats,
            'speakers': speaker_stats,
            'keywords': keyword_stats,
            'time': time_stats,
            'sentiment': sentiment_stats,
            'extraction_time': datetime.now().isoformat()
        }

        # 8. 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_stats, f, ensure_ascii=False, indent=2)

        return all_stats

    def _extract_basic_stats(self, content: str) -> Dict:
        """提取基础统计"""
        lines = content.split('\n')
        chars = len(content)
        words = len(content.split())

        # Token 估算（中文约 1.5 字符/token，英文约 0.75 单词/token）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        estimated_tokens = int(chinese_chars / 1.5 + english_words / 0.75)

        return {
            'total_lines': len(lines),
            'total_chars': chars,
            'total_words': words,
            'estimated_tokens': estimated_tokens,
            'avg_chars_per_line': int(chars / len(lines)) if lines else 0,
            'avg_chars_per_word': int(chars / words) if words else 0,
            'chinese_ratio': chinese_chars / chars if chars else 0,
            'english_ratio': english_words / words if words else 0
        }

    def _extract_speaker_stats(self, content: str) -> Dict:
        """提取说话人统计"""
        # 说话人标记正则
        speaker_patterns = [
            r'\*\*([^*]+)\*\*:',  # **张三**:
            r'\[([^\]]+)\]：',      # [张三]：
            r'^([^:]+)：',          # 张三：
            r'^([^:]+):',          # 张三:
        ]

        speakers = defaultdict(lambda: {'count': 0, 'chars': 0, 'words': 0})

        for pattern in speaker_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for speaker in matches:
                speakers[speaker]['count'] += 1

        # 计算每个说话人的内容长度
        for speaker in speakers:
            # 匹配该说话人的所有段落
            for pattern in speaker_patterns:
                speaker_content = re.findall(
                    rf'{re.escape(pattern.replace("([^:]+)", speaker))}(.*?)(?=\n\*\*|\n\[|\n[^:]+：|\n[^:]+:|\Z)',
                    content,
                    re.DOTALL
                )
                if speaker_content:
                    text = ' '.join([match[1] if isinstance(match, tuple) else match for match in speaker_content])
                    speakers[speaker]['chars'] += len(text)
                    speakers[speaker]['words'] += len(text.split())

        # 计算比例
        total_speeches = sum(s['count'] for s in speakers.values())
        for speaker in speakers:
            speakers[speaker]['percentage'] = speakers[speaker]['count'] / total_speeches * 100 if total_speeches else 0

        return {
            'total_speakers': len(speakers),
            'speaker_list': list(speakers.keys()),
            'distribution': dict(speakers),
            'most_active': max(speakers.items(), key=lambda x: x[1]['count'])[0] if speakers else None,
            'balance_score': self._calculate_balance_score(speakers) if speakers else 0
        }

    def _extract_keyword_stats(self, content: str) -> Dict:
        """提取关键词统计"""
        # 分词（简单处理）
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', content)
        # 过滤停用词和短词
        filtered_words = [w for w in words if w not in self.stopwords and len(w) > 1]

        # 词频统计
        word_freq = Counter(filtered_words)

        # 模式匹配关键词
        pattern_matches = {}
        for category, pattern in self.keyword_patterns.items():
            matches = re.findall(pattern, content)
            pattern_matches[category] = {
                'count': len(matches),
                'examples': matches[:5]  # 前5个示例
            }

        return {
            'top_words': word_freq.most_common(50),
            'total_unique_words': len(word_freq),
            'vocabulary_diversity': len(word_freq) / len(filtered_words) if filtered_words else 0,
            'pattern_matches': pattern_matches,
            'avg_word_length': sum(len(w) for w in filtered_words) / len(filtered_words) if filtered_words else 0
        }

    def _extract_time_stats(self, content: str) -> Dict:
        """提取时间相关统计"""
        time_patterns = {
            'dates': r'(\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日)',
            'times': r'(\d{1,2}:\d{2}(?::\d{2})?)',
            'durations': r'(\d+分钟|\d+小时|\d+天|\d+周|\d+个月|\d+年)',
            'relative_time': r'(今天|明天|后天|下周|上月|明年|上周|前天|后天)'
        }

        time_stats = {}
        for category, pattern in time_patterns.items():
            matches = re.findall(pattern, content)
            time_stats[category] = {
                'count': len(matches),
                'examples': matches[:10]
            }

        return time_stats

    def _extract_sentiment_stats(self, content: str) -> Dict:
        """提取情感统计"""
        sentiment_counts = {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }

        for sentiment, words in self.sentiment_words.items():
            for word in words:
                sentiment_counts[sentiment] += content.count(word)

        total_sentiment = sum(sentiment_counts.values())
        sentiment_percentages = {
            k: (v / total_sentiment * 100) if total_sentiment > 0 else 0
            for k, v in sentiment_counts.items()
        }

        return {
            'counts': sentiment_counts,
            'percentages': sentiment_percentages,
            'overall_tone': max(sentiment_counts.items(), key=lambda x: x[1])[0] if total_sentiment > 0 else 'neutral'
        }

    def _calculate_balance_score(self, speakers: Dict) -> float:
        """计算说话人平衡度（0-1，1最平衡）"""
        if not speakers:
            return 0

        counts = [s['count'] for s in speakers.values()]
        if len(counts) <= 1:
            return 0

        # 使用标准差计算平衡度
        mean_count = sum(counts) / len(counts)
        variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
        std_dev = math.sqrt(variance)

        # 平衡度 = 1 - (标准差 / 平均值)
        balance_score = 1 - (std_dev / mean_count) if mean_count > 0 else 0
        return max(0, balance_score)  # 确保不为负数

    def generate_summary(self, stats: Dict) -> str:
        """生成文本摘要"""
        basic = stats['basic']
        speakers = stats['speakers']
        keywords = stats['keywords']

        summary = f"""
文件统计摘要：
- 总长度: {basic['total_chars']} 字符，{basic['estimated_tokens']} tokens（估算）
- 说话人: {speakers['total_speakers']} 人（{', '.join(speakers['speaker_list'][:5])}）
- 词汇: {keywords['total_unique_words']} 个不重复词
- 活跃度最高: {speakers['most_active']}（{speakers['distribution'][speakers['most_active']]['count']} 次发言）
- 平衡度: {speakers['balance_score']:.2f}
        """.strip()

        return summary


def main():
    """命令行调用"""
    if len(sys.argv) < 3:
        print("用法: python stat_extractor.py <input_file> <output_file>")
        print("示例: python stat_extractor.py normalized-input.md file-stats.json")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    # 执行统计提取
    extractor = StatExtractor()
    try:
        stats = extractor.extract_stats(input_file, output_file)
        print(f"✅ 统计提取完成: {input_file} → {output_file}")

        # 生成摘要
        summary = extractor.generate_summary(stats)
        print(f"\n📊 统计摘要:")
        print(summary)

    except Exception as e:
        print(f"❌ 统计提取失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
