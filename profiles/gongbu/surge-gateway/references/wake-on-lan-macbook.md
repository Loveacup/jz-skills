# Wake-on-LAN for household Macs / MacBook SSH access

Use this when the user asks whether a sleeping MacBook can be woken over the LAN before SSH.

## Inputs to collect

- Target IP and hostname from `~/.hermes/notes/household-network-device-inventory.md`.
- Target MAC address from inventory, DHCP lease, or ARP history.
- Whether Remote Login is enabled on the MacBook.

## Read-only probes

```bash
IP=<internal IP redacted>
MAC=5c:9b:a6:7e:e3:e1
ping -c 1 -W 1000 "$IP" || true
nc -vz -G 2 "$IP" 22 || true
arp -a | grep -i "$IP\|$MAC" || true
```

Interpretation:

- `arp ... (incomplete)`, ping timeout, and SSH timeout usually mean the Mac is asleep/offline or on a different IP.
- An open `:22` with `Permission denied` means SSH is reachable but keys/user permissions are not set up.

## Send magic packets from macOS without extra packages

Bind to the actual LAN IP if needed; do not hard-code stale local IPs. Find it with `ifconfig en0 | grep 'inet '`.

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
            if local:
                s.bind((local,0))
            s.sendto(packet,target)
            print('sent', target)
        except Exception as e:
            print('failed', target, e)
        finally:
            s.close()
    time.sleep(1)
PY
```

Then poll for up to ~60 seconds:

```bash
for i in $(seq 1 12); do
  sleep 5
  echo "check $i"
  ping -c 1 -W 1000 "$TARGET_IP" || true
  nc -vz -G 2 "$TARGET_IP" 22 && break || true
done
arp -a | grep -i "$TARGET_IP\|$TARGET_MAC" || true
```

## If wake fails

Likely causes for MacBooks:

- Not plugged in; lid closed/deep sleep; Wi-Fi sleep; AP/router does not forward broadcast; Wake for network access disabled.
- Apple devices may rely on Bonjour Sleep Proxy; WoL over Wi-Fi is less reliable than wired Ethernet.

Ask the user to wake/unlock once, then configure on the MacBook:

```bash
pmset -g | grep -E 'womp|powernap'
sudo pmset -a womp 1
sudo pmset -a powernap 1
```

Also enable **System Settings → General → Sharing → Remote Login**, add the user, and install the Hermes Mac's SSH public key in `~/.ssh/authorized_keys`.
