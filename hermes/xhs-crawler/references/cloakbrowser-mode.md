# CloakBrowser 模式实战笔记（2026-05-19 端到端验证）

SKILL.md 的"CloakBrowser 模式"章节是规范，本文是 PoC 当天的完整决策与踩坑记录，留给将来类似平台（X / B站 / Reddit / Medium）适配时复用。

---

## 1. 为什么从 CDP 切到 CloakBrowser

旧 CDP 模式（`xhs_extractor.py` / `xhs_full_extractor.py`）的痛点：

| 维度 | CDP 模式 | CloakBrowser 模式 |
|---|---|---|
| Chrome 保活 | 必须 `--remote-debugging-port=19222` 持续运行，关闭即断 | 独立 Chromium，按需启动 |
| 登录态 | 跟用户日常 Chrome 共用，profile 污染 | 独立 `~/.cloakbrowser/xhs_profile/`，~17MB |
| 反检测 | 默认 Playwright/Chrome 指纹，平台升级 fingerprint 即崩 | webdriver=false / chromeObj=object / 5 plugins / UA 不暴露 HeadlessChrome（4/4 stealth 探针过） |
| Headless | 多数小红书内部检测失败 | Headless 也能跑（humanize=True 真人化行为） |
| 安装 | 已经在用 Playwright | `pip3 install cloakbrowser`，首次跑自动下载 Chromium ~200MB |
| 维护 | 每次系统更新/Chrome 升级都可能崩 | CloakBrowser 源码级 patch 的 Chromium 146 |

**结论：默认走 CloakBrowser，CDP 保留为 fallback。** 不删旧脚本，成本只有 SKILL.md 几 KB。

## 2. 七个踩坑（按发生顺序）

### Pitfall 1：登录蒙层无法关闭

`hasLogin=false` 时小红书在 DOM 里直接渲染登录蒙层（全屏 div + 4 个 `.desc` span 包含"刷到更懂你的优质内容"等文案）。试过：

- 点 `.close-btn` / `.mask-close` → 元素存在但点击无效
- `localStorage.setItem('hasLogin', 'true')` → 重新渲染后又被覆盖
- `evaluate(() => document.querySelector('.login-container')?.remove())` → 5 秒后被 React 重新挂载

**解决**：不要执着于关蒙层。`#detail-desc` 是正文容器，蒙层不影响它的内容，**精确选元素即可**。

### Pitfall 2：通用兜底正则抓蒙层文案

最初选择器顺序：`#detail-desc` → `.note-content` → fallback 兜底（任意有内容的 `.desc`）。结果蒙层的 4 个 `.desc` span 被兜底命中，输出全是"刷到更懂你的优质内容/扫码登录解锁完整体验/..."。

**解决**：兜底 selector 增加 reject 列表：
```javascript
const REJECT_TEXTS = ['刷到更懂你', '扫码登录', '完整体验', '应用内打开'];
const isShellText = (txt) => REJECT_TEXTS.some(r => txt.includes(r));
```

### Pitfall 3：截视口模式截到登录蒙层

最初轮播图用 `page.screenshot(clip={...})` 截 swiper 区域。问题：蒙层覆盖在轮播图之上，截图里全是"登录/注册"按钮，DeepSeek-OCR-2 输出"登录登录登录..."重复 100 遍。

**解决**：完全放弃截视口，改为直连 CDN：
```python
imgs = await page.eval_on_selector_all('.note-slider-img img', 'els => els.map(e => e.src)')
# urllib + Referer: https://www.xiaohongshu.com 直接下载原图（1080×1440）
```

### Pitfall 4：CDN 图片懒加载

页面加载完立即 query `.note-slider-img img` 只有 7 张，但 swiper 显示总数更多。Swiper 是 lazy-load，只渲染当前 ±1 屏。

**解决**：`capture_carousel()` 跑前先 `page.keyboard.press('ArrowRight')` 三次，触发预加载，再 query。

### Pitfall 5：Swiper duplicate slide

`.swiper-slide` 包含 `swiper-slide-duplicate` 元素（swiper 为了循环滚动复制的副本），直接 querySelectorAll 会有重复。

**解决**：用 URL 去 query string 作为去重 key：
```python
dedup_key = src.split('!')[0]  # CDN URL 后面带 ?imageView2/2/w/... 缩略参数
```

### Pitfall 6：DeepSeek-OCR-2 复读 bug

某些图（特别是视觉特效/纯文字背景）会让 OCR 陷入复读：同一短语重复几百次（slide 4 出现"AI AI AI..."重复 21 次）。

**解决**：`_dedupe_repeats()` 两层清理：
1. 句子级去重（split by `\n` → set 去重 → 还原顺序）
2. 正则折叠连续 ≥6 次的短语：`re.sub(r'(\b\S+?\b)(\s+\1){5,}', r'\1', text)`

### Pitfall 7：DeepSeek-OCR-2 grounding 标签泄漏

DeepSeek-OCR-2 有时输出训练用的 grounding 格式：
```
<|ref|>技能集成眼<|/ref|><|det|>[[98, 189, 339, 225]]<|/det|>
```

prompt 用 `<image>\nOCR this image` 已经尽量规避，但仍偶发。

**解决**：在 `_dedupe_repeats()` 末尾加正则清理：
```python
text = re.sub(r'<\|ref\|>(.*?)<\|/ref\|>', r'\1', text, flags=re.DOTALL)
text = re.sub(r'<\|det\|>\[\[.*?\]\]<\|/det\|>', '', text, flags=re.DOTALL)
text = re.sub(r'<\|/?[a-z]+\|>', '', text)
```

## 3. 首次登录流程（一次性）

```bash
python3 scripts/xhs_cloak_login.py
# 弹出 headed CloakBrowser 窗口
# 用户扫码登录
# 脚本检测到 web_session cookie 出现 → 持久化 → 自动关闭
```

Profile：`~/.cloakbrowser/xhs_profile/`（含 12 个 xiaohongshu cookie，有效期 ~1 年）。

**安全**：profile 目录绝不 git commit，含 session cookie。已加 `.gitignore`。

## 4. OCR 接口配置

`.env`（DeepSeek-OCR-2 via vveai.com OpenAI 兼容接口）：
```bash
OCR_API_URL=https://api.vveai.com/v1/chat/completions
OCR_API_KEY=sk-xxx
OCR_MODEL=DeepSeek-OCR-2
```

请求体：
```python
{
    "model": "DeepSeek-OCR-2",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": "<image>\nOCR this image"}
        ]
    }]
}
```

注：prompt 必须含 `<image>\n` 前缀，DeepSeek-OCR-2 是基于 grounding 训练的，简单 prompt 会触发标签输出。

## 5. 端到端验证结果（2026-05-19 07:23）

目标：`http://xhslink.com/o/9HYvnxJB3ML`（jiely｜AI实战笔记 - "别再喂 AI 了"）

- 正文 568 字（一次成功，无蒙层污染）
- 作者：jiely｜AI实战笔记
- 标签 9 个全部抓到
- 评论 19/87 条（页面 lazy-load 限制，要更多需滚动）
- 轮播图 7 张 1080×1440 高清原图
- OCR 字符数：168 / 36 / 95 / 209 / 147 / 842（含 grounding 已清理）/ 156
- 输出：`~/Documents/Obsidian/AlexCai/00-Inbox/xhs_cloak_20260519_072328.{json,txt}`

## 6. 跨平台迁移参考

类似平台（X / B站 / Reddit / Medium）适配时，复用本文这 7 个 pitfall 检查清单：

1. 是否有登录蒙层？精确选元素，不要试图关。
2. 是否有不可见但占位的 `.desc` 类元素干扰兜底正则？加 reject 列表。
3. 轮播图/媒体抓取走 CDN 直连还是截视口？**永远优先 CDN 直连**。
4. 媒体是否懒加载？预触发翻页/滚动。
5. Swiper/Carousel 是否有 duplicate 元素？URL 基础部分去重。
6. OCR 模型是否复读？两层 dedupe。
7. OCR 模型是否泄漏内部标签？正则剥离。

CloakBrowser 启动方式（通用骨架）：
```python
import cloakbrowser as cb
browser = await cb.launch_persistent_context_async(
    user_data_dir=Path.home() / ".cloakbrowser/<platform>_profile",
    headless=True,
    humanize=True,
    viewport={"width": 1280, "height": 900},
    locale="zh-CN",
)
```

每个平台一个独立 `user_data_dir`，互不污染。
