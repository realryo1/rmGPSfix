import os
import struct
import difflib
import erofs_tool

def extract_compressed_file(reader, start_blk, num_blks, total_size):
    out = bytearray()
    for b in range(start_blk, start_blk + num_blks):
        raw = reader.read_bytes(b * 4096, 4096)
        i = 0
        while i < len(raw) and raw[i] == 0:
            i += 1
        rem = total_size - len(out)
        dec = erofs_tool.lz4_decompress_block(raw[i:], min(65536, rem))
        out.extend(dec)
    return bytes(out[:total_size])

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
STOCK_SUPER = ROOT_DIR / "1_stock20images" / "super.img"
STOCK_EXT = ROOT_DIR / "archive" / "stock_extracted"
DEV_ETC = ROOT_DIR / "archive" / "device_etc"

with open(STOCK_SUPER, "rb") as f:
    parts = erofs_tool.get_partitions(f)
    r_ven = erofs_tool.ErofsReader(f, parts["vendor_a"])

    # 1. build.prop: start_blk=1, u=4, size=39003
    bp = extract_compressed_file(r_ven, 1, 4, 39003)
    open(STOCK_EXT / "stock_vendor_build.prop", "wb").write(bp)

    # 2. vendor_file_contexts: hdr had 37510200 -> 0x00025137 (or 0x00025138), u=7, size=158025
    for cand in (0x25137, 0x25138):
        raw = r_ven.read_bytes(cand * 4096, 4096)
        i = 0
        while i < len(raw) and raw[i] == 0: i += 1
        dec = erofs_tool.lz4_decompress_block(raw[i:], 65536)
        if b"/vendor" in dec or b"u:object_r:" in dec:
            print(f"vendor_file_contexts starts at 0x{cand:x}, preview: {dec[:50]}")
            vfc = extract_compressed_file(r_ven, cand, 7, 158025)
            open(STOCK_EXT / "stock_vendor_file_contexts", "wb").write(vfc)
            break

    # 3. vendor_sepolicy.cil: hdr had 42510200 -> 0x00025142 (or 0x00025143), u=69, size=1701631
    for cand in (0x25142, 0x25143):
        raw = r_ven.read_bytes(cand * 4096, 4096)
        i = 0
        while i < len(raw) and raw[i] == 0: i += 1
        dec = erofs_tool.lz4_decompress_block(raw[i:], 65536)
        if dec.startswith(b"("):
            print(f"vendor_sepolicy.cil starts at 0x{cand:x}, preview: {dec[:50]}")
            cil = extract_compressed_file(r_ven, cand, 69, 1701631)
            open(STOCK_EXT / "stock_vendor_sepolicy.cil", "wb").write(cil)
            break

# Compare modules.load
s_lines = [os.path.basename(x.strip()) for x in open(STOCK_EXT / "stock_modules.load", "r", encoding="utf-8", errors="ignore").read().splitlines() if x.strip()]
e_raw = open(DEV_ETC / "evox_modules.load", "rb").read()
e_text = e_raw.decode("utf-16le") if e_raw.startswith(b"\xff\xfe") else e_raw.decode("utf-8", errors="ignore")
e_lines = [os.path.basename(x.strip()) for x in e_text.splitlines() if x.strip()]
print("modules.load in Stock but NOT EvoX:", set(s_lines) - set(e_lines))
print("modules.load in EvoX but NOT Stock:", set(e_lines) - set(s_lines))

# Diff build.prop
s_bp = open(STOCK_EXT / "stock_vendor_build.prop", "r", encoding="utf-8", errors="replace").read().splitlines()
e_bp = open(DEV_ETC / "vendor_build.prop", "r", encoding="utf-8", errors="replace").read().splitlines()
print("\n=== Diff vendor/build.prop ===")
for line in difflib.unified_diff(s_bp, e_bp, fromfile="stock", tofile="evox", n=0):
    print(line)

# Diff vendor_file_contexts
s_fc = open(STOCK_EXT / "stock_vendor_file_contexts", "r", encoding="utf-8", errors="replace").read().splitlines()
e_fc = open(DEV_ETC / "vendor_file_contexts", "r", encoding="utf-8", errors="replace").read().splitlines()
print("\n=== Diff vendor_file_contexts ===")
for line in difflib.unified_diff(s_fc, e_fc, fromfile="stock", tofile="evox", n=0):
    print(line)

# Diff vendor_sepolicy.cil
s_cil = open(STOCK_EXT / "stock_vendor_sepolicy.cil", "r", encoding="utf-8", errors="replace").read().splitlines()
e_cil = open(DEV_ETC / "vendor_sepolicy.cil", "r", encoding="utf-8", errors="replace").read().splitlines()
print("\n=== Diff vendor_sepolicy.cil ===")
for line in difflib.unified_diff(s_cil, e_cil, fromfile="stock", tofile="evox", n=0):
    print(line)
