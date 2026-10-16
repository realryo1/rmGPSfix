import struct
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "EvolutionX-NX809J-A17-20261010-MinimalGApps" / "super.img"

with open(path, "rb") as f:
    header = f.read(28)
    magic, major, minor, file_hdr_sz, chunk_hdr_sz, blk_sz, total_blks, total_chunks, crc = struct.unpack("<IHHHHIIII", header)
    # Read first few chunks to reconstruct first 1MB of unsparsed data
    buf = bytearray()
    for _ in range(total_chunks):
        if len(buf) >= 1024 * 1024:
            break
        ch = f.read(chunk_hdr_sz)
        ctype, reserved, c_blks, c_sz = struct.unpack("<HHII", ch[:12])
        data_sz = c_sz - chunk_hdr_sz
        if ctype == 0xCAC1: # RAW
            buf.extend(f.read(data_sz))
        elif ctype == 0xCAC2: # FILL
            val = f.read(4)
            buf.extend(val * (c_blks * blk_sz // 4))
        elif ctype == 0xCAC3: # DONT_CARE
            buf.extend(b'\x00' * (c_blks * blk_sz))
        else:
            f.seek(data_sz, 1)

meta_hdr = buf[0x3000:0x3100]
m_magic, major, minor, hdr_size = struct.unpack("<IHHI", meta_hdr[:12])
print(f"EvoX LP Metadata magic: 0x{m_magic:08X} (v{major}.{minor}, hdr_size={hdr_size})")
part_off, part_num, part_esz = struct.unpack("<III", meta_hdr[80:92])
ext_off, ext_num, ext_esz = struct.unpack("<III", meta_hdr[92:104])

extents = []
pos = 0x3000 + hdr_size + ext_off
for _ in range(ext_num):
    ebuf = buf[pos:pos+ext_esz]
    pos += ext_esz
    num_sec, target_type, target_data, target_source = struct.unpack("<QIQI", ebuf[:24])
    extents.append((num_sec, target_type, target_data, target_source))

pos = 0x3000 + hdr_size + part_off
for _ in range(part_num):
    pbuf = buf[pos:pos+part_esz]
    pos += part_esz
    name = pbuf[:36].split(b'\x00')[0].decode('utf-8', errors='replace')
    attrs, first_ext, num_ext, group_idx = struct.unpack("<IIII", pbuf[36:52])
    total_sec = sum(extents[first_ext + i][0] for i in range(num_ext))
    if total_sec > 0 or num_ext > 0:
        ext_info = [f"offset={extents[first_ext+i][2]*512:,}, size={extents[first_ext+i][0]*512:,}" for i in range(num_ext)]
        print(f"  Partition: {name:20s} size={total_sec*512:14,d} bytes | extents: {ext_info}")
