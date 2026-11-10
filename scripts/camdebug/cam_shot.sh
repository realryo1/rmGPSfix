#!/bin/bash
# Take one photo with the stock camera app (already open, front camera selected),
# pull it into logs/photos/ (git-ignored) and print the centre RGB of the preview
# screenshot and of the saved JPEG. A white target (tissue over the lens) makes the
# colour cast directly readable: preview ~[190,190,185], broken photo ~[90,115,20].
#   cam_shot.sh <label>
# Camera switch button in the app: `adb shell input tap 1080 2328` (1216x2688 screen).
export MSYS_NO_PATHCONV=1
LBL=$1
OUT="$(cd "$(dirname "$0")/../.." && pwd)/logs/photos"
mkdir -p "$OUT"
DIR=/sdcard/DCIM/Camera/FrontCamera
BEFORE=$(adb shell "ls $DIR 2>/dev/null | grep -E '^IMG' | sort | tail -1" | tr -d '\r')
adb exec-out screencap -p > "$OUT/prev_$LBL.png"
adb shell input keyevent 27
for i in 1 2 3 4 5 6 7 8; do
  sleep 1.5
  NEW=$(adb shell "ls $DIR 2>/dev/null | grep -E '^IMG' | sort | tail -1" | tr -d '\r')
  [ -n "$NEW" ] && [ "$NEW" != "$BEFORE" ] && break
done
echo "before=$BEFORE new=$NEW"
[ "$NEW" = "$BEFORE" ] && { echo "NO NEW PHOTO"; exit 1; }
sleep 1
adb pull "$DIR/$NEW" "$OUT/${LBL}_$NEW" >/dev/null
python - "$OUT/prev_$LBL.png" "$OUT/${LBL}_$NEW" <<'PY'
import sys
from PIL import Image, ImageStat
for p in sys.argv[1:]:
    im = Image.open(p).convert("RGB"); w, h = im.size
    c = ImageStat.Stat(im.crop((int(w*.3), int(h*.3), int(w*.7), int(h*.7)))).mean
    print(f"{p.replace(chr(92), '/').split('/')[-1]}: {w}x{h} centre RGB = {[round(v) for v in c]}")
PY
