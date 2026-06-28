# WRR v3 → v4 迁移指南

## 主要变化

1. **架构重构**: 从单文件拆分为结构化包
2. **Exa 强化**: 自动路由模式（fast/auto/deep-lite/deep）
3. **新增工具**: `web_similar`（相似内容查找）
4. **废弃 PI 支持**: 专注 Hermes 单一实现

## 版本历史

| 版本 | 说明 |
|------|------|
| v3.9 | 旧 skill 叙事阶段 |
| v3.12.2 | 多运行时自适应阶段 |
| v1.1.0 | Hermes plugin 旧实现 |
| **v4.0.0** | **当前：统一 Hermes 实现** |

## 兼容性

- `web_search` / `web_fetch` 接口保持兼容
- 新增 `mode` 参数（可选）
- 新增 `web_similar` 工具
