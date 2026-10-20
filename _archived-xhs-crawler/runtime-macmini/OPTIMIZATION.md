# xhs-crawler Skill 优化问题清单

> 创建时间：2026-02-04  
> 最后更新：2026-02-04  
> 状态：待处理  
> 优先级：🔴 高

---

## 🔴 主要问题（当前阻塞）

### 问题 1：图片数量读取不完整 ⭐⭐⭐

**现象：**
- 笔记有 14 张图片，实际只读取到部分
- CDP 截图可能只捕获当前视口内容
- 轮播图无法正确滚动和检测总数

**影响：**
- 分析报告内容不完整
- 遗漏重要项目信息

**代码位置：** `scripts/xhs_extractor.py`

**尝试过的方案：**
- [x] 全页面截图
- [x] 逐张轮播图滚动截图
- [x] JS 检测轮播图 indicators

**失败原因：**
- 小红书使用懒加载，滚动后才加载图片
- 轮播图容器结构复杂，JS 选择器不准确
- 动态渲染导致截图时部分内容未加载

**预估难度：** 中 ⭐⭐

**复现步骤：**
1. CDP 连接到 Comet
2. 导航到笔记页面：`http://xhslink.com/o/5T23GSFNX4p`
3. 执行截图和图片提取
4. 对比实际图片数量（14张）

**根因分析：**
```javascript
// 当前的检测逻辑
const indicators = document.querySelectorAll('.swiper-pagination-bullet, .indicator, [class*="pagination"]');
// 小红书的轮播图使用了动态渲染，指示器可能不完整

// 需要改进的方向
// 1. 等待所有图片加载完成
// 2. 使用 MutationObserver 监听 DOM 变化
// 3. 预加载所有轮播图
```

**待实现方案：**

#### 方案 1：增强轮播图检测

```python
# 伪代码：改进图片计数逻辑
async def detect_all_slides(page):
    # 1. 滚动到轮播图区域
    await carousel.scroll_into_view()
    
    # 2. 等待加载指示器
    await page.wait_for_selector('.swiper-pagination', timeout=5000)
    
    # 3. 获取总数
    total = await page.locator('.swiper-slide').count()
    
    # 4. 逐张滚动截图
    for i in range(total):
        await carousel.screenshot()
        await page.click('.swiper-button-next')
        await asyncio.sleep(0.5)
```

#### 方案 2：预加载所有图片

```python
# 伪代码：强制加载所有图片
await page.evaluate('''
    () => {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (img.dataset.src) {
                img.src = img.dataset.src;
            }
        });
    }
''')
await asyncio.sleep(2)  # 等待加载
```

#### 方案 3：使用 CDP Network 拦截

```python
# 伪代码：监听网络请求获取所有图片URL
async with page.expect_response() as response_info:
    await page.goto(url)
    responses = [r async for r in response_info]
    image_urls = [r.url for r in responses if 'xhscdn' in r.url]
```

---

### 问题 2：小红书 App 限制（次要）⭐⭐

**现象：**
- 笔记链接打开后显示"当前笔记暂时无法浏览，请打开小红书App扫码查看"
- 网页端被限制，只能通过 App 访问
- CDP 截图只能捕获到二维码页面，无法提取实际内容

**影响范围：**
- 大部分有流量的笔记都启用了 App 限制
- 网页端只能查看部分简单笔记
- xhs-crawler 在 CDP 模式下失效

**尝试过的方案：**
- [x] Comet CDP 连接
- [x] 页面截图 + OCR
- [x] 检查页面 DOM 结构

**失败原因：**
- 小红书服务端检测到非 App 请求，返回占位页面

**预估难度：** 高 ⭐⭐⭐

---

### 问题 3：关键词搜索模式失效 ⭐⭐

**现象：**
- `xhs_api.py search <关键词>` 返回空或错误
- API 请求被拦截或返回 403/500
- Cookie 认证失败

**代码位置：** `scripts/xhs_api.py`

**当前调用方式：**
```bash
python3 scripts/xhs_api.py search "OpenClaw 创意项目"
```

**失败表现：**
- 返回空列表 [] 或错误信息
- 网络请求超时
- 签名验证失败

**失败原因分析：**
```python
# 当前 xhs_api.py 的请求逻辑（推测）
def search_notes(keyword):
    # 1. 可能缺少必要的请求头
    headers = {
        "X_S: "xxx",      # 缺失或过期
        "X_T: "xxx",      # 时间戳过期
        "User-Agent": "Unknown",  # 被识别为爬虫
    }
    
    # 2. Cookie 可能过期或格式错误
    # web_session 和 a1 需要有效值
    
    # 3. API 签名算法变化
    # 小红书 API 经常更新签名逻辑
```

**预估难度：** 中 ⭐⭐

**待实现改进：**

#### 方案 1：更新请求头和签名

```python
# 需要实现的功能：
async def search_notes(keyword: str) -> List[dict]:
    """
    1. 获取最新的 Cookie（从浏览器或用户输入）
    2. 构建正确的请求头
    3. 实现 X-S 和 X-T 签名算法
    4. 发送 API 请求
    5. 解析返回的 JSON
    """
    pass
```

#### 方案 2：集成到 CDP 模式

```python
# 利用 CDP 的登录态，避免单独处理签名
async def search_with_cdp(page, keyword):
    # 1. 导航到搜索页面
    await page.goto(f"https://www.xiaohongshu.com/search/{keyword}")
    # 2. 滚动加载结果
    # 3. 提取笔记列表
    # 4. 返回结构化数据
```

---

### 问题 4：创作者分析模式失效 ⭐⭐

**现象：**
- `xhs_api.py creator <用户ID>` 返回空或错误
- 无法获取创作者信息和笔记列表
- 用户主页加载失败

**代码位置：** `scripts/xhs_api.py`

**当前调用方式：**
```bash
python3 scripts/xhs_api.py creator 5e11f2310000000001006031
```

**失败表现：**
- 返回空的创作者信息
- API 返回 404（用户不存在）
- 网络请求超时

**失败原因分析：**
```python
# 当前 xhs_api.py 的创作者分析逻辑（推测）

def get_creator_info(user_id: str) -> dict:
    """
    可能的问题：
    1. 用户 ID 格式错误
       - 需要使用加密后的 user_id，而不是原始 ID
       - 小红书使用短链形式的 user_id
    
    2. API 端点变化
       - /api/sns/web/v1/user/profile 获取创作者信息
       - /api/sns/web/v1/user/profile/notes 获取笔记列表
       
    3. 需要登录态
       - 未登录只能查看部分公开信息
       - 部分数据需要关注后才能查看
    """
    pass
```

**预估难度：** 中 ⭐⭐

**待实现改进：**

#### 方案 1：修复用户 ID 解析

```python
async def get_creator_info(page, profile_url: str):
    """
    1. 从 URL 提取正确的 user_id
       - URL 格式: /user/profile/5e11f2310000000001006031
       - 需要处理短链重定向
    
    2. 访问创作者主页
       await page.goto(f"https://www.xiaohongshu.com{profile_url}")
    
    3. 提取创作者信息
       - 昵称、头像、简介、粉丝数
       - 笔记数量、获赞数
    
    4. 提取笔记列表
       - 滚动加载更多笔记
       - 提取笔记标题、链接、互动数据
    """
    pass
```

#### 方案 2：CDP 模式实现

```python
async def analyze_creator_with_cdp(page, creator_url: str):
    """
    利用 CDP 的登录态，绕过 API 签名问题
    
    1. 导航到创作者主页
    2. 等待页面加载完成
    3. JS 提取创作者信息
    4. 滚动加载笔记列表
    5. 返回结构化数据
    """
    pass
```

---

## 📋 API 模式优化方案汇总

| 问题 | 方案 | 技术要点 | 预估难度 | 状态 |
|------|------|----------|----------|------|
| 问题 3：搜索失效 | 更新请求头 | X-S/X-T 签名 | 中 ⭐⭐ | 待实现 |
| 问题 3：搜索失效 | CDP 模式 | 利用登录态 | 中 ⭐⭐ | 待实现 |
| 问题 4：创作者失效 | 修复 ID 解析 | user_id 格式 | 中 ⭐⭐ | 待实现 |
| 问题 4：创作者失效 | CDP 模式 | 页面提取 | 中 ⭐⭐ | 待实现 |

---

## 🛠️ 完整优化任务清单

| 任务 | 对应问题 | 难度 | 状态 |
|------|----------|------|------|
| 增强轮播图检测逻辑 | 问题 1 | 中 | ⏳ 待开始 |
| 实现图片预加载 | 问题 1 | 中 | ⏳ 待开始 |
| 添加 Network 拦截 | 问题 1 | 中 | ⏳ 待开始 |
| 实现 App 扫码认证 | 问题 2 | 高 | ⏳ 待开始 |
| 添加用户手动输入模式 | 问题 2 | 低 | ⏳ 待开始 |
| 修复 API 请求头 | 问题 3 | 中 | ⏳ 待开始 |
| 实现 CDP 搜索模式 | 问题 3 | 中 | ⏳ 待开始 |
| 修复创作者 ID 解析 | 问题 4 | 中 | ⏳ 待开始 |
| 实现 CDP 创作者分析 | 问题 4 | 中 | ⏳ 待开始 |
| 修复 SyntaxWarning | Bug | 低 | ⏳ 待开始 |

---

## 📝 备注

**相关代码文件：**
- `scripts/xhs_extractor.py` - CDP 提取器（问题 1、2）
- `scripts/xhs_api.py` - API 模式（问题 3、4）
- `scripts/xhs_carousel_ocr.py` - 轮播图 OCR
- `scripts/cookie_manager.py` - Cookie 管理
- `extractors.js` - 浏览器端 JS

**测试用例：**
| 功能 | 测试命令 | 预期结果 |
|------|----------|----------|
| CDP 链接提取 | `python3 scripts/xhs_extractor.py <链接>` | JSON 输出 |
| 关键词搜索 | `python3 scripts/xhs_api.py search "关键词"` | 笔记列表 |
| 创作者分析 | `python3 scripts/xhs_api.py creator <用户ID>` | 创作者信息 |
| Cookie 管理 | `python3 scripts/cookie_manager.py show` | 显示保存的 Cookie |

**测试链接：**
- `http://xhslink.com/o/5T23GSFNX4p` - 14张图片的笔记（CDP 问题）

---

## 🔗 相关会话

- 2026-02-04 首次分析小红书笔记
- 发现图片数量读取不完整（14张只读到部分）
- 发现关键词搜索和创作者分析 API 模式失效
- 初步报告已生成，但内容不完整
- 创建优化文档等待后续处理
