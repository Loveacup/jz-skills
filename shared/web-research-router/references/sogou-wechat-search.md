# Sogou 微信搜索 — WRR 辅助源评估

> 评估日期：2026-06-02 | 状态：搜索可用，内容不可达

## 概述

搜狗是唯一能索引微信公众号内容的搜索引擎。其微信搜索（`weixin.sogou.com`）可作为 WRR discovery 模式的中文补充源——即使只能拿到标题和摘要，对发现「有什么文章」仍然有独特价值。

## 双层策略

```
WRR 微信内容查询
  │
  ├── Tier 1: Sogou 微信搜索（discovery 层）
  │   └── curl → weixin.sogou.com/weixin?type=2&query=...
  │       返回：标题 + 摘要 + 公众号名 + 日期 + 加密链接
  │       价值：发现文章存在性
  │
  └── Tier 2: 原文获取（fetch 层，三路 fallback）
      ├── 路径 A: RSSHub / WeRSS（推荐）
      ├── 路径 B: Scrapling StealthyFetcher（兜底，成功率低）
      └── 路径 C: 浏览器手动访问
```

## 实测结果

### 搜索接口

```bash
curl -s -o result.html \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36' \
  -H 'Accept: text/html,application/xhtml+xml' \
  -H 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' \
  'https://weixin.sogou.com/weixin?type=2&query=关键词'
```

- ✅ HTTP 200，~33KB HTML，10 条结果/页
- ✅ 标题 + 摘要 + 来源公众号名 + 日期完整可用
- ❌ 所有文章链接为 `/link?url=...` 加密重定向

### 链接追链

```bash
curl -L -H '...' 'https://weixin.sogou.com/link?url=...'
```

- ❌ 直接跳转 `https://weixin.sogou.com/antispider/` 拦截页
- ❌ HTML 中不存在任何 `mp.weixin.qq.com` 真实直链
- ❌ 反爬发生在 HTTP 302 重定向阶段，不是 JS 渲染层

### 已有方案评估

| 方案 | 状态 | 说明 |
|:-----|:-----|:-----|
| `wechatsogou` (chyroc/WechatSogou) | ❌ 已失效 | `werkzeug.contrib` 在新版 Werkzeug 中已移除 |
| `sogou-weixin-mcp-server` (ptbsare) | ⚠️ 可构建 | `uvx` 构建成功，stdio 协议初始化需调试 |
| SearXNG `sogou_wechat` engine | ⚠️ 存在 | 代码已合入 SearXNG 主线，但自建实例 Google 失效 |

### 浏览器访问

Chrome/Playwright 直接访问 `weixin.sogou.com` → 立即触发 antispider 页面。需要人工过验证码。

## WRR 集成指南

### 触发条件

- query 含「微信 / 公众号 / 订阅号 / 搜狗」
- 中文语境 + 需要公众号视角
- 不对英文 query 调用

### 返回格式

加入 source_map，标注不可抓取：

```json
{
  "id": "sogou_1",
  "title": "文章标题",
  "snippet": "摘要内容...",
  "source": "公众号名称",
  "url": "/link?url=...（加密，不可追）",
  "fetchable": false,
  "fallback": "rsshub",
  "fetched_at": "2026-06-02T00:00:00Z",
  "confidence": "medium"
}
```

### 不做什么

- ❌ 不试图破解加密链接
- ❌ 不把 Scrapling 作为微信内容主抓取路径
- ❌ 不在 cron job 中自动抓微信原文

## 评估方法模板

评估任何新的 WRR 搜索源时，复用此 6 项测试：

1. 搜索接口可达性（curl + browser headers）
2. 搜索结果质量（标题/摘要/来源完整性）
3. 链接可追性（follow redirect → 是否被反爬拦截）
4. 真实 URL 可提取性（HTML/JS 中是否有直链）
5. 现有库/API 可用性（pip/npm install + 冒烟测试）
6. MCP server 可用性（如有，uvx 构建 + stdio 协议测试）

关联文档：
- Obsidian CQI: `02-Plan/web-research-router 持续质量改进计划.md` §2.2.1-2.2.2
- Scrapling skill: `autonomous-ai-agents/claude-code` 的兼容性矩阵
- Supermemory: `Scrapling for WeChat not usable; Sogou search returns encrypted links`
