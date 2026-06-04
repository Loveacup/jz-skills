#!/bin/bash
# CosyVoice TTS wrapper for Hermes command provider.
# Usage: cosyvoice-tts.sh <text_file> <voice> <output_path>
#
# Hermes writes the TTS text to a temp file and passes:
#   {input_path} → text file path
#   {voice}      → speaker ID (e.g., "AlexCai", "女主播")
#   {output_path} → where to write the OGG output
#
# This script reads the text, calls the CosyVoice API, and saves the result.

set -euo pipefail
TEXT_FILE="$1"
VOICE="$2"
OUTPUT="$3"
API="http://<internal IP redacted>:8088/CosyVoice/v1/tts"

TEXT=$(cat "$TEXT_FILE")
if [ -z "$TEXT" ]; then
  echo "Error: empty input text" >&2
  exit 1
fi

curl -sS -X POST "$API" \
  -F "text=$TEXT" \
  -F "spk_id=$VOICE" \
  --output "$OUTPUT"

if [ ! -s "$OUTPUT" ]; then
  echo "Error: CosyVoice produced empty output" >&2
  exit 1
fi
