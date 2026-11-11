#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/gps_incamera_audio_fix.log
echo "service.sh start $(date)" >> "$LOG"

# Ensure bind mount is active
if ! grep -q "PROCESS_STATE=DISABLED" /vendor/etc/izat.conf 2>/dev/null; then
    chown root:root "$MODDIR/izat.conf"
    chmod 0644 "$MODDIR/izat.conf"
    chcon u:object_r:vendor_configs_file:s0 "$MODDIR/izat.conf"
    mount -o bind "$MODDIR/izat.conf" /vendor/etc/izat.conf >>"$LOG" 2>&1
fi

echo "service.sh gps done $(date)" >> "$LOG"
sh "$MODDIR/apply.sh"
