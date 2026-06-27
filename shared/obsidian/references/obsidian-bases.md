# Obsidian Bases 参考

> 来源：[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) · 适配 Hermes

创建和编辑 Obsidian Bases（`.base` 文件）——数据库式笔记视图，支持过滤、公式、汇总和多种视图类型。

## 工作流

1. **创建文件**：在 vault 中创建 `.base` 文件，含有效 YAML
2. **定义范围**：添加 `filters` 选择哪些笔记出现（按 tag/folder/property/date）
3. **添加公式**（可选）：在 `formulas` 区域定义计算属性
4. **配置视图**：添加一个或多个视图（`table`/`cards`/`list`/`map`），`order` 指定显示属性
5. **验证**：确认 YAML 语法正确，引用属性和公式存在
6. **测试**：在 Obsidian 中打开 `.base` 文件确认渲染

## Schema

```yaml
filters:                         # 全局过滤器，应用于所有视图
  and: []
  or: []
  not: []

formulas:                        # 计算属性
  formula_name: 'expression'

properties:                      # 属性显示名配置
  property_name:
    displayName: "Display Name"
  formula.formula_name:
    displayName: "Formula Display Name"

summaries:                       # 自定义汇总公式
  custom_summary_name: 'values.mean().round(3)'

views:                           # 一个或多个视图
  - type: table | cards | list | map
    name: "View Name"
    limit: 10
    groupBy:
      property: property_name
      direction: ASC | DESC
    filters:
      and: []
    order:
      - file.name
      - property_name
      - formula.formula_name
    summaries:
      property_name: Average
```

## 过滤器语法

```yaml
# 单一过滤器
filters: 'status == "done"'

# AND — 所有条件为真
filters:
  and:
    - 'status == "done"'
    - 'priority > 3'

# OR — 任一条件为真
filters:
  or:
    - 'file.hasTag("book")'
    - 'file.hasTag("article")'

# NOT — 排除匹配项
filters:
  not:
    - 'file.hasTag("archived")'

# 嵌套
filters:
  or:
    - file.hasTag("tag")
    - and:
        - file.hasTag("book")
        - file.hasLink("Textbook")
    - not:
        - file.hasTag("book")
        - file.inFolder("Required Reading")
```

### 过滤器运算符

| 运算符 | 含义 |
|--------|------|
| `==` | 等于 |
| `!=` | 不等于 |
| `>` | 大于 |
| `<` | 小于 |
| `>=` | 大于等于 |
| `<=` | 小于等于 |
| `&&` | 逻辑与 |
| `\|\|` | 逻辑或 |
| `!` | 逻辑非 |

## 属性类型

1. **笔记属性** — frontmatter 中定义的：`note.author` 或直接 `author`
2. **文件属性** — 文件元数据

| 属性 | 类型 | 说明 |
|------|------|------|
| `file.name` | String | 文件名 |
| `file.basename` | String | 无扩展名的文件名 |
| `file.path` | String | 完整路径 |
| `file.folder` | String | 父文件夹 |
| `file.ext` | String | 扩展名 |
| `file.size` | Number | 文件大小（字节）|
| `file.ctime` | Date | 创建时间 |
| `file.mtime` | Date | 修改时间 |
| `file.tags` | List | 文件中所有标签 |
| `file.links` | List | 内部链接 |
| `file.backlinks` | List | 反向链接 |
| `file.embeds` | List | 嵌入内容 |

3. **公式属性** — 计算值：`formula.my_formula`

### `this` 关键字

- 主内容区：指向 base 文件自身
- 嵌入式：指向嵌入文件
- 侧边栏：指向主内容区的活动文件

## 公式语法

```yaml
formulas:
  # 简单运算
  total: "price * quantity"

  # 条件逻辑
  status_icon: 'if(done, "✅", "⏳")'

  # 字符串格式化
  formatted_price: 'if(price, price.toFixed(2) + " dollars")'

  # 日期格式化
  created: 'file.ctime.format("YYYY-MM-DD")'

  # 距今天数（Duration 需访问 .days）
  days_old: '(now() - file.ctime).days'

  # 距到期天数
  days_until_due: 'if(due_date, (date(due_date) - today()).days, "")'
```

### 关键函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `date()` | `date(string): date` | 解析字符串为日期 |
| `now()` | `now(): date` | 当前日期时间 |
| `today()` | `today(): date` | 当前日期（时间=00:00:00）|
| `if()` | `if(cond, true, false?)` | 条件判断 |
| `duration()` | `duration(string): duration` | 解析时间段 |
| `file()` | `file(path): file` | 获取文件对象 |
| `link()` | `link(path, display?): Link` | 创建链接 |

### Duration 类型陷阱

日期相减返回 **Duration**，不是数字。必须先访问 `.days`/`.hours` 等字段：

```yaml
# ✅ 正确
"(date(due_date) - today()).days"
"(now() - file.ctime).days.round(0)"

# ❌ 错误 — Duration 不支持直接 round
"(now() - file.ctime).round(0)"
```

### 日期运算

```yaml
"now() + \"1 day\""        # 明天
"today() + \"7d\""         # 一周后
"now() - file.ctime"       # 返回 Duration
```

## 视图类型

### Table 视图

```yaml
views:
  - type: table
    name: "My Table"
    order:
      - file.name
      - status
      - due_date
    summaries:
      price: Sum
      count: Average
```

### Cards 视图

```yaml
views:
  - type: cards
    name: "Gallery"
    order:
      - file.name
      - cover_image
      - description
```

### List 视图

```yaml
views:
  - type: list
    name: "Simple List"
    order:
      - file.name
      - status
```

### Map 视图

```yaml
views:
  - type: map
    name: "Locations"
    # 需要 latitude/longitude 属性 + Maps 社区插件
```

map 视图需要笔记含 `latitude`/`longitude` 属性，且依赖 Maps 社区插件。

## 默认汇总公式

| 名称 | 适用类型 | 说明 |
|------|---------|------|
| `Average` | Number | 平均值 |
| `Min` | Number | 最小值 |
| `Max` | Number | 最大值 |
| `Sum` | Number | 总和 |
| `Range` | Number/Date | 极差 |
| `Median` | Number | 中位数 |
| `Stddev` | Number | 标准差 |
| `Earliest` | Date | 最早日期 |
| `Latest` | Date | 最晚日期 |
| `Checked` | Boolean | 真值计数 |
| `Unchecked` | Boolean | 假值计数 |
| `Empty` | Any | 空值计数 |
| `Filled` | Any | 非空值计数 |
| `Unique` | Any | 唯一值计数 |

## 完整示例

### 任务追踪

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'file.ext == "md"'

formulas:
  days_until_due: 'if(due, (date(due) - today()).days, "")'
  is_overdue: 'if(due, date(due) < today() && status != "done", false)'
  priority_label: 'if(priority == 1, "🔴 High", if(priority == 2, "🟡 Medium", "🟢 Low"))'

views:
  - type: table
    name: "Active Tasks"
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - status
      - formula.priority_label
      - due
      - formula.days_until_due
    groupBy:
      property: status
      direction: ASC
    summaries:
      formula.days_until_due: Average
```

### 阅读清单（Cards 视图）

```yaml
filters:
  or:
    - file.hasTag("book")
    - file.hasTag("article")

formulas:
  reading_time: 'if(pages, (pages * 2).toString() + " min", "")'
  status_icon: 'if(status == "reading", "📖", if(status == "done", "✅", "📚"))'

views:
  - type: cards
    name: "Library"
    order:
      - cover
      - file.name
      - author
      - formula.status_icon
    filters:
      not:
        - 'status == "dropped"'
```

### 每日笔记索引（Daily Notes Index）

```yaml
filters:
  and:
    - file.inFolder("Daily Notes")
    - '/^\d{4}-\d{2}-\d{2}$/.matches(file.basename)'
formulas:
  word_estimate: '(file.size / 5).round(0)'
  day_of_week: 'date(file.basename).format("dddd")'
views:
  - type: table
    name: "Recent Notes"
    limit: 30
    order:
      - file.name
      - formula.day_of_week
      - formula.word_estimate
      - file.mtime
```

kepano 原版示例：用正则 `/^\d{4}-\d{2}-\d{2}$/` 匹配 `YYYY-MM-DD` 文件名锁定每日笔记，用 `file.size / 5` 粗估字数，用 `date(file.basename).format("dddd")` 把文件名解析成日期并取星期。

## YAML 引用规则

- 含双引号的公式用单引号包裹：`'if(done, "Yes", "No")'`
- 含 `:`, `{`, `}`, `[`, `]`, `#`, `!` 等特殊字符的字符串必须加引号
- 公式中引用的每个 `formula.X` 必须在 `formulas` 区域有对应定义

## 常见陷阱

- **Duration 数学错误**：日期相减必须先访问 `.days` 字段
- **缺少 null 检查**：属性可能不存在，用 `if()` 保护
- **引用未定义公式**：`formula.total` 在 `order` 中出现但 `formulas` 中未定义 → 静默失败
- **YAML 特殊字符**：`:` 在未引号字符串中会破坏解析

## 嵌入 Bases

在普通笔记中嵌入 base 视图：

```
![[MyBase.base]]
![[MyBase.base#View Name]]
```

- `![[MyBase.base]]` 嵌入整个 base（含其所有视图）
- `![[MyBase.base#View Name]]` 嵌入指定名称的单个视图
