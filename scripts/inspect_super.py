import struct
import sys
import os

def inspect_image(path):
    print(f"=== Inspecting {path} ===")
    size = os.path.getsize(path)
    print(f"File size: {size:,} bytes")
    with open(path, "rb") as f:
        header = f.read(64)
        magic = struct.unpack("<I", header[:4])[0]
        if magic == 0xED26FF3A:
            print("Format: Android Sparse Image (0xED26FF3A)")
            major, minor, file_hdr_sz, chunk_hdr_sz, blk_sz, total_blks, total_chunks, crc = struct.unpack("<HHHHIIII", header[4:28])
            print(f"  block_size={blk_sz}, total_blocks={total_blks}, total_chunks={total_chunks}, unsparsed_size={blk_sz*total_blks:,}")
        else:
            print(f"Format: Raw Image (first 4 bytes: 0x{magic:08X})")
            # Check LP Geometry at offset 4096 (0x1000)
            f.seek(0x1000)
            geom = f.read(64)
            g_magic = struct.unpack("<I", geom[:4])[0]
            print(f"  Offset 0x1000 magic: 0x{g_magic:08X} (expected LP Geometry 0x616C4467)")
            if g_magic == 0x616C4467:
                # Parse LP metadata at 0x3000
                f.seek(0x3000)
                meta_hdr = f.read(256)
                m_magic, major, minor, hdr_size = struct.unpack("<IHHI", meta_hdr[:12])
                print(f"  LP Metadata magic: 0x{m_magic:08X} (v{major}.{minor}, hdr_size={hdr_size})")
                # Tables descriptor starts at offset 44 in LpMetadataHeader:
                # magic(4), major(2), minor(2), header_size(4), header_checksum(32),
                # tables_size(4), tables_checksum(32),
                # partitions(offset:4, num_entries:4, entry_size:4),
                # extents(offset:4, num_entries:4, entry_size:4),
                # groups(offset:4, num_entries:4, entry_size:4),
                # block_devices(offset:4, num_entries:4, entry_size:4)
                part_off, part_num, part_esz = struct.unpack("<III", meta_hdr[80:92])
                ext_off, ext_num, ext_esz = struct.unpack("<III", meta_hdr[92:104])
                f.seek(0x3000 + hdr_size + ext_off)
                extents = []
                for _ in range(ext_num):
                    ebuf = f.read(ext_esz)
                    num_sec, target_type, target_data, target_source = struct.unpack("<QIQI", ebuf[:24])
                    extents.append((num_sec, target_type, target_data, target_source))
                f.seek(0x3000 + hdr_size + part_off)
                for _ in range(part_num):
                    pbuf = f.read(part_esz)
                    name = pbuf[:36].split(b'\x00')[0].decode('utf-8', errors='replace')
                    attrs, first_ext, num_ext, group_idx = struct.unpack("<IIII", pbuf[36:52])
                    total_sec = sum(extents[first_ext + i][0] for i in range(num_ext))
                    if total_sec > 0 or num_ext > 0:
                        ext_info = [f"offset={extents[first_ext+i][2]*512:,}, size={extents[first_ext+i][0]*512:,}" for i in range(num_ext)]
                        print(f"    Partition: {name:20s} size={total_sec*512:14,d} bytes | extents: {ext_info}")

from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
inspect_image(str(root_dir / "1_stock20images" / "super.img"))
inspect_image(str(root_dir / "EvolutionX-NX809J-A17-20261010-MinimalGApps" / "super.img"))
