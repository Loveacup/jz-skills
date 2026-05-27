# MacBook SSH reachability and auth triage

Use this when a household Mac/MacBook is reachable on TCP/22 but SSH login fails.

## Key lesson

Do not stop at stale inventory. If the user corrects the IP/hostname, immediately pivot to the corrected target and re-run reachability + auth probes. Household DHCP/private Wi‑Fi addresses drift, and inventory labels can lag.

## Interpretation

- `ping` succeeds + `nc -vz <ip> 22` succeeds = network path and Remote Login service are up.
- `Permission denied (publickey,password,keyboard-interactive)` = SSH service is reachable; problem is username/key/auth policy, not network/Wake-on-LAN.
- `Operation timed out` / `Host is down` = host offline/asleep, wrong IP, firewall, or Wi‑Fi sleep/WoL limitation.

## Probe sequence

```bash
ip=<corrected-ip>
ping -c 1 -W 1000 "$ip" || true
nc -vz -G 3 "$ip" 22 || true

for u in alexcai alex Alex caijinz finalhour; do
  echo "### user=$u"
  ssh -o BatchMode=yes \
      -o ConnectTimeout=5 \
      -o StrictHostKeyChecking=accept-new \
      "$u@$ip" 'echo SSH_OK; hostname; whoami; sw_vers -productVersion' || true
done
```

If all common users fail with `Permission denied`, show the local public key and have the user add it on the MacBook:

```bash
cat ~/.ssh/id_ed25519.pub
```

On the MacBook, for the correct local account:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo '<public-key-from-agent-host>' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Then retry:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 <correct-user>@<ip> 'echo SSH_OK; hostname; whoami'
```

## Reporting

Report compactly:

- IP/hostname tested
- whether ping works
- whether TCP/22 is open
- whether auth succeeded or failed
- if auth failed, provide the exact `authorized_keys` fix and ask for `whoami` only if username remains unknown
