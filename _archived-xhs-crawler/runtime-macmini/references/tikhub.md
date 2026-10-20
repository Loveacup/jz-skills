# TikHub MCP 读取

## 连接与复用

端点：`https://mcp.tikhub.io/xiaohongshu/mcp`。

优先使用当前宿主已连接的工具。没有原生工具时，可复用已授权的 MCP 客户端或远程执行端，不必先修改宿主配置。

本机存在 `references/tikhub-local.md` 时，先读取其中的设备绑定。绑定只表示查找线索，每次仍需验证连接和文件状态；不得把机器路径写入共享版本。

通过标准 MCP 客户端调用时：

1. 发送 `initialize`，声明客户端支持的协议版本。
2. 使用服务端返回的协议版本及会话头。
3. 发送 `notifications/initialized`。
4. 用 `tools/list` 获取工具定义，再发 `tools/call`。
5. 按协议关闭会话；不得在错误日志中输出鉴权头。

HTTP 客户端接受 `application/json` 和 `text/event-stream`。SSE 按事件边界解析 `data` 字段，不能把进度事件当作最终结果。原生 MCP SDK 可负责这些协议细节。

## 工具选择

以下名称来自实际工具发现。调用时以当前返回的 schema 为准。

| 任务 | 工具 | 已观察的参数 |
|---|---|---|
| 图文详情 | `xiaohongshu_app_v2_get_image_note_detail` | `note_id`、`share_text` |
| 视频详情 | `xiaohongshu_app_v2_get_video_note_detail` | `note_id`、`share_text` |
| 主评论 | `xiaohongshu_app_v2_get_note_comments` | `note_id`、`share_text`、`cursor`、`index`、`pageArea`、`sort_strategy` |
| 回复分页 | `xiaohongshu_app_v2_get_note_sub_comments` | `comment_id`，其余参数查 schema |
| 网页详情 | `xiaohongshu_web_v3_fetch_note_detail` | 必填 `note_id`、`xsec_token` |
| 搜索 | `xiaohongshu_app_v2_search_notes` | 必填 `keyword`，筛选与分页查 schema |
| 推荐流 | `xiaohongshu_web_v3_fetch_homefeed` | 分页与分类查 schema |
| 创作者 | `xiaohongshu_app_v2_get_user_info`、`xiaohongshu_app_v2_get_user_posted_notes` | 用户标识、分享文本与分页查 schema |

图文详情的调用内容示例：

```json
{
  "name": "xiaohongshu_app_v2_get_image_note_detail",
  "arguments": {
    "share_text": "<用户原始分享文本或链接>"
  }
}
```

有已确认的 `note_id` 时一并传入。不得为使用网页详情接口丢弃原链接中的 `xsec_token`。

图文详情已足够时，不额外调用网页详情。视频详情不等于视频转录；需要分析视频内容时转视频分析技能。

## 响应解包与失败判据

区分以下层次：

- HTTP 或协议错误。
- MCP 顶层 `error`。
- `result.isError`。
- `result.structuredContent` 或文本内容块中的业务 JSON。
- TikHub 业务状态与内部平台状态。

`initialize` 和 `tools/list` 成功不能证明 Key 有效。实际数据调用可能返回外层 `isError=false`、内部 `status=401` 和 `error=unauthorized`。遇到内部错误也必须判定失败。

`structuredContent` 与文本内容块可能重复承载同一个对象；选择一份解析，不重复统计。文本里的 JSON 字符串必须再次解析，不能用字符串片段判定业务成功。

成功仍需核对笔记 ID、目标内容和数据结构。已观察到图文详情内部形态为 `data.data[].note_list[]`，其中包含 `title`、`desc`、`user.nickname`、`images_list` 和互动计数。缓存外层可能再包一层 `data`；先检查实际层级，不固定套用同一条 JSON 路径。

`result.content[0].text` 里是业务 JSON 的字符串，须再 `json.loads` 一次才能取 `data`。`images_list` 条目的 `index` 字段不可靠（可能全为 0）：下载配图时按 enumerate 位置命名（img0、img1…），不要用 `img['index']` 作唯一文件名，否则互相覆盖。

## 编码、截断与缓存

- 中文乱码时检查响应字节解码、远程控制台编码和结果文件编码。
- Windows PowerShell 可从响应字节按 UTF-8 解码，再用 UTF-8 文件传回。不得依赖 SSH 控制台转码保留中文。
- 大响应先保存到受控临时文件，程序只输出字段摘要，防止截断和重复转义。
- TikHub 成功响应可能提供签名 `cache_url`，并说明有效期和是否免费。只在该响应声明的有效期内复用；不得把缓存当成实时刷新。
- 缓存地址可能允许持链接者读取响应，不公开贴出完整签名 URL，也不写入共享 skill。
- 当前设备无法访问缓存时，可从已授权且可访问的执行端获取。鉴权密钥仍留在原执行端，不随结果回传。

## 完整性与停止条件

正文、图片和评论按 `SKILL.md` 的内容检查规则处理。

搜索和推荐流只是接口返回的样本。关键词结果不代表全站热榜，推荐流不代表所有用户看到的内容。未明确身份来源时，不称为“用户个人推荐流”。

分页以当前响应的游标继续。设定样本上限，达到上限、无后续页、无新增记录或出现错误时停止。返回页已包含回复时，先合并去重，再决定是否需要付费请求回复分页。

## 凭据和验证边界

已有凭据只在受控执行端内存中读取并发给 TikHub。新凭据通过宿主支持的隐藏输入渠道获取，按该设备支持的凭据库或用户级加密方式保存。不得把 Key 写进共享配置样例、命令行、脚本、测试夹具或报告。

临时桌面输入通过交互会话显示时，必须确认窗口已显示；任务已启动不等于用户看见。输入结束后回收临时执行任务，不留下周期性采集任务。

已实测图文详情、评论读取和缓存取回；搜索、视频和创作者工具仅发现了定义，不能据此声称端到端通过。真实数据调用可能计费，静态文档检查不重复付费请求。
