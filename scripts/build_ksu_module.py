import os
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MOD_DIR = ROOT_DIR / 'module'
MOD_DIR.mkdir(exist_ok=True)

module_prop = """id=rm11pro_gps_fix
name=RedMagic 11 Pro (NX809J) EvolutionX GPS Fix
version=v1.0
versionCode=1
author=Antigravity
description=Fixes xtra-daemon duplicate spawn and SELinux netd socket denial on EvolutionX for RedMagic 11 Pro (NX809J).
"""

sepolicy_rule = """allow netd vendor_location tcp_socket { read write getopt setopt }
allow netd vendor_location udp_socket { read write getopt setopt }
"""

post_fs_data_sh = """#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/rm11pro_gps_fix.log
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

echo "post-fs-data done $(date)" >> "$LOG"
"""

service_sh = """#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/rm11pro_gps_fix.log
echo "service.sh start $(date)" >> "$LOG"

# Ensure bind mount is active
if ! grep -q "PROCESS_STATE=DISABLED" /vendor/etc/izat.conf 2>/dev/null; then
    chown root:root "$MODDIR/izat.conf"
    chmod 0644 "$MODDIR/izat.conf"
    chcon u:object_r:vendor_configs_file:s0 "$MODDIR/izat.conf"
    mount -o bind "$MODDIR/izat.conf" /vendor/etc/izat.conf >>"$LOG" 2>&1
fi

echo "service.sh done $(date)" >> "$LOG"
"""

uninstall_sh = """#!/system/bin/sh
umount /vendor/etc/izat.conf 2>/dev/null
rm -f /data/local/tmp/rm11pro_gps_fix.log
"""

izat_conf_path = MOD_DIR / 'izat.conf'
izat_conf_bytes = izat_conf_path.read_bytes()

files = {
    'module.prop': module_prop.encode('utf-8'),
    'sepolicy.rule': sepolicy_rule.encode('utf-8'),
    'post-fs-data.sh': post_fs_data_sh.encode('utf-8'),
    'service.sh': service_sh.encode('utf-8'),
    'uninstall.sh': uninstall_sh.encode('utf-8'),
    'izat.conf': izat_conf_bytes,
}

for name, content in files.items():
    (MOD_DIR / name).write_bytes(content)

zip_path = ROOT_DIR / 'rm11pro_gps_fix_v1.0.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for name in files:
        zf.write(MOD_DIR / name, arcname=name)

print(f'Updated module files in {MOD_DIR} and packaged {zip_path}')
