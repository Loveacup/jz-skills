# 钉钉文件（PDF/Excel）下载 URL 逆向 — 结论

> 状态：**已验证可下载**。3 个样本文件（PDF×2、Excel×1，含 14MB 大文件）全部成功下载，PDF/OLE 校验通过。

---

## 1. 下载 URL 模板（核心结论）

```
https://space.dingtalk.com/attachment/mdown?biztype=file&bizid={s_id}&objectid={f_id}
```

| 占位符 | 含义 | 样本值 | 来源（解密 DB extension） |
|--------|------|--------|--------------------------|
| `{s_id}` | 群文件空间 ID（spaceId） | `22147563244` | `extension.s_id` |
| `{f_id}` | 文件 dentryId / fileId | `224016336448` | `extension.f_id` |

- `objectid` **直接用 `f_id` 即可**，无需解析文件路径 —— 这是最稳妥的方式。
- `objectid` 也接受空间内路径（如 `/6月5日计算练习.pdf`），但仅当文件在空间根目录、且文件名精确匹配时才命中；子目录文件会 `406 file not exist`。**所以一律用 `f_id`。**
- 返回 `Content-Type: application/octet-stream` + `Content-Disposition: attachment; filename*=utf-8''...`，body 即文件原始字节。PDF / Excel / 任意类型通用，无需区分 `f_type`。

### 高层封装（前端实际拼的 URL，会 302 跳到上面的 mdown）
```
https://space.dingtalk.com/auth/download?spaceId={s_id}&path=/{文件名}
```
来自 `chatfile.js` 的 `Ot = (e,t,n) => bt + "/auth/download?spaceId=" + e + "&path=" + (t||n)`。
**不要用这个**：它按 path 而非 id，子目录/重名会失败。直接打 `mdown` 用 `f_id` 最可靠。

---

## 2. 鉴权方式

**只需要一个 cookie**（cspace 会话 token）：

```
Cookie: token=dtspace_{T}
```
或等价地：
```
Cookie: dt_s={T}
```
其中 `{T}` 形如 `u-25adff5-9e9bfa7d63-21084bdf-5438b1-610a7ac9-a2d6775a-7931-48b3-a751-795340e045c0`
（`token` 的值 = 字面 `dtspace_` + `dt_s` 的值，是同一个密钥）。

实测最小集：
| Cookie | 结果 |
|--------|------|
| `token=dtspace_...` 单独 | **200 ✓** |
| `dt_s=u-...` 单独 | **200 ✓** |
| `dd_sid=...` 单独 | 401 |
| `uid=...` 单独 | 401 |
| 无 | 401 |

> ⚠️ 注意：原任务里给的 `dd_sid` **不是**下载凭证，下载用的是 cspace 的 `token`/`dt_s`。

### token 从哪来
钉钉客户端通过 LWP RPC `getMainServerCookie` / `space_cookie_service` 拿到此 token，写入本机 cookie 库：
```
~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Cookies/Cookies.binarycookies
```
域 `.dingtalk.com` 下的 cookie `token`（或 `dt_s`）。`parse_cookies.py` 可解析。token 长期有效，过期后重新从运行中的 App 提取即可。

---

## 3. 可执行 curl 示例

```bash
# T = cspace token（dt_s 的值），从 binarycookies 提取
T="u-25adff5-9e9bfa7d63-21084bdf-5438b1-610a7ac9-a2d6775a-7931-48b3-a751-795340e045c0"
SP="22147563244"      # s_id
FID="224016336448"    # f_id

curl -L -b "dt_s=$T" \
  "https://space.dingtalk.com/attachment/mdown?biztype=file&bizid=$SP&objectid=$FID" \
  -o "6月5日计算练习.pdf"
```

一行版（自动从 App cookie 库取 token，按 f_id 下载）：见 `dd_download.sh`。

---

## 4. 验证结果

| 文件 | f_id | DB f_size | 实际下载 | 校验 |
|------|------|-----------|----------|------|
| 6月5日计算练习.pdf | 224016336448 | 258752 | **258752** | `PDF document, v1.7` ✓ |
| 三下古诗176-200首.pdf | 223520886448 | 14235396 | **14235396** | `PDF document, v1.3` ✓ |
| 【302】家长护学岗….xls | 223664230720 | 26624 | 15360 | `Composite Document (Excel)` ✓ |

> xls 的 DB `f_size` 是旧值（26624），实际文件 15360 字节，但内容是有效的 DingT 创建的 Excel。**DB 里的 f_size 不可靠，以下载实际为准。**

---

## 5. 逆向路径记录（为什么是这个结论）

1. macOS 钉钉是**原生 App（CEF + wukong/lwp）**，非 Electron，给定的 asar 路径不存在。
2. 文件附件（`type=0`, `contentType=501`）属**钉盘 cspace**（`extension` 含 `s_id/f_id/sp_dentrySpaceType=group`）。
3. 主二进制 strings 命中 RPC：`/r/Adaptor/CSpace/downloadInfoV2`、`getDownloaderInfo`，以及 HTTP 端点 `space.dingtalk.com/auth/download?spaceId=...`。
4. `/r/Adaptor/*` 仅走 lwp 长连接（HTTPS 直打 302/404），webview 也通过 `ddExec` 原生 bridge 调用，**无纯 HTTP 的 RPC 网关**。
5. 关键突破：公开 CDN 上的 `chatfile.js`（`g.alicdn.com/dingding/cspace-chat-file/1.91.0/chatfile.js`）暴露了 `Ot` 拼 URL 逻辑 → `/auth/download?spaceId=&path=` → 302 到 `/attachment/mdown?biztype=file&bizid=&objectid=`。
6. 实测发现 `mdown` 的 `objectid` 既接受 path 也接受 **fileId**，用 fileId 即可绕过路径解析。
7. cookie 来自运行中 App 的 `Cookies.binarycookies`，实测下载只认 `token`/`dt_s`。

辅助发现：本机钉钉以 `--remote-debugging-port=9222` 启动（但该端口实际未监听，CDP 不可用），且全部流量经 Surge(`127.0.0.1:6152`) 隧道转发（未对 dingtalk 做 MITM 解密）。
