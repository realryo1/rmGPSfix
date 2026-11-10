"""Summarise CamX image dumps (autoImageDump) pulled from /data/vendor/camera.

Usage: python camx_dump_analyze.py <dir with pulled p[...] files>

Enable dumps by appending to /vendor/etc/camera/camxoverridesettings.txt (via a
temporary bind mount, see cam_apply.sh):
    autoImageDump=TRUE
    autoImageDumpMask=0xFFFFFFFF
    autoInputImageDumpMask=0xFFFFFFFF
    offlineImageDumpOnly=TRUE      # omit to also dump realtime (sensor RDI) frames
Dumps are ~1 GB/s while the preview runs: shoot once, restore, then delete the
p[...] files on the device.

Formats handled:
  RawPlain16LSB10bit / RawPlain16LSB14bit : uint16 LE Bayer, row stride in bytes
  YUV420NV12                              : Y plane, then interleaved UV
  PD10 (OFE DS4/DS16 outputs)             : 8 bytes per 2x2 quad = Y0 Y1 Y2 Y3 U V
                                            (8 MSBs each) + 2 bytes of LSBs
"""
import os
import re
import sys

import numpy as np

d = sys.argv[1]
pat = re.compile(r"p\[(\w+)\]_req\[(\d+)\].*?_([\w.]+)\[(\d+)\]_\[out\]_port\[(\d+)\]"
                 r"_w\[(\d+)\]_h\[(\d+)\]_stride\[(\d+)\]_scanline\[(\d+)\]_\d+_(\d{6})_(\d+)\.(\w+)")


def key(n):
    m = pat.search(n)
    return (m.group(10), int(m.group(11))) if m else ("", 0)


for f in sorted(os.listdir(d), key=key):
    m = pat.search(f)
    if not m:
        continue
    pipe, req, node, inst, port, w, h, st, sl, _, _, ext = m.groups()
    w, h, st, sl = map(int, (w, h, st, sl))
    p = os.path.join(d, f)
    tag = f"{pipe} req{req} {node}{inst} port{port} {w}x{h}"
    if ext.startswith("RawPlain16"):
        a = np.fromfile(p, dtype="<u2").reshape(sl, st // 2)[:h, :w].astype(np.float64)
        c = a[int(h * .3) // 2 * 2:int(h * .7) // 2 * 2, int(w * .3) // 2 * 2:int(w * .7) // 2 * 2]
        ph = [c[i::2, j::2].mean() for i in (0, 1) for j in (0, 1)]
        print(f"{tag} {ext[10:]}: bayer phases {[round(x, 1) for x in ph]} "
              f"min={int(a.min())} p1={int(np.percentile(a, 1))} p99={int(np.percentile(a, 99))}")
    elif ext == "YUV420NV12":
        a = np.fromfile(p, dtype=np.uint8)
        y = a[:st * sl].reshape(sl, st)[:h, :w]
        uv = a[st * sl:st * sl + st * (h // 2)].reshape(h // 2, st)[:, :w]
        cy = y[int(h * .3):int(h * .7), int(w * .3):int(w * .7)].mean()
        c = uv[int(h * .15):int(h * .35), int(w * .3) // 2 * 2:int(w * .7) // 2 * 2]
        u, v = c[:, 0::2].mean(), c[:, 1::2].mean()
        rgb = [cy + 1.402 * (v - 128), cy - 0.344 * (u - 128) - 0.714 * (v - 128), cy + 1.772 * (u - 128)]
        print(f"{tag} NV12: Y={cy:.0f} U={u:.0f} V={v:.0f} -> RGB~{[round(x) for x in rgb]}")
    elif ext == "PD10":
        a = np.fromfile(p, dtype=np.uint8)[:st * sl].reshape(sl, st)[:h // 2, :w * 4]
        a = a.reshape(h // 2, w // 2, 8).astype(np.float64)
        c = a[int(h * .15):int(h * .35), int(w * .15):int(w * .35)]
        print(f"{tag} PD10: Y={c[..., :4].mean():.0f} U={c[..., 4].mean():.0f} V={c[..., 5].mean():.0f}")
