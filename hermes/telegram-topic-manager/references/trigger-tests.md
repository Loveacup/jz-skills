# Trigger Tests — telegram-topic-manager

## Should Trigger (✅)

| # | User Input | Trigger? | Why |
|---|-----------|:---:|------|
| 1 | "帮我把这个话题改名成 Deployment" | ✅ | Matches "改话题名" |
| 2 | "create a new topic called Research in my DM" | ✅ | Matches "create topic" |
| 3 | "把 id 为 42 的话题关掉" | ✅ | Matches "话题关掉" |
| 4 | "delete topic 38814 from my private chat" | ✅ | Matches "delete topic" |
| 5 | "怎么开启 /topic 功能？" | ✅ | Matches "/topic" |
| 6 | "我的 dm_topics 配置对了吗" | ✅ | Matches "dm_topic" |
| 7 | "在 Engineering 话题里绑定 software-development skill" | ✅ | Matches "话题" + skill binding |
| 8 | "createForumTopic chat_id=7931997806 name=Test" | ✅ | Direct method name |
| 9 | "怎么关闭多会话模式" | ✅ | Matches "多会话模式" |
| 10 | "rename the forum topic in my supergroup" | ✅ | Matches "forum topic" |
| 11 | "用 editForumTopic 改个名字" | ✅ | Direct method name |
| 12 | "话题管理：把群里的 General 话题隐藏" | ✅ | Matches "话题管理" |

## Should NOT Trigger (❌)

| # | User Input | Trigger? | Why |
|---|-----------|:---:|------|
| 1 | "send a message to the Research topic" | ❌ | Just sending a message — use send_message |
| 2 | "帮我搜一下 telegram topic" | ❌ | Research/surf the web about topics |
| 3 | "这个群有人发了话题链接" | ❌ | Mentioning "话题" but not managing one |
| 4 | "把聊天记录 pin 一下" | ❌ | pin messages ≠ topic management |
| 5 | "create a new chat group" | ❌ | Creating a group ≠ creating a topic |
| 6 | "send message to thread 42" | ❌ | Just delivery targeting |
| 7 | "how do I use sendMessage?" | ❌ | General Bot API question, not topic-specific |
| 8 | "改个群名" | ❌ | Changing group name, not topic name |
| 9 | "删掉这个群" | ❌ | Deleting a group, not a topic |
| 10 | "怎么用 /start 命令" | ❌ | Hermes slash command, not topic-related |
| 11 | "设个技能给这个聊天" | ❌ | Skill assignment without topic context |
| 12 | "README 里写 topic 要怎么做" | ❌ | Documentation writing about topics |
