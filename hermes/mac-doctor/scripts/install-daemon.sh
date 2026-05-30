#!/usr/bin/env bash
# install-daemon.sh — Install the macOS Inspection Collector LaunchAgent
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DAEMON="$SKILL_DIR/scripts/collector-daemon.py"
PLIST="$HOME/Library/LaunchAgents/com.hermes.inspection-collector.plist"
LABEL="com.hermes.inspection-collector"

echo "=== Hermes Inspection Collector Installer ==="
echo ""

# Check Python
PYTHON=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: python3 not found"
    exit 1
fi
echo "Python: $PYTHON ($($PYTHON --version))"

# Ensure daemon exists
if [ ! -f "$DAEMON" ]; then
    echo "ERROR: collector-daemon.py not found at $DAEMON"
    exit 1
fi
echo "Daemon: $DAEMON"

# Create plist
mkdir -p "$(dirname "$PLIST")"

cat > "$PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$DAEMON</string>
    </array>
    <key>StartInterval</key>
    <integer>600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/hermes-inspection-collector.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/hermes-inspection-collector.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
PLISTEOF

echo "Plist: $PLIST"

# Unload existing if any
launchctl unload "$PLIST" 2>/dev/null || true

# Load
launchctl load "$PLIST"
echo ""

echo "=== Installation complete ==="
echo ""
echo "Agent status:"
launchctl list "$LABEL" 2>/dev/null || echo "  (checking...)"

echo ""
echo "Logs: tail -f /tmp/hermes-inspection-collector.log"
echo "Manual test: $PYTHON $DAEMON"
echo ""
echo "Commands:"
echo "  Status:   launchctl list $LABEL"
echo "  Stop:     launchctl unload $PLIST"
echo "  Start:    launchctl load $PLIST"
echo "  Uninstall: launchctl unload $PLIST && rm $PLIST"
echo "  Reinstall: $0"
