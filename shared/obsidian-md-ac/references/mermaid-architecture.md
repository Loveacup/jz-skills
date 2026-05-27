> [!info] Obsidian Integration
> 在 Obsidian 中，直接使用 \`\`\`mermaid 代码块即可渲染图表，无需额外配置。本文档是 [obsidian-md-ac](../SKILL.md) skill 的子参考。

# Architecture Diagrams Reference

Architecture diagrams 用于可视化云服务、CI/CD 部署和基础设施关系。引入于 Mermaid v11.1.0。

> [!warning] Obsidian 兼容性
> - 需要 Obsidian 1.8.3+（Mermaid v11）
> - **仅 5 个默认图标可用**：`cloud`, `database`, `disk`, `internet`, `server`
> - Iconify 图标包（`logos:docker` 等）在 Obsidian 中**不可用**，需要社区插件 obsidian-mermaid-icons
> - 使用不存在的图标名会导致图表**静默失败**，不会显示错误

## Basic Syntax

```mermaid
architecture-beta
    group public_api(cloud)[Public API]
    service api1(server)[API Server] in public_api
    service db(database)[Database]

    api1:R --> L:db
```

## Building Blocks

### Groups

将相关服务分组：

```
group {groupId}({icon})[{title}] (in {parentId})?
```

```mermaid
architecture-beta
    group public_api(cloud)[Public API]
    group private_api(cloud)[Private API] in public_api
```

### Services

声明服务节点：

```
service {serviceId}({icon})[{title}] (in {parentId})?
```

```mermaid
architecture-beta
    service api(server)[API Server]
    service db(database)[Database]
    service store(disk)[File Storage]
```

### Edges

连接服务：

```
{serviceId}{{group}}?:{T|B|L|R} {<}?--{>}? {T|B|L|R}:{serviceId}{{group}}?
```

**方向：** `T` (上) · `B` (下) · `L` (左) · `R` (右)

**箭头：** `<` 入方向 · `>` 出方向

```mermaid
architecture-beta
    service client(internet)[Client]
    service api(server)[API]
    service db(database)[Database]

    client:B --> T:api
    api:R --> L:db
```

### Junctions

创建四向分支：

```
junction {junctionId} (in {parentId})?
```

```mermaid
architecture-beta
    service input(server)[Input]
    service output1(server)[Output 1]
    service output2(server)[Output 2]

    junction j1

    input:R --> L:j1
    j1:T --> B:output1
    j1:B --> T:output2
```

## Icons

### 默认图标（Obsidian 可用）

| Icon | Name | Typical Use |
|------|------|-------------|
| `cloud` | Cloud | Cloud services, API gateways, CDN |
| `database` | Database | SQL/NoSQL databases, data stores |
| `disk` | Disk | File storage, object storage, cache |
| `internet` | Internet | External users, public network |
| `server` | Server | Application servers, load balancers, microservices |

> [!caution] 图标限制
> 在 Obsidian 中**只有上述 5 个图标可用**。使用 `load_balancer`、`api`、`redis` 等自定义名称会导致图表**静默渲染失败**。
>
> **替代策略：** 用 `server` 替代 load balancer/API server，用 `disk` 替代 cache/storage，通过 `[Label]` 标签区分。

### Iconify 图标包（仅 CLI 可用）

如果使用 Mermaid CLI (`mmdc`) 导出 SVG，可安装 iconify 图标包获得 200,000+ 图标：

```bash
npm install @iconify-json/logos @mermaid-js/mermaid-cli
mmdc --iconPacks @iconify-json/logos -i ./diagram.mmd -o ./output.svg
```

常用包：`@iconify-json/logos`（品牌）· `@iconify-json/mdi`（Material Design）· `@iconify-json/simple-icons`

## Complex Example

### 负载均衡架构

```mermaid
architecture-beta
    group internet_zone(cloud)[Internet Zone]
    group private_vpc(cloud)[Private VPC]

    service lb(server)[Load Balancer] in internet_zone
    service api1(server)[API Server 1] in private_vpc
    service api2(server)[API Server 2] in private_vpc
    service db(database)[Primary Database] in private_vpc
    service replica(database)[Read Replica] in private_vpc
    service cache(disk)[Redis Cache] in private_vpc

    lb:R --> L:api1
    lb:R --> L:api2
    api1:R --> L:db
    api2:R --> L:db
    api1:B --> T:cache
    api2:B --> T:cache
    db:R --> L:replica
```

### 微服务架构

```mermaid
architecture-beta
    group external(internet)[External]
    group gateway(cloud)[API Gateway]
    group services(cloud)[Microservices]
    group data(cloud)[Data Layer]

    service users(internet)[Users] in external
    service gw(server)[Gateway] in gateway
    service auth(server)[Auth Service] in services
    service app(server)[App Service] in services
    service userdb(database)[User DB] in data
    service appdb(database)[App DB] in data
    service files(disk)[File Store] in data

    users:B --> T:gw
    gw:B --> T:auth
    gw:B --> T:app
    auth:B --> T:userdb
    app:B --> T:appdb
    app:R --> L:files
```

### CI/CD Pipeline

```mermaid
architecture-beta
    group dev(cloud)[Development]
    group ci(cloud)[CI/CD]
    group prod(cloud)[Production]

    service repo(disk)[Git Repo] in dev
    service build(server)[Build Server] in ci
    service test(server)[Test Runner] in ci
    service staging(server)[Staging] in prod
    service live(server)[Production] in prod
    service db(database)[Database] in prod

    repo:R --> L:build
    build:R --> L:test
    test:R --> L:staging
    staging:R --> L:live
    live:B --> T:db
```

## Edge Patterns

| Pattern              | Description       |
| -------------------- | ----------------- |
| `A:R -- L:B`         | Horizontal edge   |
| `A:T -- B:B`         | Vertical edge     |
| `A:R --> L:B`        | Edge with arrow   |
| `A:R <--> L:B`       | Bidirectional     |
| `A{group}:R --> L:B` | From group boundary |

## Group Edges

用 `{group}` 修饰符连接分组：

```mermaid
architecture-beta
    group frontend(cloud)[Frontend]
    group backend(cloud)[Backend]

    service client(internet)[Client] in frontend
    service api(server)[API] in backend

    client{group}:B --> T:api{group}
```

## Best Practices

1. **只用默认图标** — 在 Obsidian 中坚持 `cloud`, `database`, `disk`, `internet`, `server`
2. **用标签区分** — 相同图标通过 `[Label]` 标签说明用途（如 `service cache(disk)[Redis Cache]`）
3. 按环境/层级分组 — public/private 或 frontend/backend
4. 标注协议 — 在标签中说明 HTTPS、TCP 等
5. 用 junction 做扇出 — fan-out 模式
6. 保持聚焦 — 复杂架构拆成多个视图
7. **增量测试** — 每添加几个节点就在 Obsidian 中预览

## Reference

- [Official Documentation](https://mermaid.js.org/syntax/architecture.html)
- [Iconify Icons](https://iconify.design)（仅 CLI 可用）
