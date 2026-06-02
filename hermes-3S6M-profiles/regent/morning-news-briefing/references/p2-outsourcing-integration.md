# P2 外包 Skill 集成规范 v1.0

> 早新闻 v5.1 接驳 4 个外包 skill 的接口契约、触发条件、错误处理。

---

## 1. de-slop — AI 去味（Step 2.5）

### 触发条件
- **时机**: Assembly 产出 `morning-news-{date}.md` 后，Render 之前
- **强制执行**: 不可跳过

### 接口契约
```
输入: morning-news-{date}.md（汇编写出的全文）
处理:
  1. 加载 de-slop skill
  2. 语言检测 → 中文走 ZH Pipeline、英文走 EN Pipeline
  3. 中文 ZH Pipeline:
     - 门检：真人写作特征检测 → 通过则跳过
     - 语体识别：博客/评论/新闻 3 种语体匹配
     - 25+ 模式扫描 + 密度三问
     - AI 不敢写测试（具体细节、矛盾情感）
     - 5 维评分 ≥35
  4. 英文 EN Pipeline:
     - 30+ 模式扫描 (significance inflation / em dashes / hedging cluster 等)
     - 5 维评分 ≥35
  5. 逐段重写 → Audit → Final → 增量修改原文件
     🛡️ 保护区：含 `$数字`/价格/百分比的句子、以及带 citation 锚（`[sN]`）的句子**不重写**，
        仅改写其前后叙述层——保住 verbatim quote 可追溯（morning-news Core Rule #2）
输出: morning-news-{date}.md（在原文件上直接改写）
```

### 与现有 banned-phrases 的关系
- banned-phrases（15 禁词 + Sherman Kent）在 Assembly 阶段跑
- de-slop 补 banned-phrases 未覆盖的 55+ AI 模式（30+ EN + 25+ ZH）
- de-slop 不替代 banned-phrases——两者先后互补

### 错误处理
- de-slop 修改后导致分析格式破坏 → 二次 assembly 修复
- de-slop 评分 <35 3 次仍不通过 → 标记 "de-slop-partial"，不阻塞交付

---

## 2. source-verification — 声明级验证（Step 4 审计阶段）

### 触发条件
- **时机**: PDF 渲染完成后，审计阶段
- **范围**: 高频 claim 类型（抽样，不全量）：价格/数据/排名/政策声明

### 接口契约
```
输入: 审计阶段从 PyMuPDF 提取的关键 claim（≤10 条/版）
处理:
  1. 加载 source-verification skill
  2. 逐条对照原文 source_map 的 extracted_quotes[]
  3. 对每条 claim 标置信度：
     - verified: extracted_quotes[] 直接支撑
     - partial: 间接支撑但口径可能不同
     - contradicted: 两个来源相互矛盾
     - not found: 无法从任何 source 验证
  4. 输出 verification-{date}.json
输出: 标注了置信度的 claim 列表
```

### 门禁规则
- "contradicted" → 删除该 claim，重新 assembly 该段落
- "not found" → 标注 `⚠️ 未验证` 但不删除（可能是推理层产出）
- "partial" → 标注 `📎 部分验证` 通过
- 全量 "verified" + "partial" → 通过

### 错误处理
- source_map 损坏 → 跳过 source-verification，标记 "audit-skip-verification"
- 所有 claim 都是 "not found" → 不阻塞交付，但日志告警

---

## 3. tts-manager — 语音播报（Step 5 交付阶段）

### 触发条件
- **时机**: 双版 PDF 生成后，最终交付前
- **可选**: 如果 H200 CosyVoice 不可达，静默跳过

### 接口契约
```
输入: 
  - 执行摘要（3-5 条 bullet，中文）
  - 头条板块标题 + 第一段（中文）
  - 总长 ≤500 汉字
处理:
  1. 组装 TTS 文本：
     "Alex 早新闻，{日期}。{执行摘要逐条朗读}。
      头条：{头条标题}。{头条正文}。"
  2. 调 Hermes text_to_speech 工具（后端由 tts-manager skill 管理，当前默认 CosyVoice/AlexCai 音色）
  3. 保存到 workspace: morning-news-{date}/output/morning-news-{date}.ogg
  4. 验证文件存在 + 时长 ≤2min
输出: ~/.hermes/workspaces/morning-news-{date}/output/morning-news-{date}.ogg
```

### 门禁规则
- 文件不存在 → 静默跳过 TTS，不影响 PDF 交付
- 时长 >2min → 截断重生成
- CosyVoice 不可达 → 静默跳过，不阻塞

### 交付格式
随 PDF 一起发送：`MEDIA:morning-news-{date}.ogg`

---

## 4. pdf — 后处理（备选）

### 定位
**不替换现有 Playwright 渲染管线。** 仅用作后处理能力：

- bookmark 添加（pypdf auto-outline）
- 大文件压缩（仅 Standard A4 版，>3MB 时）
- 完整性验证：页数、文本提取、字体嵌入检查

### 触发条件
- **时机**: Render 产出 PDF 后（Step 3.5），可选
- **非强制**

### 接口契约
```
输入: 双版 PDF 路径
处理:
  1. 加载 pdf skill
  2. 检查 PDF 页数（mobile ≥4、standard ≥6）
  3. 如 standard.pdf >3MB → Ghostscript 压缩
  4. pypdf 添加 PDF bookmarks（h1-h2 层级）
输出: 可能压缩/加书签后的 PDF（路径不变）
```

### 错误处理
- 压缩失败 → 使用原始 PDF
- bookmark 失败 → 跳过，不阻塞
- pdf skill 不可用 → 静默跳过

---

## 5. 端到端顺序

```
Step 1: Parallel Search (delegate_task × 3 lanes)
Step 2: Assembly (news-assembly → morning-news-{date}.md)
Step 2.5: de-slop ★ 强制执行
Step 3: Render (Playwright → mobile.pdf + standard.pdf)
Step 3.5: pdf 后处理（可选：bookmark + 压缩）
Step 4: Audit (7 sentinels + source-verification ★)
Step 5: Deliver (PDFs + TTS ★)
```

★ = P2 新增步骤
