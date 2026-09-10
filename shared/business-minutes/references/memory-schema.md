# Memory Schema Reference

v6.0 记忆系统 JSON Schema 参考文档。

---

## speakers.json

说话人记忆库，跨会话积累说话人身份信息。

### Schema

```json
{
  "version": "1.0",
  "speakers": {
    "<speaker_name>": {
      "roles": ["string"],
      "organizations": ["string"],
      "aliases": ["string"],
      "first_seen": "YYYY-MM-DD",
      "last_seen": "YYYY-MM-DD",
      "session_count": 0,
      "co_speakers": ["string"],
      "typical_topics": ["string"]
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `roles` | string[] | 是 | 角色列表，如 "产品经理"、"CTO" |
| `organizations` | string[] | 是 | 所属组织，如 "研发部"、"ABC公司" |
| `aliases` | string[] | 是 | 别名列表，包括转录中的标记如 "Speaker 0"、"发言人1" |
| `first_seen` | string | 是 | 首次出现日期，格式 YYYY-MM-DD |
| `last_seen` | string | 是 | 最后出现日期，格式 YYYY-MM-DD |
| `session_count` | number | 是 | 累计出现会话数 |
| `co_speakers` | string[] | 是 | 经常一起出现的说话人名称 |
| `typical_topics` | string[] | 是 | 典型讨论话题 |

---

## projects.json

项目记忆库，追踪转录中反复出现的项目/产品。

### Schema

```json
{
  "version": "1.0",
  "projects": {
    "<project_name>": {
      "aliases": ["string"],
      "status": "active|completed|paused",
      "key_people": ["string"],
      "related_notes": ["string"],
      "last_mentioned": "YYYY-MM-DD",
      "mention_count": 0
    }
  }
}
```

---

## patterns.json

模式库，存储从多次会话中结晶出的可复用规则。

### Schema

```json
{
  "version": "1.0",
  "patterns": [
    {
      "id": "P001",
      "type": "speaker_mapping|meeting_structure|quality_optimization|topic_classification|asr_correction",
      "rule": "string",
      "confidence": 0.0,
      "occurrences": 0,
      "first_seen": "YYYY-MM-DD",
      "last_applied": "YYYY-MM-DD",
      "status": "active|candidate|deprecated|stale"
    }
  ]
}
```

### v6.0 新增

- type 新增 `asr_correction`（ASR纠错模式）
- status 新增 `stale`（30天未应用，不删除但不主动注入）

---

## sessions.json

会话记录，记录每次处理的元数据用于模式分析。

### Schema

```json
{
  "version": "1.0",
  "sessions": [
    {
      "id": "S001",
      "timestamp": "ISO8601",
      "scene_type": "string",
      "meeting_subtype": "string|null",
      "speakers": ["string"],
      "topics": ["string"],
      "quality_score": "A|B|C|D",
      "output_files": ["string"],
      "user_feedback": "string|null",
      "patterns_applied": ["string"],
      "analyzed": false,
      "metadata": {}
    }
  ],
  "max_sessions": 50
}
```

### 会话轮转

当 `sessions` 数组长度超过 `max_sessions` 时，移除最早的会话记录（FIFO）。被移除的会话若尚未分析（`analyzed: false`），应先触发 pattern_analyzer 分析。

---

## corrections.json (v6.0 新增)

ASR纠错日志，记录每次纠错及其出现频率，用于模式结晶。

### Schema

```json
{
  "version": "1.0",
  "corrections": [
    {
      "wrong": "string",
      "correct": "string",
      "type": "speaker_name|product_name|term|organization",
      "occurrences": 0,
      "first_seen": "YYYY-MM-DD",
      "last_seen": "YYYY-MM-DD",
      "crystallized": false
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `wrong` | string | 是 | ASR 错误文本 |
| `correct` | string | 是 | 正确文本 |
| `type` | enum | 是 | 纠错类型：`speaker_name`(人名) / `product_name`(产品名) / `term`(术语) / `organization`(组织名) |
| `occurrences` | number | 是 | 累计出现次数 |
| `first_seen` | string | 是 | 首次发现日期 |
| `last_seen` | string | 是 | 最后出现日期 |
| `crystallized` | boolean | 是 | 是否已结晶（写入 rule_based_cleaner.py） |

### 结晶规则

- `occurrences` ≥ 3 且 `crystallized` == false → 触发结晶
- 结晶 = 将 `wrong` → `correct` 映射写入 `scripts/rule_based_cleaner.py` 的纠错字典
- 结晶后设置 `crystallized` = true
- 结晶后的纠错零 token 消耗，Python 脚本自动替换

---

## metrics.json (v6.0 新增)

Foundry 式工作流执行指标，用于追踪每次执行的质量和效率。

### Schema

```json
{
  "version": "1.0",
  "sessions": [
    {
      "session_id": "S001",
      "date": "YYYY-MM-DD",
      "mode": "fast|standard|deep",
      "duration_minutes": null,
      "agent_count": 0,
      "user_corrections": 0,
      "verification_intercepts": 0,
      "asr_corrections": 0,
      "quality_score": "A|B|C|D",
      "notes": "string|null"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `session_id` | string | 是 | 对应 sessions.json 中的 ID |
| `date` | string | 是 | 执行日期 |
| `mode` | enum | 是 | 执行模式 |
| `duration_minutes` | number/null | 否 | 总耗时（分钟） |
| `agent_count` | number | 是 | 启动的 agent 数量 |
| `user_corrections` | number | 是 | 用户事后修正次数（0=成功，≥3=需学习） |
| `verification_intercepts` | number | 是 | Phase 5 验证关卡拦截的不一致数 |
| `asr_corrections` | number | 是 | ASR 纠错数 |
| `quality_score` | enum | 是 | 质量评分 |
| `notes` | string/null | 否 | 备注 |

### 质量追踪

- `user_corrections` == 0 → 执行成功，无需学习
- `user_corrections` ≥ 3 → 需要分析失败原因，触发模式学习

---

## voiceprints.json (v6.1 新增)

声纹嵌入向量库，由 `audio-transcriber` skill 注册写入，本 skill 只读。

用途：Phase 1 记忆注入时，若 voiceprints.json 存在已注册声纹，将声纹对应的说话人标记为"声纹已验证"（confidence=1.0），跳过 Phase 5 的说话人确认环节。

### Schema

```json
[
  {
    "name": "string",
    "embedding": [0.0],
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
]
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 说话人姓名，与 speakers.json 中的 key 对应 |
| `embedding` | number[] | 是 | 256 维声纹嵌入向量（wespeaker-voxceleb-resnet34） |
| `created_at` | string | 是 | 首次注册时间 |
| `updated_at` | string | 否 | 最后更新时间 |

### 与 speakers.json 的关系

- `voiceprints.json` 存储声纹向量（audio-transcriber 用于转录时自动匹配说话人）
- `speakers.json` 存储说话人元信息（角色、组织、别名、话题等）
- 两者通过 `name` 字段关联
- `audio-transcriber register` 命令同时写入两个文件

### 在本 skill 中的使用方式

**Phase 1（读取已知声纹）**：读取 voiceprints.json 中已注册的姓名列表（不需要读向量），与转录文本中的说话人标签交叉比对：
- 转录中出现 "蔡总" 且 voiceprints.json 中有 "蔡总" → known-facts.json 中标记 confidence=1.0（声纹验证）
- 转录中出现 "Speaker 1" 但 audio-transcriber 未能匹配 → 保持正常流程，Phase 5 询问用户

**Phase 5（注册未知声纹，v6.2 新增）**：当转录文件旁存在 `*-speaker-embeddings.json` sidecar 文件时：
1. 读取 sidecar，获取未匹配说话人的嵌入向量
2. 通过 AskUserQuestion 询问 "Speaker N 是谁？"
3. 用户回答后，将嵌入向量追加到 voiceprints.json（格式同上述 Schema）
4. 同步更新 speakers.json（新增说话人条目，或更新已有条目的 last_seen/session_count）
5. 替换 preprocessed.md 中所有 "Speaker N" 为用户确认的真实姓名
6. 删除已处理的 sidecar 文件

### speaker-embeddings.json sidecar 格式

由 audio-transcriber 转录时自动生成，存放在转录输出文件旁：

```json
{
  "version": "1.0",
  "source": "transcript.md",
  "unknown_speakers": {
    "Speaker 1": {
      "embedding": [0.0, ...]
    },
    "Speaker 2": {
      "embedding": [0.0, ...]
    }
  }
}
```

- 文件命名: `<transcript_name>-speaker-embeddings.json`
- 仅包含**未匹配**声纹库的说话人（已匹配的不会出现在此文件中）
- embedding 为 256 维归一化向量（与 voiceprints.json 格式一致）
- 处理完毕后由 Phase 5 删除，避免残留

---

## preferences.json

用户偏好设置，记录用户的自定义配置和修正历史。

### Schema

```json
{
  "version": "1.0",
  "output_preferences": {
    "default_mode": "fast|standard|deep",
    "preferred_format": "obsidian|standard_markdown",
    "wikilink_style": "short|long"
  },
  "output": {
    "file_count": "single|layered",
    "include_deep_analysis": true,
    "include_action_items": true,
    "include_decision_log": true,
    "obsidian_format": true
  },
  "correction_history": [
    {
      "timestamp": "ISO8601",
      "type": "speaker_name|term|format|structure",
      "original": "string",
      "corrected": "string",
      "context": "string"
    }
  ],
  "custom_templates": {}
}
```

### v6.0 新增字段

`output` 对象：记录用户的输出偏好，在下次执行时自动应用。

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_count` | enum | `single`(默认单文件) / `layered`(分层输出) |
| `include_deep_analysis` | boolean | 是否包含深度分析章节 |
| `include_action_items` | boolean | 是否包含行动项 |
| `include_decision_log` | boolean | 是否包含决策日志 |
| `obsidian_format` | boolean | 是否使用 Obsidian 格式 |

---

## known-facts.json (v6.0 新增，Phase 1 输出)

每次执行时由主Claude生成，注入所有 agent 的 prompt 头部。**不持久化存储**，仅在 `/tmp/vtm-workspace/` 中生存。

### Schema

```json
{
  "session_context": {
    "date": "YYYY-MM-DD",
    "user": "用户名(称呼)",
    "user_role": "用户角色描述"
  },
  "verified_speakers": [
    {
      "name": "string",
      "role": "string",
      "aliases": ["string"],
      "confidence": 0.0
    }
  ],
  "verified_products": [
    {
      "name": "string",
      "type": "string",
      "common_asr_errors": ["string"]
    }
  ],
  "active_project": {
    "name": "string",
    "key_products": ["string"],
    "recent_context": "string"
  },
  "crystallized_corrections": {
    "<wrong>": "<correct>"
  }
}
```

### 生成逻辑（Phase 1 主Claude执行）

1. 读取 speakers.json → 提取 confidence > 0.8 的说话人填入 `verified_speakers`
2. 读取 corrections.json → 提取所有已知纠错填入 `verified_products` 的 `common_asr_errors`
3. 读取 corrections.json → crystallized == true 的填入 `crystallized_corrections`
4. 读取 projects.json → 匹配当前会话的项目填入 `active_project`

### 注入方式

在每个 agent prompt 头部加入：
```
## 已验证事实（来自记忆系统，必须遵守）
[known-facts.json 内容]

⚠️ 你必须使用上述已验证的人名、产品名、公司名。
如果转录文本中出现与上述不一致的名称，以已验证事实为准。
```

---

## verified-facts.json (v6.0 新增，Phase 5 输出)

Phase 5 验证关卡输出，记录用户确认后的实体信息。**不持久化存储**，仅在 `/tmp/vtm-workspace/` 中生存。

### Schema

```json
{
  "timestamp": "ISO8601",
  "entities_checked": 0,
  "entities_confirmed": 0,
  "entities_corrected": 0,
  "entities_new": 0,
  "corrections": [
    {
      "original": "string",
      "corrected": "string",
      "type": "speaker_name|product_name|term|organization",
      "source": "memory_mismatch|user_correction|new_entity"
    }
  ],
  "confirmed_entities": [
    {
      "name": "string",
      "type": "person|company|product",
      "role": "string|null"
    }
  ]
}
```

### 生成逻辑（Phase 5 主Claude执行）

1. 从 preprocessed.md 提取所有实体（NER + 正则）
2. 与 known-facts.json 比对
3. 不一致处通过 AskUserQuestion 确认
4. 确认结果写入 verified-facts.json
5. 如有修正，更新 preprocessed.md

---

## manifest.json (v6.0 新增，Phase 0 输出)

资料清点结果，记录所有输入材料的类型和预处理状态。**不持久化存储**，仅在 `/tmp/vtm-workspace/` 中生存。

### Schema

```json
{
  "primary": {
    "type": "transcript|lecture|interview",
    "path": "string",
    "chars": 0,
    "lines": 0,
    "speakers_detected": ["string"]
  },
  "references": [
    {
      "type": "ppt|image|prototype_url|document_url|pdf|docx",
      "path": "string|null",
      "url": "string|null",
      "processed_path": "string",
      "topic_association": "string"
    }
  ],
  "user_metadata": {
    "date": "YYYY-MM-DD",
    "mode": "fast|standard|deep",
    "participants": ["string"],
    "output_directory": "string",
    "output_filename": "string|null"
  }
}
```

### 生成逻辑（Phase 0 主Claude执行）

1. 扫描用户提供的所有文件路径和 URL
2. 按类型识别和分类
3. 执行预处理：
   - PPT/PPTX → pptx-converter 转 markdown
   - 图片 → mcp__vision__ocr_image 提取文字
   - URL(原型) → Playwright 抓取页面结构
   - URL(文档) → WebFetch 提取内容
   - PDF → Read 工具读取
4. 输出 manifest.json
