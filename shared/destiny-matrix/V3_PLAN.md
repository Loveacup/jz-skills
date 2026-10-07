# Destiny Matrix v3 施工蓝图

> 所有参与本次重构的 agent **必须先读本文档**，再开始任务。

---

## 核心理念（不可妥协）

**性格决定命运，玄学辅证，命运可塑。**

1. **性格是主语**：荣格八维是「主语」，八字/紫微/占星是「谓语与状语」
2. **玄学辅证**：玄学不"决定"任何事，它"印证 / 映照 / 解释"性格的展开
3. **命运可塑**：性格可发展（Jung 个体化进程），因此命运不是预定剧本

## 哲学骨架

```
性格 ──────────┬────── 是谁（恒量 · 可发展）
               │
               ├─ 八字「解构」── 这把剑的材质
               ├─ 紫微「对应」── 剧本舞台
               └─ 占星「映照」── 宇宙节律

命运 = 性格 × 时机（玄学提供时机窗口）
终极裁判：性格自身（个体化进程 / 劣势功能整合）
```

## 三大原则

1. 性格是主语，玄学是注解
2. 命运可塑（反对宿命论是 skill 的内置态度）
3. 玄学的价值在「文化坐标」，不在「预言」

## 输出结构（修订后）

| Chapter | 主题 | 篇幅 |
|:---|:---|:---|
| 1 | **性格画像（荣格主导）** | 35-45% |
| 2 | 八字解构 —— 性格的能量基础 | 15% |
| 3 | 紫微对应 —— 性格的剧场舞台 | 15% |
| 4 | 占星映照 —— 性格的宇宙节律 | 15% |
| 5 | 三维印证度评估 | 5% |
| 6 | 双轨时间线（性格发展 + 玄学时机） | 5% |
| 7 | 感情专题（荣格骨架 + 玄学应期） | 必须充分 |
| 8 | 终极课题（个体化任务 + 应期窗口） | 5% |

## 措辞统一

| 旧 | 新 |
|:---|:---|
| "决定" | "印证 / 映照 / 解释" |
| "命中注定" | "天然倾向 / 默认路径" |
| "命运" | "性格在时机中的展开" |
| "四维一致 = 信心高" | "玄学三维印证性格签名" |

## 命运密码公式

```
命运密码 = 性格底色（荣格） × 玄学时机（大运/大限/行运）
```

终极课题必出自荣格劣势功能 / 阴影整合，玄学只用来标注「应期窗口」。

## Sprint 分工

### 第一波（并行 · 当前执行）
- **S5 哲学骨架**（Agent A）：SKILL.md 重写 + 新建 manifesto + inference-workflow
- **S1+S2 计算基础设施**（Agent B）：_common.py + 修 P0 bug + geonamescache + DST + 真太阳时
- **S4 jung_calc.py**（Agent C）：荣格计算引擎（功能栈 + Beebe + Grip + 性格签名）
- **S3 八字数据增强**（Agent D）：神煞 + 调候补全 + 子时规则 + 节气警告
- **S6 荣格典籍化**（Agent E）：cognitive-functions.md 扩展 + jung-classical-texts.md
- **S10 交叉分析重写**（Agent F）：cross-analysis-patterns.md（三精细映射表 + 纵向递进）
- **S7 关系动力学**（Agent G）：jung-relationship-dynamics.md

### 第二波（待第一波完成后）
- S9 output-template 重构
- S8 荣格视觉化（认知雷达图 + Beebe 环）
- S11 占星严谨性（高纬度 fallback + 扩展配点）
- S12 紫微严谨性（派别明示 + 闰月双盘）
- S13 kerykeion SVG 接入
- S14 合盘脚本
- S15 Phase-Gating + Adversarial Evaluator
- S16 MingLi-Bench 回归测试

## 文件变更清单

### 新增
```
references/character-first-manifesto.md    ★ 哲学骨架
references/character-inference-workflow.md ★ 无测试数据工作流
references/jung-classical-texts.md         ★ 荣格典籍
references/jung-relationship-dynamics.md   ★ 关系动力学
references/shensha-table.md                八字神煞表
scripts/_common.py                         公共工具
scripts/jung_calc.py                       ★ 荣格计算引擎
```

### 重写
```
scripts/bazi_calc.py                神煞 + 调候补全 + 子时规则 + 节气警告
scripts/astro_calc.py               修 P0 bug + 扩展配点
scripts/cast_chart.py               geonamescache + 真太阳时
references/cognitive-functions.md   123 → 400+ 行
references/cross-analysis-patterns.md  三精细映射表
SKILL.md                            性格本位骨架重写
```

## 默认决策（v3 已拍板）

- D1 = A：性格本位写入 frontmatter description
- D2 = A：Tier 1-3 全支持（必测 / 访谈反推 / 玄学反推）
- D3 = A：玄学解释力评级硬性要求
- D4 = A：命书第一章固定性格画像
- D5 = A+B：manifesto + 措辞落地
- D6 = A：默认篇幅等分（玄学三维各 15%）
- D7 = A：可塑路径必须给具体行动
- D8 = A：《果老星宗》"体用相参" 中的「体」重新解读为性格本位

## 工作原则（对所有 agent）

1. 所有文档保持中文
2. 不写 emoji 除非数据可视化必需
3. 注释保持极简，让代码自解释
4. 引用典籍要标注卷次/页码
5. 不要碰其他 agent 负责的文件
6. 输出必须能被 cast_chart.py 调用（计算脚本组）
7. 文档新增/重写完成后，在文件头部加 v3 标记

## 依赖追加（v3）

```bash
pip install geonamescache timezonefinder kerykeion --break-system-packages
```

v2 已有依赖（保留）：lunar_python, iztro-py, pyswisseph, sxtwl
