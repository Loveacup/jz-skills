# legacy/ —— CDP + xhshow 兜底链路（非主力）

主力后端已切换为 **XHS-Downloader 子进程**（见 `scripts/xhs_backend.py`），
免登录即可提取元数据、标签、互动数据、图片 URL。

本目录保留旧的 CDP 浏览器自动化链路，**仅在需要 XHS-Downloader 拿不到的数据时**
作为兜底：

- **评论内容**（XHS-Downloader 免登录模式拿不到，报告第 2 章依赖）
- **轮播图 OCR**（XHS-Downloader 只返回图片 URL，图文笔记正文常嵌在图里）

## 文件

| 文件 | 用途 | 依赖 |
|---|---|---|
| `xhs_extractor_v2.py` | CDP 提取器（正文 + 评论 + 轮播图截图） | Chrome CDP + 登录态 |
| `xhs_carousel_ocr.py` | 轮播图 Qwen3-VL OCR | OCR 服务 |
| `cookie_manager.py` | Cookie 存取（`~/.xhs_cookie`） | — |
| `extractors.js` | 浏览器端 JS 提取逻辑（注入用） | DOM 结构，极脆弱 |
| `config.py` `progress.py` `validators.py` | 旧链路支持模块 | — |

## 何时用

仅当报告**必须**包含评论分析或图文 OCR，且 XHS-Downloader 主力路径已成功拿到元数据时，
再启用本链路补齐评论/OCR。前提：Chrome CDP（端口 19222）+ 小红书登录态。

## ⚠️ 注意

- 这些脚本依赖小红书前端 DOM 与签名，**容易随平台更新失效**，正是当初切换到
  XHS-Downloader 的原因。改动前确认 DOM 是否变化。
- 遇到 IP 风控（错误码 `300012`）**立即止损**，不要轮换方案（见 SKILL.md）。
