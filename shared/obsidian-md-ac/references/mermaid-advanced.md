> [!info] Obsidian Integration
> 在 Obsidian 中，直接使用 \`\`\`mermaid 代码块即可渲染图表，无需额外配置。本文档是 [obsidian-md-ac](../SKILL.md) skill 的子参考。

# Advanced Mermaid Features

Obsidian 中 Mermaid 图表的高级配置、样式、主题和专业技巧。

**本文档涵盖：** Frontmatter 配置、内置主题、自定义色彩、CSS 类样式、布局与外观选项。
**各图表类型特有的高级用法**（如 Sequence 的 alt/loop、Class 的接口继承）见对应的专用参考文件。

> [!warning] Obsidian 兼容性须知
> - **ELK 布局不可用** — Obsidian 的 Mermaid v11 不包含 ELK 布局引擎，只能用 `dagre`
> - **统一使用 frontmatter config** — 不要用旧版 `%%{init: {...}}%%` 语法，行为不一致
> - **HTML/React 集成不适用** — Obsidian 通过 ` ```mermaid ` 代码块渲染
> - **CLI 导出不适用** — `mmdc` 是独立工具，不在 Obsidian 内使用

## Frontmatter 配置（推荐方式）

在图表顶部添加 YAML 配置：

```mermaid
---
config:
  theme: dark
  themeVariables:
    primaryColor: "#ff6b6b"
    primaryTextColor: "#fff"
    primaryBorderColor: "#333"
    lineColor: "#666"
    secondaryColor: "#4ecdc4"
    tertiaryColor: "#ffe66d"
---
flowchart TD
    A --> B
```

> [!warning] 不要使用旧版 init 语法
> 避免使用 `%%{init: {'theme':'forest'}}%%` 这种内联初始化语法。它是旧版 Mermaid 遗留语法，在 Obsidian 的 Mermaid v11 中行为可能不一致。**统一使用 YAML frontmatter config。**

## Themes

### Built-in Themes

| Theme | Description |
|-------|-------------|
| `default` | Standard blue theme |
| `forest` | Green earth tones |
| `dark` | Dark mode friendly |
| `neutral` | Grayscale professional |
| `base` | Minimal base theme for customization |

### Theme Examples

**Default Theme:**
```mermaid
---
config:
  theme: default
---
flowchart LR
    A[Start] --> B[Process]
    B --> C{Decision}
    C -->|Yes| D[Action 1]
    C -->|No| E[Action 2]
```

**Dark Theme:**
```mermaid
---
config:
  theme: dark
---
flowchart LR
    A[Start] --> B[Process]
    B --> C{Decision}
```

**Forest Theme:**
```mermaid
---
config:
  theme: forest
---
flowchart LR
    A[Start] --> B[Process]
```

## Custom Theme Variables

覆盖特定颜色（从 `base` 主题开始以获得完全控制）：

```mermaid
---
config:
  theme: base
  themeVariables:
    primaryColor: "#ff6b6b"
    primaryTextColor: "#fff"
    primaryBorderColor: "#d63031"
    lineColor: "#74b9ff"
    secondaryColor: "#00b894"
    tertiaryColor: "#fdcb6e"
    background: "#f0f0f0"
    mainBkg: "#ffffff"
    textColor: "#333333"
    nodeBorder: "#333333"
    clusterBkg: "#f9f9f9"
    clusterBorder: "#666666"
---
flowchart TD
    A --> B --> C
```

## Layout Options

Obsidian 仅支持 **dagre** 布局引擎：

```mermaid
---
config:
  layout: dagre
---
flowchart TD
    A --> B
```

> [!warning] ELK 布局不可用
> ELK 从 Mermaid v11.0 主包移除，需单独安装 `@mermaid-js/layout-elk`。Obsidian 未包含此包。
>
> **替代方案：**
> - 调整流向（`TD` vs `LR`）减少交叉线
> - 拆分为多个小图
> - 调整节点声明顺序（影响布局优先级）
> - 使用 subgraph 分组引导布局

## Look Options

### Classic Look

传统 Mermaid 外观：

```mermaid
---
config:
  look: classic
---
flowchart LR
    A --> B --> C
```

### Hand-Drawn Look

手绘草图风格：

```mermaid
---
config:
  look: handDrawn
---
flowchart LR
    A --> B --> C
```

## Complete Configuration Example

```mermaid
---
config:
  theme: base
  look: handDrawn
  layout: dagre
  themeVariables:
    primaryColor: "#ff6b6b"
    primaryTextColor: "#fff"
    primaryBorderColor: "#d63031"
    lineColor: "#74b9ff"
    secondaryColor: "#00b894"
    tertiaryColor: "#fdcb6e"
---
flowchart TD
    Start([Begin Process]) --> Input[Gather Data]
    Input --> Process{Valid?}
    Process -->|Yes| Store[(Save to DB)]
    Process -->|No| Error[Show Error]
    Store --> Notify[Send Notification]
    Error --> Input
    Notify --> End([Complete])
```

## Diagram-Specific Styling

### Flowchart Styling

**Class-based styling（推荐）：**
```mermaid
flowchart TD
    A[Normal]:::success
    B[Warning]:::warning
    C[Error]:::error

    classDef success fill:#00b894,stroke:#00a383,color:#fff
    classDef warning fill:#fdcb6e,stroke:#e8b923,color:#333
    classDef error fill:#ff6b6b,stroke:#ee5253,color:#fff

    A --> B --> C
```

**Node-specific styling：**
```mermaid
flowchart LR
    A[Node A]
    B[Node B]
    C[Node C]

    style A fill:#ff6b6b,stroke:#333,stroke-width:4px
    style B fill:#4ecdc4,stroke:#333,stroke-width:2px
    style C fill:#ffe66d,stroke:#333,stroke-width:2px

    A --> B --> C
```

**Link styling：**
```mermaid
flowchart LR
    A --> B
    B --> C
    C --> D

    linkStyle 0 stroke:#ff6b6b,stroke-width:4px
    linkStyle 1 stroke:#4ecdc4,stroke-width:2px
    linkStyle 2 stroke:#ffe66d,stroke-width:2px
```

### Sequence Diagram Theming

```mermaid
---
config:
  theme: forest
---
sequenceDiagram
    participant A
    participant B
    participant C

    A->>B: Message 1
    B->>C: Message 2

    Note over A,C: Styled note
```

### Class Diagram Theming

```mermaid
---
config:
  theme: dark
---
classDiagram
    class User {
        +String name
        +login()
    }

    class Admin {
        +manageUsers()
    }

    User <|-- Admin
```

## Click Events and Links

添加交互元素（链接会在浏览器中打开）：

```mermaid
flowchart LR
    A[GitHub]
    B[Documentation]
    C[Live Demo]

    click A "https://github.com" "Go to GitHub"
    click B "https://mermaid.js.org" "View Docs"
    click C "https://mermaid.live" "Try Live Editor"

    A --> B --> C
```

## Subgraph Styling

```mermaid
flowchart TB
    subgraph Frontend
        A[Web App]
        B[Mobile App]
    end

    subgraph Backend
        C[API]
        D[Database]
    end

    A & B --> C
    C --> D

    style Frontend fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style Backend fill:#fff3e0,stroke:#ff9800,stroke-width:2px
```

## Comments and Documentation

```mermaid
flowchart TD
    %% This is a single-line comment

    %% Multi-line comments can be created
    %% by using multiple comment lines

    A[Start]
    B[Process]
    C[End]

    %% Define relationships
    A --> B
    B --> C

    %% Add styling
    style A fill:#90EE90
    style C fill:#FFB6C1
```

> [!caution] 注释中避免使用 `{}`
> Mermaid 解析器会将 `{}` 解释为语法结构，即使在 `%%` 注释中也可能破坏图表渲染。用自然语言代替。

## Complex Styling Example

```mermaid
flowchart TB
    subgraph production[Production Environment]
        direction LR
        lb[Load Balancer]

        subgraph servers[Application Servers]
            app1[Server 1]
            app2[Server 2]
            app3[Server 3]
        end

        cache[(Redis Cache)]
        db[(PostgreSQL)]
    end

    subgraph monitoring[Monitoring]
        logs[Log Aggregator]
        metrics[Metrics Dashboard]
    end

    users[Users] --> lb
    lb --> app1 & app2 & app3
    app1 & app2 & app3 --> cache
    app1 & app2 & app3 --> db
    app1 & app2 & app3 --> logs
    logs --> metrics

    style production fill:#e8f5e9,stroke:#4caf50,stroke-width:3px
    style servers fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style monitoring fill:#e3f2fd,stroke:#2196f3,stroke-width:2px

    style lb fill:#ffeb3b,stroke:#fbc02d,stroke-width:2px
    style cache fill:#ce93d8,stroke:#ab47bc,stroke-width:2px
    style db fill:#ce93d8,stroke:#ab47bc,stroke-width:2px

    classDef serverClass fill:#81c784,stroke:#4caf50,stroke-width:2px,color:#000
    class app1,app2,app3 serverClass

    linkStyle 0,1,2,3 stroke:#4caf50,stroke-width:2px
    linkStyle 4,5,6,7,8,9 stroke:#ff9800,stroke-width:1px
```

## Performance Tips for Large Diagrams

**在 Obsidian 中优化复杂图表（无 ELK 的替代方案）：**
- 用 `subgraph` 组织复杂性并引导布局
- 调整流向（`TD` vs `LR` vs `TB`）减少交叉线
- 超过 20 个节点的图拆成多个聚焦视图
- 样式集中在关键元素 — 颜色太多降低清晰度
- 用 `A & B & C --> D` 语法简化多连接

## Accessibility Considerations

```mermaid
---
config:
  theme: base
  themeVariables:
    primaryColor: "#0066cc"
    primaryTextColor: "#ffffff"
    primaryBorderColor: "#003d7a"
    lineColor: "#333333"
    background: "#ffffff"
    mainBkg: "#f0f0f0"
---
flowchart TD
    A[High Contrast Text] --> B[Clear Labels]
    B --> C[Meaningful Colors]
```

**Accessibility tips:**
- Use high contrast color combinations
- Don't rely solely on color to convey meaning
- Include descriptive text labels
- Test with color blindness simulators
- Consider dark mode alternatives (use `dark` theme or test with Obsidian's dark mode)

## Best Practices for Advanced Features

1. **Use themes consistently** — 同一笔记中相关图表使用同一主题
2. **Don't over-style** — 颜色太多降低清晰度
3. **Test hand-drawn look** — 某些场景 `handDrawn` 比 `classic` 更合适
4. **Use subgraphs for complex layouts** — 这是 Obsidian 中引导布局的主要方式
5. **Comment complex configurations** — 解释不直观的样式选择（但注释中避免 `{}`）
6. **Keep it accessible** — 足够的颜色对比度
7. **Use `base` theme for custom colors** — 其他主题会部分覆盖你的 themeVariables
8. **Prefer `classDef` over `style`** — 更可复用、更整洁
