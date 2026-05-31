# Memory Schema Reference

v3.0 记忆系统 JSON Schema 参考文档。

---

## topics.json

主题记忆库，跨会话积累分析过的主题信息。

### Schema

```json
{
  "version": "1.0",
  "topics": {
    "<topic_name>": {
      "analysis_type": "phenomenon|industry|enterprise|trend|comparison|exploratory",
      "keywords": ["string"],
      "first_analyzed": "YYYY-MM-DD",
      "last_analyzed": "YYYY-MM-DD",
      "analysis_count": 0,
      "avg_quality_score": 0.0,
      "key_insights": ["string"],
      "related_topics": ["string"],
      "frameworks_used": ["string"],
      "mode_used": "fast|standard|deep"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `analysis_type` | enum | 是 | 分析类型 |
| `keywords` | string[] | 是 | 主题关键词列表 |
| `first_analyzed` | string | 是 | 首次分析日期，格式 YYYY-MM-DD |
| `last_analyzed` | string | 是 | 最后分析日期，格式 YYYY-MM-DD |
| `analysis_count` | number | 是 | 累计分析次数 |
| `avg_quality_score` | number | 是 | 平均质量评分（1.0-5.0） |
| `key_insights` | string[] | 是 | 历次分析的核心洞察摘要 |
| `related_topics` | string[] | 是 | 关联主题名称列表 |
| `frameworks_used` | string[] | 是 | 使用过的分析框架列表 |
| `mode_used` | string | 是 | 最后使用的分析模式 |

### 示例

```json
{
  "version": "1.0",
  "topics": {
    "新能源汽车行业": {
      "analysis_type": "industry",
      "keywords": ["新能源", "电动车", "锂电池", "充电桩"],
      "first_analyzed": "2026-01-15",
      "last_analyzed": "2026-02-08",
      "analysis_count": 3,
      "avg_quality_score": 4.2,
      "key_insights": [
        "渗透率突破30%标志着从爆发期进入成熟期",
        "充电基础设施是制约因素而非车辆本身"
      ],
      "related_topics": ["碳中和政策", "锂矿资源"],
      "frameworks_used": ["std_cube", "pestle", "porter_five_forces"],
      "mode_used": "deep"
    },
    "AI大模型商业化": {
      "analysis_type": "trend",
      "keywords": ["大模型", "AI", "商业化", "应用场景"],
      "first_analyzed": "2026-02-01",
      "last_analyzed": "2026-02-01",
      "analysis_count": 1,
      "avg_quality_score": 4.5,
      "key_insights": [
        "To B场景率先落地，To C场景仍在探索期"
      ],
      "related_topics": ["AI芯片市场"],
      "frameworks_used": ["std_cube", "causal_chain"],
      "mode_used": "standard"
    }
  }
}
```

---

## sources.json

来源记忆库，跨会话积累信息来源的可靠性评价。

### Schema

```json
{
  "version": "1.0",
  "sources": {
    "<source_name>": {
      "type": "official|research|media|self_media|expert|database",
      "url": "string|null",
      "domains": ["string"],
      "reliability_grade": "A|B|C|D",
      "usage_count": 0,
      "avg_score": 0.0,
      "first_seen": "YYYY-MM-DD",
      "last_used": "YYYY-MM-DD",
      "notes": "string"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | enum | 是 | 来源类型：`official`(官方机构) / `research`(研究机构/咨询公司) / `media`(主流媒体) / `self_media`(自媒体) / `expert`(专家/学者) / `database`(数据库) |
| `url` | string/null | 否 | 来源的主要 URL（如有） |
| `domains` | string[] | 是 | 擅长的领域列表 |
| `reliability_grade` | enum | 是 | 可靠性等级：A(高度可靠) / B(较可靠) / C(一般) / D(存疑) |
| `usage_count` | number | 是 | 累计使用次数 |
| `avg_score` | number | 是 | 平均评分（1.0-5.0） |
| `first_seen` | string | 是 | 首次使用日期 |
| `last_used` | string | 是 | 最后使用日期 |
| `notes` | string | 否 | 备注说明 |

### 示例

```json
{
  "version": "1.0",
  "sources": {
    "国家统计局": {
      "type": "official",
      "url": "https://www.stats.gov.cn",
      "domains": ["宏观经济", "人口", "消费"],
      "reliability_grade": "A",
      "usage_count": 8,
      "avg_score": 4.8,
      "first_seen": "2026-01-15",
      "last_used": "2026-02-08",
      "notes": "官方统计数据，高度权威"
    },
    "艾瑞咨询": {
      "type": "research",
      "url": "https://www.iresearch.com.cn",
      "domains": ["互联网", "消费", "科技"],
      "reliability_grade": "B",
      "usage_count": 5,
      "avg_score": 3.8,
      "first_seen": "2026-01-20",
      "last_used": "2026-02-05",
      "notes": "数据口径需注意，部分预测偏乐观"
    }
  }
}
```

---

## frameworks.json

框架效果记忆库，记录各分析框架在不同场景下的效果评价。

### Schema

```json
{
  "version": "1.0",
  "frameworks": {
    "<framework_id>": {
      "display_name": "string",
      "usage_count": 0,
      "avg_quality_score": 0.0,
      "best_for": ["string"],
      "effectiveness_by_type": {
        "<analysis_type>": {
          "count": 0,
          "avg_score": 0.0,
          "last_used": "YYYY-MM-DD"
        }
      }
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `display_name` | string | 是 | 框架显示名称 |
| `usage_count` | number | 是 | 累计使用次数 |
| `avg_quality_score` | number | 是 | 总体平均质量评分（1.0-5.0） |
| `best_for` | string[] | 是 | 最适合的分析类型列表 |
| `effectiveness_by_type` | object | 是 | 按分析类型分的效果数据 |
| `effectiveness_by_type.<type>.count` | number | 是 | 在该类型下的使用次数 |
| `effectiveness_by_type.<type>.avg_score` | number | 是 | 在该类型下的平均评分 |
| `effectiveness_by_type.<type>.last_used` | string | 是 | 在该类型下的最后使用日期 |

### 示例

```json
{
  "version": "1.0",
  "frameworks": {
    "std_cube": {
      "display_name": "S-T-D 立方体",
      "usage_count": 12,
      "avg_quality_score": 4.3,
      "best_for": ["industry", "trend", "phenomenon"],
      "effectiveness_by_type": {
        "industry": {
          "count": 5,
          "avg_score": 4.5,
          "last_used": "2026-02-08"
        },
        "phenomenon": {
          "count": 4,
          "avg_score": 4.2,
          "last_used": "2026-02-05"
        },
        "trend": {
          "count": 3,
          "avg_score": 4.1,
          "last_used": "2026-01-28"
        }
      }
    },
    "pestle": {
      "display_name": "PESTLE 宏观分析",
      "usage_count": 6,
      "avg_quality_score": 4.0,
      "best_for": ["industry", "trend"],
      "effectiveness_by_type": {
        "industry": {
          "count": 4,
          "avg_score": 4.2,
          "last_used": "2026-02-08"
        },
        "trend": {
          "count": 2,
          "avg_score": 3.7,
          "last_used": "2026-01-25"
        }
      }
    }
  }
}
```

---

## sessions.json

会话记录，记录每次战略分析的元数据用于模式分析。

### Schema

```json
{
  "version": "1.0",
  "max_sessions": 50,
  "sessions": [
    {
      "id": "S001",
      "timestamp": "ISO8601",
      "topic": "string",
      "analysis_type": "phenomenon|industry|enterprise|trend|comparison|exploratory",
      "mode": "fast|standard|deep",
      "frameworks_used": ["string"],
      "quality_score": 0.0,
      "insights_count": 0,
      "sources_count": 0,
      "output_files": ["string"],
      "wikilinks_used": 0,
      "user_feedback": "string|null",
      "patterns_applied": ["string"],
      "analyzed": false
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 会话唯一 ID，格式 S001, S002... |
| `timestamp` | string | 是 | ISO 8601 时间戳 |
| `topic` | string | 是 | 分析主题名称 |
| `analysis_type` | enum | 是 | 分析类型 |
| `mode` | enum | 是 | 使用的分析模式 |
| `frameworks_used` | string[] | 是 | 使用的框架 ID 列表 |
| `quality_score` | number | 是 | 质量评分（1.0-5.0） |
| `insights_count` | number | 是 | 生成的洞察数量 |
| `sources_count` | number | 是 | 使用的来源数量 |
| `output_files` | string[] | 是 | 生成的输出文件路径 |
| `wikilinks_used` | number | 是 | 嵌入的 wikilinks 数量 |
| `user_feedback` | string/null | 是 | 用户反馈，无反馈为 null |
| `patterns_applied` | string[] | 是 | 本次分析应用的模式 ID 列表 |
| `analyzed` | boolean | 是 | 是否已被 pattern_analyzer 分析过 |

### 示例

```json
{
  "version": "1.0",
  "max_sessions": 50,
  "sessions": [
    {
      "id": "S001",
      "timestamp": "2026-02-08T14:30:00+08:00",
      "topic": "新能源汽车行业深度分析",
      "analysis_type": "industry",
      "mode": "deep",
      "frameworks_used": ["std_cube", "pestle", "porter_five_forces"],
      "quality_score": 4.5,
      "insights_count": 5,
      "sources_count": 12,
      "output_files": [
        "~/Obsidian/AlexCai/03-Resources/战略分析/新能源汽车-战略洞察.md"
      ],
      "wikilinks_used": 8,
      "user_feedback": null,
      "patterns_applied": [],
      "analyzed": false
    },
    {
      "id": "S002",
      "timestamp": "2026-02-10T10:00:00+08:00",
      "topic": "AI大模型商业化趋势",
      "analysis_type": "trend",
      "mode": "standard",
      "frameworks_used": ["std_cube", "causal_chain"],
      "quality_score": 4.2,
      "insights_count": 4,
      "sources_count": 8,
      "output_files": [
        "~/Obsidian/AlexCai/03-Resources/战略分析/AI大模型商业化-战略洞察.md"
      ],
      "wikilinks_used": 5,
      "user_feedback": "洞察深度不错，但缺少具体案例",
      "patterns_applied": ["P001"],
      "analyzed": true
    }
  ]
}
```

### 会话轮转

当 `sessions` 数组长度超过 `max_sessions` 时，移除最早的已分析会话记录（FIFO）。被移除的会话若尚未分析（`analyzed: false`），应先触发 pattern_analyzer 分析。

---

## preferences.json

用户偏好设置，记录用户的自定义配置和修正历史。

### Schema

```json
{
  "version": "1.0",
  "output_preferences": {
    "default_mode": "fast|standard|deep",
    "preferred_format": "standard|obsidian_v2|obsidian_v3",
    "wikilink_style": "short|long",
    "language": "string"
  },
  "analysis_preferences": {
    "preferred_depth": "light|standard|deep",
    "enable_counterfactual": true,
    "enable_cross_matrix": true,
    "min_sources": 3
  },
  "correction_history": [
    {
      "timestamp": "ISO8601",
      "type": "term|framework|format|structure",
      "original": "string",
      "corrected": "string",
      "context": "string"
    }
  ],
  "custom_templates": {
    "<template_name>": {
      "description": "string",
      "template_path": "string"
    }
  }
}
```

### 字段说明

#### output_preferences

| 字段 | 类型 | 说明 |
|------|------|------|
| `default_mode` | enum | 默认分析模式 |
| `preferred_format` | enum | 首选输出格式 |
| `wikilink_style` | enum | Wikilink 风格：`short`(`[[note]]`) / `long`(`[[path/note\|显示名]]`) |
| `language` | string | 输出语言，如 "zh-CN" |

#### analysis_preferences

| 字段 | 类型 | 说明 |
|------|------|------|
| `preferred_depth` | enum | 偏好的分析深度 |
| `enable_counterfactual` | boolean | 是否启用反事实分析 |
| `enable_cross_matrix` | boolean | 是否启用跨维度交叉矩阵 |
| `min_sources` | number | 最少来源数量要求 |

#### correction_history 数组元素

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | 修正时间 |
| `type` | enum | 修正类型：`term`(术语) / `framework`(框架选择) / `format`(格式) / `structure`(结构) |
| `original` | string | 原始内容 |
| `corrected` | string | 修正后内容 |
| `context` | string | 修正的上下文说明 |

#### custom_templates

键值对，键为模板名称，值包含 `description`(描述) 和 `template_path`(模板文件路径)。

### 示例

```json
{
  "version": "1.0",
  "output_preferences": {
    "default_mode": "standard",
    "preferred_format": "obsidian_v3",
    "wikilink_style": "short",
    "language": "zh-CN"
  },
  "analysis_preferences": {
    "preferred_depth": "deep",
    "enable_counterfactual": true,
    "enable_cross_matrix": true,
    "min_sources": 3
  },
  "correction_history": [
    {
      "timestamp": "2026-02-08T15:00:00+08:00",
      "type": "term",
      "original": "NEV",
      "corrected": "新能源汽车(NEV)",
      "context": "用户要求在首次出现时展开英文缩写"
    },
    {
      "timestamp": "2026-02-07T10:30:00+08:00",
      "type": "framework",
      "original": "仅使用 std_cube",
      "corrected": "std_cube + pestle 组合",
      "context": "用户反馈行业分析需要包含宏观环境分析"
    }
  ],
  "custom_templates": {
    "industry_brief": {
      "description": "简版行业分析模板（2000字内）",
      "template_path": "templates/industry-brief.md"
    }
  }
}
```

---

## patterns.json

模式库，存储从多次分析中结晶出的可复用规则。

### Schema

```json
{
  "version": "1.0",
  "patterns": [
    {
      "id": "P001",
      "type": "framework_effectiveness|source_reliability|writing_optimization|analysis_depth|topic_association",
      "rule": "string",
      "confidence": 0.0,
      "occurrences": 0,
      "first_seen": "YYYY-MM-DD",
      "last_applied": "YYYY-MM-DD",
      "status": "active|candidate|deprecated",
      "metadata": {}
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 模式唯一 ID，格式 P001, P002... |
| `type` | enum | 是 | 模式类型（见下方类型说明表） |
| `rule` | string | 是 | 规则的自然语言描述，需具体可执行 |
| `confidence` | number | 是 | 置信度 0-1 |
| `occurrences` | number | 是 | 规则被观察到的次数 |
| `first_seen` | string | 是 | 首次发现日期 |
| `last_applied` | string | 是 | 最后应用日期 |
| `status` | enum | 是 | 状态：`active`(活跃) / `candidate`(候选) / `deprecated`(已废弃) |
| `metadata` | object | 否 | 额外元数据，结构因模式类型而异 |

### 模式类型说明

| 类型 | 说明 | metadata 示例 |
|------|------|--------------|
| `framework_effectiveness` | 框架对特定分析类型的效果 | `{"analysis_types": ["industry"], "avg_quality": 4.5}` |
| `source_reliability` | 来源在特定领域的可靠性 | `{"source_name": "艾瑞咨询", "domains": ["互联网"]}` |
| `writing_optimization` | 写作策略优化 | `{"strategy": "case_opening", "analysis_types": ["phenomenon"]}` |
| `analysis_depth` | 分析深度策略 | `{"mode": "deep", "quality_improvement": "30%"}` |
| `topic_association` | 主题关联模式 | `{"topics": ["新能源", "碳中和"], "correlation": 0.85}` |

### 示例

```json
{
  "version": "1.0",
  "patterns": [
    {
      "id": "P001",
      "type": "framework_effectiveness",
      "rule": "在行业分析类型中，S-T-D立方体 + PESTLE 组合使用时，质量评分平均达到 4.5+",
      "confidence": 0.88,
      "occurrences": 5,
      "first_seen": "2026-01-20",
      "last_applied": "2026-02-08",
      "status": "active",
      "metadata": {
        "analysis_types": ["industry"],
        "avg_quality": 4.6,
        "sample_topics": ["新能源汽车行业", "AI芯片市场"]
      }
    },
    {
      "id": "P002",
      "type": "writing_optimization",
      "rule": "现象分析类文章使用案例切入开篇，读者反馈评分比问题引入开篇高 0.3 分",
      "confidence": 0.78,
      "occurrences": 4,
      "first_seen": "2026-01-25",
      "last_applied": "2026-02-05",
      "status": "active",
      "metadata": {
        "strategy": "case_opening",
        "analysis_types": ["phenomenon"],
        "comparison_strategy": "question_opening",
        "score_diff": 0.3
      }
    },
    {
      "id": "P003",
      "type": "analysis_depth",
      "rule": "企业战略类主题使用 deep 模式比 standard 模式质量提升约 25%",
      "confidence": 0.72,
      "occurrences": 3,
      "first_seen": "2026-02-01",
      "last_applied": "2026-02-08",
      "status": "active",
      "metadata": {
        "mode_comparison": {"deep": 4.4, "standard": 3.5},
        "analysis_types": ["enterprise"]
      }
    },
    {
      "id": "P004",
      "type": "topic_association",
      "rule": "新能源 和 碳中和 主题高度关联（相关度 0.85），建议在分析新能源时参考碳中和历史分析",
      "confidence": 0.65,
      "occurrences": 2,
      "first_seen": "2026-02-05",
      "last_applied": "2026-02-08",
      "status": "candidate",
      "metadata": {
        "topics": ["新能源", "碳中和"],
        "correlation": 0.85
      }
    }
  ]
}
```

### 置信度衰减

active 模式超过 30 天未应用时，confidence 按以下公式衰减：

```
days_inactive = (today - last_applied).days
if days_inactive > 30:
    decay_rounds = days_inactive // 30
    new_confidence = max(0.3, confidence - decay_rounds * 0.05)
    if new_confidence < 0.5:
        status = "deprecated"
```
