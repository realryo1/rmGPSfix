# RedMagic 11 Pro (NX809J) EvolutionX GPS Fix

[日本語 (README.md)](./README.md)

A KernelSU module and analysis toolkit that fixes non-functional GPS / GNSS positioning on custom ROMs (such as EvolutionX) for the RedMagic 11 Pro (`NX809J` / Snapdragon 8 Elite Gen 2 `SM8850` `canoe`).

---

## Root Cause Analysis

By comparing all partitions of the Stock ROM (`super.img`, RedMagic OS B20) against the Custom ROM (`super.img`, EvolutionX) and analyzing live device logs (`logcat`, `dumpsys location`, `dmesg`), two root causes were identified for the GPS positioning failure:

### 1. Duplicate `xtra-daemon` Spawn & SELinux Denial Causing XTRA / NTP Lockout
- `/vendor/etc/init/xtra-daemon.rc` starts `xtra-daemon` via `init` in its legitimate SELinux domain (`u:r:vendor_location_xtra_daemon:s0`).
- However, in the custom ROM's `/vendor/etc/izat.conf`, only `PROCESS_NAME=lowi-server` was changed to `PROCESS_STATE=DISABLED`, while `PROCESS_NAME=xtra-daemon` remained `PROCESS_STATE=ENABLED`.
- Furthermore, because `(allow vendor_location vendor_location_xtra_daemon_exec (file (execute_no_trans)))` was added in `/vendor/etc/selinux/vendor_sepolicy.cil`, `loc_launcher` (`u:r:vendor_location:s0`) **spawned a second instance of `xtra-daemon` inside the wrong SELinux domain (`u:r:vendor_location:s0`)**.
- This second `xtra-daemon` overwrote and hijacked both the AIDL service (`ILocAidlXtraService`) and the IPC socket (`/dev/socket/location/xtra/socket_xtra`). When it attempted to bind sockets to the network via `netd` (`fwmarkd`), `netd` (`permissive=0`) rejected the `tcp_socket` with `avc: denied { read write }` because `netd` lacks `{ read write getopt setopt }` permissions for `u:r:vendor_location:s0` sockets, resulting in `android_setsocknetwork failure: Message too long`.
- After repeated failures, the retry counter (`xtra_request_retry_num`) in `/data/vendor/location/xtra/xtra.sqlite` hit its maximum limit (`6`), permanently locking out XTRA ephemeris and integrity downloads (`Retry dropped`).

### 2. Disabled Google Location Accuracy (Network Location Provider)
- When GMS's `network provider` is disabled by default, the GNSS HAL cannot receive coarse location assistance (`GNSS HAL Requesting location updates from network provider`), preventing initial sky-view computation and severely delaying or preventing cold-start satellite acquisition.

---

## What This Fix Does (`rm11pro_gps_fix_v1.0.zip`)

The included module (`module/` and `rm11pro_gps_fix_v1.0.zip`) applies the following systemless fixes:

1. **Fixes and Bind-Mounts `/vendor/etc/izat.conf` (`post-fs-data.sh`, `service.sh`)**:
   - Sets `PROCESS_STATE=DISABLED` for `PROCESS_NAME=xtra-daemon` in `izat.conf` and bind-mounts it to `/vendor/etc/izat.conf` during `post-fs-data` (before `loc_launcher` starts).
   - This prevents `loc_launcher` from spawning the duplicate rogue process and allows the legitimate `init`-spawned `xtra-daemon` (`u:r:vendor_location_xtra_daemon:s0`) to download and inject XTRA / NTP data cleanly.
2. **Automatically Resets Locked `xtra.sqlite` on First Boot (`post-fs-data.sh`)**:
   - On the first boot after installing the module, any existing `/data/vendor/location/xtra/xtra.sqlite` that has already hit the retry lockout limit is backed up to `.bak` and regenerated cleanly by `xtra-daemon`.
3. **Supplements SELinux Policy Rules (`sepolicy.rule`)**:
   - Adds `allow netd vendor_location { tcp_socket udp_socket } { read write getopt setopt }` so `netd` will not reject socket operations even if a process in the `vendor_location` domain initiates network connections.

---

## Verified Environment

| Item | Details |
|---|---|
| Device | RedMagic 11 Pro (`NX809J`) |
| ROM | EvolutionX (`A17` / build 2026-10-10, MinimalGApps) |
| Root | KernelSU (verified). Magisk / APatch are not verified |

---

## Installation Instructions

1. **Install the Module**
   - Flash [`rm11pro_gps_fix_v1.0.zip`](./rm11pro_gps_fix_v1.0.zip) in your KernelSU manager app and reboot your device.
2. **Enable Google Location Accuracy**
   - On your device, go to **Settings > Location > Location services > Google Location Accuracy** and turn it **ON**.
3. **Verify Positioning**
   - Open an app such as GPSTest near a window or outdoors and verify that the satellite list, signal strength (`CN0`), and position fix work properly.

---

## Repository Structure

- `module/`: Source files for the KernelSU module
  - `module.prop`: Module metadata
  - `izat.conf`: Fixed configuration disabling duplicate `xtra-daemon` launch from `loc_launcher`
  - `post-fs-data.sh` / `service.sh` / `uninstall.sh`: Mount and initialization scripts
  - `sepolicy.rule`: Additional SELinux rules for `netd`
- `scripts/`: Python scripts for ROM image (`EROFS` / Sparse LP `super.img`) inspection and module packaging
  - `build_ksu_module.py`: Builds `rm11pro_gps_fix_v1.0.zip` from `module/`
  - `erofs_tool.py`: Pure-Python EROFS image & LP metadata parser
  - `diff_super.py` / `compare_details.py`: Scripts to diff all partitions between Stock ROM and Custom ROM
  - `inspect_super.py` / `inspect_evox_super.py`: Scripts to inspect Raw / Sparse `super.img` partition tables
- `sagyou.md`: Detailed investigation and verification log (in Japanese)

---

## Reproducing the Scripts

The analysis scripts in `scripts/` expect ROM images that are not included in this repository:

- `1_stock20images/super.img`: Stock ROM (RedMagic OS) `super.img`
- `EvolutionX-NX809J-A17-20261010-MinimalGApps/super.img`: Custom ROM `super.img`

Please extract these from your own device. `build_ksu_module.py` does not need any ROM image; it generates the ZIP from `module/` alone.

---

## Known Issue: Greenish Front-Camera Photos (Under Investigation, Not Fixed)

Photos taken with the stock camera app's under-display front camera are saved with a green tint. This is **not fixed yet**; this module does not contain a fix for it.

- Video is fine; only photos lose blue (the AWB gains are most likely not applied in the photo pipeline).
- Sensor tuning, AI models, QNN libraries and the camera HAL match the stock ROM, so replacing vendor files is unlikely to help.
- See milestone 7 in [`sagyou.md`](./sagyou.md) (Japanese) for details.

---

## License

- The scripts, documentation, and module scripts in this repository are released under the [MIT License](./LICENSE).
- `module/izat.conf` is a modified configuration file derived from EvolutionX / Qualcomm. The original rights belong to their respective authors; please check whether redistribution is permitted for you.
