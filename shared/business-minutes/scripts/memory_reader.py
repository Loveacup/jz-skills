# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆上下文读取器
v5.0 新增 - 从持久化记忆中匹配与当前输入相关的上下文

功能：
1. 读取 memory/ 下所有 JSON 文件
2. 根据输入文本匹配相关说话人（名称、别名）
3. 根据输入文本关键词匹配相关项目
4. 筛选活跃模式和最近会话
5. 输出 memory-context.json 供后续处理使用
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Set, Tuple


class MemoryReader:
    """记忆上下文读取器"""

    # 说话人标识模式（与 speaker_mapper.py 一致）
    SPEAKER_PATTERNS = [
        re.compile(r'\*\*([^*]+)\*\*\s*[:：]'),       # **张三**:
        re.compile(r'【([^】]+)】\s*[:：]?'),           # 【张三】
        re.compile(r'\[([^\]]+)\]\s*[:：]'),            # [张三]:
        re.compile(r'(Speaker\s*\d+)\s*[:：]'),        # Speaker 0:
        re.compile(r'(发言人[A-Z0-9]+)\s*[:：]'),       # 发言人A:
        re.compile(r'^([A-Z])\s*[:：]', re.MULTILINE),  # A:
    ]

    # 中文关键词提取模式（2-4字）
    KEYWORD_PATTERN = re.compile(r'[\u4e00-\u9fff]{2,4}')

    # 常见停用词
    STOPWORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
        '没有', '看', '好', '自己', '这', '那', '里', '后', '以', '所',
        '如果', '可以', '因为', '所以', '但是', '而且', '或者', '还是',
        '已经', '正在', '可能', '应该', '需要', '能够', '这个', '那个',
        '什么', '怎么', '哪个', '为什么', '大家', '我们', '你们', '他们',
        '今天', '明天', '昨天', '现在', '然后', '其实', '觉得', '知道',
        '时候', '问题', '工作', '情况', '方面', '进行', '开始', '通过',
        '关于', '对于', '之后', '之前', '比较', '这样', '那样', '一下',
        '一些', '一起', '一直', '不是', '没有', '还有', '这里', '那里',
    }

    DEFAULT_DECAY_RATE = 0.995

    def __init__(self, memory_dir: Path, max_recent_sessions: int = 5):
        self.memory_dir = memory_dir
        self.max_recent_sessions = max_recent_sessions
        self.speakers_data = {}
        self.projects_data = {}
        self.patterns_data = []
        self.sessions_data = []
        self.preferences_data = {}

    def load_memory(self):
        """加载所有记忆文件"""
        self.speakers_data = self._load_json('speakers.json').get('speakers', {})
        self.projects_data = self._load_json('projects.json').get('projects', {})
        self.patterns_data = self._load_json('patterns.json').get('patterns', [])
        sessions_file = self._load_json('sessions.json')
        self.sessions_data = sessions_file.get('sessions', [])
        self.preferences_data = self._load_json('preferences.json')

    def _load_json(self, filename: str) -> dict:
        """安全加载 JSON 文件"""
        filepath = self.memory_dir / filename
        if not filepath.exists():
            print(f"[memory_reader] 记忆文件不存在，使用空数据: {filepath}", file=sys.stderr)
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[memory_reader] JSON 解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def extract_speakers_from_text(self, text: str) -> Set[str]:
        """从输入文本提取所有说话人标记"""
        speakers = set()
        for pattern in self.SPEAKER_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                name = match.strip()
                if name:
                    speakers.add(name)
        return speakers

    def extract_keywords_from_text(self, text: str) -> List[str]:
        """从输入文本提取关键词（2-4字中文词组）"""
        from collections import Counter

        matches = self.KEYWORD_PATTERN.findall(text)
        # 过滤停用词
        keywords = [w for w in matches if w not in self.STOPWORDS]
        # 统计频率，返回高频词
        counter = Counter(keywords)
        # 取出现2次以上的词，或前30个高频词
        result = [word for word, count in counter.most_common(50) if count >= 2]
        if len(result) < 10:
            result = [word for word, _ in counter.most_common(30)]
        return result

    def match_speakers(self, text_speakers: Set[str]) -> Dict[str, dict]:
        """根据输入文本中的说话人匹配记忆中的说话人"""
        matched = {}
        today = date.today()

        for speaker_name, speaker_info in self.speakers_data.items():
            aliases = speaker_info.get('aliases', [])
            all_names = {speaker_name} | set(aliases)

            # 检查输入文本中是否有匹配
            if text_speakers & all_names:
                confidence = self._calculate_speaker_confidence(speaker_info, today)
                matched[speaker_name] = {
                    'roles': speaker_info.get('roles', []),
                    'organizations': speaker_info.get('organizations', []),
                    'aliases': aliases,
                    'session_count': speaker_info.get('session_count', 0),
                    'confidence': round(confidence, 3),
                    'co_speakers': speaker_info.get('co_speakers', []),
                }

        return matched

    def _calculate_speaker_confidence(self, speaker_info: dict, today: date) -> float:
        """计算说话人置信度（贝叶斯平滑 + 时间衰减）"""
        session_count = speaker_info.get('session_count', 0)
        base_confidence = session_count / (session_count + 3)

        last_seen_str = speaker_info.get('last_seen', '')
        if last_seen_str:
            try:
                last_seen = datetime.fromisoformat(last_seen_str).date()
                days_since_last = (today - last_seen).days
            except (ValueError, TypeError):
                days_since_last = 30
        else:
            days_since_last = 30

        confidence = base_confidence * (self.DEFAULT_DECAY_RATE ** days_since_last)
        return confidence

    def match_projects(self, keywords: List[str]) -> Dict[str, dict]:
        """根据关键词匹配记忆中的项目"""
        matched = {}
        keyword_set = set(keywords)

        for project_name, project_info in self.projects_data.items():
            aliases = project_info.get('aliases', [])
            all_names = {project_name} | set(aliases)
            project_keywords = set(project_info.get('keywords', []))

            # 项目名或别名出现在关键词中
            name_match = bool(all_names & keyword_set)

            # 项目关键词与输入关键词有交集
            keyword_match = bool(project_keywords & keyword_set)

            if name_match or keyword_match:
                matched[project_name] = {
                    'aliases': aliases,
                    'status': project_info.get('status', 'unknown'),
                    'key_people': project_info.get('key_people', []),
                    'related_notes': project_info.get('related_notes', []),
                }

        return matched

    def get_active_patterns(self) -> List[dict]:
        """筛选 status==active 的模式"""
        active = []
        for pattern in self.patterns_data:
            if pattern.get('status') == 'active':
                active.append({
                    'id': pattern.get('id', ''),
                    'type': pattern.get('type', ''),
                    'rule': pattern.get('rule', ''),
                    'confidence': pattern.get('confidence', 0.0),
                })
        return active

    def get_recent_sessions(self) -> List[dict]:
        """获取最近 N 条会话"""
        # 按 timestamp 降序排列
        sorted_sessions = sorted(
            self.sessions_data,
            key=lambda s: s.get('timestamp', ''),
            reverse=True
        )
        recent = sorted_sessions[:self.max_recent_sessions]

        result = []
        for session in recent:
            result.append({
                'id': session.get('id', ''),
                'timestamp': session.get('timestamp', ''),
                'scene_type': session.get('scene_type', ''),
                'speakers': session.get('speakers', []),
                'topics': session.get('topics', []),
            })
        return result

    def get_user_preferences(self) -> dict:
        """读取用户偏好"""
        prefs = self.preferences_data.get('output_preferences', {})
        return {
            'default_mode': prefs.get('default_mode', 'standard'),
            'preferred_format': prefs.get('preferred_format', 'obsidian'),
            'wikilink_style': prefs.get('wikilink_style', 'short'),
        }

    def build_context(self, input_text: str) -> dict:
        """构建完整的记忆上下文"""
        # 提取说话人
        text_speakers = self.extract_speakers_from_text(input_text)
        print(f"[memory_reader] 从输入文本中提取到 {len(text_speakers)} 个说话人标记", file=sys.stderr)

        # 提取关键词
        keywords = self.extract_keywords_from_text(input_text)
        print(f"[memory_reader] 提取到 {len(keywords)} 个关键词", file=sys.stderr)

        # 匹配说话人
        known_speakers = self.match_speakers(text_speakers)
        print(f"[memory_reader] 匹配到 {len(known_speakers)} 个已知说话人", file=sys.stderr)

        # 匹配项目
        known_projects = self.match_projects(keywords)
        print(f"[memory_reader] 匹配到 {len(known_projects)} 个已知项目", file=sys.stderr)

        # 获取活跃模式
        active_patterns = self.get_active_patterns()
        print(f"[memory_reader] 找到 {len(active_patterns)} 个活跃模式", file=sys.stderr)

        # 获取最近会话
        recent_sessions = self.get_recent_sessions()
        print(f"[memory_reader] 加载最近 {len(recent_sessions)} 条会话", file=sys.stderr)

        # 获取用户偏好
        user_preferences = self.get_user_preferences()

        return {
            'known_speakers': known_speakers,
            'known_projects': known_projects,
            'active_patterns': active_patterns,
            'recent_sessions': recent_sessions,
            'user_preferences': user_preferences,
        }


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='记忆上下文读取器 - 从持久化记忆中匹配与当前输入相关的上下文'
    )
    parser.add_argument(
        'input_file',
        help='输入文件路径（如 normalized-input.md）'
    )
    parser.add_argument(
        'output_file',
        help='输出文件路径（如 memory-context.json）'
    )
    parser.add_argument(
        '--memory-dir',
        default=None,
        help='记忆目录路径（默认: 脚本所在目录的 ../memory/）'
    )
    parser.add_argument(
        '--max-recent-sessions',
        type=int,
        default=5,
        help='最近会话数量（默认: 5）'
    )
    return parser.parse_args()


def main():
    """命令行入口"""
    args = parse_args()

    input_file = Path(args.input_file)
    output_file = Path(args.output_file)

    if not input_file.exists():
        print(f"[memory_reader] 错误: 输入文件不存在: {input_file}", file=sys.stderr)
        sys.exit(1)

    # 确定记忆目录
    if args.memory_dir:
        memory_dir = Path(args.memory_dir)
    else:
        memory_dir = Path(__file__).resolve().parent.parent / 'memory'

    if not memory_dir.exists():
        print(f"[memory_reader] 警告: 记忆目录不存在: {memory_dir}", file=sys.stderr)
        # 输出空上下文
        context = {
            'known_speakers': {},
            'known_projects': {},
            'active_patterns': [],
            'recent_sessions': [],
            'user_preferences': {
                'default_mode': 'standard',
                'preferred_format': 'obsidian',
                'wikilink_style': 'short',
            },
        }
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
        print(f"[memory_reader] 空上下文已保存到: {output_file}", file=sys.stderr)
        sys.exit(0)

    print(f"[memory_reader] 记忆目录: {memory_dir}", file=sys.stderr)
    print(f"[memory_reader] 输入文件: {input_file}", file=sys.stderr)

    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()

    print(f"[memory_reader] 输入文本长度: {len(input_text)} 字符", file=sys.stderr)

    # 构建上下文
    reader = MemoryReader(
        memory_dir=memory_dir,
        max_recent_sessions=args.max_recent_sessions
    )
    reader.load_memory()
    context = reader.build_context(input_text)

    # 保存输出
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    print(f"[memory_reader] 记忆上下文已保存到: {output_file}", file=sys.stderr)

    # 输出摘要
    total_matched = len(context['known_speakers']) + len(context['known_projects'])
    print(f"[memory_reader] 总匹配: {total_matched} (说话人 {len(context['known_speakers'])}, "
          f"项目 {len(context['known_projects'])})", file=sys.stderr)


if __name__ == '__main__':
    main()
