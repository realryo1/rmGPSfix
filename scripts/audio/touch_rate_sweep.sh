#!/usr/bin/env bash
# /proc/touchscreen/tp_report_rate と play_game を切り替えて、実際の報告間隔を測る。
# 最初のタッチを待ってから開始する。終了時に元の値へ戻す。
# 使い方: scripts/audio/touch_rate_sweep.sh [各段の秒数=10]
set -u
export MSYS_NO_PATHCONV=1
SEC=${1:-10}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; OUT="$ROOT/prsk/logs/$(date +%Y%m%d_%H%M%S)_touch_sweep"; mkdir -p "$OUT"
TOUCH=$(adb shell 'getevent -pl 2>/dev/null' | tr -d '\r' | awk '/add device/{d=$NF} /synaptics_tcm_touch/{print d}')
get() { adb shell "su -c 'cat /proc/touchscreen/$1'" | tr -d '\r'; }
set_() { adb shell "su -c 'echo $2 > /proc/touchscreen/$1'"; }
R0=$(get tp_report_rate); G0=$(get play_game)
echo "元の値: tp_report_rate=$R0 play_game=$G0" | tee "$OUT/summary.txt"
restore() { set_ tp_report_rate "$R0"; set_ play_game "$G0"; echo "復元: tp_report_rate=$(get tp_report_rate) play_game=$(get play_game)" | tee -a "$OUT/summary.txt"; }
trap restore EXIT
echo "最初のタッチ待ち…"; adb shell "getevent -c 1 $TOUCH" >/dev/null
# 段の指定: CFGS="rate,game ..." （例: CFGS="3,0 4,0 4,1"）
for cfg in ${CFGS:-0,0 1,0 2,0 3,0 4,0 4,1 1,1}; do
  r=${cfg%,*}; g=${cfg#*,}
  adb shell 'su -c "dmesg -c >/dev/null"' 2>/dev/null
  set_ play_game "$g"; set_ tp_report_rate "$r"
  f="$OUT/rate${r}_game${g}.txt"
  adb shell "timeout $SEC getevent -lt $TOUCH" > "$f"
  {
    echo "=== 書き込み rate=$r game=$g → 読み戻し rate=$(get tp_report_rate) game=$(get play_game)"
    adb shell 'su -c "dmesg"' | grep -iE "success in|report.?rate|play_game|game mode" | tail -3 | cut -c1-140
    (cd "$ROOT" && python scripts/audio/analyze_getevent.py "${f#$ROOT/}") 2>&1 | head -3
  } | tee -a "$OUT/summary.txt"
done
