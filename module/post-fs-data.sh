#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/gps_incamera_audio_fix.log
echo "post-fs-data start $(date)" > "$LOG"

chown root:root "$MODDIR/izat.conf"
chmod 0644 "$MODDIR/izat.conf"
chcon u:object_r:vendor_configs_file:s0 "$MODDIR/izat.conf" >>"$LOG" 2>&1

umount /vendor/etc/izat.conf 2>/dev/null
if mount -o bind "$MODDIR/izat.conf" /vendor/etc/izat.conf >>"$LOG" 2>&1; then
    echo "bind mount /vendor/etc/izat.conf ok" >> "$LOG"
else
    echo "bind mount /vendor/etc/izat.conf failed" >> "$LOG"
fi

# Reset xtra.sqlite once on first install in case retry limit (6) was already reached
if [ ! -f "$MODDIR/.xtra_reset_done" ]; then
    if [ -f /data/vendor/location/xtra/xtra.sqlite ]; then
        cp -p /data/vendor/location/xtra/xtra.sqlite /data/vendor/location/xtra/xtra.sqlite.bak 2>/dev/null
        rm -f /data/vendor/location/xtra/xtra.sqlite
        echo "reset locked xtra.sqlite" >> "$LOG"
    fi
    touch "$MODDIR/.xtra_reset_done"
fi

echo "post-fs-data gps done $(date)" >> "$LOG"

# 音声: sku_canoe の HAL 設定に欠けている raw_out（FAST|RAW、超低遅延の出力）を足した版に差し替える。
# 音声 HAL は post-fs-data の後に起動して設定を読むので、ここで差し替える。
AUDIO_CFG=/vendor/etc/audio/sku_canoe/audio_module_config_primary.xml
if [ -f "$AUDIO_CFG" ]; then
    chown root:root "$MODDIR/audio_module_config_primary.xml"
    chmod 0644 "$MODDIR/audio_module_config_primary.xml"
    chcon u:object_r:vendor_configs_file:s0 "$MODDIR/audio_module_config_primary.xml" >>"$LOG" 2>&1
    umount "$AUDIO_CFG" 2>/dev/null
    if mount -o bind "$MODDIR/audio_module_config_primary.xml" "$AUDIO_CFG" >>"$LOG" 2>&1; then
        echo "bind mount $AUDIO_CFG ok" >> "$LOG"
    else
        echo "bind mount $AUDIO_CFG failed" >> "$LOG"
    fi
else
    echo "skip audio: $AUDIO_CFG not found" >> "$LOG"
fi
echo "post-fs-data audio done $(date)" >> "$LOG"
: > /data/local/tmp/gps_incamera_audio_fix_frontcam.log
sh "$MODDIR/apply.sh"
