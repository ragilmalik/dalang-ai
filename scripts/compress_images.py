"""Shrink the committed PNGs (README screenshots, web share card and icons) without changing how they look.

    python scripts/compress_images.py            # in place; prints before/after sizes

Uses pngquant (palette, quality 75-92, only kept when smaller) when it is installed, else Pillow's adaptive
palette with dithering. Run it after scripts/screenshots.py or scripts/make_web_assets.py.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [*sorted((ROOT / "docs" / "screenshots").glob("*.png")), *sorted((ROOT / "web" / "app").glob("*.png")),
           *sorted((ROOT / "web" / "public").glob("*.png"))]


def shrink(path: Path) -> tuple[int, int]:
    before = path.stat().st_size
    tmp = path.with_suffix(".tmp.png")
    if shutil.which("pngquant"):
        subprocess.run(["pngquant", "--quality=75-92", "--speed=1", "--strip", "--force", "--output", str(tmp), str(path)],
                       capture_output=True)
    else:
        with Image.open(path) as im:
            im.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG) \
              .save(tmp, optimize=True)
    if tmp.exists() and tmp.stat().st_size < before * 0.95:
        tmp.replace(path)
    else:
        tmp.unlink(missing_ok=True)
    return before, path.stat().st_size


def main() -> int:
    total_b = total_a = 0
    for p in TARGETS:
        b, a = shrink(p)
        total_b, total_a = total_b + b, total_a + a
        print(f"{p.relative_to(ROOT)}: {b // 1024} KB -> {a // 1024} KB")
    print(f"total {total_b // 1024} KB -> {total_a // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
