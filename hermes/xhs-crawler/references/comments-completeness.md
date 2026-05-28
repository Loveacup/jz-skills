# 评论完整抓取 — 真实瓶颈与诊断

**最后实测：2026-05-19**（含 headless 模式坑发现）

## TL;DR

小红书评论的完整抓取**有两个独立硬约束**：

1. **必须有活跃登录态**（session 未过期）
2. **必须 headed 模式（headless=False）** —  这是 2026-05-19 新发现的坑

常见症状是抓到 19/87 或 29/87 条就抓不动了，根因几乎都是 session 失效**或者 headless 模式开着**。

### 四大硬限制

1. **未登录 / session 失效时**（即使 cookie 文件存在也算）：
   - DOM 滚动最多得到 10 条主评论 + 1 张主评论里嵌入的 sub_comments（共 ~10-20 条）
   - 滚动到底会出现明确提示：「**登录查看全部评论内容**」（DOM: `.note-scroller` 末尾的 `.tips-el`）
   - API `/api/sns/web/v2/comment/page?cursor=` 即使带 cookie 也返回 `data: {}`
   - 翻页 cursor 不工作

2. **🆕 headless 模式即使带完整 web_session 也会被降级**（2026-05-19 新发现）：
   - cloakbrowser `headless=True` 会被小红书识别为"未登录态"，渲染同样的「登录查看全部评论内容」占位符
   - 即使 cookie jar 含完整 web_session、a1、xsec_token，headless 下 Vue 仍只挂载 10 条预览
   - **解决方案：`headless=False`**（headed 模式），改完直接 79/87 条
   - 应用场景影响：评论抓取必须能弹出窗口，cron / 远程 SSH 环境跑不了

3. **`.show-more`「展开 N 条回复」按钮**：
   - 未登录态下 DOM 上没有 Vue 监听器（`__vueParentComponent`、`__vue__` 都为 false，`@click` attr 为 null）
   - 用 `evaluate(el => el.click())` / Playwright `locator.click({force:true})` / `dispatch_event('click')` / `page.mouse.click(bbox.x, bbox.y)` 都不触发展开
   - 登录后 + headed 下：`page.mouse.click(bbox.x+w/2, bbox.y+h/2)` + `scroll_into_view_if_needed` 有效
   - 同样根因：未登录态下小红书禁用了这个 handler

4. **直接 fetch /comment/page API 无效**：
   - 即使在登录浏览器里通过 `page.evaluate("fetch(...)")` 调用，缺 `x-s`/`x-t`/`x-s-common` 签名头会返回 `code: 300011, msg: "当前账号存在异常，请切换账号后重试"`
   - 这些签名是 Vue 组件内置 axios interceptor 动态计算的，非浏览器自动加（即使 cookie 完整）
   - 已尝试方案：URL 编码 xsec_token、监听真实请求复用 headers、被动监听 API 响应 — 都无法可靠分页

## 诊断顺序（按这个顺序走，5 分钟内定位）

1. 跑提取，看脚本输出末尾的「评论: X/Y 条」。如果 X << Y，进入步骤 2。
2. **先确认 headed 模式**：检查 `scripts/xhs_cloak_extractor.py` 里 `launch_persistent_context_async(headless=...)` 是否为 `False`。改成 False 再跑一遍。
3. 检查页面底部文字：
   ```python
   tail = await page.evaluate(
       "() => document.querySelector('.note-scroller').innerText.split('\\n').slice(-10)"
   )
   ```
   出现「登录查看全部评论内容」→ session 失效 OR headless 模式开着。
4. 手动验 API：
   ```python
   from urllib.parse import quote
   url = f"https://edith.xiaohongshu.com/api/sns/web/v2/comment/page?note_id={NOTE_ID}&cursor=&top_comment_id=&image_formats=jpg,webp,avif&xsec_token={quote(XSEC, safe='')}"
   r = await page.evaluate("async u => (await fetch(u, {credentials:'include'})).json()", url)
   ```
   - `data.comments` 长度 0 → session 失效

   - `data.comments` 长度 10 + `has_more=True` 但翻页 cursor 也返回 0 → 同样是 session 失效
   - 长度 10 + `has_more=False` → 真的就 10 条

## 修复

**唯一可靠路径**：重跑 `scripts/xhs_cloak_login.py`，扫码刷新 session。Profile 文件夹（`~/.cloakbrowser/xhs_profile/`）会被复用，只是 `web_session` 这条 cookie 被替换为新值。

不要试图：
- 多次重试同一 API（浪费时间）
- 增加滚动次数（最多就是 30 条主评论的天花板）
- 用 `force:true` 反复点击 `.show-more`（按钮没绑事件）
- 用 `dispatch_event` 触发 click（同上）

## 评论 API 参考

### 主评论
```
GET https://edith.xiaohongshu.com/api/sns/web/v2/comment/page
    ?note_id={note_id}
    &cursor={cursor}            # 首页空，后续用上次响应的 data.cursor
    &top_comment_id=
    &image_formats=jpg,webp,avif
    &xsec_token={url_encoded}   # 必须 URL encode，= 编为 %3D
```

响应 schema:
```json
{
  "code": 0,
  "data": {
    "comments": [
      {
        "id": "...",
        "content": "正文",
        "user_info": {"nickname": "...", "user_id": "...", "image": "..."},
        "create_time": 1778860455000,
        "like_count": "1",
        "ip_location": "浙江",
        "show_tags": ["is_author"],  // 楼主回复标记
        "sub_comment_count": "3",
        "sub_comment_has_more": true,
        "sub_comment_cursor": "...",
        "sub_comments": [...]  // 首条预加载
      }
    ],
    "cursor": "下一页 cursor",
    "has_more": true
  }
}
```

### 子评论
```
GET https://edith.xiaohongshu.com/api/sns/web/v2/comment/sub/page
    ?note_id={note_id}
    &root_comment_id={parent_id}
    &num=10
    &cursor={sub_cursor}
    &image_formats=jpg,webp,avif
    &xsec_token={url_encoded}
```

子评论里的 `target_comment.user_info.nickname` 是被回复者，扁平化时建议拼成 `"回复 @{target_user}: {text}"`。

### 签名 headers（已观察到的请求头）

浏览器自带签名，从 `page.evaluate(fetch)` 走时自动注入：
- `x-s` / `x-t` / `x-s-common`：小红书风控签名
- `x-b3-traceid`：trace
- `cookie` / `referer: https://www.xiaohongshu.com/`：会话身份

**重要**：从 Python `requests` 直接打这个 API 必须自己实现 `x-s`/`x-t` 签名（参考 `xhshow` 库），否则一律 461。但**用 `page.evaluate("fetch(...)")` 不需要**，浏览器会自动签——这是最省事的路径。

## DOM 选择器

| 元素 | 选择器 | 备注 |
|------|--------|------|
| 评论滚动容器 | `.note-scroller` | 独立滚动，`scrollHeight > clientHeight` |
| 主评论 | `.parent-comment` 或 `.comment-item`（不带 sub） | 两者重叠，去重时用元素引用而不是字符串 key |
| 子评论 | `.comment-item-sub` | class 还会同时含 `comment-item` |
| 展开按钮 | `.show-more` | 文本："展开 N 条回复"。**未登录态下无事件监听器** |
| 楼主标签 | 评论内 `[class*="author-tag"]` 或 `.tag-item` | 用于标 `is_author_reply` |

## 已实测但失败的方案（不要再走）

| 方案 | 结果 |
|------|------|
| `evaluate(el => el.click())` | 不触发 Vue handler |
| `locator.click({force: true})` | 同上 |
| `dispatch_event('click', {bubbles:true})` | 同上 |
| `page.mouse.click(bbox.x, bbox.y)` 真实坐标 | 同上 |
| 三事件链 `mousedown / mouseup / click` | 同上 |
| 自实现签名打 `requests.get` | 缺 cookies+签名链路验证太重 |
| `page.evaluate(fetch)` 不带 xsec_token | 后端返回 `data: {}` |
| `page.evaluate(fetch)` 带未编码 xsec_token | 同上 |
| 增加 DOM 滚动次数到 50+ | 主评论卡在 30 上限不再增 |

## 已实测可行的方案（按优先级，2026-05-19 更新）

1. **登录态新鲜 + headed 模式 + DOM 滚动 + 倒序点击视口内 `.show-more`**：实测 79/87（91%）抓取率。这是当前唯一稳定路径。
2. **登录态失效**：放弃，先跑 `xhs_cloak_login.py` 刷新 session。
3. ~~`page.evaluate(fetch)` 直接调评论 API~~：已 **DEPRECATED**。即使在登录浏览器里，缺 `x-s`/`x-t` 签名头会返回 `code: 300011, msg: "当前账号存在异常"`。签名是 Vue 组件内置 axios interceptor 动态计算的，浏览器 fetch 不会自动加。

## 评论加载入口实现要点（已合并到 `scripts/xhs_cloak_extractor.py`）

```python
async def load_all_comments(page, note_id="", xsec_token=""):
    """纯 DOM 模式：滚动 + 倒序点 .show-more"""
    # 阶段 1：滚动 .note-scroller 加载所有主评论
    # 阶段 2：循环遍历 .show-more，scroll_into_view + mouse.click(bbox center)
    # 关键：必须 headless=False，必须登录态新鲜
    return await page.evaluate(EXTRACT_COMMENTS_JS)
```

URL 解析：
```python
import re
from urllib.parse import urlparse, parse_qs
final_url = page.url
note_id = re.search(r"/explore/([a-f0-9]+)", final_url).group(1)
xsec_token = parse_qs(urlparse(final_url).query)["xsec_token"][0]
```

## 当评论确实拿不全时怎么办（任务层面）

1. 不要假装抓全。报告里如实写 `[评论数据不完整: 19/87 条，因登录态失效]`。
2. 抓到的 19 条几乎一定包含作者所有回复（楼主回复是首屏置顶），所以**作者观点是完整的**，只是用户讨论不全。
3. 建议用户在下次类似任务前主动跑 `xhs_cloak_login.py` 续期 session，比每次失败后救火便宜。
