# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
说话人标记规范化脚本
统一多种说话人标记格式，合并同一人的不同称呼

支持格式：
- [张三]：你好
- 张三: 你好
- 张三：你好
- Speaker 1: Hello
- S1: Hello
- A: Hello, B: World

预计节约 Token：15-20%（避免 LLM 处理格式混乱）
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter


class SpeakerNormalizer:
    """说话人标记规范化器"""

    def __init__(self):
        # 说话人标记正则模式（按优先级排序）
        self.patterns = [
            (r'^\[([^\]]+)\]：?\s*', 'bracket'),      # [张三]：你好
            (r'^([^\]]+):\s*', 'colon'),              # 张三: 你好
            (r'^([^\]]+)：\s*', 'colon_cn'),          # 张三：你好
            (r'^Speaker\s+(\d+):\s*', 'speaker'),     # Speaker 1: Hello
            (r'^S(\d+):\s*', 's_number'),            # S1: Hello
            (r'^([A-Z]{1,2})\s*:?\s*', 'letter'),   # A: Hello
            (r'^(\d+)\.\s*', 'number'),               # 1. 你好
        ]

        # 称呼映射规则（规则合并）
        self.title_mapping = {
            # 领导/职位
            '张总': '张三', '李总': '李四', '王总': '王五',
            '张经理': '张三', '李经理': '李四',
            '张总监': '张三', '李总监': '李四',
            '张主管': '张三', '李主管': '李四',

            # 常见称呼
            '老板': 'Boss', '经理': 'Manager', '主管': 'Supervisor',
            '同事': 'Colleague', '同学': 'Classmate',
            '老师': 'Teacher', '教授': 'Professor',
            '医生': 'Doctor', '博士': 'Doctor',

            # 性别/角色
            '男士': 'Male', '女士': 'Female',
            '主持人': 'Host', '嘉宾': 'Guest',
            '提问者': 'Questioner', '回答者': 'Answerer',
        }

        # 数字到字母的映射
        self.number_to_letter = {
            '1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E',
            '6': 'F', '7': 'G', '8': 'H', '9': 'I', '10': 'J'
        }

        # 说话人信息收集
        self.speaker_info = defaultdict(list)
        self.speaker_mapping = {}  # 原始标记 -> 规范化名称

    def normalize_file(self, input_path: Path, output_path: Path) -> Dict:
        """规范化整个文件"""
        # 1. 读取文件
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 2. 提取所有说话人标记
        speakers = self._extract_speakers(lines)

        # 3. 生成说话人映射
        speaker_mapping = self._generate_speaker_mapping(speakers)

        # 4. 规范化文本
        normalized_lines = []
        for line in lines:
            normalized_line = self._normalize_line(line, speaker_mapping)
            normalized_lines.append(normalized_line)

        # 5. 写入输出
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(normalized_lines))

        # 6. 生成统计
        return self._generate_stats(speaker_mapping, speakers)

    def _extract_speakers(self, lines: List[str]) -> List[Dict]:
        """提取所有说话人标记"""
        speakers = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern, pattern_type in self.patterns:
                match = re.match(pattern, line)
                if match:
                    speaker_raw = match.group(1).strip()
                    speakers.append({
                        'raw': speaker_raw,
                        'type': pattern_type,
                        'line': line
                    })
                    break

        return speakers

    def _generate_speaker_mapping(self, speakers: List[Dict]) -> Dict[str, str]:
        """生成说话人映射规则"""
        # 1. 收集所有说话人
        all_speakers = [s['raw'] for s in speakers]

        # 2. 频率统计
        speaker_freq = Counter(all_speakers)

        # 3. 按频率排序，优先保留高频称呼
        sorted_speakers = sorted(speaker_freq.items(), key=lambda x: x[1], reverse=True)

        # 4. 生成映射
        mapping = {}

        for raw_name, _ in sorted_speakers:
            # 跳过已映射的
            if raw_name in mapping:
                continue

            # 查找可能的同一人
            canonical_name = self._find_canonical_name(raw_name, sorted_speakers)

            # 统一格式
            normalized_name = self._normalize_name(canonical_name)

            # 标记原始名称 -> 规范化名称
            for speaker_raw, _ in sorted_speakers:
                if self._are_same_person(speaker_raw, canonical_name):
                    mapping[speaker_raw] = normalized_name

        return mapping

    def _find_canonical_name(self, name: str, all_speakers: List[Tuple[str, int]]) -> str:
        """找到最合适的规范名称"""
        # 1. 检查是否有明确的职位称呼
        if name in self.title_mapping:
            return self.title_mapping[name]

        # 2. 选择最长的形式（通常更完整）
        candidates = [s for s, _ in all_speakers if self._are_same_person(s, name)]
        if candidates:
            return max(candidates, key=len)

        return name

    def _are_same_person(self, name1: str, name2: str) -> bool:
        """判断两个名称是否指同一人"""
        # 完全相同
        if name1 == name2:
            return True

        # 职位称呼映射
        if name1 in self.title_mapping and self.title_mapping[name1] == name2:
            return True
        if name2 in self.title_mapping and self.title_mapping[name2] == name1:
            return True

        # 基础姓名匹配（去掉职位）
        name1_base = re.sub(r'(总|经理|总监|主管)$', '', name1)
        name2_base = re.sub(r'(总|经理|总监|主管)$', '', name2)

        if name1_base == name2_base:
            return True

        # 数字编号映射（Speaker 1 = S1 = 1）
        if self._is_number_pattern(name1) and self._is_number_pattern(name2):
            n1 = self._extract_number(name1)
            n2 = self._extract_number(name2)
            return n1 == n2

        return False

    def _is_number_pattern(self, name: str) -> bool:
        """检查是否是数字编号模式"""
        return bool(re.match(r'(Speaker\s*\d+|S\d+|\d+)', name, re.IGNORECASE))

    def _extract_number(self, name: str) -> int:
        """从说话人名称中提取数字"""
        match = re.search(r'\d+', name)
        return int(match.group()) if match else 0

    def _normalize_name(self, name: str) -> str:
        """规范化名称格式"""
        # 职位称呼转换
        if name in self.title_mapping:
            return self.title_mapping[name]

        # 数字编号转换为字母（避免重复）
        if self._is_number_pattern(name):
            number = self._extract_number(name)
            return self.number_to_letter.get(str(number), f'Speaker{number}')

        # 保持原样
        return name

    def _normalize_line(self, line: str, mapping: Dict[str, str]) -> str:
        """规范化单行文本"""
        for raw_name, normalized_name in mapping.items():
            # 匹配各种格式的说话人标记
            patterns = [
                f'[{raw_name}]：?',     # [张三]：你好
                f'{raw_name}：?',       # 张三：你好
                f'{raw_name}:?',        # 张三: 你好
                rf'Speaker\s*{self._extract_number(raw_name)}:',  # Speaker 1: Hello
                f'S{self._extract_number(raw_name)}:',           # S1: Hello
                f'{raw_name}:?',        # A: Hello
            ]

            for pattern in patterns:
                if re.match(r'^\[', raw_name):
                    # 括号格式特殊处理
                    line = re.sub(f'\\[{re.escape(raw_name)}\\]：?', f'**{normalized_name}**:', line)
                else:
                    line = re.sub(f'^{re.escape(pattern)}', f'**{normalized_name}**:', line, flags=re.IGNORECASE)

        return line

    def _generate_stats(self, mapping: Dict[str, str], speakers: List[Dict]) -> Dict:
        """生成统计信息"""
        # 统计原始说话人
        raw_speakers = list(set(s['raw'] for s in speakers))

        # 统计规范化后说话人
        normalized_speakers = list(set(mapping.values()))

        # 映射关系
        mapping_details = []
        for raw, norm in mapping.items():
            if raw != norm:  # 只显示有变化的映射
                mapping_details.append({'from': raw, 'to': norm})

        return {
            'original_speakers': raw_speakers,
            'normalized_speakers': normalized_speakers,
            'mapping_count': len(mapping),
            'mapping_details': mapping_details,
            'reduction_ratio': len(raw_speakers) / len(normalized_speakers) if normalized_speakers else 0
        }


def main():
    """命令行调用"""
    if len(sys.argv) < 3:
        print("用法: python speaker_normalizer.py <input_file> <output_file>")
        print("示例: python speaker_normalizer.py standard-input.md normalized-input.md")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    # 执行规范化
    normalizer = SpeakerNormalizer()
    try:
        stats = normalizer.normalize_file(input_file, output_file)
        print(f"✅ 说话人规范化完成: {input_file} → {output_file}")
        print(f"📊 统计信息:")
        print(f"  原始说话人: {', '.join(stats['original_speakers'])}")
        print(f"  规范化后: {', '.join(stats['normalized_speakers'])}")
        print(f"  映射关系: {len(stats['mapping_details'])} 个")
        if stats['reduction_ratio'] > 1:
            print(f"  规范化效果: 合并了 {stats['reduction_ratio']:.1f} 倍")

        # 保存统计到 JSON
        stats_file = output_file.parent / "speaker-normalization-stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"📄 统计详情已保存: {stats_file}")

    except Exception as e:
        print(f"❌ 规范化失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
