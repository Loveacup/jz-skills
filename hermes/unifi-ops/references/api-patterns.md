# UniFi Controller API 模式

## 2FA 登录（密码|验证码）

Controller 开启邮件 2FA 后，API 登录秘诀：

```bash
# 一步完成：密码后加 |验证码
curl -sk --http1.1 --noproxy '*' \
  -c /tmp/unifi_cookies.txt \
  -X POST -H 'Content-Type: application/json' \
  -d '{"username":"<email redacted>","password":"<password redacted>|809822","remember":true}' \
  https://<internal IP redacted>:8443/api/login
# → HTTP 200, meta.rc=ok, cookie 含 csrf_token
```

> 注意：不能用 `/api/auth/login`（UniFi OS 端点），老版 Controller 用 `/api/login`。

## CSRF Token

登录后 cookie 中含 `csrf_token`，所有 POST/PUT/DELETE 需带 header：
```bash
CSRF=$(grep csrf_token /tmp/unifi_cookies.txt | awk -F'\t' '{print $NF}')
curl ... -H "X-CSRF-Token: $CSRF" -b /tmp/unifi_cookies.txt ...
```

## 关键 API 端点

| 操作 | 方法 | 路径 |
|------|------|------|
| 设备列表 | GET | `/api/s/default/stat/device` |
| WLAN 列表 | GET | `/api/s/default/rest/wlanconf` |
| 客户端列表 | GET | `/api/s/default/stat/sta` |
| 强制 provision | POST | `/api/s/default/cmd/devmgr` `{"cmd":"force-provision","mac":"xx:xx:..."}` |
| 重启设备 | POST | `/api/s/default/cmd/devmgr` `{"cmd":"restart","mac":"xx:xx:..."}` |
| 站点健康 | GET | `/api/s/default/stat/health` |
| 验证 session | GET | `/api/self` |

## 注意事项

- 老版 Controller 用 `/api/s/default/...` 路径，不是 `/proxy/network/...`
- HTTP/2 有兼容问题，必须 `--http1.1`
- SSL 自签名证书，需 `-k`
- Session 在 Controller 重启后失效
- 如果长期需要 API 访问，建议在 Controller 中创建本地管理员账号（免 2FA）

## force-provision 实战

```bash
# 删掉 WLAN 后，强制 AP 重新获取配置
curl -sk --http1.1 -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -X POST -d '{"cmd":"force-provision","mac":"18:e8:29:bc:fa:a3"}' \
  https://<internal IP redacted>:8443/api/s/default/cmd/devmgr
```
