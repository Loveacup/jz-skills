---
name: de-slop
description: |
  Detect and remove AI writing patterns from prose. Bilingual engine: English (30+ patterns)
  and Chinese (25+ Chinese-native patterns with register-aware detection). Use when editing,
  rewriting, or reviewing text to eliminate predictable AI tells and inject authentic human voice.
  
  Triggers: humanize, de-AI, de-slop, un-ChatGPT, rewrite, edit draft, polish prose, check for AI tells,
  去AI味, 说人话, 改得自然一点, 别像模板
  DO NOT use for: code review, grammar-only fixes, technical documentation formatting
version: 2.0.0
license: MIT
sources:
  - https://github.com/blader/humanizer (v2.7.0, MIT)
  - https://github.com/hardikpandya/stop-slop (MIT)
  - https://github.com/LifelongLazyLearner/qu-ai-wei (MIT, Chinese patterns)
  - https://github.com/MrGeDiao/shuorenhua (MIT, Chinese guardrails)
---

# de-slop — AI Text Detector & Humanizer (Bilingual)

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "这文章读起来还行，不需要改" | AI 痕迹是统计性的——单独看没问题，聚类就是 confession |
| "我直接删几个 em dash / 四字成语就行了" | 30+/25+ 模式互相印证。修一个漏十个，文本还是 AI |
| "评分太主观，跳过吧" | 5 维评分是硬约束。EN < 35 / ZH < 35 必须重写 |
| "中文和英文差不多，套同一套规则" | 中文 AI 腔靠密度 × 语体 × 功能判断，跟英文 pattern matching 是两套逻辑 |
| "这是技术文档，不需要 Personality" | Personality & Soul 已加了 context guard：百科/技术/法律文本跳过 |

## 🔀 Decision Tree

```
用户输入文本
    ↓
[0] 语言检测
    ├─→ 中文 → 🀄 ZH Pipeline（chinese-system.md + chinese-patterns.md）
    └─→ 英文/其他 → 🇬🇧 EN Pipeline（patterns.md + scoring.md）
    ↓
[1] 有用户写作样本？ → Voice Calibration
    ↓
[2] 内容类型？
    ├─→ 博客/随笔/观点 → Personality Mode
    ├─→ 技术/百科/法律 → Clean Mode
    └─→ PR/邮件/简历 → Polished Mode
    ↓
执行对应语言的流水线
```

---

## 🀄 ZH Pipeline（中文）

中文 AI 检测不是 pattern matching，而是**密度 × 语体 × 功能**三维判断。先加载中文体系文件，再执行流程。

```
[ZH-0] 加载 chinese-system.md → 冲突仲裁树 + 门检 + 语体矩阵
[ZH-1] 门检：是不是真人写的？→ 是 → 停手
[ZH-2] 识别语体 → 激活对应规则子集
[ZH-3] Scan → 对照 chinese-patterns.md 标记
[ZH-4] Draft → 逐段改写（减法 + 打磨）
[ZH-5] Audit → 密度三问 + 过度消毒反制 + AI 不敢写测试
[ZH-6] Final → 修复残留 → 打磨报告
[ZH-7] Score → 5 维评分 → < 35 回到 ZH-4
```

详见 `references/chinese-system.md` 和 `references/chinese-patterns.md`。

---

## 🇬🇧 EN Pipeline（英文）

```
[1] Calibrate  → 有样本则分析风格
[2] Scan       → 对照 patterns.md 标记
[3] Draft      → 逐段重写
[4] Audit      → "What makes this AI?"
[5] Final      → 修复残留 → 注入 Personality
[6] Score      → 5 维 → < 35 回到 [3]
```

### 🎯 Quick Reference: Top 15 AI Tells

扫第一遍时对照此表。完整 30+ 模式见 `references/patterns.md`。

| # | 模式 | 一句话 | 典型例子 |
|---|------|--------|---------|
| 1 | Significance inflation | 把普通事吹成里程碑 | "marking a pivotal moment" |
| 2 | -ing padding | 句子尾巴加假深度 | "showcasing how...contributing to..." |
| 3 | Promotional language | 广告腔 | "nestled...breathtaking...vibrant" |
| 4 | Vague attributions | 无名无姓的"专家" | "Industry observers have noted" |
| 5 | AI vocabulary | 高频 AI 词聚类 | "delve, tapestry, landscape, crucial" |
| 6 | Copula avoidance | 不用 is/are | "serves as" instead of "is" |
| 7 | Em dashes | AI 最可靠信号之一 | "—not by the people themselves—" |
| 8 | Throat-clearing | 开场不说正事 | "Here's the thing...Let me be clear" |
| 9 | Binary contrasts | 制造假冲突 | "It's not about X. It's about Y." |
| 10 | Rule of three | 硬凑三个 | 三名词、三动词、三段式结尾 |
| 11 | Sycophantic tone | 过分讨好 | "Great question! You're absolutely right!" |
| 12 | False agency | 死物做人事 | "the decision emerges" → 谁决定的？ |
| 13 | Hedging cluster | 层层包裹 | "could potentially possibly be argued" |
| 14 | Chatbot artifacts | 对话残渣 | "I hope this helps! Let me know if..." |
| 15 | Generic conclusion | 万能结尾 | "The future looks bright..." |

### ⚡ Quick-Check (EN Final Pass)

- [ ] 任何副词？杀了
- [ ] 被动语态？找主语
- [ ] 无生命物做人的动作？说出谁干的
- [ ] Wh- 开头句子？重构
- [ ] "here's what/this/that" 清嗓子？直接说
- [ ] "not X, it's Y" 对比？直接说 Y
- [ ] 三个连续句子等长？打断
- [ ] Em dash？去掉
- [ ] 模糊宣言？说出具体意义
- [ ] 旁观者叙事？把读者放到场景里
- [ ] 元衔接？删了

---

## 🗣️ Voice Calibration（中英通用）

如果用户提供了自己的写作样本：

1. **分析:** 句长模式、用词层级、段落开头习惯、标点习惯、过渡方式
2. **匹配:** 重写时换上用户的节奏
3. **无样本:** 回退到自然、多变、有态度的默认声音

## 💬 Personality & Soul（中英通用）

⚠️ **适用范围：** 博客、随笔、个人写作、观点文。技术文档、百科、法律文本 → 跳过。

**注入人声：** 有态度、变节奏、留点乱、情绪具体化。

## 📊 Scoring System（中英通用）

5 维评分，每维 1-10。总分 50，< 35 重写。详见 `references/scoring.md`。

| 维度 | 衡量 |
|------|------|
| Directness | 陈述 vs 宣告？ |
| Rhythm | 多变 vs 节拍器？ |
| Trust | 尊重读者智力？ |
| Authenticity | 像人说话？ |
| Density | 有没有可砍的？ |

## Detection Guidance（中英通用）

⚠️ **不要误杀：** 完美语法、正式词汇、孤立 em dash、缺引用——不是可靠 AI 信号。

**人类写作信号（保留）：** 具体罕见细节、矛盾情感、带年代引用、真正旁白和自我纠错。

---

## 📦 References

| 文件 | 语言 | 何时读取 |
|------|:--:|------|
| `references/patterns.md` | 🇬🇧 | EN 完整 30+ 模式 |
| `references/scoring.md` | 🌐 | 中英通用 5 维评分 |
| `references/chinese-system.md` | 🀄 | ZH 冲突仲裁 + 门检 + 语体矩阵 + 反消毒 + 打磨 |
| `references/chinese-patterns.md` | 🀄 | ZH 完整 25+ 模式 |
| `references/trigger-tests.md` | 🌐 | 修改 triggers 后的回归测试 |

---

## ✅ Verification Checklist

- [ ] 语言路由是否正确（ZH 加载 chinese-system/patterns，EN 加载 patterns）？
- [ ] ZH：门检 + 语体识别 + AI 不敢写测试？
- [ ] EN/ZH：完整流水线（Scan → Draft → Audit → Final → Score）？
- [ ] EN/ZH：5 维评分 ≥ 35？
- [ ] Quick-Check 通过（EN 或 ZH 对应版本）？
- [ ] 是否误杀了人类写作信号？
- [ ] 输出是否包含完整 deliverable？
