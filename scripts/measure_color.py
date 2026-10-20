"""Print mean R/G/B (and G/B, R/B ratios) of images, to quantify a colour cast.

Usage: python measure_color.py <image> [<image> ...]
Requires Pillow. Images are read locally only; nothing is written or sent.
"""
import sys
from PIL import Image, ImageStat

for path in sys.argv[1:]:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    mean = ImageStat.Stat(im).mean
    center = ImageStat.Stat(im.crop((w // 3, h // 3, 2 * w // 3, 2 * h // 3))).mean
    print(f"{path}: {w}x{h} mean={[round(v) for v in mean]} "
          f"G/B={mean[1] / mean[2]:.2f} R/B={mean[0] / mean[2]:.2f} "
          f"center={[round(v) for v in center]}")
