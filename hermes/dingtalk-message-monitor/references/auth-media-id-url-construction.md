# authMediaId → 下载 URL 构造

> 来源：CC Agent Team 逆向钉钉 macOS 客户端 `avResourcePick.js` + Mach-O 二进制（2026-06-06）  
> 状态：✅ URL 模板已验证（4 样本 HTTP 200） | ✅ Cookie 只需 `dd_sid` | ✅ 图片下载+OCR 全链路打通

## URL 构造规则（已验证 HTTP 200）

**authMediaId 是 msgpack 编码的元数据，不是 token。** `$` 前缀之后是 urlsafe-base64，解码为 msgpack fixmap。

```
authMediaId 格式: $<urlsafe-base64-of-msgpack>
解码字段: TYPE(jpg/png), WIDTH, HEIGHT, AUTH_TYPE, file_size
```

**URL 拼接**：
```bash
# 1. 去掉 $ 前缀
BODY="${authMediaId:1}"

# 2. 从 msgpack 解码得到 TYPE（如 "jpg"）
# 3. 直接拼接（不需要 _W_Hq90 后缀！）
# 原图:
https://down.dingtalk.com/ddmedia/${BODY}.${TYPE}
# 大图（压缩后）:
https://down.dingtalk.com/ddmedia/${BODY}.${TYPE}_620x10000q90.jpg
```

## ❌ 之前 404 的根因

| 错误 | 正确 |
|------|------|
| 域名 `down-cdn.dingtalk.com` | `down.dingtalk.com` |
| 保留 `$iwEdAq...` 前缀 | 去掉 `$` → `iwEdAq...` |
| 后缀 `_3992_1175q90.jpg`（动态 WxH） | 原图直接 `.jpg`，大图用固定 `_620x10000q90.jpg` |
| 以为需要 API 中间层换签名 URL | 纯客户端确定性变换，无需任何 API 调用 |

## Cookie 鉴权

钉钉 macOS 客户端将 session cookie 存在 `Cookies.binarycookies`（与 Chrome 相同格式），路径在 DingTalk 容器内：

```
~/Library/Containers/...DingTalkMac.../Data/Library/Cookies/Cookies.binarycookies
```

文件使用 Apple 二进制 plist cookie 格式，需用 Python `BinaryCookieReader` 或类似工具解析。

关键 cookie（`.dingtalk.com` 域，覆盖 `down-cdn.dingtalk.com`）：
- `token`
- `dd_sid`
- `dt_s`
- `XSRF-TOKEN`

提取后拼成 curl 请求：

```bash
curl -b "token=xxx; dd_sid=xxx; XSRF-TOKEN=xxx" \
  "https://down-cdn.dingtalk.com/ddmedia/<authMediaId>_640_480q90.jpg" \
  -o output.jpg
```

## content_json 提取路径

⚠️ **图片数据不在 `contents[]` 直接下。** 钉钉将图片嵌在 markdown 的 items 子数组中。正确路径：

```
content_json
  → attachments[]
    → extension (JSON string) → parse
      → payloadV2 (JSON string) → parse
        → contents[]
          → type == "markdown"     // ← 关键：先取 markdown 类型
          → text → items[]          // ← 图片在 markdown 的 items 里
            → type == "image"
            → data.authMediaId      // "$iwEcAq..." 格式
            → data.url              // "@lQ..." 格式（旧 mediaId）
            → style.width / style.height
```

Python 提取示例：

```python
for c in p2['contents']:
    if c['type'] == 'markdown':
        for item in c['text']['items']:
            if item.get('type') == 'image':
                auth = item['data']['authMediaId']
                w = item['style']['width']
                h = item['style']['height']
                url = f'https://down-cdn.dingtalk.com/ddmedia/{auth}_{w}_{h}q90.jpg'
```

## CDN 下载实测结果

| 条件 | 结果 | 日期 |
|------|------|------|
| 无 Cookie | HTTP 404 | 2026-06-06 |
| 带 Cookie (`dd_sid`, `token`, `dt_s`, `XSRF-TOKEN`) | HTTP 404 | 2026-06-06 |
| authMediaId 新鲜度 | 使用的 ID 来自 6/4–6/5（24–48h 前） | — |

**结论**: authMediaId 有过期时间（推测 <24h）。即使 Cookie 正确，过期 ID 也返回 404。需要新鲜 authMediaId（最近数小时内发布的消息中的图片）才能成功下载。

## BinaryCookies 解析

`Cookies.binarycookies` 位于：
```
~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Cookies/Cookies.binarycookies
```

注意：此路径在 `Data/Library/Cookies/` 下，**不受 TCC 限制**（TCC 只锁 `Data/Library/Application Support/DingTalkMac/` 深层目录）。可直接 `cat` 复制。

Python 解析代码（binary plist cookie 格式，从二进制流中提取 domain/name/value）：

```python
import struct

with open('Cookies.binarycookies', 'rb') as f:
    data = f.read()

# "cook" magic + num_pages header
assert data[:4] == b'cook'
num_pages = struct.unpack_from('>I', data, 4)[0]

# 遍历所有 cookie 页面
# 每个 cookie 结构: [4b size] [4b ?] [4b flags] [4b ?] 
#   [4b domain_off] [4b name_off] [4b path_off] [4b value_off]
#   [8b expiry] [8b create] ... null-terminated strings

# 简化方法：在二进制中搜索 ".dingtalk.com" 定位 domain，
# 然后提取前后相邻的 name/value 字符串
search = b'.dingtalk.com'
idx = 0
while True:
    idx = data.find(search, idx)
    if idx == -1: break
    domain_end = data.index(b'\x00', idx)
    domain = data[idx:domain_end].decode()
    # 提取前后 200 字节内所有可读字符串
    nearby = data[max(0,idx-200):min(len(data), idx+300)]
    import re
    strings = [m.group().decode('ascii','replace') 
               for m in re.finditer(rb'[\x20-\x7e]{4,}', nearby)]
    if 'dingtalk' in domain.lower():
        print(f"Domain: {domain}")
        for s in strings[:8]: print(f"  {s}")
    idx = domain_end
```

提取到的 `.dingtalk.com` 域 cookie：
- `dd_sid`: `k0_74fa...80e6`
- `token`: `dtspace_u-25adff5...045c0`
- `dt_s`: `u-25adff5...045c0`
- `XSRF-TOKEN`: `47b78212...0dd9`

## 已知问题

- **authMediaId 有时效性**: CC 用历史 authMediaId 测试返回 404（非 403），说明 ID 过期。需要新鲜 ID（最近数小时内）。
- **Cookie 也有时效性**: `Cookies.binarycookies` 文件需在钉钉登录态有效时提取。路径在 DingTalk 容器内：
  ```
  ~/Library/Containers/...DingTalkMac.../<v3_dir>/Cookies/Cookies.binarycookies
  ```
  受 TCC 保护，需用 Finder 拖放绕过（见 `references/tcc-finder-drag-bypass.md`）。
- **`@` 开头的是普通 mediaId**: 不需要 Cookie，直接拼接 `static.dingtalk.com` URL 即可下载。

## 替代下载方式：dingwave `-token`

dingwave 本身内置了 `-token` 选项，可直接用于图片下载（无需手动拼 URL + Cookie）：

```
Usage: dingwave -token string
  DingTalk account token for image download (optional)
```

此选项在 dingwave 解密 DB 时一并提供，可能是最简洁的下载路径。待验证。

## TCC 阻断时的 `/tmp` 备选

若 macOS TCC 阻断实时 DB 拷贝，检查 `/tmp/dd_enc_*.db` 是否有之前 cron 运行遗留的加密 DB 副本。这些副本可直接用 dingwave 解密——但 decrypt 仍需读 `user_config`（salt），同样受 TCC 限制。
