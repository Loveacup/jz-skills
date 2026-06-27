#!/bin/bash
# 钉钉群文件下载器 — 按 spaceId(s_id) + fileId(f_id) 下载
# 自动从运行中的钉钉 App 的 binarycookies 提取 cspace 会话 token
#
# 用法:
#   ./dd_download.sh <s_id> <f_id> <输出文件名>
# 例:
#   ./dd_download.sh 22147563244 224016336448 "6月5日计算练习.pdf"
set -e

SP="$1"; FID="$2"; OUT="${3:-dd_file_$2}"
if [ -z "$SP" ] || [ -z "$FID" ]; then
  echo "用法: $0 <s_id> <f_id> [输出文件名]"; exit 1
fi

CB="$HOME/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac/Data/Library/Cookies/Cookies.binarycookies"
[ -f "$CB" ] || { echo "找不到钉钉 cookie 库: $CB"; exit 1; }

# 从 binarycookies 提取 .dingtalk.com 的 dt_s（cspace 会话 token）
TOKEN=$(python3 - "$CB" <<'PY'
import struct,sys
data=open(sys.argv[1],'rb').read()
np=struct.unpack('>I',data[4:8])[0]
ps=[struct.unpack('>I',data[8+i*4:12+i*4])[0] for i in range(np)]
off=8+np*4; pages=[]
for sz in ps: pages.append(data[off:off+sz]); off+=sz
def cstr(b,p): e=b.index(b'\x00',p); return b[p:e].decode('utf-8','replace')
val=None
for page in pages:
    n=struct.unpack('<I',page[4:8])[0]
    for i in range(n):
        co=struct.unpack('<I',page[8+i*4:12+i*4])[0]; c=page[co:]
        d=cstr(c,struct.unpack('<I',c[16:20])[0]); nm=cstr(c,struct.unpack('<I',c[20:24])[0]); v=cstr(c,struct.unpack('<I',c[28:32])[0])
        if d.endswith('.dingtalk.com') and nm=='dt_s': val=v
print(val or '')
PY
)
[ -n "$TOKEN" ] || { echo "未提取到 cspace token(dt_s)，请确认钉钉已登录"; exit 1; }

URL="https://space.dingtalk.com/attachment/mdown?biztype=file&bizid=${SP}&objectid=${FID}"
echo "下载: $OUT"
echo "URL : $URL"
curl -fL -b "dt_s=${TOKEN}" "$URL" -o "$OUT" \
  -w "完成: HTTP=%{http_code}  size=%{size_download} bytes  type=%{content_type}\n"
file "$OUT"
