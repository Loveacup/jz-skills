# Issue: 轮播图 OCR 提取问题汇总

**Issue ID**: issue-002-carousel-ocr-problems  
**创建日期**: 2026-02-06  
**状态**: 待修复  
**优先级**: 高

---

## 问题描述

在使用 xhs-crawler 提取小红书笔记时，轮播图的 OCR 功能存在多个问题，导致无法正确提取图片中的文字内容。

---

## 具体问题

### 1. `xhs_extractor.py` 默认跳过 OCR

**现象**:  
运行 `fetch_all.py` 或 `xhs_extractor.py` 时，轮播图的 `carousel_ocr` 字段返回空数组或空文本。

**根因**:  
- `xhs_extractor.py` 默认参数可能未启用 OCR
- 使用 `--no-ocr` 参数时会跳过 OCR 步骤

**临时解决**:  
手动调用 `xhs_carousel_ocr.py` 进行 OCR，但该脚本也存在问题（见下文）。

---

### 2. `xhs_carousel_ocr.py` 脚本错误

**现象**:  
```bash
python3 scripts/xhs_carousel_ocr.py /tmp/xhs_analyzer/full_20260206_165255/
```

报错：
```
playwright._impl._errors.Error: Page.goto: Protocol error (Page.navigate): 
Cannot navigate to invalid URL
Call log:
  - navigating to "/tmp/xhs_analyzer/full_20260206_165255/", 
    waiting until "domcontentloaded"
```

**根因**:  
脚本期望传入的是 URL，但实际传入的是本地文件夹路径。脚本逻辑错误地将本地路径作为 URL 进行导航。

**代码位置**:  
`scripts/xhs_carousel_ocr.py` 第 94 行：
```python
await page.goto(url, wait_until="domcontentloaded")
```

**修复建议**:  
- 修改脚本支持本地图片文件批量处理
- 或使用本地 Qwen3-VL API 直接处理图片，无需通过浏览器

---

### 3. SyntaxWarning: 无效的转义序列

**现象**:  
运行时出现警告：
```
~/clawd/skills/xhs-crawler/scripts/xhs_extractor.py:165: 
SyntaxWarning: "\d" is an invalid escape sequence. 
Such sequences will not work in the future. 
Did you mean "\\d"? A raw string is also an option.
  const match = lel.textContent.match(/(\d+)/);
```

**根因**:  
JavaScript 代码嵌入 Python 字符串时，反斜杠转义问题。

**修复建议**:  
将字符串改为原始字符串（raw string）：
```python
# 修改前
const match = lel.textContent.match(/(\d+)/);

# 修改后
const match = lel.textContent.match(/(\\d+)/);
# 或使用原始字符串
r'const match = lel.textContent.match(/(\d+)/);'
```

---

### 4. 轮播图数量与内容冗余

**现象**:  
该笔记共有 18 张轮播图，但只有前 6 张包含独特内容，后 12 张是重复的评论区截图。

**数据分析**:  
| 轮播图 | 内容 |
|--------|------|
| 00-05 | 独特内容（封面、功能介绍、数据展示） |
| 06-17 | 重复的评论区截图（共12张） |

**优化建议**:  
- 增加内容去重机制
- 或提供参数控制只提取前 N 张轮播图
- 识别并跳过重复/相似图片

---

## 实际提取的数据（本次案例）

**笔记**: 小红书 /insights 功能介绍  
**时间**: 2026-01-05 至 2026-02-04（30天）

### 核心数据（从 slide_03 和 slide_05 提取）

```
📊 使用量统计：
- 会话数：2,518 个
- 消息数：25,578 条
- 使用时长：23,728 小时
- 提交次数：302 次
- 日均消息：882 条

💻 代码产出：
- 新增代码：+814,624 行
- 删除代码：-239,912 行
- 净增代码：+574,712 行
- 文件数：5,617 个

🎯 会话过滤：
- 排除子会话、短会话
- 提取12+项元数据（token用量、工具调用、编程语言等）
```

---

## 修复方案

### 短期（已完成）

1. **修复 SyntaxWarning**
   - **状态**: ✅ 已完成 (2026-02-06)
   - **文件**: `scripts/xhs_extractor.py`
   - **修改**: 将 `JS_EXTRACTOR` 定义改为原始字符串 `r"""..."""`，解决了 `\d` 转义警告。

2. **修复 `xhs_carousel_ocr.py` 脚本**
   - **状态**: ✅ 已完成 (2026-02-06)
   - **文件**: `scripts/xhs_carousel_ocr.py`
   - **修改**: 重构了脚本架构，新增 `process_local_images` 函数。现在脚本可以自动识别输入是 URL 还是本地文件夹路径。如果是本地路径，直接读取并 OCR 识别，不再尝试打开浏览器。

### 中期（优化建议）

3. **优化轮播图提取逻辑**
   - **状态**: ⏳ 待处理
   - **方案**: 增加内容去重机制，识别相似图片并跳过重复的评论区截图。

### 长期（本月）

4. **改进 OCR 流程**
   - 考虑使用本地视觉模型（Qwen3-VL）替代浏览器截图 OCR
   - 提高 OCR 速度和准确率
   - 支持批量并发处理

---

## 参考资源

- **相关文件**: 
  - `scripts/xhs_extractor.py`
  - `scripts/xhs_carousel_ocr.py`
  - `scripts/qwen_vl_local.py`（本地 OCR 替代方案）

- **测试笔记**: 
  - http://xhslink.com/o/5Y1HKawRMLl
  - 18 张轮播图，涵盖功能介绍、数据展示、评论区

---

## 新增问题（2026-02-06 第二批）

### 5. CDP 连接失败导致提取中断

**现象**:  
运行 `xhs_extractor.py` 时报错：
```
playwright._impl._errors.Error: BrowserType.connect_over_cdp: 
connect ECONNREFUSED 127.0.0.1:19222
```

**根因**:  
Comet 浏览器未启动，或 CDP 端口未正确配置。

**影响**:  
- 无法提取轮播图
- 无法获取互动数据（点赞/收藏/评论数）
- 无法执行 JavaScript 获取动态内容

**临时解决**:  
手动启动 Comet：
```bash
/Applications/Comet.app/Contents/MacOS/Comet \
  --remote-debugging-port=19222 \
  --no-first-run \
  --no-default-browser-check &
```

**长期解决**:  
- 添加自动检测 CDP 状态的逻辑
- 如果 CDP 未启动，提示用户启动或自动尝试启动
- 提供友好的错误信息，而非直接报错

---

### 6. `xhs_extractor.py` 提取过程卡住/超时

**现象**:  
提取过程在以下阶段卡住：
- 轮播图 OCR 阶段（第 4-7 张轮播图时）
- 进程无输出，但 CPU 占用正常
- 需要手动 kill 进程才能退出

**根因分析**:  
- OCR 服务（Qwen3-VL）响应时间过长
- Playwright 截图操作在某些页面元素上阻塞
- 网络延迟导致页面资源加载超时

**临时解决**:  
- 使用 `--no-ocr` 参数跳过 OCR
- 手动使用简化脚本提取基础数据

**修复建议**:  
- 添加超时机制（每个操作设置最大等待时间）
- 添加断点续传功能（记录已完成的轮播图，中断后可继续）
- 优化 OCR 调用，使用异步并发处理

---

### 7. `JS_EXTRACTOR` 正则表达式语法错误

**现象**:  
执行时报错：
```
playwright._impl._errors.Error: Page.evaluate: SyntaxError: 
Invalid regular expression flags
```

**根因**:  
- `JS_EXTRACTOR` 字符串中包含 JavaScript 正则表达式
- Python 字符串转义与 JavaScript 正则转义冲突
- 使用 `"""` 普通字符串时，`\d` 被 Python 解释为转义序列
- 使用 `r"""` 原始字符串时，JavaScript 中的 `\\` 可能处理不正确

**代码位置**:  
`scripts/xhs_extractor.py` 中的 `JS_EXTRACTOR` 变量

**尝试的修复**:  
1. 改为原始字符串 `r"""` - 导致其他转义问题
2. 改为普通字符串 `"""` - 出现 SyntaxWarning
3. 双重转义 `\\d` - 需要大量修改，维护困难

**最终方案**:  
暂时接受 SyntaxWarning，确保功能正常。长期应重构为：
- 将 JavaScript 代码保存到独立 `.js` 文件
- 通过 `page.add_script_tag()` 或 `page.evaluate()` 加载文件内容
- 避免 Python 字符串转义与 JavaScript 正则的冲突

---

### 8. `web_fetch` 降级方案局限性

**现象**:  
当 CDP 不可用时，使用 `web_fetch` 获取小红书笔记：
- ✅ 可以获取标题、正文（静态 HTML 中）
- ❌ 无法获取互动数据（点赞/收藏/评论数）
- ❌ 无法获取轮播图（需要 JavaScript 执行）
- ❌ 无法获取评论（需要 API 调用或滚动加载）

**根因**:  
小红书使用现代前端框架（React/Vue），大部分数据通过 JavaScript 动态加载：
- 互动数据通过 API 请求获取
- 轮播图需要浏览器渲染
- 评论需要滚动触发懒加载

**影响**:  
报告不完整，缺少关键数据（互动数据反映笔记热度，轮播图可能包含核心内容）。

**建议**:  
- 明确标注 `web_fetch` 模式的局限性
- 优先使用 CDP 模式，仅在紧急情况下使用 `web_fetch` 降级
- 考虑结合 API 模式补充互动数据（需要 Cookie）

---

## 修复方案更新

### 已完成（2026-02-06）

1. **修复 SyntaxWarning** - ✅ 已应用临时方案（接受 Warning）
2. **修复 `xhs_carousel_ocr.py`** - ✅ 已完成
3. **CDP 连接问题** - ✅ 手动解决，需自动化
4. **提取卡住问题** - ⏳ 观察中，必要时添加超时机制

### 待处理（优先级排序）

| 优先级 | 问题 | 方案 |
|:---|:---|:---|
| **P0** | CDP 自动检测/启动 | 添加启动检测逻辑，友好提示 |
| **P1** | 提取超时机制 | 每个操作添加 timeout |
| **P2** | JS_EXTRACTOR 重构 | 分离到独立 .js 文件 |
| **P3** | web_fetch 局限性文档 | 更新 SKILL.md，明确标注限制 |
| **P4** | 断点续传 | 记录进度，支持中断后继续 |

---

## 参考案例

### 成功案例：GEO 笔记完整提取

**笔记**: http://xhslink.com/o/9fJymQ31ass  
**时间**: 2026-02-06  
**结果**: ✅ 成功提取全部 14 张轮播图

**关键操作**:  
1. 确保 Comet 已启动（CDP 19222 端口可用）
2. 运行 `xhs_extractor.py`（带 OCR）
3. 等待约 30 分钟（14 张轮播图 × 每张 2-3 分钟 OCR）
4. 成功获取约 20,000 字 OCR 内容

**数据产出**:  
- 基础数据：标题、正文、作者、标签
- 互动数据：点赞 127、收藏 247、评论 43
- 评论：3 条（含置顶引导）
- 轮播图 OCR：详细的方法论步骤、Agent 配置、案例数据

---

## 更新记录

| 日期 | 更新 |
|:---|:---|
| 2026-02-06 | 创建 Issue，记录 OCR 提取问题 |
| 2026-02-06 | **更新**：添加 CDP 连接、提取卡住、JS 语法错误、web_fetch 局限性等问题 |
| 2026-02-06 | **更新**：添加 GEO 笔记成功案例，验证修复效果 |

---

*记录人: 小黄*  
*关联: xhs-crawler v5.2.0*
