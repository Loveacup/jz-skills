# 周报格式规范

本文档定义周报 markdown 的完整输出格式。生成周报时读取此文件获取格式要求。

## YAML Frontmatter

```yaml
---
class: 20-Areas
status: 常青
type: 周报
priority: 正常
aliases: [YYYY年M月第N周, MM月周报, WeekN-YYYY]
tags: [周报, 总结, 复盘]
created: YYYY-MM-DD
modified: YYYY-MM-DD
---
```

## 文件命名

`YYYY-Www周报.md`（ISO 周数，W 后两位数字，不足补 0）

示例：`2026-W21周报.md`、`2026-W08周报.md`

## 输出路径

`~/Documents/Obsidian/AlexCai/50-Self/02_周报/`

⚠️ 与日记目录（`01_日记/`）**平级**，不是日记的子目录。

## 段落结构

### 1. 标题 + 时间范围
```markdown
# 周报：YYYY-MM-DD 至 YYYY-MM-DD

## 📅 时间范围
**YYYY年M月D日（周X）至 YYYY年M月D日（周X）**
```

### 2. 行动项汇总
```markdown
## ✅ 行动项汇总

### 待处理
- [ ] **项目名**（日期 提及）
  - 具体行动点

### 生活事项
- [ ] 生活相关事项
```
- 从所有日记中提取 `- [ ]` 未完成项
- 按工作/生活分类

### 3. 本周主题与洞察
```markdown
## 🎯 本周主题与洞察

### 核心主题
1. **主题1**: 简述
2. **主题2**: 简述

### 关键进展

#### 1. 主题名（相关日期）

**子标题**：
- 要点1
- 要点2
- 参考：[[wikilink to related note]]
```
- 聚合一周事件和成果 (Daily-notes-processor)
- 发现关联主题并用 `[[wikilinks]]` 链接 (Note-cross-linker)
- 提炼主题和洞察 (Insight-synthesizer)

### 4. 相关链接
```markdown
## 🔗 相关链接

### 日记链接
- [[50-Self/01_日记/YYYY-MM-DD|YYYY-MM-DD]]
- [[50-Self/01_日记/归档/YYYY-MM-DD|YYYY-MM-DD]]

### 人物链接
- [[人物名|显示名]]

### 项目与方法论链接
- [[路径/文件名|显示名]]
```
- 使用 Obsidian wikilinks 格式
- 日记在归档文件夹的用归档路径 (Backlink-closure)

### 5. 数据统计
```markdown
## 📊 数据统计

- **日记天数**：N天（有记录）
- **有实质内容天数**：N天
- **主要关注领域**：领域1、领域2
- **主要人物提及**：人物1（N次）、人物2（N次）
```

### 6. 下周重点
```markdown
## 💡 下周重点

1. **方向1**：具体计划
2. **方向2**：具体计划
```

### 7. 临时笔记汇总
```markdown
## 📌 临时笔记汇总

- **MM-DD**：笔记内容
```

### 8. 页脚
```markdown
---

*Last updated: YYYY-MM-DD*
```

## 5个分析维度处理指令

生成周报时按以下维度处理日记内容：

1. **Daily-notes-processor**: 逐日阅读日记内容，提取事件、成果、决策
2. **Note-cross-linker**: 发现跨日重复出现的主题，使用 `[[wikilinks]]` 建立关联
3. **Action-item-agent**: 收集所有 `- [ ]` 待办项，标注来源日期
4. **Insight-synthesizer**: 从事件中提炼高层洞察和模式
5. **Backlink-closure**: 为所有人物、项目、方法论生成 wikilink，确保双向链接

**注意**: V1 版本在单个 prompt 中完成所有维度的分析，不使用多 agent 编排。
