# 钉钉群消息实时接收 — 替代方案调研

> 调研日期: 2026-06-06 | 来源: Exa + web_search + Tavily + CC agent team 讨论 + 本地实验

## 消息接收方案对比

| 方案 | 实时性 | 能收全部群消息？ | 需要权限 | 稳定性 |
|------|:---:|:---:|---|:---:|
| dingwave 本地解密（当前） | 分钟级 | ✅ | 无 | ⭐⭐⭐⭐ |
| Stream Mode 机器人 | 实时 | ❌ 仅 @机器人 | 企业应用 | ⭐⭐⭐⭐⭐ |
| RPA/UI 自动化 | 秒级 | ✅ | 无 | ⭐⭐ |
| 企业事件订阅 | 实时 | 取决于事件 | 管理员 | ⭐⭐⭐⭐ |

## 方案一：dingwave 本地解密（当前）

**优势**: 无侵入，不需要任何钉钉权限，能读到全部群消息。

**劣势**: 依赖钉钉桌面端持续运行；非实时；SQLite WAL 未合并可能导致数据滞后数小时（v1.1.0 修复）；macOS TCC 沙箱可能拦截文件访问。

## 方案二：Stream Mode 机器人

**原理**: WebSocket 长连接，客户端主动连接钉钉服务器，无需公网 IP。

**关键限制**: ⚠️ 群聊中只接收 @机器人的消息。私聊可收全部，群聊不行。

Hermes Agent 已原生支持: `hermes gateway setup` → DingTalk → Stream Mode。

## 方案三：RPA / UI 自动化

保持钉钉窗口打开，PyAutoGUI / 影刀RPA 抓取聊天区域。能实时但脆弱。

## 方案四：企业事件订阅

需要管理员权限 + 公网服务器。能否订阅"群消息全部内容"取决于钉钉版本。

---

# 图片与文件附件提取 — 技术方案调研

> 2026-06-06 | 来源: CC agent team 讨论 + 本地实验

## 背景

dingwave 解密文本，但图片/文件附件引用 `@lQLP...` 格式的 `mediaId`，无法直接 HTTP 访问。`ImageFiles/` 缓存只有其他会话的 `@lQDP...` 缩略图。

## 三路线（按可行性）

### 路线 A：Electron CDP 🥇

重启钉钉加 `--remote-debugging-port=9222` → Chrome DevTools Protocol 直连：
- `Runtime.evaluate` — 在已登录渲染进程里执行 JS，拿到 authMediaId→URL 逻辑
- `Network` domain — 抓取图片下载请求的完整 URL + auth header
- 把认证问题转化为"在已登录上下文执行 JS"，绕开 access_token
- 验证成本 10 秒：`curl localhost:9222/json`

### 路线 A+B 组合（推荐终局）

1. CDP Network domain 抓一次完整图片下载请求
2. 从样本逆出 authMediaId → URL 签名规则
3. 固化成离线脚本 → 不需 CDP 常驻

### 路线 C：asar 静态分析

解包 `app.asar` → 读懂 authMediaId 签名算法 → 纯离线下载。最优但逆向成本高，建议作 A 成功后提炼固化。

### 路线 B：Surge MITM 🥈

被动、不中断进程。风险：certificate pinning 可能挡住核心 API，但图片 CDN 通常不 pin。

### 路线 D：lldb/dtrace 🥉

仅兜底。

## 推荐顺序

1. 探针：重启钉钉验证 CDP（10s）
2. CDP Network 抓图片下载 → 逆出签名 → 固化离线脚本
3. CDP 屏蔽 → 退路线 B
4. D 仅兜底

## 本地实验

- 9222 监听但拒绝连接（未注入 flag）
- ImageFiles/ 12 张缩略图 ID 不匹配
- 无 macOS `storage/file/`（Windows 有）
- `127.0.0.1:8440` 可连但 404
