# JSON Canvas 参考

> 来源：[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) · 基于 [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)

创建和编辑 Obsidian Canvas（`.canvas`）文件——可视化画布，含节点、边、分组和连接。

## 工作流

### 1. 创建新 Canvas

1. 创建 `.canvas` 文件，基础结构 `{"nodes": [], "edges": []}`
2. 为每个节点生成唯一 16 字符 hex ID（如 `"6f0ad84f44ce9c17"`）
3. 添加节点，必填字段：`id`, `type`, `x`, `y`, `width`, `height`
4. 添加边，引用有效节点 ID（`fromNode`/`toNode`）
5. **验证**：解析 JSON 确认有效，所有 `fromNode`/`toNode` 值在 nodes 数组中存在

### 2. 添加节点

1. 读取并解析现有 `.canvas` 文件
2. 生成不与现有 ID 冲突的唯一 ID
3. 选择不重叠的位置（留 50-100px 间距）
4. 追加节点到 `nodes` 数组
5. 可选：添加连接新节点与现有节点的边
6. **验证**：所有 ID 唯一，边引用有效

### 3. 连接两个节点

1. 识别源节点和目标节点 ID
2. 生成唯一边 ID
3. 设置 `fromNode` / `toNode`
4. 可选：设置 `fromSide`/`toSide`（`top`, `right`, `bottom`, `left`）
5. 可选：设置 `label` 给边添加描述文字
6. **验证**：确认 `fromNode` 和 `toNode` 引用存在

## 文件结构

```json
{
  "nodes": [],
  "edges": []
}
```

- `nodes`（可选）：节点对象数组，顺序决定 z-index（第一个=底层，最后一个=顶层）
- `edges`（可选）：边对象数组

## 节点

### 通用属性

| 属性 | 必需 | 类型 | 说明 |
|------|:--:|------|------|
| `id` | ✅ | string | 唯一 16 字符 hex 标识符 |
| `type` | ✅ | string | `text`, `file`, `link`, `group` |
| `x` | ✅ | integer | X 位置（像素），坐标可为负 |
| `y` | ✅ | integer | Y 位置（像素），向下递增 |
| `width` | ✅ | integer | 宽度（像素）|
| `height` | ✅ | integer | 高度（像素）|
| `color` | ❌ | canvasColor | 预设 `"1"`-`"6"` 或 hex `"#FF0000"` |

### Text 节点

| 属性 | 必需 | 类型 | 说明 |
|------|:--:|------|------|
| `text` | ✅ | string | 支持 Markdown 语法的纯文本 |

```json
{
  "id": "6f0ad84f44ce9c17",
  "type": "text",
  "x": 0,
  "y": 0,
  "width": 400,
  "height": 200,
  "text": "# Hello World\n\nThis is **Markdown** content."
}
```

> 🪤 **换行陷阱**：JSON 中用 `\n`，不要用字面的 `\\n`。

### File 节点

| 属性 | 必需 | 类型 | 说明 |
|------|:--:|------|------|
| `file` | ✅ | string | 系统内文件路径 |
| `subpath` | ❌ | string | 链接到标题或块（以 `#` 开头）|

```json
{
  "id": "a1b2c3d4e5f67890",
  "type": "file",
  "x": 500,
  "y": 0,
  "width": 400,
  "height": 300,
  "file": "Attachments/diagram.png"
}
```

### Link 节点

| 属性 | 必需 | 类型 | 说明 |
|------|:--:|------|------|
| `url` | ✅ | string | 外部 URL |

```json
{
  "id": "c3d4e5f678901234",
  "type": "link",
  "x": 1000,
  "y": 0,
  "width": 400,
  "height": 200,
  "url": "https://obsidian.md"
}
```

### Group 节点

分组是可视化容器，用于组织其他节点。子节点应放置于分组边界内。

| 属性 | 必需 | 类型 | 说明 |
|------|:--:|------|------|
| `label` | ❌ | string | 分组标签 |
| `background` | ❌ | string | 背景图片路径 |
| `backgroundStyle` | ❌ | string | `cover`, `ratio`, `repeat` |

```json
{
  "id": "d4e5f6789012345a",
  "type": "group",
  "x": -50,
  "y": -50,
  "width": 1000,
  "height": 600,
  "label": "Project Overview",
  "color": "4"
}
```

## 边

通过 `fromNode` 和 `toNode` ID 连接节点。

| 属性 | 必需 | 类型 | 默认 | 说明 |
|------|:--:|------|------|------|
| `id` | ✅ | string | - | 唯一标识符 |
| `fromNode` | ✅ | string | - | 源节点 ID |
| `fromSide` | ❌ | string | - | `top`, `right`, `bottom`, `left` |
| `fromEnd` | ❌ | string | `none` | `none` 或 `arrow` |
| `toNode` | ✅ | string | - | 目标节点 ID |
| `toSide` | ❌ | string | - | `top`, `right`, `bottom`, `left` |
| `toEnd` | ❌ | string | `arrow` | `none` 或 `arrow` |
| `color` | ❌ | canvasColor | - | 线条颜色 |
| `label` | ❌ | string | - | 文字标签 |

```json
{
  "id": "0123456789abcdef",
  "fromNode": "6f0ad84f44ce9c17",
  "fromSide": "right",
  "toNode": "a1b2c3d4e5f67890",
  "toSide": "left",
  "toEnd": "arrow",
  "label": "leads to"
}
```

## 颜色

| 预设 | 颜色 |
|------|------|
| `"1"` | 红色 |
| `"2"` | 橙色 |
| `"3"` | 黄色 |
| `"4"` | 绿色 |
| `"5"` | 青色 |
| `"6"` | 紫色 |

预设颜色值有意未定义——应用使用各自品牌色。也可直接使用 hex（如 `"#FF0000"`）。

## ID 生成

生成 16 字符小写十六进制字符串（64 位随机值）：

```
"6f0ad84f44ce9c17"
"a3b2c1d0e9f8a7b6"
```

## 布局指南

- 坐标可为负数（canvas 无限延伸）
- `x` 向右增加，`y` 向下增加
- 节点间距 50-100px；分组内边距 20-50px
- 对齐到网格（10 或 20 的倍数）更整洁

| 节点类型 | 推荐宽度 | 推荐高度 |
|---------|---------|---------|
| 小文本 | 200-300 | 80-150 |
| 中文本 | 300-450 | 150-300 |
| 大文本 | 400-600 | 300-500 |
| 文件预览 | 300-500 | 200-400 |
| 链接预览 | 250-400 | 100-200 |

## 验证清单

1. 所有 `id` 值在 nodes 和 edges 中唯一 ✅
2. 每个 `fromNode` 和 `toNode` 引用存在 ✅
3. 每种节点类型必填字段完整（`text`/`file`/`url`）✅
4. `type` 为 `text`、`file`、`link` 或 `group` ✅
5. `fromSide`/`toSide` 值为 `top`, `right`, `bottom`, `left` ✅
6. `fromEnd`/`toEnd` 值为 `none` 或 `arrow` ✅
7. 颜色预设为 `"1"`-`"6"` 或有效 hex ✅
8. JSON 有效可解析 ✅
