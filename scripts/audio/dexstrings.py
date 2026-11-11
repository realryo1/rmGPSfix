"""APK 内の全 dex から文字列テーブルを取り出す。使い方: python scripts/audio/dexstrings.py app.apk [正規表現]"""
import sys, zipfile, struct, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
def uleb(b, o):
    r = s = 0
    while True:
        c = b[o]; o += 1; r |= (c & 0x7f) << s; s += 7
        if c < 0x80: return r, o
def strings(d):
    n, off = struct.unpack_from('<II', d, 0x38)
    for i in range(n):
        o = struct.unpack_from('<I', d, off + 4 * i)[0]
        _, o = uleb(d, o); e = d.index(b'\0', o)
        yield d[o:e].decode('utf-8', 'replace')
pat = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
z = zipfile.ZipFile(sys.argv[1]); seen = set()
for name in z.namelist():
    if re.fullmatch(r'classes\d*\.dex', name):
        for s in strings(z.read(name)):
            if s not in seen and (not pat or pat.search(s)):
                seen.add(s); print(s)
