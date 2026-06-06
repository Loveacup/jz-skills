import base64, sys

# Category id -> CATE_TYPE  (from module 38542)
CATE = {-1:"FILE_UNKNOWN",0:"IMAGE_JPG",1:"IMAGE_GIF",2:"IMAGE_PNG",3:"IMAGE_BMP",
        4:"AUDIO_AMR",5:"AUDIO_MP3",6:"VIDEO_MP4",7:"AUDIO_WAV",8:"NORMAL_FILE"}
TYPE2ID = {v.split("_")[1].lower():k for k,v in CATE.items() if k>=0}

S = "static.dingtalk.com"; L = "down.dingtalk.com"; CDN = "down-cdn.dingtalk.com"
# layout for authMediaId ($)
M = {"IDC":1,"TYPE":2,"AUTH_TYPE":3,"WIDTH":4,"HEIGHT":5,"RAND":6}

def std_b64(s): return s.replace('-','+').replace('_','/')
def urlsafe(s): return s.replace('+','-').replace('/','_')

def msgpack_decode(b):
    # minimal decoder for fixmap/fixstr/ints used by DingTalk mediaId
    pos = 0
    def rd():
        nonlocal pos
        c = b[pos]; pos += 1
        if c <= 0x7f: return c                       # positive fixint
        if 0x80 <= c <= 0x8f:                         # fixmap
            n = c & 0x0f; d={}
            for _ in range(n):
                k = rd(); v = rd(); d[k]=v
            return d
        if 0x90 <= c <= 0x9f:                         # fixarray
            return [rd() for _ in range(c & 0x0f)]
        if 0xa0 <= c <= 0xbf:                         # fixstr
            n = c & 0x1f; s = b[pos:pos+n]; pos2(n); return s.decode('latin1')
        if c == 0xcc: v=b[pos]; pos2(1); return v
        if c == 0xcd: v=int.from_bytes(b[pos:pos+2],'big'); pos2(2); return v
        if c == 0xce: v=int.from_bytes(b[pos:pos+4],'big'); pos2(4); return v
        if c == 0xd0: v=int.from_bytes(b[pos:pos+1],'big',signed=True); pos2(1); return v
        if c == 0xd1: v=int.from_bytes(b[pos:pos+2],'big',signed=True); pos2(2); return v
        if c == 0xd2: v=int.from_bytes(b[pos:pos+4],'big',signed=True); pos2(4); return v
        if c == 0xd3: v=int.from_bytes(b[pos:pos+8],'big',signed=True); pos2(8); return v
        if c == 0xcf: v=int.from_bytes(b[pos:pos+8],'big'); pos2(8); return v
        if c == 0xcb:
            import struct; v=struct.unpack('>d', b[pos:pos+8])[0]; pos2(8); return v
        if 0xe0 <= c <= 0xff: return c-256            # negative fixint
        raise ValueError(f"unhandled byte 0x{c:02x} at {pos-1}")
    def pos2(n):
        nonlocal pos; pos += n
    return rd()

def build(amid, image_size="origin", auto_rotate=False):
    assert amid[0]=='$', "only authMediaId ($) handled here"
    body = amid[1:]                       # strip $
    raw = base64.b64decode(std_b64(body) + '='*(-len(body)%4))
    obj = msgpack_decode(raw)
    typ = obj[M["TYPE"]]                  # e.g. "jpg"/"png"
    auth = obj[M["AUTH_TYPE"]]
    w = obj.get(M["WIDTH"],0); h = obj.get(M["HEIGHT"],0)
    cate = CATE[TYPE2ID[typ.lower()]].split("_")   # ["IMAGE","JPG"]
    host = CDN if auth in (0,6) else L
    O = f"https://{host}/ddmedia/"
    E = typ; P = ""
    if cate[0]=="IMAGE":
        if image_size=="origin":
            C = body + P + "." + E
        elif image_size=="thumb":
            suf = "_620x10000.jpg" if cate[1]=="GIF" else "_120x120q90.jpg"
            C = body + P + "." + E + suf
        elif cate[1]=="GIF":
            C = body + P + "." + E
        else:  # default large
            suf = "_620x10000q90" + ("g" if auto_rotate else "") + ".jpg"
            C = body + P + "." + E + suf
    else:
        C = body + "." + E
    url = O + urlsafe(C)
    return dict(url=url, type=typ, auth_type=auth, width=w, height=h, host=host, fields=obj)

if __name__=="__main__":
    for amid in sys.argv[1:]:
        for sz in ("origin","default"):
            r = build(amid, sz)
            print(f"[{sz:7}] {r['url']}")
        print(f"          type={r['type']} auth_type={r['auth_type']} {r['width']}x{r['height']} host={r['host']}")
        print(f"          raw fields={r['fields']}")
        print()
