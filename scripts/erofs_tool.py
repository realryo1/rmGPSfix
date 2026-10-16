import struct
import os
import sys

def lz4_decompress_block(src, uncompressed_size):
    dst = bytearray()
    pos = 0
    src_len = len(src)
    while pos < src_len and len(dst) < uncompressed_size:
        token = src[pos]
        pos += 1
        lit_len = token >> 4
        if lit_len == 15:
            while pos < src_len:
                b = src[pos]
                pos += 1
                lit_len += b
                if b != 255:
                    break
        dst.extend(src[pos:pos+lit_len])
        pos += lit_len
        if pos >= src_len or len(dst) >= uncompressed_size:
            break
        offset = src[pos] | (src[pos+1] << 8)
        pos += 2
        if offset == 0:
            break
        match_len = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while pos < src_len:
                b = src[pos]
                pos += 1
                match_len += b
                if b != 255:
                    break
        start = len(dst) - offset
        for i in range(match_len):
            dst.append(dst[start + i])
            if len(dst) >= uncompressed_size:
                break
    return bytes(dst[:uncompressed_size])

class ErofsReader:
    def __init__(self, f, extents):
        self.f = f
        # extents: list of (logical_start, length, physical_offset)
        self.extents = []
        cur_log = 0
        for num_sec, _, target_data, _ in extents:
            length = num_sec * 512
            phys = target_data * 512
            self.extents.append((cur_log, length, phys))
            cur_log += length

        sb = self.read_bytes(1024, 128)
        magic = struct.unpack("<I", sb[:4])[0]
        if magic != 0xE0F5E1E2:
            raise ValueError(f"Not EROFS: 0x{magic:08X}")
        self.blkszbits = sb[12]
        self.blksz = 1 << self.blkszbits
        self.root_nid = struct.unpack("<H", sb[14:16])[0]
        self.meta_blkaddr = struct.unpack("<I", sb[40:44])[0]
        self.xattr_blkaddr = struct.unpack("<I", sb[44:48])[0]

    def read_bytes(self, offset, size):
        res = bytearray()
        rem = size
        cur = offset
        while rem > 0:
            found = False
            for log_start, length, phys in self.extents:
                if log_start <= cur < log_start + length:
                    avail = min(rem, log_start + length - cur)
                    self.f.seek(phys + (cur - log_start))
                    chunk = self.f.read(avail)
                    res.extend(chunk)
                    cur += avail
                    rem -= avail
                    found = True
                    break
            if not found:
                raise IOError(f"Offset {cur} out of extents")
        return bytes(res)

    def read_inode(self, nid):
        off = self.meta_blkaddr * self.blksz + nid * 32
        buf = self.read_bytes(off, 64)
        i_format, i_xattr_icount, i_mode = struct.unpack("<HHH", buf[:6])
        is_extended = (i_format & 1) != 0
        datalayout = (i_format >> 1) & 0x7
        if xattr_icount := i_xattr_icount:
            xattr_size = 12 + (xattr_icount - 1) * 4
        else:
            xattr_size = 0
        if not is_extended:
            # compact: 32 bytes
            i_nlink, i_size, i_reserved, i_u, i_ino, i_uid, i_gid = struct.unpack("<HI4sIIHH", buf[6:28])
            inode_size = 32
            mtime = 0
        else:
            # extended: 64 bytes
            i_size, i_u, i_ino, i_uid, i_gid, mtime = struct.unpack("<QIIIIQ", buf[8:40])
            inode_size = 64
        data_inline_off = off + inode_size + xattr_size
        return {
            "nid": nid,
            "mode": i_mode,
            "size": i_size,
            "datalayout": datalayout,
            "u": i_u,
            "mtime": mtime,
            "inline_off": data_inline_off,
        }

    def read_uncompressed_data(self, inode):
        size = inode["size"]
        if size == 0:
            return b""
        dl = inode["datalayout"]
        if dl == 0: # FLAT_PLAIN
            return self.read_bytes(inode["u"] * self.blksz, size)
        elif dl == 2: # FLAT_INLINE
            nblocks = size // self.blksz
            rem = size % self.blksz
            res = bytearray()
            if nblocks > 0:
                res.extend(self.read_bytes(inode["u"] * self.blksz, nblocks * self.blksz))
            if rem > 0:
                res.extend(self.read_bytes(inode["inline_off"], rem))
            return bytes(res)
        return None

    def list_dir(self, nid):
        inode = self.read_inode(nid)
        if (inode["mode"] & 0o170000) != 0o040000:
            return []
        data = self.read_uncompressed_data(inode)
        if not data:
            return []
        entries = []
        nblocks = (len(data) + self.blksz - 1) // self.blksz
        for b in range(nblocks):
            blk = data[b*self.blksz : min(len(data), (b+1)*self.blksz)]
            if len(blk) < 12:
                break
            first_nameoff = struct.unpack("<H", blk[8:10])[0]
            num_entries = first_nameoff // 12
            dirents = []
            for i in range(num_entries):
                d_nid, d_nameoff, d_ftype, _ = struct.unpack("<QHBB", blk[i*12:(i+1)*12])
                dirents.append((d_nid, d_nameoff, d_ftype))
            for i, (d_nid, d_nameoff, d_ftype) in enumerate(dirents):
                end_off = dirents[i+1][1] if i + 1 < num_entries else len(blk)
                name = blk[d_nameoff:end_off].split(b'\x00')[0].decode('utf-8', errors='replace')
                if name not in (".", ".."):
                    entries.append((name, d_nid, d_ftype))
        return entries

    def walk(self, nid=None, prefix=""):
        if nid is None:
            nid = self.root_nid
        for name, d_nid, d_ftype in self.list_dir(nid):
            full_path = f"{prefix}/{name}"
            yield full_path, d_nid, d_ftype
            if d_ftype == 2: # directory
                yield from self.walk(d_nid, full_path)

def get_partitions(f):
    f.seek(0x3000)
    meta_hdr = f.read(256)
    m_magic, major, minor, hdr_size = struct.unpack("<IHHI", meta_hdr[:12])
    part_off, part_num, part_esz = struct.unpack("<III", meta_hdr[80:92])
    ext_off, ext_num, ext_esz = struct.unpack("<III", meta_hdr[92:104])
    f.seek(0x3000 + hdr_size + ext_off)
    extents = []
    for _ in range(ext_num):
        ebuf = f.read(ext_esz)
        extents.append(struct.unpack("<QIQI", ebuf[:24]))
    f.seek(0x3000 + hdr_size + part_off)
    parts = {}
    for _ in range(part_num):
        pbuf = f.read(part_esz)
        name = pbuf[:36].split(b'\x00')[0].decode('utf-8', errors='replace')
        attrs, first_ext, num_ext, group_idx = struct.unpack("<IIII", pbuf[36:52])
        if num_ext > 0 and not name.endswith("-cow"):
            parts[name] = [extents[first_ext + i] for i in range(num_ext)]
    return parts

if __name__ == "__main__":
    from pathlib import Path
    root_dir = Path(__file__).resolve().parent.parent
    super_path = root_dir / "1_stock20images" / "super.img"
    out_dir = root_dir / "archive" / "stock_extracted"
    os.makedirs(out_dir, exist_ok=True)
    with open(super_path, "rb") as f:
        parts = get_partitions(f)
        for pname in ["vendor_a", "odm_a", "system_ext_a", "product_a", "system_a"]:
            print(f"Scanning {pname}...")
            reader = ErofsReader(f, parts[pname])
            list_file = os.path.join(out_dir, f"{pname}_files.txt")
            gps_matches = []
            with open(list_file, "w", encoding="utf-8") as lf:
                for path, nid, ftype in reader.walk():
                    inode = reader.read_inode(nid)
                    lf.write(f"{ftype}\t{inode['size']}\t{path}\n")
                    low = path.lower()
                    if any(k in low for k in ["gps", "gnss", "location", "izat", "xtra", "lowi", "sap", "mlid", "qmi", "flp", "nlp", "fused", "manifest", "build.prop"]):
                        gps_matches.append((path, nid, ftype, inode["size"], inode["datalayout"]))
            print(f"  Total GPS/Location/Config related entries in {pname}: {len(gps_matches)}")
            match_file = os.path.join(out_dir, f"{pname}_gps_matches.txt")
            with open(match_file, "w", encoding="utf-8") as mf:
                for p, nid, ft, sz, dl in gps_matches:
                    mf.write(f"ft={ft} size={sz:10d} dl={dl} nid={nid:10d} {p}\n")
