# Obsidian CLI 参考

> 来源：[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) · 适配 Hermes

使用 `obsidian` CLI 与运行中的 Obsidian 实例交互。需要 Obsidian 处于打开状态。

## 语法

**参数** 用 `=` 赋值，含空格的值用引号包裹：

```bash
obsidian create name="My Note" content="Hello world"
```

**标志** 是布尔开关，不加值：

```bash
obsidian create name="My Note" silent overwrite
```

多行内容用 `\n` 换行、`\t` 缩进。

## 文件定位

- `file=` — 按 wikilink 方式解析（仅文件名，无需路径或扩展名）
- `path=` — 从 vault 根目录的精确路径，如 `folder/note.md`

不指定时默认为当前活动文件。

## Vault 定位

默认操作最近聚焦的 vault。用 `vault=` 作为第一个参数指定目标：

```bash
obsidian vault="My Vault" search query="test"
```

## 常用命令

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
```

- `--copy`：复制输出到剪贴板
- `silent`：阻止文件自动打开
- `total`：列表命令返回计数

## 插件开发

代码修改后的开发/测试循环：

1. **重载插件**：
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **检查错误** — 如有错误，修复后从步骤 1 重复：
   ```bash
   obsidian dev:errors
   ```
3. **验证视觉** — 截图或 DOM 检查：
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **检查控制台输出**：
   ```bash
   obsidian dev:console level=error
   ```

### 额外开发命令

在应用上下文中执行 JavaScript：

```bash
obsidian eval code="app.vault.getFiles().length"
```

检查 CSS 值：

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

切换移动端模拟：

```bash
obsidian dev:mobile on
```

> 运行 `obsidian help` 查看完整命令列表（包括 CDP 和调试器控制）。
