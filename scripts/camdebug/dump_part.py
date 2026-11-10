"""Copy one logical partition out of a raw (non-sparse) super.img.

Usage: python dump_part.py <super.img> <partition, e.g. vendor_a> <out.img>

The result is an EROFS image. Extract it with erofs-utils >= 1.9, e.g. in WSL:
    fsck.erofs --extract=<dir> <out.img>            # whole partition
    dump.erofs --path=/etc/build.prop --cat <out.img>   # one file
(scripts/erofs_tool.py cannot read compressed files, so do not use it for contents.)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import erofs_tool

sup, part, out = sys.argv[1:4]
with open(sup, "rb") as f:
    parts = erofs_tool.get_partitions(f)
    with open(out, "wb") as o:
        for num_sec, _, target, _ in parts[part]:
            f.seek(target * 512)
            n = num_sec * 512
            while n > 0:
                b = f.read(min(n, 1 << 24))
                o.write(b)
                n -= len(b)
print("ok", part)
