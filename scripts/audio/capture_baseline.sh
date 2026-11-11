#!/usr/bin/env bash
# 公式アプリのプレイ中に、外側から読み取りだけで状態を記録する。
# 使い方: scripts/audio/capture_baseline.sh [秒数=360] [ラベル=baseline]
# 端末の設定は変えない（SurfaceFlinger の timestats だけ一時的に有効化し、最後に無効化する）。
set -u
export MSYS_NO_PATHCONV=1
DUR=${1:-360}; LABEL=${2:-baseline}
OUT="$(cd "$(dirname "$0")/../.." && pwd)/prsk/logs/$(date +%Y%m%d_%H%M%S)_$LABEL"
mkdir -p "$OUT"
TOUCH=$(adb shell 'getevent -pl 2>/dev/null' | tr -d '\r' | awk '/add device/{d=$NF} /synaptics_tcm_touch/{print d}')
echo "touch=$TOUCH dur=$DUR out=$OUT" | tee "$OUT/meta.txt"

adb shell 'dumpsys SurfaceFlinger --timestats -clear -enable' >/dev/null
adb shell "timeout $DUR getevent -lt $TOUCH" > "$OUT/getevent.txt" &
GE=$!

END=$(( $(date +%s) + DUR )); i=0
while [ "$(date +%s)" -lt "$END" ]; do
  t=$(printf '%03d' $i)
  adb shell 'dumpsys media.audio_flinger' > "$OUT/audio_flinger_$t.txt" 2>&1
  adb shell 'dumpsys media.aaudio'        > "$OUT/aaudio_$t.txt" 2>&1
  # 直近 127 フレームの表示時刻（ゲームの SurfaceView レイヤー）
  LAYER=$(adb shell 'dumpsys SurfaceFlinger --list' | tr -d '
' | grep -oE '[0-9a-f]+ SurfaceView\[com\.sega\.pjsekai[^]]*\]\(BLAST\)#[0-9]+' | head -1)
  [ -n "$LAYER" ] && adb shell "dumpsys SurfaceFlinger --latency '$LAYER'" > "$OUT/sf_latency_$t.txt" 2>&1
  adb shell 'su -c "
    date +%s.%N
    echo == touchscreen; cd /proc/touchscreen; for f in tp_report_rate play_game single_game sensibility follow_hand_level stability_level game_partition edge_report_limit; do echo \$f=\$(cat \$f 2>&1 | head -3 | tr \"\n\" \" \"); done
    echo == cpufreq; for p in /sys/devices/system/cpu/cpufreq/policy*; do echo \$p \$(cat \$p/scaling_governor) cur=\$(cat \$p/scaling_cur_freq) max=\$(cat \$p/scaling_max_freq) hwmax=\$(cat \$p/cpuinfo_max_freq); done
    echo == top; dumpsys activity activities | grep -E \"topResumedActivity|mFocusedApp\" | head -2
    echo == display; dumpsys display | grep -E \"mActiveSfDisplayMode|mActiveModeId|renderFrameRate\" | head -4
    echo == thermal; dumpsys thermalservice | grep -E \"Thermal Status|mName=(skin|battery|cpu-0-0|gpuss-0)\" | head -8
    echo == threads; pid=\$(pidof com.sega.pjsekai); echo pid=\$pid; [ -n \"\$pid\" ] && cat /proc/\$pid/cgroup | head -3 && ps -T -p \$pid -o tid,pri,ni,rtprio,psr,comm | grep -iE \"cri|audio|aaudio|unitymain|unitygfx|il2cpp\" | head -20
  "' > "$OUT/state_$t.txt" 2>&1
  i=$((i+1)); sleep 20
done
wait $GE
adb shell 'dumpsys SurfaceFlinger --timestats -dump' > "$OUT/sf_timestats.txt" 2>&1
adb shell 'dumpsys SurfaceFlinger --timestats -disable -clear' >/dev/null
echo "done: $OUT"; ls "$OUT" | wc -l; wc -l "$OUT/getevent.txt"
