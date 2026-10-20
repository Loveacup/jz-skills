# XHS-Downloader 集成参考

## 来源

- 仓库：`https://github.com/JoeanAmier/XHS-Downloader`
- 438 commits · 18 releases · 2026 年持续活跃
- License: GPL-3.0
- Python ≥3.12 必需

## 已验证成功的工作流（2026-06-10）

### 部署

```bash
cd /tmp
git clone --depth 1 https://github.com/JoeanAmier/XHS-Downloader.git
cd XHS-Downloader
uv sync --no-dev
```

### 启动 + 提取

```bash
# Terminal 1: 启动 API 服务器
cd /tmp/XHS-Downloader && uv run main.py api

# Terminal 2: 提取笔记（curl）
curl -s -X POST http://127.0.0.1:5556/xhs/detail \
  -H "Content-Type: application/json" \
  -d '{"url":"https://xhslink.com/o/6ftw6lhxIOy","download":false,"cookie":""}'
```

### 验证过的测试案例

测试笔记：ID `6a116dd8000000003502a688`
- 短链 `http://xhslink.com/o/6ftw6lhxIOy` → ✅ 成功（免 Cookie）
- 直接链接 `https://www.xiaohongshu.com/explore/6a116dd8000000003502a688` → ❌ 失败
- 传入 `"cookie":""` 空字符串 → ✅ 关键
- 传入 `"cookie":null` 或不传 cookie → ❌ 失败

## 返回数据样本

```json
{
  "message": "获取小红书作品数据成功",
  "data": {
    "收藏数量": "1641",
    "评论数量": "15",
    "分享数量": "190",
    "点赞数量": "959",
    "作品标签": "Obsidian Obsidian插件 Ob ob插件 Obsidian插件 AI工具 插件",
    "作品ID": "6a116dd8000000003502a688",
    "作品标题": "",
    "作品描述": "Obsidian 用得越久，我反而越离不开这 3 个插件\n分享三个高效插件：自动保存历史、图片处理和智能搜索...",
    "作品类型": "图文",
    "发布时间": "2026-05-23_20:01:14",
    "作者昵称": "艾康的AI自留地",
    "作者ID": "65e17d09000000000500d97b",
    "下载地址": ["17 image URLs"]
  }
}
```

## 与 CDP/xhshow 方案对比

| 维度 | XHS-Downloader | CDP + xhshow |
|------|---------------|--------------|
| 免登录提取 | ✅ `cookie:""` | ❌ 需 Chrome 登录态 |
| 提取正文 | ⚠️ 可能截断（图文在图片中） | ✅ 完整正文 |
| 提取评论 | ❌ 需登录 | ✅ 可滚动加载 |
| 轮播图 OCR | ❌ 只返回 URL | ✅ Qwen3-VL OCR |
| 部署复杂度 | ⭐ 简单（git clone + uv sync） | ⭐⭐⭐ CDP + xhshow + Chrome登录 |
| 稳定性 | ⭐⭐⭐ 438 commits 维护中 | ⭐ 签名算法容易过期 |
| Python 要求 | ≥3.12 | ≥3.9（签名库 3.10+） |

## 服务管理

```bash
# 查看进程
lsof -i:5556

# 停止服务
kill $(lsof -t -i:5556) 2>/dev/null
```
