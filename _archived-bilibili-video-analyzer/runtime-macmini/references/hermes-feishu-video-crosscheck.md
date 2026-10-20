# Hermes/飞书类 B站配置视频交叉校验笔记

适用场景：B站视频主题是 Hermes Agent、飞书/Lark、Gateway、多 profile、多机器人、平台集成等配置教程。

## 关键做法

1. **视频转录只当操作记录，不当事实权威。**
   - 先抽取视频里的命令、配置项、UI 步骤、评论区故障。
   - 再用 Hermes 官方文档校验：飞书/Lark messaging 文档、多 profile gateway 文档、profiles 文档。

2. **视频简介里的飞书 wiki/私有文档可能抓不到。**
   - 如果 `web_extract`/fetch 返回 private/internal network blocked 或空内容，不要卡住。
   - 在报告 §0 或 §8 明确写“视频简介文档未能读取”，并改用 Hermes 官方 docs 交叉校验。

3. **飞书多机器人配置的事实核验重点。**
   - 多机器人通常是“一 Hermes profile 对一飞书机器人 App”，每个 profile 独立 `.env/config/SOUL/skills/memory/sessions`。
   - 默认模型是一 profile 一 gateway service；另有 `gateway.multiplex_profiles=true` 的 default gateway multiplexer 模式，需说明取舍。
   - WebSocket 模式是官方推荐的本机/工作站方式，无需公网 webhook。
   - 群聊默认需要 @ 机器人，且受 `FEISHU_GROUP_POLICY`、`FEISHU_ALLOWED_USERS`、`FEISHU_REQUIRE_MENTION`、group_rules 影响。
   - Hermes 默认忽略其他机器人消息；机器人互相 @ 需 `FEISHU_ALLOW_BOTS=mentions` 或 `all`，优先建议 `mentions`，并提醒防循环。

4. **评论区故障要转成排查清单。**
   - 私聊正常、群聊不回复：查 gateway log、是否 @、群策略、白名单、bot open_id、应用权限。
   - 机器人互相 @ 无效：查 `FEISHU_ALLOW_BOTS` 与自身 bot 身份识别。
   - “一个 gateway 能否多个 profile”：说明默认多进程 vs multiplex_profiles 两种模型。

## 报告中建议固定加入的小节

- §0 “事实对照”：视频说法 / 官方资料对照 / 判断。
- §2.5 评论分析：把评论问题映射到具体配置项或故障域。
- §4 Deep Dive：至少覆盖 Profile 隔离、群聊策略、bot-to-bot、gateway 运维模式。
- §8 Appendix：加入官方配置速查和群聊/机器人互相 @ 排查清单。
