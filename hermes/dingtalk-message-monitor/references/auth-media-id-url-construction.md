# authMediaId → 下载 URL 构造

> 来源：CC Agent Team 逆向钉钉 macOS 客户端 `avResourcePick.js` + Mach-O 二进制（2026-06-06）
> 状态：✅ URL 模板已验证 HTTP 200（4 样本） | ✅ Cookie 只需 `dd_sid` | ✅ 图片下载+OCR 全链路打通

## URL 构造规则（已验证）

**authMediaId 是 msgpack 编码的元数据，不是 token。**

```
authMediaId: $iwEdAqNwbmcDAQTRDs4...
              ↑ $ 前缀
                ↑ 之后是 urlsafe-base64 → msgpack fixmap
```

msgpack 解码字段：

| key | 含义    | 样本值   |
|-----|---------|----------|
| 1   | IDC     | 29       |
| 2   | TYPE    | "jpg"    |
| 3   | AUTH_TYPE | 1     |
| 4   | WIDTH   | 1920     |
| 5   | HEIGHT  | 1440     |
| 6   | RAND    | 16 bytes |
| 11  | file_size | 220259 |

**URL 拼接**（`avResourcePick.js` 模块 39549 逆向）：

```bash
# 1. 去掉 $ 前缀
BODY="${authMediaId:1}"        # iwEdAqNwbmc...

# 2. msgpack 解码得到 TYPE（"jpg"/"png"/"gif"）
# 3. 原图（全分辨率）：
https://down.dingtalk.com/ddmedia/${BODY}.${TYPE}

# 4. 大图（压缩后，固定后缀）：
https://down.dingtalk.com/ddmedia/${BODY}.${TYPE}_620x10000q90.jpg
```

## 之前 404 的根因

| 错误                                    | 正确                                  |
|-----------------------------------------|--------------------------------------|
| 域名 `down-cdn.dingtalk.com`            | `down.dingtalk.com`                  |
| 保留 `$` 前缀                           | 去掉 `$`                             |
| 后缀 `_3992_1175q90.jpg`（动态 WxH）    | 原图直接 `.jpg`                      |
| 以为需要 API 中间层                      | 纯客户端确定性变换，无需 API 调用    |
| 传了 `token`/`dt_s`/`XSRF-TOKEN` 所有 4 个 cookie | **只需 `dd_sid`** 一个           |

## Cookie 鉴权

仅需 `dd_sid`：

```bash
DDSID="k0_74fa0b0b9ed5236ac15b_0b0b74fa6a23d59e691c001a5901b804caabf67c80e6"
curl -fL -H "User-Agent: Mozilla/5.0" -b "dd_sid=$DDSID" \
  "https://down.dingtalk.com/ddmedia/${BODY}.jpg" -o image.jpg
```

无 cookie → 403。`dd_sid` 从 `Cookies.binarycookies` 中提取（路径：`~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Cookies/`，不受 TCC 限制，可直接 `cat`）。

## 实测记录

CC Agent Team 用 `dd_fresh_merged.db` 中 4 个新鲜 authMediaId 测试：

| 尺寸      | file_size 字段 | 实际下载       | 状态 |
|-----------|---------------|----------------|------|
| 1920×1440 | 220,259       | 220,259 bytes  | ✅   |
| 4096×3072 | 12,791,858    | 12,791,858     | ✅   |
| (jpg)     | —             | 1,754,513      | ✅   |
| thumb     | —             | 2,609          | ✅   |

下载字节数与 msgpack `file_size` 字段完全吻合。所有 4 个 HTTP 200。

旧 authMediaId（24h+ 前发布）可能过期返回 404，必须趁热下载。

## content_json 提取路径

```python
# 图片在 markdown items 里，不在 contents[] 直接下
p2 = json.loads(ext['payloadV2'])
for c in p2['contents']:
    if c['type'] == 'markdown':
        for item in c['text']['items']:
            if item.get('type') == 'image':
                auth = item['data']['authMediaId']   # "$iwEdAq..."
                w = item['style']['width']
                h = item['style']['height']
```

## 工具

- `scripts/build_url.py` — `python3 build_url.py '$iwEdAq...'` → 输出 URL + 解码字段
- `scripts/dingtalk-image-ocr.py` — 全自动：下载 + GPT-5.5 vision OCR + 缓存
- `scripts/dingtalk-class-monitor.sh` v5 — cron 监控脚本，已集成图片 OCR
