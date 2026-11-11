#!/bin/sh
# PC 内蔵マイクで録音する（48 kHz モノラル 16 bit）。
# 使い方: scripts/audio/record_mic.sh <秒> <ラベル>  → prsk/logs/mic/tap_YYYYmmdd_HHMMSS_<ラベル>.wav
SEC=${1:-40}; LABEL=${2:-test}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; OUT="$ROOT/prsk/logs/mic/tap_$(date +%Y%m%d_%H%M%S)_${LABEL}.wav"
mkdir -p "$ROOT/prsk/logs/mic"
ffmpeg -hide_banner -loglevel error -f dshow -i "audio=マイク配列 (Realtek(R) Audio)" \
  -t "$SEC" -ac 1 -ar 48000 -c:a pcm_s16le -y "$OUT" && echo "$OUT"
