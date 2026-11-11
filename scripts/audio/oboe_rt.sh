#!/bin/sh
# 注意（2026-11-12）: この端末では「please wait」のまま止まり、結果が出なかった。画面操作版の scripts/audio/oboe_ui.py を使う。
# OboeTester の往復遅延（スピーカー → 端末マイク）を intent で自動実行し、結果を表示する。
# 使い方: scripts/audio/oboe_rt.sh <ラベル> [OboeTester の intent 引数...]
#   例: scripts/audio/oboe_rt.sh mmap --es out_api aaudio --es out_perf lowlat --es out_sharing exclusive
LABEL=$1; shift
export MSYS_NO_PATHCONV=1
F=/sdcard/Download/oboe_rt_$LABEL.txt
adb shell rm -f $F
adb shell am force-stop com.mobileer.oboetester
adb shell am start -n com.mobileer.oboetester/.MainActivity --es test latency --es file $F "$@" >/dev/null
for i in $(seq 40); do sleep 2; adb shell "test -s $F" && break; done
sleep 1; echo "== $LABEL"; adb shell cat $F 2>/dev/null | grep -E "^(out\.|in\.)?(api|sharing|perf|mmap|burst|buffer|device|channels|preset|usage|content)|latency\.msec|confidence|timestamp\.latency|result|^out|^in" | head -40
