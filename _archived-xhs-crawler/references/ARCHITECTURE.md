# XHS Crawler v5 架构设计

## 系统流转图

📱 XHS Link / Keyword / Creator URL
    ↓
🔀 Mode Detection (link / search / creator)
    ↓
┌─── Link Mode ──────────────────────────────┐
│ 🖥️ CDP + Playwright (xhs_extractor.py)      │
│     → Page navigation + login session reuse  │
│     → Comment scroll loading                 │
│     → JS injection extraction (extractors.js)│
│     → Carousel screenshot + Qwen3-VL OCR     │
│     → Output: JSON data to stdout            │
└──────────────────────────────────────────────┘
┌─── Search/Creator Mode ────────────────────┐
│ 🔑 xhshow signing library                  │
│     → Pure algorithm signature generation   │
│ 📡 xhs_api.py                              │
│     → search_notes / get_note_detail        │
│     → get_note_comments                     │
│     → get_creator_info / get_creator_notes  │
│     → Output: JSON data                     │
└──────────────────────────────────────────────┘
    ↓
🤖 Agent generates report (using references/xhs-report-prompt.md template)
    ↓
💾 Save to Obsidian / output to user

## 模块职责表

| Module | File | Responsibility |
|--------|------|---------------|
| CDP Extractor | scripts/xhs_extractor.py | CDP connection, page nav, JS extraction, carousel OCR |
| API Client | scripts/xhs_api.py | Pure API calls (search/detail/comments/creator) via xhshow signing |
| Signing Library | xhshow/ | XHS request signature generation (X-S, X-T, x-S-Common) |
| Carousel OCR | scripts/xhs_carousel_ocr.py | Screenshot + Qwen3-VL OCR |
| Cookie Manager | scripts/cookie_manager.py | Save/load XHS cookies |
| URL Parser | scripts/parse_xhs_url.py | Extract note_id from various URL formats |
| JS Extractor | scripts/extractors.js | Browser-side content extraction |
| Report Template | references/xhs-report-prompt.md | LLM prompt template for report generation |

## 核心设计变更

- **移除外部 API 链**: 删除了旧版本中多模型自动切换逻辑。
- **内置报告生成**: 依靠 Agent 自身的 LLM 能力配合 `xhs-report-prompt.md` 生成深度报告。
- **混合模式**: 引入基于 `xhshow` 算法签名的纯 API 模式，用于搜索和博主主页抓取。
- **CDP 深度提取**: 仅在需要处理复杂详情页（如轮播图 OCR、大量评论滚动）时使用 Playwright。
- **全环境变量化**: 所有硬编码路径均已迁移至环境变量，支持跨设备部署。

## 错误处理工作流

### 优雅降级策略

```
用户请求
  ↓
尝试主方案
  ↓
成功？──→ 是 ──→ 返回结果
  ↓ 否
记录失败原因
  ↓
尝试备用方案
  ↓
成功？──→ 是 ──→ 返回结果 + 降级通知
  ↓ 否
返回部分数据 + 错误标注
```

### 具体降级链

| 主方案 | 备用方案 | 最终降级 | 错误标注 |
|:---|:---|:---|:---|
| CDP 提取 | API 模式 | 返回基础数据 | `[CDP失败，使用API]` |
| OCR 识别 | 跳过 OCR | 仅文本内容 | `[OCR不可用]` |
| 评论滚动 | 减少滚动次数 | 部分评论 | `[评论数据不足]` |
| 完整数据 | 部分字段 | 必需字段 | `[字段缺失列表]` |

### 错误传播规则

**部分失败 ≠ 全部失败**

```python
# ✅ 正确：章节级错误标注
result = {
    "title": "笔记标题",
    "content": "正文内容",
    "comments": "[获取失败 - 需要登录]",  # 标注而非跳过
    "carousel_ocr": "[OCR服务不可用]"
}

# ❌ 错误：直接跳过或返回空
result = {
    "title": "笔记标题",
    "content": "正文内容"
    # 缺少 comments 和 carousel_ocr 字段
}
```

### 章节级错误标注规范

| 标注 | 含义 | 使用场景 |
|:---|:---|:---|
| `[数据不足]` | 正常但数据量少 | 评论少于预期 |
| `[获取失败]` | 技术错误 | API 返回错误 |
| `[需要登录]` | 权限限制 | 私密内容 |
| `[不支持]` | 功能限制 | 视频笔记暂不支持 |
| `[超时]` | 操作超时 | 网络慢 |
| `[降级]` | 使用备用方案 | 主方案失败 |

### 新增工具模块

#### validators.py - 数据契约验证
- **职责**: 验证提取数据的完整性
- **关键函数**:
  - `validate_data()`: 检查必需字段
  - `validate_field_types()`: 检查字段类型
  - `generate_data_report()`: 生成数据质量报告

#### progress.py - 进度汇报器
- **职责**: 统一的进度显示和状态汇报
- **关键类**:
  - `ProgressReporter`: 带 emoji 的进度汇报
  - `SilentReporter`: 静默模式（用于批量操作）

#### config.py - 配置管理
- **职责**: 集中管理环境变量和配置
- **关键特性**:
  - 自动加载 `.env` 文件
  - 自动检测 Obsidian Vault
  - 配置验证

## 性能优化

### 并发控制
- **CDP 模式**: 单页面顺序执行（避免浏览器过载）
- **API 模式**: 支持批量并发（需控制速率）

### 缓存策略
- **Cookie**: 本地文件缓存，避免重复登录
- **签名**: 复用签名结果（有效期内）

### 资源清理
- **临时文件**: 自动清理 `/tmp/xhs_*`
- **浏览器页面**: 提取完成后关闭页面
- **CDP 连接**: 保持长连接，避免重复建立

## 安全考虑

### 敏感信息处理
- **Cookie**: 仅存储在 `~/.xhs_cookie`，不输出到日志
- **Token**: 内存中使用，不持久化
- **日志**: 自动脱敏，移除敏感字段

### 反爬虫对抗
- **自适应延迟**: 根据成功率动态调整
- **指纹模拟**: 模拟真实浏览器环境
- **请求分散**: 避免固定时间模式
