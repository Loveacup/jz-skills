# Game Download Speed Diagnosis

Use when the user says a game platform (Steam, Epic, Battle.net, etc.) downloads slowly.

## Step 1: Check Current Routing

```bash
"$SURGE_CLI" environment | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('ProxyGroupSelection',{}), indent=2))"
```

Look for the game platform's policy group (e.g., `🎮 Steam`).

## Step 2: Find Active CDN Connections

```bash
"$SURGE_CLI" dump active | grep -i 'steamcontent\|steamcdn\|cdn.*steam'
```

Key CDN domains to watch:
- Steam: `cache*-hkg*.steamcontent.com` (HK), `cache*-lax*.steamcontent.com` (LA), `*.cs.steamchina.com` (China)
- Epic: `epicgames-download*.akamaized.net`
- Battle.net: `level3.blizzard.com`, `blzddist*.akamaihd.net`

## Step 3: Check DNS Resolution

```bash
nslookup <cdn-domain>
```

- `198.18.x.x` address → Surge fake-IP mode, rules control routing
- Real IP → check if it's China or overseas

## Step 4: Speed Test

```bash
# Test to the specific CDN being used
curl -s -o /dev/null -w "Speed: %{speed_download} B/s\n" --max-time 10 "https://<cdn-domain>/..."

# Compare to general bandwidth
curl -s -o /dev/null -w "Speed: %{speed_download} B/s\n" --max-time 10 "http://speedtest.tele2.net/100MB.zip" -r 0-10485760
```

## Step 5: Diagnose

| CDN Location | Routing | Expected |
|-------------|---------|----------|
| China | DIRECT | Fast (domestic) |
| Overseas (HK/JP/SG) | DIRECT | Slow (cross-border throttling) |
| Overseas | Proxy | Fast (proxy tunnel) |
| China | Proxy | Fast (tromboning but acceptable) |

## Common Root Causes

1. **Game platform selected overseas CDN + routing is DIRECT**: Most common. Steam's `SteamCN.list` forces all `steamcontent.com` to DIRECT, including foreign CDN nodes.

2. **Game platform selected China CDN but routing is proxy**: Tromboning — traffic goes out and back. Not slow but unnecessary.

3. **Download region mismatch**: Steam's download region setting (Settings → Downloads → Download Region) influences CDN selection. Match it to geographic location.

## Fix Paths

1. **Steam-specific**: Change download region to a China city (Shanghai/Beijing/Guangzhou). This biases CDN selection toward domestic nodes that work well over DIRECT.

2. **Config fix**: If the user wants downloads DIRECT but encounters foreign CDN regularly, the issue is CDN selection, not routing. Don't change Surge rules — fix the client setting.

3. **Fallback**: If CDN selection can't be controlled (e.g., Epic always picks overseas), consider routing downloads through proxy instead of DIRECT.
