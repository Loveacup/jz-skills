# TikHub 不可用时的备用方案

默认路由由 `SKILL.md` 定义。本文件只在 TikHub 不可用、用户明确指定浏览器，或需要核对页面状态时使用。

## 按缺口选择

- 搜索或推荐流：优先 OpenCLI 已有小红书 adapter。
- 已登录页面读取：按当前宿主的 BrowserSkill 或 OpenCLI 技能操作。
- 单篇公开笔记元信息：可使用已就绪的 XHS-Downloader。
- 已配置的 xhshow API：仅在现有凭据和签名可用时使用，不为备用调用索取聊天明文 Cookie。
- 评论或页面图片补全：可使用已有 CDP 方案，先验证指定浏览器和登录态。
- 通用浏览器只读到分享页摘要时，必须标注未取得正文。

浏览器渠道必须遵守用户指定的实例或 profile。指定实例未连接时，不得改用其他实例。成功和失败均回收任务创建的会话。

## OpenCLI

先加载当前 `opencli-usage` 技能，检查实际版本、站点命令帮助和连接状态；参数以当前 CLI 为准。

已有小红书命令包括 `feed`、`search`、`whoami`。不得把搜索结果解释为全站热榜，也不得把隔离浏览器解释为用户登录会话。

## XHS-Downloader

仅当后端已就绪，或用户同意修复该备用后端时，读取 `xhs-downloader-integration.md`。

```bash
python3 scripts/xhs_bootstrap.py doctor
python3 scripts/xhs_backend.py '<笔记链接>'
```

从技能目录运行命令。脚本使用独立 Python 环境；环境缺失属于依赖错误，不等于笔记不存在。不得把原始 `FileNotFoundError` 当作成功结果。

胶水层必须向下游显式传 `cookie=""`，调用 `fetch_note(url)` 时函数默认值已负责该约束。不得把“调用方省略参数”和“下游未收到空字符串”混为一谈。

旧解析器可能不识别 `xhslink.cn`。此时保留原始分享文本，可用 GET 解析跳转；HEAD 返回 404 不足以判定短链失效。落到登录页时，跳转参数中的目标页只能用于定位，不能作为已读正文的证据。

后端免登录模式不能提供评论和图片 OCR。原文是否完整必须单独检查。

## CDP 与诊断

仅在已有授权浏览器和可用登录态下启用 `scripts/legacy/xhs_extractor_v2.py`。运行前读取 `scripts/legacy/README.md` 和当前浏览器技能。

没有现成 CDP 时，不因本技能而重启共享浏览器、修改用户启动参数或安装扩展。Browser-Harness 的旧用法只作诊断资料，不覆盖用户当前的浏览器绑定。

出现风控 `300012` 时停止受限路径。不索取聊天明文 Cookie，不通过轮换代理或账户规避。回报已得到的内容与具体缺口即可。
