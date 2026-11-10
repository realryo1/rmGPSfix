"""module/ を配布用 ZIP にする。テキストは LF に揃えてから格納する。"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "module"
NAMES = [
    "module.prop",
    "sepolicy.rule",
    "post-fs-data.sh",
    "service.sh",
    "uninstall.sh",
    "apply.sh",
    "izat.conf",
]

zip_path = ROOT / "gps_incamera_fix_v2.0.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in NAMES:
        path = MOD / name
        data = path.read_bytes().replace(b"\r\n", b"\n")
        path.write_bytes(data)
        zf.writestr(name, data)

print(f"packaged {zip_path}")
