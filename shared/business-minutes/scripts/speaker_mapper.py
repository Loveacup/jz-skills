# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
说话人智能映射
v4.0 新增 - 将 Speaker 0/A/B 映射到真实姓名

功能：
1. 正则匹配自我介绍
2. 识别称呼模式
3. 用户提示合并
4. LLM推断（可选）
5. 交互式确认
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class SpeakerInfo:
    """说话人信息"""
    original_id: str          # 原始标识 (Speaker 0, A, 发言人1)
    mapped_name: Optional[str] = None  # 映射后的姓名
    role: Optional[str] = None         # 角色 (主持人, 技术负责人)
    organization: Optional[str] = None  # 组织
    confidence: float = 0.0            # 映射置信度
    source: str = "unknown"            # 来源 (regex, reference, user, llm)
    utterance_count: int = 0           # 发言次数


@dataclass
class MappingResult:
    """映射结果"""
    speakers: List[SpeakerInfo]
    mapped_text: str
    unmapped_count: int
    mapping_table: Dict[str, str]


class SpeakerMapper:
    """说话人映射器"""
    
    # 说话人标识模式
    SPEAKER_ID_PATTERNS = [
        (r'【([^】]+)】', 'bracket_cn'),           # 【张三】
        (r'\[([^\]]+)\]', 'bracket_en'),           # [张三]
        (r'\*\*([^*]+)\*\*', 'bold'),              # **张三**
        (r'(Speaker\s*\d+)', 'speaker_num'),       # Speaker 1
        (r'(发言人[A-Z0-9]+)', 'speaker_cn'),      # 发言人A
        (r'^([A-Z])[：:]', 'single_letter'),       # A:
    ]
    
    # 自我介绍模式
    INTRO_PATTERNS = [
        r'大家好[，,]?\s*我是(.{2,8})',
        r'我是(.{2,8})[，,]',
        r'我叫(.{2,6})',
        r'(.{2,6})给大家(介绍|汇报)',
        r'这里是(.{2,8})[，,]',
    ]
    
    # 称呼模式
    REFERENCE_PATTERNS = [
        r'([张李王刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢唐许邓冯韩曹曾彭肖蒋蔡潘田董][^\s，。,\.]{0,3}(?:总|经理|老师|博士|教授|主任|部长|院长|董事))',
        r'请([^\s，。,\.]{2,6})(介绍|分享|汇报)',
        r'([^\s，。,\.]{2,6})(刚才|之前)(说|提到|讲)',
        r'感谢([^\s，。,\.]{2,6})的(分享|介绍|汇报)',
    ]
    
    def __init__(self):
        self._intro_patterns = [re.compile(p) for p in self.INTRO_PATTERNS]
        self._ref_patterns = [re.compile(p) for p in self.REFERENCE_PATTERNS]
    
    def extract_speaker_ids(self, text: str) -> List[str]:
        """提取所有说话人标识"""
        speaker_ids = set()
        
        for pattern, _ in self.SPEAKER_ID_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                speaker_ids.add(match.strip())
        
        return sorted(list(speaker_ids))
    
    def find_introductions(self, text: str) -> Dict[str, str]:
        """
        从自我介绍中提取说话人姓名
        
        返回: {speaker_id: name}
        """
        mappings = {}
        lines = text.split('\n')
        
        current_speaker = None
        for line in lines:
            # 检测当前说话人
            for pattern, _ in self.SPEAKER_ID_PATTERNS:
                match = re.match(pattern + r'[：:]?', line)
                if match:
                    current_speaker = match.group(1).strip()
                    break
            
            # 在当前说话人的发言中查找自我介绍
            if current_speaker:
                for pattern in self._intro_patterns:
                    match = pattern.search(line)
                    if match:
                        name = match.group(1).strip()
                        # 过滤无效名字
                        if self._is_valid_name(name):
                            mappings[current_speaker] = name
                            break
        
        return mappings
    
    def find_references(self, text: str, known_speakers: List[str]) -> Dict[str, str]:
        """
        从称呼中推断说话人身份
        
        这是辅助信息，置信度较低
        """
        references = {}
        
        for pattern in self._ref_patterns:
            matches = pattern.findall(text)
            for match in matches:
                name = match[0] if isinstance(match, tuple) else match
                name = name.strip()
                if self._is_valid_name(name):
                    # 尝试匹配到已知说话人
                    for speaker in known_speakers:
                        if speaker not in references:
                            references[speaker] = name
                            break
        
        return references
    
    def _is_valid_name(self, name: str) -> bool:
        """验证是否为有效姓名"""
        if not name or len(name) < 2 or len(name) > 8:
            return False
        
        # 排除常见非人名词汇
        invalid_words = [
            '大家', '我们', '你们', '他们', '这里', '那里',
            '今天', '明天', '昨天', '现在', '之后', '之前',
            '首先', '然后', '接下来', '最后', '另外',
        ]
        if name in invalid_words:
            return False
        
        # 检查是否包含中文
        if not re.search(r'[\u4e00-\u9fff]', name):
            return False
        
        return True
    
    def count_utterances(self, text: str, speaker_ids: List[str]) -> Dict[str, int]:
        """统计每个说话人的发言次数"""
        counts = {s: 0 for s in speaker_ids}
        
        for line in text.split('\n'):
            for speaker in speaker_ids:
                if speaker in line:
                    # 检查是否是说话人标记行
                    for pattern, _ in self.SPEAKER_ID_PATTERNS:
                        if re.match(f'{pattern}[：:]', line.replace(speaker, f'({speaker})')):
                            counts[speaker] = counts.get(speaker, 0) + 1
                            break
        
        return counts
    
    def map_speakers(
        self, 
        text: str, 
        hints: Optional[Dict[str, str]] = None,
        interactive: bool = False
    ) -> MappingResult:
        """
        执行说话人映射
        
        Args:
            text: 输入文本
            hints: 用户提供的映射提示 {speaker_id: name}
            interactive: 是否交互式确认
        
        Returns:
            MappingResult
        """
        # 1. 提取所有说话人标识
        speaker_ids = self.extract_speaker_ids(text)
        
        # 2. 初始化说话人信息
        speakers = {s: SpeakerInfo(original_id=s) for s in speaker_ids}
        
        # 3. 统计发言次数
        utterance_counts = self.count_utterances(text, speaker_ids)
        for speaker_id, count in utterance_counts.items():
            if speaker_id in speakers:
                speakers[speaker_id].utterance_count = count
        
        # 4. 从自我介绍中提取
        intro_mappings = self.find_introductions(text)
        for speaker_id, name in intro_mappings.items():
            if speaker_id in speakers:
                speakers[speaker_id].mapped_name = name
                speakers[speaker_id].confidence = 0.9
                speakers[speaker_id].source = "introduction"
        
        # 5. 从称呼中补充
        unmapped = [s for s in speaker_ids if speakers[s].mapped_name is None]
        ref_mappings = self.find_references(text, unmapped)
        for speaker_id, name in ref_mappings.items():
            if speaker_id in speakers and speakers[speaker_id].mapped_name is None:
                speakers[speaker_id].mapped_name = name
                speakers[speaker_id].confidence = 0.6
                speakers[speaker_id].source = "reference"
        
        # 6. 合并用户提示（最高优先级）
        if hints:
            for speaker_id, name in hints.items():
                if speaker_id in speakers:
                    speakers[speaker_id].mapped_name = name
                    speakers[speaker_id].confidence = 1.0
                    speakers[speaker_id].source = "user"
        
        # 7. 交互式确认（如果需要）
        if interactive:
            speakers = self._interactive_confirm(speakers)
        
        # 8. 构建映射表
        mapping_table = {}
        for speaker_id, info in speakers.items():
            if info.mapped_name:
                mapping_table[speaker_id] = info.mapped_name
            else:
                # 未映射的使用默认格式
                mapping_table[speaker_id] = f"发言人{speaker_id}"
        
        # 9. 应用映射
        mapped_text = self._apply_mapping(text, mapping_table)
        
        # 10. 统计未映射数量
        unmapped_count = sum(1 for s in speakers.values() if s.mapped_name is None)
        
        return MappingResult(
            speakers=list(speakers.values()),
            mapped_text=mapped_text,
            unmapped_count=unmapped_count,
            mapping_table=mapping_table
        )
    
    def _interactive_confirm(self, speakers: Dict[str, SpeakerInfo]) -> Dict[str, SpeakerInfo]:
        """交互式确认映射"""
        print("\n" + "="*50)
        print("说话人映射确认")
        print("="*50)
        
        for speaker_id, info in speakers.items():
            if info.mapped_name:
                print(f"\n{speaker_id} -> {info.mapped_name}")
                print(f"  来源: {info.source}, 置信度: {info.confidence:.0%}")
                print(f"  发言次数: {info.utterance_count}")
                confirm = input("  确认? [Y/n/修改名字]: ").strip()
                
                if confirm.lower() == 'n':
                    info.mapped_name = None
                    info.source = "rejected"
                elif confirm and confirm.lower() != 'y':
                    info.mapped_name = confirm
                    info.source = "user_edit"
                    info.confidence = 1.0
            else:
                print(f"\n{speaker_id} -> 未识别")
                print(f"  发言次数: {info.utterance_count}")
                name = input("  请输入姓名 (回车跳过): ").strip()
                
                if name:
                    info.mapped_name = name
                    info.source = "user_input"
                    info.confidence = 1.0
        
        return speakers
    
    def _apply_mapping(self, text: str, mapping: Dict[str, str]) -> str:
        """应用映射到文本"""
        result = text
        
        # 按长度降序排序，避免短字符串替换长字符串的一部分
        sorted_mappings = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
        
        for original, mapped in sorted_mappings:
            # 替换各种格式的说话人标记
            patterns = [
                (f'【{original}】', f'【{mapped}】'),
                (f'[{original}]', f'[{mapped}]'),
                (f'**{original}**', f'**{mapped}**'),
                (f'{original}:', f'{mapped}:'),
                (f'{original}：', f'{mapped}：'),
            ]
            for old, new in patterns:
                result = result.replace(old, new)
        
        return result
    
    def generate_mapping_report(self, result: MappingResult) -> str:
        """生成映射报告"""
        lines = [
            "# 说话人映射报告",
            "",
            "## 映射结果",
            "",
            "| 原始标识 | 映射姓名 | 来源 | 置信度 | 发言次数 |",
            "|---------|---------|------|--------|---------|",
        ]
        
        for speaker in sorted(result.speakers, key=lambda x: x.utterance_count, reverse=True):
            name = speaker.mapped_name or "(未映射)"
            lines.append(
                f"| {speaker.original_id} | {name} | "
                f"{speaker.source} | {speaker.confidence:.0%} | "
                f"{speaker.utterance_count} |"
            )
        
        lines.extend([
            "",
            "## 统计",
            "",
            f"- 总说话人数: {len(result.speakers)}",
            f"- 已映射: {len(result.speakers) - result.unmapped_count}",
            f"- 未映射: {result.unmapped_count}",
        ])
        
        return '\n'.join(lines)


def main():
    """命令行入口"""
    if len(sys.argv) < 3:
        print("用法: python speaker_mapper.py <input_file> <output_file> [--interactive]")
        print("示例: python speaker_mapper.py normalized-input.md mapped-output.md")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    interactive = '--interactive' in sys.argv
    
    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)
    
    # 读取输入
    print(f"读取文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 检查是否有用户提示文件
    hints = {}
    hints_file = input_file.parent / "speaker_hints.json"
    if hints_file.exists():
        with open(hints_file, 'r', encoding='utf-8') as f:
            hints = json.load(f)
        print(f"加载用户提示: {hints_file}")
    
    # 执行映射
    print("执行说话人映射...")
    mapper = SpeakerMapper()
    result = mapper.map_speakers(text, hints=hints, interactive=interactive)
    
    # 输出统计
    print("\n" + "="*50)
    print("映射统计:")
    print(f"  总说话人数: {len(result.speakers)}")
    print(f"  已映射: {len(result.speakers) - result.unmapped_count}")
    print(f"  未映射: {result.unmapped_count}")
    print()
    
    for speaker in result.speakers:
        status = "✅" if speaker.mapped_name else "❌"
        name = speaker.mapped_name or "(未识别)"
        print(f"  {status} {speaker.original_id} -> {name} [{speaker.source}]")
    
    print("="*50)
    
    # 保存映射后的文本
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result.mapped_text)
    print(f"\n映射后文本保存到: {output_file}")
    
    # 保存映射表
    mapping_file = output_file.parent / "speaker_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump({
            "mapping_table": result.mapping_table,
            "speakers": [asdict(s) for s in result.speakers]
        }, f, ensure_ascii=False, indent=2)
    print(f"映射表保存到: {mapping_file}")
    
    # 保存报告
    report_file = output_file.parent / "speaker_mapping_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(mapper.generate_mapping_report(result))
    print(f"映射报告保存到: {report_file}")


if __name__ == "__main__":
    main()
