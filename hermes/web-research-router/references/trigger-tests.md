# Trigger Validation Test Suite

Re-validate after every change to `description` or `triggers`.

## Should Trigger

| # | 用户输入 | 预期模式 |
|---|---------|:--:|
| 1 | "搜索一下 Obsidian CLI 的用法" | discovery |
| 2 | "检索 GitHub 上相关的 skill 项目" | discovery → GitHub |
| 3 | "有没有类似 tRPC 的框架？" | discovery |
| 4 | "查一下 React 19 的发布日期" | grounding |
| 5 | "核实这个数据的真实性" | grounding |
| 6 | "调研一下微前端方案的优劣" | research |
| 7 | "对比一下 Exa 和 Tavily 的搜索效果" | research |
| 8 | "这个链接打不开了，帮我找原始出处" | recovery |
| 9 | "找几篇 RAG 相关的论文" | academic |
| 10 | "看看 Obsidian CLI 的源码实现" | discovery → GitHub |
| 11 | "这个函数怎么实现的，搜一下 GitHub" | discovery → GitHub |
| 12 | "帮我找一下关于 agent skill 的资料" | discovery |
| 13 | "看看推特上大家怎么评价 Claude Opus" | platform (twitter) |
| 14 | "reddit 上有没有关于这个框架的讨论" | platform (reddit) |
| 15 | "b站搜一下 Claude Code 教程" | platform (bilibili) |
| 16 | "小红书上这个产品的口碑怎么样" | platform (xiaohongshu) |
| 17 | "把这期小宇宙播客转成文字" | platform (xiaoyuzhou) |

## Should NOT Trigger

| # | 用户输入 | 应该用什么 |
|---|---------|----------|
| 1 | "帮我读一下这个文件" | read 工具 |
| 2 | "运行 npm install" | bash 工具 |
| 3 | "这个函数怎么改" | edit 工具 |
| 4 | "git log 看一下最近提交" | bash 工具 |
| 5 | "这个项目文档里已经有了，帮我改一行" | edit 工具 |
| 6 | "帮我写个 Python 脚本" | write 工具 |
| 7 | "这段代码有 bug 吗" | 代码分析 |
| 8 | "列出当前目录的文件" | bash |
| 9 | "保存这个配置到本地" | write 工具 |
| 10 | "帮我翻译这段文字" | 翻译 |

## Step 0.6 实体接地门控（v3.11）

> 验证 Step 0.6 只在**命名实体类** query 触发，纯概念/背景类跳过（省一次预搜索）。description/triggers 未变，故此节只验证 intra-skill 门控，不影响上面的 mode 路由测试。

| # | 用户输入 | 跑 Step 0.6? | 预解析落点 → 下游 |
|---|---------|:--:|---|
| 1 | "RWKV 这个项目大家怎么评价" | ✅ 是 | `r/RWKV` + `@RWKV_AI` + repo → 定向 reddit/twitter（不需用户指名平台） |
| 2 | "Anthropic Series D 估值多少" | ✅ 是 | 官方域 anthropic.com → 锚定主搜（grounding） |
| 3 | "看看推上怎么评价 Claude Opus" | ✅ 是 | `@AnthropicAI` → twitter user-posts |
| 4 | "微前端方案有哪些优劣" | ❌ 跳过 | 纯概念，无命名实体 → 直接 Step 2 research |
| 5 | "RAG 的基本原理是什么" | ❌ 跳过 | 纯概念/背景 → 直接 Step 2 discovery |
| 6 | "怎么用 Python 读 CSV" | ❌ 跳过 | how-to 无命名实体 → 直接 Step 2 |

**判据：** query 含具体人/产品/项目/公司/开源库/社区名 → 跑 Step 0.6；纯概念/how-to/背景 → 跳过。

## Verification Method

1. All should-trigger: agent reads this skill and follows routing mode
2. All should-not-trigger: agent skips this skill, uses other tools
3. Step 0.6 门控：命名实体类跑预搜索解析，纯概念类跳过
4. Adjust `description` or `triggers` if any test fails, then re-validate
