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
    "audio_module_config_primary.xml",
]

zip_path = ROOT / "gps_incamera_audio_fix_v3.0.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in NAMES:
        path = MOD / name
        data = path.read_bytes().replace(b"\r\n", b"\n")
        path.write_bytes(data)
        zf.writestr(name, data)

print(f"packaged {zip_path}")
