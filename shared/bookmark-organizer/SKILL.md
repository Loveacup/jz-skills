---
name: bookmark-organizer
description: |
  书签批量整理工具。解析浏览器导出的书签文件（Netscape HTML / Chrome 原生 JSON 自动嗅探），
  规则优先（L1 零 API 成本）+ agent 语义分类兜底（L2），输出可重导入的分类 HTML + Obsidian Markdown 索引。

  触发场景：整理书签、书签整理、书签分类、清理书签、书签去重、organize bookmarks、bookmark organizer
  DO NOT use for: 单条书签增删、浏览器内实时操作、一般网页抓取与摘要（非书签文件）
type: routine
---

# Bookmark Organizer - 书签批量整理

三层架构：**L1 规则匹配（零 API）→ L2 agent 语义分类（你自己就是 LLM）→ L3 后处理**。
CLI 负责一切确定性工作，你负责语义判断与用户交互。

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "我直接看书签自己分类就行" | 9000 条书签会撑爆上下文；L1 规则免费处理 60%+，跳过 = 烧 token |
| "分类体系我现编一套更贴合" | 类别清单唯一来源是 references/classification-rules.json；现编 = 类别爆炸 + merge 校验全部打回 |
| "未命中的我一条条分类" | 必须批量：每批 30–50 条一次性输出 JSON 补丁，逐条 = 百倍调用浪费 |
| "用户没给文件，我去读浏览器配置" | 先问用户要导出文件路径；Chrome 本机 `Bookmarks`/`Bookmarks.bak` 仅在用户明确同意后读取 |
| "按年份直接用原始 add_date 分组就行" | 同步/导入会污染时间戳；年份考古必须 URL 去重取最早 `add_date`、检测迁移批次——`timeline` 已内置该口径，直接用它 |
| "常用/点击排序书签导出里应该有" | 书签导出不含点击数据；必须另读 Chromium History，且需单独隐私授权、快照只读、覆盖率诚实报告（P2，暂缓未实现） |
| "dry-run 跳过直接全量跑" | dry-run 是用户确认 LLM 成本前的刹车点，默认必经 |

## 工作流程（4 步）

```
1. 定位输入 → 2. dry-run 预览（用户确认）→ 3. 分类执行（L1 + L2 回灌）→ 4. 渲染产出
```

> 📌 年份归档/书签考古已实现（`timeline`，见「书签时光机」一节）；常用/点击排序（usage）
> 仍是规划，需 History 隐私授权，暂缓——不要把它报告为可用命令。
> 设计细节见 `references/timeline-and-usage-design.md`。

### Step 1: 定位输入

用户给文件路径；没给时先扫 `~/Downloads/` 最新的 `bookmarks*.html` / `书签*.html`，
找不到再询问。Chrome/Edge 原生 `Bookmarks` JSON 文件也可直接解析（须用户明确指定/同意）。

```bash
python3 $SKILL_DIR/scripts/bookmark-cli.py parse <输入文件> -o bookmarks.json
```

### Step 2: dry-run 预览（默认必经）

```bash
python3 $SKILL_DIR/scripts/bookmark-cli.py classify bookmarks.json --dry-run
```

向用户输出短统计（IM 友好，勿刷屏）：总条数、浏览器内部页/脚本数、L1 命中率、
待 L2 条数（唯一 URL 数）≈ LLM 批次数。**等用户确认后再继续**（用户说过"直接跑"则跳过）。

### Step 3: 分类执行

```bash
python3 $SKILL_DIR/scripts/bookmark-cli.py classify bookmarks.json -o classified.json --unmatched unmatched.json
```

然后做 L2（见下节），每批生成补丁文件后回灌：

```bash
python3 $SKILL_DIR/scripts/bookmark-cli.py merge classified.json patch-N.json
```

merge 幂等、可多次增量调用，中断后可随时续跑（unmatched.json 在磁盘上就是断点）。

### Step 4: 渲染产出

```bash
python3 $SKILL_DIR/scripts/bookmark-cli.py render classified.json -o organized.html --md 书签索引_<来源>_YYYYMMDD.md
```

向用户汇报产物路径 + 最终统计。若 obsidian 能力可用且用户需要入库：MD 索引放入
vault 的 `00-Inbox/`（两阶段收件箱工作流），不要直接写终目录。

## 扩展工作流：书签时光机（年份归档 / 考古）

触发：按年份归档、书签时光机、书签考古、地层报告。输入是走完 L1/L2 的 classified.json。

```bash
python3 $SKILL_DIR/scripts/bookmark-cli.py timeline classified.json \
  --source-name Chrome -o 书签时光机_Chrome_YYYYMMDD.md --stats-json timeline-stats.json
```

口径已内置，勿手工绕过：URL 去重取最早 `add_date` → `first_added_at`/`year`；默认排除
`browser-internal`/`bookmarklet`（`--include-internal` 可含）；同一分钟 ≥30 个唯一 URL
判定为迁移批次（批内时间戳只是下界）；年份 <2000 或晚于当前年份 → 「年份未知」桶。

- **产物 1（确定性）**：时光机 MD —— frontmatter + 总览 callout + 迁移批次警告 +
  年代总览表 + 逐年节（Top 分类/域名 + 代表书签）。入库放 vault `00-Inbox/`。
- **产物 2（你来写，可选）**：地层报告 —— 读 `--stats-json` 的年份×分类×域名统计，
  按「地层」写考古叙事。每个数字必须来自统计 JSON，禁止编造年份/数量；
  对批内条目只说「进入本库的时间」，不声称原始收藏年份。
- 默认不输出 HTML 时光机（重导入会复制书签）；用户明确要求再考虑。

## L2 语义分类约定（你的职责）

1. 读 `unmatched.json`，**每批 30–50 条**
2. 类别清单**从规则文件生成**：读 `references/classification-rules.json` 的
   `categories[].{id, name, hint}`，放进 prompt；只允许返回清单内的 `id`
3. 利用条目的 `title` + `url` 判断；不确定的条目宁可不输出（留在未分类），不要硬猜
4. 每批输出纯 JSON 补丁文件：`[{"id": "<条目id>", "category_id": "<类别id>"}]`。
   可选字段：`"title"`（顺便精简冗余标题，原标题自动存入 `orig_title`）、
   `"subcategory"`（二级文件夹名，render 自动呈现为子文件夹 / MD 三级标题）
5. `merge` 会做 6 层 fallback 解析 + 类别合法性校验：非法类别自动打回未分类并计数；
   规则/手工分类的条目受保护，补丁无法改其分类（title/subcategory 不受此限制）
6. **大类拆分（L3）**：某分类 >60 条时，按域名/主题制定子分类映射（LLM 定规则、
   脚本批量打标），通过补丁的 `subcategory` 字段回灌；标题批量清洗同理
   （双语重复、站点尾缀等规律性冗余走规则脚本，无意义标题逐条 LLM 改名）

## CLI 子命令速查

| 子命令 | 输入 → 输出 | 说明 |
|--------|------------|------|
| `parse` | HTML/Chrome JSON → bookmarks.json | 格式自动嗅探；剥 ICON；空标题用域名兜底 |
| `classify` | bookmarks.json → classified.json + unmatched.json | L1 打分；`--dry-run` 仅统计；unmatched 按唯一 URL 去重 |
| `merge` | classified.json + 补丁 → 更新 classified.json | 宽容解析 LLM 输出；幂等增量；同 URL 重复条目一并应用 |
| `render` | classified.json → HTML + MD 索引 | HTML 可重导入 Chrome/Edge；MD 未分类置顶、🤖 标记 LLM 条目 |
| `timeline` | classified.json → 时光机 MD（+ 统计 JSON） | URL 去重取最早 add_date；迁移批次检测；`--stats-json` 供地层叙事 |

> 规划中的 `usage` / `render --sort usage`（P2 点击排序）见
> `references/timeline-and-usage-design.md`；代码未实现，且需 History 隐私授权，暂缓。

内置桶（不占用规则）：`browser-internal`（chrome:// 等内部页）、`bookmarklet`（javascript: 脚本）、
`uncategorized`（未分类）。

## 输出产物

1. **organized.html** — Netscape 格式，分类 = 一级文件夹，可重导入浏览器
2. **书签索引_*.md** — Obsidian 格式：frontmatter + 统计 callout + 未分类置顶 +
   每类一节；🤖 标记 = LLM 分类（用户纠错重点区）

## 规则维护

- 规则文件：`references/classification-rules.json`（41 类，category 中文名 + 英文 id + hint）
- 打分权重与阈值在文件头部 `scoring` / `threshold`，调参不改代码
- 用户对分类提出纠正时：记下来（supermemory 可用时写入）；**同类纠错 ≥3 次**，
  建议用户把对应 keywords/url_patterns 写进规则文件——L1 命中率随使用上升
- 新增规则字段要求：id 唯一（英文 slug）、name 唯一（中文）、keywords/url_patterns 至少一项非空

## 故障排查

| 症状 | 处理 |
|------|------|
| parse 结果 0 条 | 确认文件是书签导出而非普通网页；HTML 须含 `<DT><A HREF=...>` 结构 |
| 重复 URL 异常多（>50%） | 浏览器同步复制症，正常；重复条目保留不删，dry-run 会报唯一 URL 数 |
| L1 命中率 <30% | 书签库偏小众/长尾，属正常；看 unmatched 高频域名，值得的补进规则文件 |
| merge 报"补丁解析失败" | 你输出的 JSON 混了过多解释文字；重新输出纯 JSON 数组 |
| 类别爆炸/出现怪类别 | 检查是否绕过了规则清单自行发明类别；merge 的"非法类别"计数 >0 即是信号 |
| 上千条待 L2 跑不完 | 分批是常态；merge 增量幂等，跨会话续跑即可 |
