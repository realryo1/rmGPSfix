#!/system/bin/sh
umount /vendor/etc/izat.conf 2>/dev/null
umount /vendor/lib64/com.qti.feature2.gs.sm8850.so 2>/dev/null
rm -f /data/local/tmp/gps_incamera_fix.log /data/local/tmp/gps_incamera_fix_frontcam.log
