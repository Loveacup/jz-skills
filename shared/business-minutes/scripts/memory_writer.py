# Provenance: adapted from voice-to-markdown-workflow v6.0 (jz-skills, recovered 2026-09-09). Stdlib only.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆持久化写入器
v5.0 新增 - 将处理结果写入持久化记忆

功能：
1. 读取工作目录中的处理结果（analysis.json 等）
2. 更新 speakers.json（新增/更新说话人信息）
3. 更新 projects.json（新增/更新项目信息）
4. 追加 sessions.json（新增会话记录）
5. 使用 write-then-rename 模式确保数据安全
"""

import re
import sys
import json
import argparse
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set


class MemoryWriter:
    """记忆持久化写入器"""

    def __init__(self, workspace_dir: Path, memory_dir: Path):
        self.workspace_dir = workspace_dir
        self.memory_dir = memory_dir
        self.analysis = {}
        self.quality_report = {}
        self.speaker_mapping = {}
        self.memory_context = {}

    def load_workspace(self):
        """加载工作目录中的处理结果"""
        # 必须存在
        self.analysis = self._load_json(self.workspace_dir / 'analysis.json')
        if not self.analysis:
            print("[memory_writer] 警告: analysis.json 不存在或为空", file=sys.stderr)

        # 可选文件
        self.quality_report = self._load_json(self.workspace_dir / 'quality-report.json')
        self.speaker_mapping = self._load_json(self.workspace_dir / 'speaker_mapping.json')
        self.memory_context = self._load_json(self.workspace_dir / 'memory-context.json')

    def _load_json(self, filepath: Path) -> dict:
        """安全加载 JSON 文件"""
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[memory_writer] JSON 解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def _load_memory_json(self, filename: str) -> dict:
        """加载记忆文件"""
        filepath = self.memory_dir / filename
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[memory_writer] 记忆文件解析错误: {filepath}: {e}", file=sys.stderr)
            return {}

    def _safe_write(self, filepath: Path, data: dict):
        """安全写入（write-then-rename）"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(filepath.parent),
                suffix='.tmp',
                prefix=filepath.stem + '_'
            )
            tmp_file = Path(tmp_path)
            with open(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')
            tmp_file.rename(filepath)
            print(f"[memory_writer] 已更新: {filepath}", file=sys.stderr)
        except OSError as e:
            print(f"[memory_writer] 写入失败: {filepath}: {e}", file=sys.stderr)
            # 清理临时文件
            if 'tmp_file' in locals() and tmp_file.exists():
                tmp_file.unlink()

    def update_speakers(self):
        """更新 speakers.json"""
        speakers_file = self._load_memory_json('speakers.json')
        speakers = speakers_file.get('speakers', {})

        now = datetime.now().isoformat(timespec='seconds')

        # 从 analysis.json 获取说话人列表
        analysis_speakers = self.analysis.get('speakers', [])
        if isinstance(analysis_speakers, dict):
            # 兼容 dict 格式
            speaker_list = []
            for name, info in analysis_speakers.items():
                entry = {'name': name}
                if isinstance(info, dict):
                    entry.update(info)
                speaker_list.append(entry)
            analysis_speakers = speaker_list

        # 从 speaker_mapping.json 获取映射信息
        mapping_speakers = self.speaker_mapping.get('speakers', [])
        mapping_table = self.speaker_mapping.get('mapping_table', {})

        # 收集本次会话的所有说话人名称
        session_speaker_names = set()

        for speaker in analysis_speakers:
            name = speaker.get('name', speaker.get('mapped_name', ''))
            if not name or name.startswith('Speaker') or name.startswith('发言人'):
                continue

            session_speaker_names.add(name)

            if name in speakers:
                # 已存在，更新
                existing = speakers[name]
                existing['last_seen'] = now
                existing['session_count'] = existing.get('session_count', 0) + 1

                # 合并角色
                new_roles = speaker.get('roles', [])
                if isinstance(new_roles, str):
                    new_roles = [new_roles]
                existing_roles = set(existing.get('roles', []))
                existing_roles.update(new_roles)
                existing['roles'] = sorted(existing_roles)

                # 合并组织
                new_orgs = speaker.get('organizations', [])
                if isinstance(new_orgs, str):
                    new_orgs = [new_orgs]
                existing_orgs = set(existing.get('organizations', []))
                existing_orgs.update(new_orgs)
                existing['organizations'] = sorted(existing_orgs)

                # 合并话题
                new_topics = speaker.get('typical_topics', [])
                existing_topics = set(existing.get('typical_topics', []))
                existing_topics.update(new_topics)
                # 保留最近 20 个话题
                existing['typical_topics'] = sorted(existing_topics)[-20:]

            else:
                # 新说话人
                role = speaker.get('role', '')
                roles = speaker.get('roles', [role] if role else [])
                if isinstance(roles, str):
                    roles = [roles]

                org = speaker.get('organization', '')
                organizations = speaker.get('organizations', [org] if org else [])
                if isinstance(organizations, str):
                    organizations = [organizations]

                speakers[name] = {
                    'roles': [r for r in roles if r],
                    'organizations': [o for o in organizations if o],
                    'aliases': [],
                    'first_seen': now,
                    'last_seen': now,
                    'session_count': 1,
                    'typical_topics': speaker.get('typical_topics', []),
                    'co_speakers': [],
                }

        # 更新别名映射（从 mapping_table）
        for original_id, mapped_name in mapping_table.items():
            if mapped_name in speakers:
                aliases = set(speakers[mapped_name].get('aliases', []))
                if original_id != mapped_name:
                    aliases.add(original_id)
                speakers[mapped_name]['aliases'] = sorted(aliases)

        # 更新 co_speakers
        speaker_names_list = sorted(session_speaker_names)
        for name in speaker_names_list:
            if name in speakers:
                co = set(speakers[name].get('co_speakers', []))
                co.update(speaker_names_list)
                co.discard(name)
                speakers[name]['co_speakers'] = sorted(co)

        count_new = len(session_speaker_names - set(speakers_file.get('speakers', {}).keys()))
        count_updated = len(session_speaker_names) - count_new
        print(f"[memory_writer] 说话人: 新增 {count_new}, 更新 {count_updated}", file=sys.stderr)

        speakers_file['speakers'] = speakers
        self._safe_write(self.memory_dir / 'speakers.json', speakers_file)

    def update_projects(self):
        """更新 projects.json"""
        projects_file = self._load_memory_json('projects.json')
        projects = projects_file.get('projects', {})

        now = datetime.now().isoformat(timespec='seconds')

        # 从 analysis.json 提取话题/项目关键词
        content_sections = self.analysis.get('content_sections', [])
        topics = set()

        for section in content_sections:
            title = section.get('title', '')
            if title:
                topics.add(title)
            section_topics = section.get('topics', [])
            topics.update(section_topics)

        # 也从 analysis.json 顶层的 topics/key_topics 提取
        top_topics = self.analysis.get('topics', self.analysis.get('key_topics', []))
        if isinstance(top_topics, list):
            topics.update(top_topics)

        if not topics:
            print("[memory_writer] 未发现项目/话题关键词，跳过项目更新", file=sys.stderr)
            return

        # 收集说话人（关联到项目）
        speakers_in_session = []
        for s in self.analysis.get('speakers', []):
            name = s.get('name', s.get('mapped_name', ''))
            if name and not name.startswith('Speaker') and not name.startswith('发言人'):
                speakers_in_session.append(name)

        matched_count = 0
        new_count = 0

        for topic in topics:
            if not topic or len(topic) < 2:
                continue

            # 查找是否匹配已有项目
            matched_project = None
            for project_name, project_info in projects.items():
                aliases = set(project_info.get('aliases', []))
                all_names = {project_name} | aliases
                if topic in all_names:
                    matched_project = project_name
                    break

            if matched_project:
                # 更新已有项目
                proj = projects[matched_project]
                proj['last_mentioned'] = now
                proj['mention_count'] = proj.get('mention_count', 0) + 1

                # 合并关键人物
                existing_people = set(proj.get('key_people', []))
                existing_people.update(speakers_in_session)
                proj['key_people'] = sorted(existing_people)

                matched_count += 1
            else:
                # 检查是否值得新建项目（至少3个字，且不是纯动词/形容词）
                if len(topic) >= 3 and not self._is_generic_topic(topic):
                    projects[topic] = {
                        'aliases': [],
                        'status': 'active',
                        'key_people': speakers_in_session,
                        'related_notes': [],
                        'keywords': [],
                        'first_mentioned': now,
                        'last_mentioned': now,
                        'mention_count': 1,
                    }
                    new_count += 1

        print(f"[memory_writer] 项目: 匹配 {matched_count}, 新增 {new_count}", file=sys.stderr)

        projects_file['projects'] = projects
        self._safe_write(self.memory_dir / 'projects.json', projects_file)

    def _is_generic_topic(self, topic: str) -> bool:
        """判断是否为过于通用的话题（不值得单独建项目）"""
        generic = {
            '讨论', '总结', '汇报', '介绍', '分享', '开场', '结束',
            '背景', '概述', '进展', '更新', '其他', '备注', '补充',
            '后续', '待办', '决议', '问答', '讨论环节', '自由讨论',
        }
        return topic in generic

    def append_session(self):
        """追加会话到 sessions.json"""
        sessions_file = self._load_memory_json('sessions.json')
        sessions = sessions_file.get('sessions', [])
        max_sessions = sessions_file.get('max_sessions', 50)

        now = datetime.now().isoformat(timespec='seconds')

        # 生成新 ID
        existing_ids = [s.get('id', '') for s in sessions]
        max_num = 0
        for sid in existing_ids:
            if sid.startswith('S') and sid[1:].isdigit():
                max_num = max(max_num, int(sid[1:]))
        new_id = f'S{max_num + 1:03d}'

        # 提取说话人
        speakers = []
        for s in self.analysis.get('speakers', []):
            name = s.get('name', s.get('mapped_name', ''))
            if name:
                speakers.append(name)

        # 提取话题
        topics = self.analysis.get('topics', self.analysis.get('key_topics', []))
        if not isinstance(topics, list):
            topics = []

        # 场景类型
        scene_type = self.analysis.get('scene_type', 'unknown')
        meeting_subtype = self.analysis.get('meeting_subtype', '')

        # 质量评分
        quality_score = ''
        if self.quality_report:
            quality_score = self.quality_report.get('grade', self.quality_report.get('overall_grade', ''))

        new_session = {
            'id': new_id,
            'timestamp': now,
            'scene_type': scene_type,
            'meeting_subtype': meeting_subtype,
            'speakers': speakers,
            'topics': topics[:10],  # 限制话题数量
            'quality_score': quality_score,
            'analyzed': False,
        }

        sessions.append(new_session)

        # 超过最大数量时，删除最早的记录
        if len(sessions) > max_sessions:
            sessions = sessions[-max_sessions:]
            print(f"[memory_writer] 会话记录超过上限 {max_sessions}，已裁剪", file=sys.stderr)

        print(f"[memory_writer] 新增会话: {new_id} ({scene_type})", file=sys.stderr)

        sessions_file['sessions'] = sessions
        self._safe_write(self.memory_dir / 'sessions.json', sessions_file)

    def run(self):
        """执行全部更新"""
        print("[memory_writer] 开始更新记忆...", file=sys.stderr)
        self.load_workspace()

        if not self.analysis:
            print("[memory_writer] analysis.json 为空，跳过记忆更新", file=sys.stderr)
            return

        self.update_speakers()
        self.update_projects()
        self.append_session()

        print("[memory_writer] 记忆更新完成", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='记忆持久化写入器 - 将处理结果写入持久化记忆'
    )
    parser.add_argument(
        'workspace_dir',
        help='工作目录路径（如 /tmp/vtm-workspace/）'
    )
    parser.add_argument(
        'memory_dir',
        help='记忆目录路径（如 ~/.claude/skills/voice-to-markdown-workflow/memory/）'
    )
    return parser.parse_args()


def main():
    """命令行入口"""
    args = parse_args()

    workspace_dir = Path(args.workspace_dir)
    memory_dir = Path(args.memory_dir).expanduser()

    if not workspace_dir.exists():
        print(f"[memory_writer] 错误: 工作目录不存在: {workspace_dir}", file=sys.stderr)
        sys.exit(1)

    if not memory_dir.exists():
        print(f"[memory_writer] 错误: 记忆目录不存在: {memory_dir}", file=sys.stderr)
        sys.exit(1)

    writer = MemoryWriter(workspace_dir, memory_dir)
    writer.run()


if __name__ == '__main__':
    main()
