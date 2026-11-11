#!/system/bin/sh
# GetNZSLSnapshotFlag の戻り値下位 32bit (nzsl flags) を 0 にする。
# 2026-10-10 ビルドの命令 eb 03 17 2a だけを eb 03 1f 2a に変える。
MODDIR=${0%/*}
LOG=/data/local/tmp/gps_incamera_audio_fix_frontcam.log
SO=/vendor/lib64/com.qti.feature2.gs.sm8850.so
OUT="$MODDIR/gs.sm8850.so"
EXPECT_SIZE=1545632
INSN_OFF=871972
BYTE_OFF=871974

log() { echo "$(date) $*" >> "$LOG"; }

sig_of() {
    dd if="$1" bs=1 skip="$INSN_OFF" count=4 2>/dev/null | od -An -tx1 | tr -d '[:space:]'
}

if grep "sm8850.so" /proc/self/mountinfo 2>/dev/null | grep -q "/${MODDIR##*/}/"; then
    log "already bind-mounted"
    exit 0
fi

umount "$SO" 2>/dev/null
size=$(stat -c %s "$SO" 2>/dev/null)
sig=$(sig_of "$SO")
log "vendor size=$size sig=$sig"

if [ "$size" = "$EXPECT_SIZE" ] && [ "$sig" = "eb03172a" ]; then
    cp -f "$SO" "$OUT" || { log "copy failed"; exit 1; }
    printf '\037' | dd of="$OUT" bs=1 seek="$BYTE_OFF" conv=notrunc >>"$LOG" 2>&1 || { log "patch write failed"; exit 1; }
    newsig=$(sig_of "$OUT")
    log "patched sig=$newsig"
    if [ "$newsig" != "eb031f2a" ]; then
        log "verify failed"
        rm -f "$OUT"
        exit 1
    fi
elif [ -f "$OUT" ] && [ "$(sig_of "$OUT")" = "eb031f2a" ]; then
    log "reuse existing patched file"
else
    log "library does not match this build, skipped"
    exit 0
fi

chown root:root "$OUT"
chmod 0644 "$OUT"
chcon u:object_r:vendor_file:s0 "$OUT" >>"$LOG" 2>&1
if mount -o bind "$OUT" "$SO" >>"$LOG" 2>&1; then
    log "bind ok"
else
    log "bind failed"
    exit 1
fi
