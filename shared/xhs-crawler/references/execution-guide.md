# 小红书提取器执行指南

**用途说明：** 本文档包含 xhs-crawler 的所有脚本使用方法、依赖配置、环境变量说明、调试技巧等操作细节。在需要执行具体操作或遇到问题时加载。

---

## 目录

1. [依赖安装详细步骤](#1-依赖安装详细步骤)
2. [环境变量完整列表](#2-环境变量完整列表)
3. [脚本详细用法](#3-脚本详细用法)
4. [文件保存与清理流程](#4-文件保存与清理流程)
5. [调试技巧](#5-调试技巧)
6. [故障排除工作流](#6-故障排除工作流)

---

## 1. 依赖安装详细步骤

### 1.1 Python 环境

**要求：** Python 3.10+

**检查版本：**
```bash
python3 --version
# 应显示 Python 3.10.x 或更高
```

**安装依赖：**
```bash
cd ~/clawd/skills/xhs-crawler
pip3 install -r requirements.txt
```

**requirements.txt 内容：**
```
playwright>=1.40.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
requests>=2.31.0
```

### 1.2 Playwright 配置

**安装 Chromium：**
```bash
python3 -m playwright install chromium
```

**验证安装：**
```bash
python3 -c "from playwright.sync_api import sync_playwright; print('✅ Playwright OK')"
```

**常见问题：**
- **下载超时：** 设置镜像 `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com`
- **权限错误：** `sudo python3 -m playwright install-deps chromium`

### 1.3 Chrome CDP 设置

**启动 Chrome（带 CDP）：**

通过 OpenClaw Browser Extension：
1. 在 Chrome 中安装 OpenClaw Browser Extension
2. 点击扩展图标 → 显示 **ON** 表示 CDP 已连接
3. 默认 CDP 地址：`ws://127.0.0.1:18792/cdp`

**验证 CDP：**
```bash
curl http://127.0.0.1:18792/json/list
# 应返回 JSON 格式的页面列表
```

**或使用 Comet（备选）：**
```bash
/Applications/Comet.app/Contents/MacOS/Comet \
  --remote-debugging-port=19222 \
  --no-first-run \
  --no-default-browser-check
```
验证：`curl http://127.0.0.1:19222/json/list`

### 1.4 Qwen3-VL OCR 服务

**本地部署（推荐）：**
```bash
# 使用 vllm 启动 Qwen3-VL
cd ~/models
python3 -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-VL-32B \
  --port 9998 \
  --tensor-parallel-size 2
```

**验证服务：**
```bash
curl http://localhost:9998/v1/models
# 应返回可用模型列表
```

**环境变量：**
```bash
export QWEN_API_URL="http://localhost:9998/v1/chat/completions"
```

---

## 2. 环境变量完整列表

### 2.1 必需变量

| 变量 | 用途 | 默认值 | 设置示例 |
|:---|:---|:---|:---|
| `CHROME_CDP_URL` | Chrome CDP 连接地址 | `ws://127.0.0.1:18792/cdp` | `export CHROME_CDP_URL="ws://localhost:18792/cdp"` |
| `QWEN_API_URL` | OCR 服务地址 | - | `export QWEN_API_URL="http://localhost:9998/v1/chat/completions"` |

### 2.2 可选变量

| 变量 | 用途 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `XHS_OUTPUT_DIR` | 报告输出目录 | `~/Documents/Obsidian/AlexCai/00-Inbox` | 自动检测 Obsidian Vault |
| `XHS_PROXY` | HTTP 代理 | - | 格式：`http://host:port` |
| `XHS_COOKIE_FILE` | Cookie 存储路径 | `~/.xhs_cookie` | 通常无需修改 |
| `XHS_REQUEST_TIMEOUT` | 请求超时(秒) | `30` | 网络慢时增加 |
| `XHS_MAX_RETRIES` | 最大重试次数 | `3` | API 不稳定时增加 |
| `XHS_RATE_LIMIT_DELAY` | 请求间隔(秒) | `1.0` | 防爬虫检测 |

### 2.3 环境变量配置方法

**方法 1: .env 文件（推荐）**

创建 `.env` 文件：
```bash
cd ~/clawd/skills/xhs-crawler
cp .env.example .env
```

编辑 `.env`：
```bash
CHROME_CDP_URL=ws://127.0.0.1:18792/cdp
QWEN_API_URL=http://localhost:9998/v1/chat/completions
XHS_OUTPUT_DIR=~/Documents/Obsidian/AlexCai/00-Inbox
# XHS_PROXY=http://127.0.0.1:7890
```

**方法 2: 命令行导出**
```bash
export CHROME_CDP_URL="ws://127.0.0.1:18792/cdp"
export QWEN_API_URL="http://localhost:9998/v1/chat/completions"
python3 scripts/xhs_extractor.py "<url>"
```

**方法 3: 一行设置**
```bash
CHROME_CDP_URL=ws://127.0.0.1:18792/cdp QWEN_API_URL=http://localhost:9998/v1/chat/completions python3 scripts/xhs_extractor.py "<url>"
```

---

## 3. 脚本详细用法

### 3.1 xhs_extractor.py - CDP 全量提取

**基本用法：**
```bash
python3 scripts/xhs_extractor.py "<小红书链接>"
```

**带选项：**
```bash
python3 scripts/xhs_extractor.py "<url>" \
  --no-ocr \              # 跳过 OCR
  --scroll-times 10 \     # 增加滚动次数
  --output /path/to/dir   # 自定义输出目录
```

**参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `url` | 必需 | - | 小红书链接（支持 xhslink.com 短链） |
| `--no-ocr` | 可选 | False | 跳过轮播图 OCR |
| `--scroll-times` | 可选 | 5 | 评论区滚动次数 |
| `--output` | 可选 | $XHS_OUTPUT_DIR | 报告输出目录 |
| `--verbose` | 可选 | False | 详细日志输出 |

**输出示例：**
```json
{
  "title": "笔记标题",
  "author": "作者名",
  "content": "正文内容...",
  "tags": ["标签1", "标签2"],
  "comments": [
    {"user": "用户名", "text": "评论内容", "likes": "9", "time": "01-19"}
  ],
  "images": ["https://..."],
  "stats": {"likes": "822", "collects": "2081"},
  "carousel_ocr": [{"slide": 1, "text": "OCR文本..."}],
  "full_content": "正文 + OCR 合并"
}
```

### 3.2 xhs_api.py - 纯 API 客户端

**关键词搜索：**
```bash
python3 scripts/xhs_api.py search "关键词"
```

**创作者分析：**
```bash
python3 scripts/xhs_api.py creator "用户ID"
```

**笔记详情：**
```bash
python3 scripts/xhs_api.py note "笔记ID"
```

**返回格式：**
```json
{
  "notes": [
    {
      "id": "笔记ID",
      "title": "标题",
      "author": "作者",
      "likes": 100,
      "url": "https://..."
    }
  ]
}
```

### 3.3 cookie_manager.py - Cookie 管理

**保存 Cookie：**
```bash
python3 scripts/cookie_manager.py save 'web_session=xxx;a1=xxx'
```

**查看 Cookie：**
```bash
python3 scripts/cookie_manager.py show
```

**删除 Cookie：**
```bash
python3 scripts/cookie_manager.py clear
```

**获取 Cookie 方法：**
1. 在 Comet/Chrome 中登录小红书
2. 打开 DevTools (F12)
3. 切换到 Application/Storage → Cookies
4. 找到 `www.xiaohongshu.com`
5. 复制 `web_session` 和 `a1` 的值

### 3.4 parse_xhs_url.py - URL 解析

**解析短链：**
```bash
python3 scripts/parse_xhs_url.py "http://xhslink.com/xxxxx"
# 输出: {"note_id": "123456", "type": "note"}
```

**解析完整链接：**
```bash
python3 scripts/parse_xhs_url.py "https://www.xiaohongshu.com/explore/123456"
# 输出: {"note_id": "123456", "type": "note"}
```

### 3.5 xhs_carousel_ocr.py - 轮播图 OCR

**通常由 xhs_extractor 自动调用，也可单独使用：**

```bash
python3 scripts/xhs_carousel_ocr.py --image /path/to/image.png
```

---

## 4. 文件保存与清理流程

### 4.1 临时文件位置

| 文件类型 | 位置 | 命名模式 | 生命周期 |
|:---|:---|:---|:---|
| JSON 数据 | `/tmp/` | `xhs_{note_id}_data.json` | 提取完成后删除 |
| 截图 | `/tmp/` | `xhs_{note_id}_{n}.png` | OCR 完成后删除 |
| OCR 文本 | `/tmp/` | `xhs_{note_id}_ocr.txt` | 合并后删除 |
| 日志 | `/tmp/` | `xhs_{note_id}.log` | 可选保留 |

### 4.2 输出路径检测流程

```python
# 伪代码
if XHS_OUTPUT_DIR env var exists:
    use XHS_OUTPUT_DIR
else:
    vault = find_obsidian_vault()
    if vault exists:
        use vault + "/00-Inbox"
    else:
        use "~/clawd/00-Inbox"
```

### 4.3 手动清理命令

**清理所有临时文件：**
```bash
rm -f /tmp/xhs_*.json /tmp/xhs_*.png /tmp/xhs_*.txt /tmp/xhs_*.log
rm -rf /tmp/xhs_analyzer/
```

**清理特定笔记：**
```bash
NOTE_ID="123456"
rm -f /tmp/xhs_${NOTE_ID}*
```

**查看临时文件占用：**
```bash
du -sh /tmp/xhs_* /tmp/xhs_analyzer/ 2>/dev/null
```

---

## 5. 完整执行流程（推荐）

### 7.1 标准提取流程（含完整OCR）

```bash
# Step 1: 启动 Chrome（如未运行）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=19222 \
  --user-data-dir="$HOME/Library/Application Support/xhs-crawler-chrome" \
  --no-first-run \
  --no-default-browser-check &

# Step 2: 等待 Chrome 启动
sleep 5
curl http://127.0.0.1:19222/json/list

# Step 3: 执行完整提取（含OCR和自动清理）
cd ~/clawd/skills/xhs-crawler
python3 scripts/xhs_full_extractor.py "<小红书链接>"

# 该脚本会自动完成：
# - 基础数据提取
# - 所有轮播图截图
# - 逐张OCR识别
# - 即时删除截图
# - 生成完整报告
# - 清理所有临时文件
```

### 7.2 完整提取检查清单

执行前：
- [ ] Chrome 已启动且 CDP 可连接
- [ ] Chrome 中已登录小红书
- [ ] Qwen3-VL OCR 服务正常运行
- [ ] 磁盘空间充足（临时文件约需 50MB）

执行中：
- [ ] 笔记页面正常打开
- [ ] 正文内容长度 > 50 字符（否则重试）
- [ ] 评论区滚动加载完成（直到无新增）
- [ ] 评论去重完成
- [ ] 轮播图数量检测正确（记录总页数）
- [ ] 每张截图后立即执行OCR
- [ ] OCR完成后立即删除截图

执行后：
- [ ] 报告文件已生成（> 5KB）
- [ ] JSON数据文件已生成
- [ ] 正文完整性验证通过（长度合理）
- [ ] 评论完整性验证通过（数量接近显示值）
- [ ] 临时截图已删除
- [ ] 临时目录已清理
- [ ] 仅保留最终报告和数据文件

### 7.3 自动化脚本示例

**创建完整提取脚本：**
```bash
#!/bin/bash
# ~/.local/bin/extract-xhs.sh

URL="$1"
if [ -z "$URL" ]; then
    echo "Usage: extract-xhs.sh <小红书链接>"
    exit 1
fi

# 检查 Chrome
if ! curl -s http://127.0.0.1:19222/json/list > /dev/null; then
    echo "🚀 启动 Chrome..."
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=19222 \
        --user-data-dir="$HOME/Library/Application Support/xhs-crawler-chrome" \
        --no-first-run --no-default-browser-check &
    sleep 5
fi

# 执行提取
cd ~/clawd/skills/xhs-crawler
python3 scripts/xhs_full_extractor.py "$URL"

echo "✅ 提取完成！"
```

### 7.4 故障排查速查表

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| CDP 连接失败 | Chrome 未启动 | 启动 Chrome 并检查端口 |
| 页面 404 | 笔记已删除或私密 | 确认链接有效 |
| 评论为 0 | 滚动不足或未登录 | 增加滚动次数，检查登录态 |
| OCR 失败 | Qwen3-VL 服务异常 | 检查服务状态 |
| 磁盘空间不足 | 截图未清理 | 手动清理 /tmp/xhs_analyzer/ |

---

## 6. 调试技巧

### 7.1 启用详细日志

```bash
python3 scripts/xhs_extractor.py "<url>" --verbose
```

日志输出示例：
```
[DEBUG] 2026-02-06 10:30:15 - Connecting to CDP at ws://127.0.0.1:18792/cdp
[DEBUG] 2026-02-06 10:30:16 - CDP connected, target ID: 12345
[DEBUG] 2026-02-06 10:30:17 - Navigating to https://www.xiaohongshu.com/explore/xxx
[DEBUG] 2026-02-06 10:30:20 - Page loaded, extracting data...
```

### 7.2 手动验证 CDP

**检查 CDP 端点：**
```bash
curl http://127.0.0.1:18792/json/list | jq '.[0] | {id, title, url}'
```

**检查页面元素：**
1. 在 Chrome 中打开小红书笔记（确保已登录）
2. 按 F12 打开 DevTools
3. 在 Console 中运行 `extractors.js` 的内容
4. 检查返回的数据结构

### 7.3 测试 API 签名

```bash
python3 -c "
from xhshow import Xhshow
client = Xhshow()
headers = client.sign_headers('GET', '/api/sns/web/v1/feed', '')
print(headers)
"
```

### 7.4 检查 Cookie 有效性

```bash
python3 scripts/cookie_manager.py show
# 检查 web_session 和 a1 是否存在且未过期
```

### 7.5 网络调试

**使用代理：**
```bash
export XHS_PROXY="http://127.0.0.1:7890"
python3 scripts/xhs_extractor.py "<url>"
```

**抓包分析：**
```bash
# 使用 mitmproxy 或 Charles
mitmproxy --mode regular --listen-port 8080
export XHS_PROXY="http://127.0.0.1:8080"
```

---

## 7. 故障排除工作流

### 7.1 标准排查流程

```
遇到问题
  ↓
查看错误信息
  ↓
检查 SKILL.md 故障排除章节
  ↓
按 FAQ 排查（Q1-Q6）
  ↓
启用 --verbose 查看详细日志
  ↓
检查环境变量和依赖
  ↓
尝试最小复现（--no-ocr 等）
  ↓
查看 references/ARCHITECTURE.md
  ↓
提交 Issue（带日志和复现步骤）
```

### 7.2 常见错误快速修复

| 错误 | 快速修复命令 |
|:---|:---|
| Chrome CDP 未启动 | 确保 OpenClaw Extension 已启用并显示 ON，或手动启动 Chrome：`/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=18792` |
| 正文提取不完整 | 增加页面等待时间，使用 `xhs_full_extractor.py` 的多选择器备选方案 |
| 评论提取为 0 或很少 | 增加滚动次数至 15 次，检查 Chrome 登录态是否有效 |
| Cookie 过期 | `python3 scripts/cookie_manager.py save 'web_session=xxx;a1=xxx'` |
| OCR 失败 | `python3 scripts/xhs_extractor.py "<url>" --no-ocr` |
| 临时文件过多 | `rm -f /tmp/xhs_*` |
| 依赖缺失 | `pip3 install -r requirements.txt` |

### 7.3 获取帮助

**提交 Issue 时需提供：**
1. 执行的完整命令
2. `--verbose` 输出的日志（脱敏后）
3. 环境信息：`python3 --version`, OS 版本
4. 复现步骤
5. 已尝试的解决方案

---

**文档版本：** v1.1 | 最后更新：2026-02-23
