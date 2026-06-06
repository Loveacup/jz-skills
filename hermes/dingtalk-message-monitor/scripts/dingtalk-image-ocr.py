#!/usr/bin/env python3
"""
DingTalk 图片下载 + OCR 脚本
输入：dingwave 解密的 SQLite DB 路径
输出：JSON 数组 [{time, text, image_path, size}, ...]

流程：authMediaId → build_url → curl + dd_sid → download → GPT-5.5 vision OCR
内置缓存：相同 authMediaId 不重复下载/OCR
"""

import sys, os, json, sqlite3, base64, subprocess, tempfile, hashlib
from datetime import datetime

# Config
CLASS_CID = "52993580719"
DDSID = "k0_74fa0b0b9ed5236ac15b_0b0b74fa6a23d59e691c001a5901b804caabf67c80e6"
IMAGE_DIR = os.path.expanduser("~/.hermes/data/dingtalk_images")
OCR_CACHE = os.path.expanduser("~/.hermes/data/dingtalk_images/.ocr_cache.json")
STATE_FILE = os.path.expanduser("~/.hermes/data/dingtalk_images/.last_downloaded")
VISION_MODEL = "gpt-5.5"

# ── Minimal msgpack decoder ──
def msgpack_decode(b):
    pos = 0
    def rd():
        nonlocal pos
        c = b[pos]; pos += 1
        if c <= 0x7f: return c
        if 0x80 <= c <= 0x8f: n = c & 0x0f; d = {}; [d.update({rd(): rd()}) for _ in range(n)]; return d
        if 0x90 <= c <= 0x9f: return [rd() for _ in range(c & 0x0f)]
        if 0xa0 <= c <= 0xbf: n = c & 0x1f; s = b[pos:pos+n]; pos += n; return s.decode('utf-8', errors='replace')
        if c in (0xcc,0xcd,0xce,0xcf,0xd0,0xd1,0xd2,0xd3):
            sizes = {0xcc:1,0xcd:2,0xce:4,0xcf:8,0xd0:1,0xd1:2,0xd2:4,0xd3:8}
            signed = c >= 0xd0
            return int.from_bytes(b[pos:pos+sizes[c]], 'big', signed=signed)
        if 0xe0 <= c <= 0xff: return c - 256
        raise ValueError(f"unhandled 0x{c:02x}")
    return rd()

def build_url(amid):
    body = amid[1:]
    raw = base64.b64decode(body.replace('-','+').replace('_','/') + '=' * (-len(body) % 4))
    obj = msgpack_decode(raw)
    typ = obj.get(2, 'jpg')
    return f"https://down.dingtalk.com/ddmedia/{body}.{typ}", obj

# ── Extract images from DB ──
def extract_images(db_path, last_id=0):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT rowid, datetime(created_at/1000, 'unixepoch', '+8 hours'), content_json
        FROM messages WHERE cid=? ORDER BY created_at ASC
    """, (CLASS_CID,)).fetchall()
    conn.close()
    images = []
    for rowid, ts, raw in rows:
        if rowid <= last_id: continue
        d = json.loads(raw)
        for att in d.get('attachments', []):
            ext_s = att.get('extension', '{}')
            ext = json.loads(ext_s) if ext_s else {}
            p2_s = ext.get('payloadV2', '{}')
            if not p2_s: continue
            p2 = json.loads(p2_s) if isinstance(p2_s, str) else p2_s
            for c in p2.get('contents', []):
                if c.get('type') != 'markdown': continue
                for item in c.get('text', {}).get('items', []):
                    if item.get('type') != 'image': continue
                    data = item.get('data', {})
                    auth = data.get('authMediaId', '')
                    if auth:
                        w = item.get('style', {}).get('width', 0)
                        h = item.get('style', {}).get('height', 0)
                        images.append({'rowid': rowid, 'time': ts, 'authMediaId': auth, 'width': w, 'height': h})
    return images

# ── Download ──
def download_image(amid, out_path):
    url, meta = build_url(amid)
    r = subprocess.run(['curl', '-s', '-f', '-L', '-o', out_path,
        '-b', f'dd_sid={DDSID}', '-H', 'User-Agent: Mozilla/5.0', url],
        capture_output=True, timeout=30)
    if r.returncode != 0: return None, f"curl {r.returncode}"
    sz = os.path.getsize(out_path)
    if sz < 100: return None, f"too small ({sz}b)"
    return url, None

# ── OCR ──
def ocr_image(img_path):
    try:
        import urllib.request, ssl, yaml
    except ImportError:
        return "[OCR: missing deps]"
    with open(img_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    # Try to read API key from Hermes config
    api_key = os.environ.get('OPENAI_API_KEY', '')
    api_base = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    if not api_key:
        try:
            for prof in ['default', 'cron-worker']:
                cfg_path = os.path.expanduser(f'~/.hermes/profiles/{prof}/config.yaml')
                if os.path.exists(cfg_path):
                    with open(cfg_path) as f: cfg = yaml.safe_load(f)
                    for p in cfg.get('providers', {}).values():
                        if 'openai' in p.get('base_url', ''):
                            api_key = p.get('api_key', ''); api_base = p.get('base_url', api_base)
        except: pass
    if not api_key: return "[OCR: no API key]"
    payload = {'model': VISION_MODEL, 'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': '请提取这张图片中的所有文字内容，保持原始格式和排版。只输出文字，不要额外说明。'},
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}]}], 'max_tokens': 2000}
    req = urllib.request.Request(f'{api_base}/chat/completions', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'})
    try:
        resp = urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=60)
        return json.loads(resp.read())['choices'][0]['message']['content']
    except Exception as e:
        return f"[OCR 失败: {e}]"

# ── Main ──
def main():
    if len(sys.argv) < 2:
        print("[]"); return
    db_path = sys.argv[1]
    os.makedirs(IMAGE_DIR, exist_ok=True)
    ocr_cache = json.load(open(OCR_CACHE)) if os.path.exists(OCR_CACHE) else {}
    last_id = int(open(STATE_FILE).read().strip() or 0) if os.path.exists(STATE_FILE) else 0
    images = extract_images(db_path, last_id)
    if not images:
        print("[]"); return
    outputs = []
    for img in images:
        aid = img['authMediaId']
        hsh = hashlib.md5(aid.encode()).hexdigest()[:12]
        path = os.path.join(IMAGE_DIR, f"{img['time'][:10]}_{hsh}.jpg")
        if hsh in ocr_cache:
            text = ocr_cache[hsh]
        elif os.path.exists(path):
            text = ocr_image(path)
            ocr_cache[hsh] = text
        else:
            url, err = download_image(aid, path)
            if err: continue
            text = ocr_image(path)
            ocr_cache[hsh] = text
        outputs.append({'time': img['time'], 'text': text, 'image_path': path, 'size': f"{img['width']}x{img['height']}"})
    with open(OCR_CACHE, 'w') as f: json.dump(ocr_cache, f, ensure_ascii=False)
    with open(STATE_FILE, 'w') as f: f.write(str(max(img['rowid'] for img in images)))
    print(json.dumps(outputs, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
