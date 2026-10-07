#!/usr/bin/env bash
# Install or replace the mac-doctor collector LaunchAgent.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
DAEMON="$SKILL_DIR/scripts/collector-daemon.py"
LABEL="com.hermes.inspection-collector"
PYTHON=/usr/bin/python3
if [[ -x /opt/homebrew/bin/python3 ]]; then
    PYTHON=/opt/homebrew/bin/python3
fi
ACCOUNT_HOME="$("$PYTHON" -c 'import os, pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
PLIST="$ACCOUNT_HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

[[ -x "$PYTHON" ]] || { echo "ERROR: Python not executable: $PYTHON" >&2; exit 1; }
[[ -f "$DAEMON" ]] || { echo "ERROR: collector missing: $DAEMON" >&2; exit 1; }
mkdir -p "$(dirname "$PLIST")"
TMP_PLIST="$(mktemp "${PLIST}.XXXXXX")"
trap 'rm -f "$TMP_PLIST"' EXIT
cat > "$TMP_PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PYTHON</string><string>$DAEMON</string></array>
  <key>StartInterval</key><integer>600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/tmp/mac-doctor-collector.log</string>
  <key>StandardErrorPath</key><string>/tmp/mac-doctor-collector.err</string>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict></plist>
PLISTEOF
/usr/bin/plutil -lint "$TMP_PLIST" >/dev/null
mv "$TMP_PLIST" "$PLIST"
trap - EXIT
# bootout is expected to fail when not currently loaded; bootstrap must succeed.
launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl print "$DOMAIN/$LABEL" >/dev/null
echo "Installed and verified $LABEL ($PYTHON, $DAEMON)"
