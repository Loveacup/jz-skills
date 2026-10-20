# xhs-crawler 故障排除

<!-- 从 SKILL.md 拆出，需要详细排障时加载 -->

## 常见问题速查 (FAQ)

#### Q0: XHS-Downloader 提取失败（`status=failed` / `error`）？

**排查步骤：**
1. **后端是否就绪** — `python3 {baseDir}/scripts/xhs_bootstrap.py doctor`；`ready:false` 则先跑 `xhs_bootstrap.py`
2. **链接是否带 token** — 优先用短链或带 `xsec_token` 的分享链；裸 `explore/<id>` 易被风控失败
3. **链接格式** — 确认是 `explore/`、`discovery/item/` 或 `xhslink.com/`
4. **IP 是否被封** — `status=ip_risk`（300012）见 Q7，**立即止损**
5. **更新上游** — `cd {baseDir}/.xhs-downloader && git pull && uv sync --no-dev`

**cookie 陷阱：** 胶水层已固化 `cookie=""`（`build_command`）；若手改 runner/backend 传了 `None` 会失败。

**Python 版本：** XHS-Downloader 需 ≥3.12，由 `.xhs-downloader/.venv`（uv 管理）满足，与 skill 胶水层的 `python3`(3.9) 互不影响。`uv` 未装则 `brew install uv`。

---

#### Q1: CDP 连接失败怎么办？

**症状：** `🔌 连接 Chrome CDP...` 后报错或超时

**排查步骤：**
1. 检查 Chrome 是否已启动远程调试：
   ```bash
   curl http://127.0.0.1:19222/json/list
   ```
2. 如果未运行，启动 Chrome（带 CDP）：
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=19222 \
     --no-first-run \
     --no-default-browser-check &
   ```
3. 或使用 Comet（备选）：
   ```bash
   /Applications/Comet.app/Contents/MacOS/Comet \
     --remote-debugging-port=19222 \
     --no-first-run \
     --no-default-browser-check &
   ```
   此时需设置环境变量：`export CHROME_CDP_URL=http://127.0.0.1:19222`

**预防措施：**
- 将 Chrome CDP 启动命令加入开机启动项
- 使用 cron job 保持 Chrome 运行

---

#### Q1b: xhshow 导入失败？

**症状：** `ModuleNotFoundError: No module named 'xhshow'` 或 `xhshow 库未安装`

**解决步骤：**
```bash
cd ~/.hermes/skills/xhs-crawler
ls setup.py || echo "需要创建 setup.py"
cat > setup.py << 'EOF'
from setuptools import setup, find_packages
setup(name="xhshow", version="0.1.0", packages=find_packages(), python_requires=">=3.9")
EOF
pip3 install -e .
python3 -c "from xhshow import Xhshow; print('xhshow OK')"
```

**常见陷阱：**
- 系统 Python 是 3.9，但 setup.py 要求 `>=3.10` → 修改 setup.py 为 `>=3.9`
- 使用了 `--user` 安装但不在 PYTHONPATH → 使用 `pip3 install -e .`（开发模式）
- 在错误目录执行 → 必须在 `~/.hermes/skills/xhs-crawler/` 目录执行

---

#### Q2: 评论提取为 0 或很少？

**症状：** 评论区显示有大量评论，但提取结果只有 0-3 条

**原因分析：**
1. **滚动加载未完成** - 小红书使用懒加载，需要多次滚动
2. **DOM 结构变化** - 小红书更新了前端代码
3. **登录态失效** - 部分评论需要登录才能查看

**解决方案：**
1. 脚本已内置 5 次滚动，如仍不足可手动增加：
   ```bash
   python3 scripts/legacy/xhs_extractor_v2.py "<url>" --scroll-times 10
   ```
2. 检查 Chrome 中是否已登录小红书
3. 如 DOM 结构变化，需更新 `extractors.js`（⚠️ 谨慎操作）

**Fallback：**
- 评论不足时标注 `"[评论数据不足]"`，继续生成其他章节

---

#### Q3: OCR 失败或识别率低？

**症状：** 轮播图 OCR 返回空或乱码

**排查步骤：**
1. 检查 Qwen3-VL 服务状态：
   ```bash
   curl $QWEN_API_URL/../models
   ```
2. 检查图片是否成功截图：
   ```bash
   ls -la /tmp/xhs_*.png
   ```
3. 跳过 OCR 快速验证：
   ```bash
   python3 scripts/legacy/xhs_extractor_v2.py "<url>" --no-ocr
   ```

**优化建议：**
- 确保 Qwen3-VL 服务在本地运行（默认端口 9998）
- 对于纯文字笔记，可直接使用 `--no-ocr` 提升速度

---

#### Q4: Cookie 失效如何更新？

**症状：** API 模式返回 401 或 "登录过期"

**解决步骤：**
1. 在 Chrome 中登录小红书
2. 打开 DevTools → Application → Cookies
3. 复制 `web_session` 和 `a1` 字段的值
4. 更新 Cookie：
   ```bash
   python3 scripts/legacy/cookie_manager.py save 'web_session=xxx;a1=xxx'
   ```

**自动化方案：**
- 使用 CDP 模式继承浏览器登录态，无需手动管理 Cookie

---

#### Q7: IP 被小红书封锁（错误 300012）？

**症状：** 浏览器导航到小红书后显示"安全限制"页面，错误码 300012，`error_msg=IP at risk`

**根因：** 小红书对非住宅代理 IP、数据中心 IP、或频繁访问的 IP 实施风控封锁。CDP 和 API 模式都会同时被封。

**处理流程（严格遵守）：**
1. ❌ **不要尝试换方案** — web_extract / browser_navigate / Tavily / CDP / API 全都会被同一个 IP 封锁，切换只是浪费 token
2. ✅ **立即止损** — 确认错误后直接向用户汇报，附上已穷尽的方案列表
3. ✅ **提供三个选项** — (A) 提供 Cookie（`web_session` + `a1`）用 API 模式 (B) 换代理 IP (C) 手动复制内容发过来
4. ⚠️ **禁止**手动写 CDP WebSocket 脚本、浏览器截图 OCR、或搜索笔记 ID 跨平台转载 — 这些都已验证无效

**预防措施：**
- 提前配置 Cookie 可绕过 IP 风控（API 模式对登录用户更宽松）
- 使用住宅代理（如 Bright Data / Oxylabs）

---

#### Q8: OpenCLI feed/search 失败？

**症状：** `opencli xiaohongshu feed/search` 报错或返回空

**排查步骤：**
1. 检查 OpenCLI 版本和能力：
   ```bash
   opencli --version
   opencli list -f json
   opencli xiaohongshu --help
   ```
   预期：version ≥ v1.8.5；`list` 输出含 xiaohongshu；`--help` 列出 `feed` 和 `search`。

2. 检查 browser bridge 和登录态：
   ```bash
   opencli doctor
   opencli xiaohongshu whoami -f yaml --window foreground --site-session persistent
   ```
   预期：`doctor` green for browser bridge；`whoami.logged_in=true`。

3. adapter 报错时收集诊断证据：
   ```bash
   opencli browser xhs-debug bind
   opencli browser xhs-debug state
   opencli browser xhs-debug network --filter "note,title"
   opencli browser xhs-debug unbind
   ```

**常见问题：**
- command missing → 先跑 `opencli list/help`；不要杜撰语法。
- browser bridge/login failure → `opencli doctor`、`whoami` if available；仅在需要 login/MFA 时询问用户。
- schema/selector drift → rerun with verbose/trace if supported；收集 OpenCLI browser network/state 证据。

---

#### Q9: Browser-Harness 连接失败或返回空页面？

**症状：** `browser-harness` 无法启动或 `page_info()` 返回空/错误 URL

**排查步骤：**
1. 检查 browser-harness 健康状态：
   ```bash
   browser-harness --doctor
   ```
2. 确认连接的是主 Chrome 还是 isolated profile：
   - 主 Chrome（带登录态）：`browser-harness`
   - 隔离干净 profile：`browser-harness-isolated`
   - 如之前用了 `browser-harness-isolated` 或自启 `--user-data-dir=...isolated-chrome-profile`，先停掉隔离 Chrome，再声明"主 Chrome 登录态"。
3. 检查 page_info 和截图：
   ```bash
   browser-harness <<'PY'
   print(page_info())
   capture_screenshot()
   PY
   ```

**常见陷阱：**
- 使用 isolated profile 时必须在结果中说明"这不是登录态主 Chrome session"。
- 用户纠正"这个没登录用户的 Chrome"时，立即重验浏览器来源，不要辩解。

**定位：**
- Browser-Harness 只用于诊断 UI/DOM/debug 缺口，产出 partial/debug evidence。
- 能沉淀成稳定流程时再回到 OpenCLI adapter。

---

#### Q5: 提取速度慢如何优化？

| 瓶颈 | 优化方案 | 效果 |
|:---|:---|:---|
| OCR 耗时 | 使用 `--no-ocr` 跳过 | 提升 50-80% |
| 评论滚动 | 减少 `--scroll-times` | 线性减少时间 |
| 网络延迟 | 使用代理 `--proxy` | 视网络环境 |
| 并发提取 | 批量模式（待实现） | 大幅提升 |

---

#### Q6: 报告保存到哪里？

**默认路径：** `~/Documents/Obsidian/AlexCai/00-Inbox/`

**自定义路径：**
```bash
export XHS_OUTPUT_DIR="~/Documents/MyReports"
python3 scripts/legacy/xhs_extractor_v2.py "<url>"
```

**自动检测逻辑：**
1. 查找标准 Obsidian Vault 位置
2. 回退到 `~/clawd/00-Inbox/`
3. 确保目录存在，不存在则创建

---

## 错误代码速查

| 错误信息 | 原因 | 解决方案 |
|:---|:---|:---|
| `CDP Connection Error` | 浏览器未启动 | 启动 Chrome（或 Comet） |
| `TimeoutError` | 页面加载超时 | 检查网络，增加超时时间 |
| `JSONDecodeError` | 提取数据格式异常 | DOM 结构变化，需更新 extractors.js |
| `OCR Service Unavailable` | Qwen3-VL 未启动 | 启动 OCR 服务或使用 `--no-ocr` |
| `Cookie Expired` | 登录态失效 | 更新 Cookie 或使用 CDP 模式 |
| `Rate Limited` | 请求过快 | 增加延迟，降低并发 |
| `IP at risk (300012)` | 当前 IP 被小红书风控封锁 | 见 Fallback 策略：立即止损上报用户，禁止继续尝试其他方案；不要换方案魔改 CDP WebSocket 手写脚本，也不要继续用其他后端重试 |
| `XHS-Downloader 失败 (empty cookie)` | cookie 参数传了 null 或未传 | 改为 `"cookie":""` 显式传空字符串 |
| `OpenCLI command not found` | xiaohongshu command 不存在或版本过旧 | 运行 `opencli list` 和 `opencli xiaohongshu --help`；不要杜撰语法 |
| `OpenCLI browser bridge failure` | browser daemon 未启动或登录态失效 | 运行 `opencli doctor`、`whoami`；仅在需要 login/MFA 时询问用户 |
| `OpenCLI schema/selector drift` | 网页结构变化 | 收集 `opencli browser <session> state/network` 证据；rerun with verbose if supported |
| `Browser-Harness connection error` | 无法连接 Chrome 或 isolated profile | 运行 `browser-harness --doctor`；确认连接主 Chrome 还是 isolated profile |
| `Browser-Harness page_info() empty` | 未打开页面或连接错误 endpoint | 检查 page_info/screenshot；说明是否使用 isolated profile（非登录态）|

---

## 调试技巧

**1. 查看详细日志：**
```bash
python3 scripts/legacy/xhs_extractor_v2.py "<url>" --verbose
```

**2. 手动验证 CDP：**
```bash
curl http://127.0.0.1:18792/json/list | head -20
```

**3. 测试 API 签名：**
```bash
python3 -c "from xhshow import Xhshow; print(Xhshow().sign_headers('GET', '/api/sns/web/v1/feed', ''))"
```

**4. 清理临时文件：**
```bash
rm -f /tmp/xhs_*.json /tmp/xhs_*.png /tmp/xhs_*.txt
```
