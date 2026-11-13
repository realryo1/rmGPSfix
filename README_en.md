# RedMagic 11 Pro (NX809J) EvolutionX fixes

[日本語 (README.md)](./README.md)

A KernelSU module that fixes non-working GPS, green-tinted front-camera photos, and late game audio (a missing low-latency output) on EvolutionX (2026-10-10). One download: [`gps_incamera_audio_fix_v3.0.zip`](./gps_incamera_audio_fix_v3.0.zip).

| Item | Details |
|---|---|
| Device | RedMagic 11 Pro (`NX809J`) |
| ROM | EvolutionX A17 / 2026-10-10 / MinimalGApps |
| Root | KernelSU (verified). Magisk / APatch are not verified |

## Install

1. Remove `gps_incamera_fix` (v2.0), `rhythm_latency_fix`, `rm11pro_gps_fix` and the test module `rm11pro_frontcam_wb` if they are installed. The id is now `gps_incamera_audio_fix`, so they are not replaced automatically.
2. Flash [`gps_incamera_audio_fix_v3.0.zip`](./gps_incamera_audio_fix_v3.0.zip) in KernelSU and reboot.
3. Turn **Settings → Location → Location services → Google Location Accuracy** ON.
4. Check a fix outdoors. A white subject in a front-camera photo should keep its blue instead of turning green.
5. For rhythm games, open rmcontrol (the RedMagic settings app), turn **Extra loudness off** and set **Touch sampling while gaming to 720 Hz** (see “Audio” below).

`scripts/build_ksu_module.py` builds the ZIP from `module/`.

## GPS

The custom ROM leaves `xtra-daemon` `ENABLED` in `/vendor/etc/izat.conf`. `loc_launcher` starts a second copy in the `vendor_location` SELinux domain, and that copy takes the XTRA socket. `netd` denies that domain, downloads fail, and `/data/vendor/location/xtra/xtra.sqlite` stops at retry 6. With Google Location Accuracy off, coarse-location assist is missing too.

The module bind-mounts an `izat.conf` with `xtra-daemon` `DISABLED`, resets a locked `xtra.sqlite` once, and adds an SELinux rule so `netd` can use `vendor_location` sockets.

## Front-camera green tint

Only photos are green. Preview and video are fine. Asking for 4608×3456 sends the under-display camera down the Quad CFA non-ZSL path, where OFE never applies white balance. AWB wants blue at about 3×, so the photo loses blue. Rear photos use another path and OFE does apply white balance. Forcing the photo IPE white-balance block on makes the picture black.

The fix zeroes the low 32 bits of `GetNZSLSnapshotFlag` in `com.qti.feature2.gs.sm8850.so`: one byte at file offset 0xd4e26, `17` to `1f`. Capture stays on the 2304×1728 path, where white balance works, then scales to 4608×3456. The file is still reported as 16MP. On each boot the module copies the on-device library, changes that byte, and bind-mounts it. It applies only when the file is 1545632 bytes and the instruction is `eb 03 17 2a` (the 2026-10-10 build). Other builds are left alone.

On a checked photo, a blue plush eye was about RGB [36, 78, 120] and white fabric about [182, 183, 174]. A broken white subject was about [90, 115, 20].

Fine detail is softer than a full Quad CFA readout. The sensor is Quad Bayer, so its optical resolution is about 4MP. The difference from a full readout was not measured against the stock ROM.

The patched function is the shared graph selector, not a front-camera-only path. Ordinary rear photos do not use this non-ZSL path, so they stay as they are. A rear high-resolution mode that uses the same flag would also fall back to the 4MP path. That mode was not rechecked after the patch.

## Not in this module

- The bottom-left thumbnail opens Glimpse (`org.lineageos.glimpse`) directly. Clearing the default image app does not switch it to Google Photos.
- While “Hold the device firmly while shooting” is on screen, the under-display capture is still running and the JPEG does not exist yet. Open the thumbnail after that message goes away. The rear camera does not show it, so an immediate open is fine.
- If rmcontrol's Quick Settings tiles (such as the fan) react late or ignore repeated taps, count your custom tiles (tiles from other apps). SystemUI binds at most 3 custom tiles at a time; with 4 or more, a tap can wait up to about 5 s after you open the shade, and taps made meanwhile collapse into one. Keep 3 or fewer custom tiles. If a tile comes from your own app, declaring it as an `ACTIVE_TILE` keeps it out of that limit. Details: milestone 17 in [`docs/sagyou.md`](./docs/sagyou.md).

Measurements and rejected ideas are in [`docs/sagyou.md`](./docs/sagyou.md) and [`docs/frontcam_handoff.md`](./docs/frontcam_handoff.md) (Japanese).

## Audio (rhythm-game latency)

The ROM's audio HAL config `/vendor/etc/audio/sku_canoe/audio_module_config_primary.xml` has no `raw_out` (FAST|RAW) output. An app that asks for FAST|RAW lands on the slower `low_latency_out`. The stock ROM config lacks it too. The module bind-mounts a config with `raw_out` added for the speaker, wired headset and USB audio routes.

Tap-to-sound in Project SEKAI (song “ray”), measured with a PC microphone:

| State | Tap → SE (median) |
|---|---|
| ROM default (Extra loudness on) | about 180 ms (estimated from OS-reported latency) |
| Extra loudness off | 79 ms |
| plus `raw_out` (this module) | 66 ms |
| same, 3.5 mm wired earphones | 31 ms |
| reference: iPad mini (A17 Pro) speaker | 43 ms |

Settings to change yourself (the module does not touch them):
- **Extra loudness** (rmcontrol): when on, it adds loudness processing to the speaker and disables the low-latency output for every app. Turn it off.
- **Touch sampling while gaming** (rmcontrol): 720 Hz raises touch reports from about 180 Hz to 363 Hz (measured).

The built-in speakers keep about 35 ms of delay that the OS does not report. It comes from processing the audio DSP adds only for the speaker; the amp profile and speaker protection made no difference. The earpiece and wired paths do not have it, so 3.5 mm wired earphones are the fastest way to play.

Procedures and results are in [`docs/audio/progress.md`](./docs/audio/progress.md) (Japanese).

## Layout

- `module/` — the module
- `scripts/` — `super.img` diffs and camera measurements. ROM images are not in this repository
- `scripts/audio/` — audio and touch latency measurement scripts. Recordings and other measurement data are not included
- `docs/` — work logs (Japanese): `sagyou.md` and `frontcam_handoff.md` for GPS and camera, `audio/` for audio

## License

Scripts and docs are under the [MIT License](./LICENSE). `module/izat.conf`, `module/audio_module_config_primary.xml` and the configs in `docs/audio/experiments/` are modified EvolutionX / Qualcomm configs.
