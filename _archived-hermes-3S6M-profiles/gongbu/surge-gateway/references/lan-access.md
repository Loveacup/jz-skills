# LAN Access — Wake-on-LAN + SSH to Household Macs

Use when the user asks whether a sleeping Mac/MacBook on the household LAN can be woken or reached over SSH.

## Prerequisites

- Target IP and hostname from `~/.hermes/notes/household-network-device-inventory.md`
- Target MAC address from inventory, DHCP lease, or ARP history
- Whether Remote Login is enabled on the target Mac

## Reachability Probe

```bash
IP=<internal IP redacted>
MAC=5c:9b:a6:7e:e3:e1
ping -c 1 -W 1000 "$IP" || true
nc -vz -G 2 "$IP" 22 || true
arp -a | grep -i "$IP\|$MAC" || true
```

**Interpretation:**
- `arp ... (incomplete)` + ping timeout + SSH timeout → asleep/offline or wrong IP
- TCP/22 open + `Permission denied` → SSH reachable, auth problem → use auth triage below
- `Operation timed out` / `Host is down` → offline/asleep, wrong IP, or Wi‑Fi sleep

**Pitfall:** Inventory IPs can be stale (DHCP drift, private Wi‑Fi addresses). If the user corrects the IP/hostname, immediately pivot to the corrected target — don't defend old inventory.

## SSH Auth Triage

When TCP/22 is reachable but SSH login fails:

```bash
ip=<corrected-ip>
for u in alexcai alex Alex caijinz finalhour; do
  echo "### user=$u"
  ssh -o BatchMode=yes \
      -o ConnectTimeout=5 \
      -o StrictHostKeyChecking=accept-new \
      "$u@$ip" 'echo SSH_OK; hostname; whoami; sw_vers -productVersion' || true
done
```

If all users fail with `Permission denied`, show the local public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

On the target Mac, add it:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo '<public-key>' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Retry: `ssh -o BatchMode=yes -o ConnectTimeout=5 <user>@<ip> 'echo SSH_OK; hostname; whoami'`

## Wake-on-LAN

Send magic packets from the local Mac (bind to actual LAN IP):

```bash
LOCAL_IP=$(ipconfig getifaddr en0)
TARGET_MAC="5c:9b:a6:7e:e3:e1"
TARGET_IP="<internal IP redacted>"
BCAST="<internal IP redacted>"

python3 - <<PY
import socket, binascii, time, os
mac=os.environ.get('TARGET_MAC','').replace(':','').replace('-','')
local=os.environ.get('LOCAL_IP')
ip=os.environ.get('TARGET_IP')
bcast=os.environ.get('BCAST')
packet=b'\\xff'*6 + binascii.unhexlify(mac)*16
for _ in range(3):
    for target in [(bcast,9),(bcast,7),(ip,9),(ip,7),(bcast,0)]:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            if local: s.bind((local,0))
            s.sendto(packet,target)
            print('sent', target)
        except Exception as e:
            print('failed', target, e)
        finally:
            s.close()
    time.sleep(1)
PY
```

Poll for 30-90 seconds:

```bash
for i in $(seq 1 12); do
  sleep 5
  echo "check $i"
  ping -c 1 -W 1000 "$TARGET_IP" || true
  nc -vz -G 2 "$TARGET_IP" 22 && break || true
done
arp -a | grep -i "$TARGET_IP\|$TARGET_MAC" || true
```

## If Wake Fails

Likely causes for MacBooks:
- Not plugged in; lid closed/deep sleep; Wi‑Fi sleep
- "Wake for network access" disabled in System Settings → Battery → Options
- AP/router not forwarding broadcast packets
- Bonjour Sleep Proxy unavailable

Setup for reliable future access:
```bash
sudo pmset -a womp 1      # Wake on network access
sudo pmset -a powernap 1   # Power Nap
```
Also enable **System Settings → General → Sharing → Remote Login** and install SSH key.

## Reporting

Report compactly: IP/hostname → ping result → TCP/22 status → auth result → next step.
