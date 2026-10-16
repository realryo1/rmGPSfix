import struct
import os
import bisect
from erofs_tool import ErofsReader, get_partitions

class SparseFileWrapper:
    def __init__(self, path):
        self.f = open(path, "rb")
        header = self.f.read(28)
        magic, major, minor, file_hdr_sz, chunk_hdr_sz, blk_sz, total_blks, total_chunks, crc = struct.unpack("<IHHHHIIII", header)
        if magic != 0xED26FF3A:
            raise ValueError("Not a sparse image")
        self.blk_sz = blk_sz
        self.f.seek(file_hdr_sz)
        self.starts = []
        self.chunks = [] # (unsparsed_start, unsparsed_len, ctype, file_offset_or_fill_val)
        cur_unsparsed = 0
        for _ in range(total_chunks):
            ch = self.f.read(chunk_hdr_sz)
            ctype, reserved, c_blks, c_sz = struct.unpack("<HHII", ch[:12])
            data_sz = c_sz - chunk_hdr_sz
            u_len = c_blks * blk_sz
            self.starts.append(cur_unsparsed)
            if ctype == 0xCAC1: # RAW
                self.chunks.append((cur_unsparsed, u_len, ctype, self.f.tell()))
                self.f.seek(data_sz, 1)
            elif ctype == 0xCAC2: # FILL
                val = self.f.read(4)
                self.chunks.append((cur_unsparsed, u_len, ctype, val))
                if data_sz > 4:
                    self.f.seek(data_sz - 4, 1)
            elif ctype == 0xCAC3: # DONT_CARE
                self.chunks.append((cur_unsparsed, u_len, ctype, 0))
                if data_sz > 0:
                    self.f.seek(data_sz, 1)
            else:
                self.chunks.append((cur_unsparsed, u_len, ctype, 0))
                self.f.seek(data_sz, 1)
            cur_unsparsed += u_len
        self.pos = 0

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            raise ValueError("Unsupported whence")

    def read(self, size):
        res = bytearray()
        rem = size
        while rem > 0:
            idx = bisect.bisect_right(self.starts, self.pos) - 1
            if idx < 0 or idx >= len(self.chunks):
                break
            u_start, u_len, ctype, param = self.chunks[idx]
            off_in_chunk = self.pos - u_start
            avail = min(rem, u_len - off_in_chunk)
            if avail <= 0:
                break
            if ctype == 0xCAC1:
                self.f.seek(param + off_in_chunk)
                res.extend(self.f.read(avail))
            elif ctype == 0xCAC3:
                res.extend(b'\x00' * avail)
            elif ctype == 0xCAC2:
                # param is 4-byte fill
                repeats = (avail + 3) // 4 + 1
                buf = (param * repeats)[off_in_chunk % 4 : (off_in_chunk % 4) + avail]
                res.extend(buf)
            self.pos += avail
            rem -= avail
        return bytes(res)

    def close(self):
        self.f.close()

def scan_super(f_obj):
    parts = get_partitions(f_obj)
    result = {}
    for pname, exts in parts.items():
        if pname.endswith("_b") or pname.endswith("-cow"):
            continue
        reader = ErofsReader(f_obj, exts)
        files = {}
        for path, nid, ftype in reader.walk():
            ino = reader.read_inode(nid)
            files[path] = (ftype, ino["size"], ino["mtime"], nid, ino["datalayout"])
        result[pname] = files
    return result

if __name__ == "__main__":
    from pathlib import Path
    root_dir = Path(__file__).resolve().parent.parent
    print("Scanning Stock super.img...")
    with open(root_dir / "1_stock20images" / "super.img", "rb") as sf:
        stock_data = scan_super(sf)

    print("Scanning EvoX super.img...")
    ef = SparseFileWrapper(str(root_dir / "EvolutionX-NX809J-A17-20261010-MinimalGApps" / "super.img"))
    evox_data = scan_super(ef)
    ef.close()

    out_dir = str(root_dir / "archive" / "stock_extracted")
    for pname in ["vendor_a", "odm_a", "vendor_dlkm_a", "system_dlkm_a", "system_ext_a", "product_a", "system_a"]:
        s_files = stock_data.get(pname, {})
        e_files = evox_data.get(pname, {})
        removed = sorted(set(s_files.keys()) - set(e_files.keys()))
        added = sorted(set(e_files.keys()) - set(s_files.keys()))
        modified = sorted(k for k in (set(s_files.keys()) & set(e_files.keys())) if s_files[k][:2] != e_files[k][:2])
        print(f"=== {pname}: stock={len(s_files)}, evox={len(e_files)} | removed={len(removed)}, added={len(added)}, size_changed={len(modified)} ===")
        with open(os.path.join(out_dir, f"diff_{pname}.txt"), "w", encoding="utf-8") as df:
            df.write(f"=== {pname} ===\n")
            df.write(f"--- REMOVED IN EVOX ({len(removed)}) ---\n")
            for k in removed:
                df.write(f"  [-] {k} (size={s_files[k][1]})\n")
            df.write(f"\n--- ADDED IN EVOX ({len(added)}) ---\n")
            for k in added:
                df.write(f"  [+] {k} (size={e_files[k][1]})\n")
            df.write(f"\n--- SIZE/TYPE CHANGED ({len(modified)}) ---\n")
            for k in modified:
                df.write(f"  [*] {k} (stock={s_files[k][1]} -> evox={e_files[k][1]})\n")
