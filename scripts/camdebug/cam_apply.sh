#!/bin/bash
# Temporarily bind-mount a local test file over a /vendor file, then restart the
# camera provider and the stock camera app. Nothing is written to /vendor; a reboot
# (or --restore) undoes everything.
#   cam_apply.sh <local file> <vendor path>
#   cam_apply.sh --restore <vendor path>
# Note: `adb shell su -c 'a; b'` must be quoted as ONE string ("su -c '...'"),
# otherwise only the first command runs as root.
export MSYS_NO_PATHCONV=1
PROVIDER=vendor.qti.camera.provider-service_64
if [ "$1" = "--restore" ]; then
  T=$2
  for i in 1 2 3 4; do
    adb shell "su -c 'kill \$(pidof $PROVIDER) 2>/dev/null; sleep 1; umount $T 2>/dev/null'"
    [ "$(adb shell "su -c 'mount | grep -c $T'" | tr -d '\r')" = "0" ] && break
  done
  adb shell "su -c 'rm -f /data/local/tmp/camtest_*; mount | grep -c $T'"
else
  L=$1; T=$2; N=/data/local/tmp/camtest_$(basename "$T")
  CTX=$(adb shell "su -c 'ls -Z $T'" | awk '{print $1}' | tr -d '\r')
  adb shell "su -c 'umount $T 2>/dev/null'"
  adb push "$L" "$N" >/dev/null
  adb shell "su -c 'chown root:root $N; chmod 644 $N; chcon $CTX $N; mount -o bind $N $T; sha256sum $T | cut -c1-16'"
fi
adb shell am force-stop com.android.camera
# `stop`/`start` do not work for this service; killing it makes init restart it.
adb shell "su -c 'kill \$(pidof $PROVIDER) 2>/dev/null'"
sleep 4
adb shell am start -n com.android.camera/.Camera >/dev/null
sleep 5
adb shell "dumpsys media.camera | grep -E 'Number of camera|Client Package Name' | head -3"
