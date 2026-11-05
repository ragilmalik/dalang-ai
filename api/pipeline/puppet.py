"""Turn a generated puppet picture into a reusable transparent cut-out (SAM 3.1 masks)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter


def cutout_from_sam(image_path: Path, matches: list[dict[str, Any]], out: Path) -> Path | None:
    """Combine SAM matches into one alpha mask (best match plus any touching parts like rods)."""
    if not matches:
        return None
    im = Image.open(image_path).convert("RGBA")
    W, H = im.size
    alpha = np.zeros((H, W), dtype=np.uint8)

    def area(m: dict[str, Any]) -> int:
        return max(0, m["right"] - m["left"]) * max(0, m["bottom"] - m["top"])

    ranked = sorted(matches, key=lambda m: ((m.get("confidence") or 0.5) * area(m)), reverse=True)
    best = ranked[0]
    keep = [best]
    for m in ranked[1:]:  # keep pieces overlapping the main puppet's box (e.g. a detached rod or prop)
        if (m.get("confidence") or 0) > 0.5 and not (
            m["right"] < best["left"] or m["left"] > best["right"] or m["bottom"] < best["top"] or m["top"] > best["bottom"]
        ):
            keep.append(m)
    for m in keep:
        bw, bh = m["right"] - m["left"], m["bottom"] - m["top"]
        if bw <= 0 or bh <= 0:
            continue
        raster = np.frombuffer(m["mask"], dtype=np.uint8).reshape(m["mh"], m["mw"]) * 255
        mask_img = Image.fromarray(raster, "L").resize((bw, bh), Image.Resampling.NEAREST)
        region = np.array(mask_img)
        y0, x0 = max(0, m["top"]), max(0, m["left"])
        y1, x1 = min(H, m["top"] + bh), min(W, m["left"] + bw)
        alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], region[: y1 - y0, : x1 - x0])
    if alpha.max() == 0:
        return None
    a = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.8))
    im.putalpha(a)
    _trim(im).save(out)
    return out


def cutout_by_background(image_path: Path, out: Path, tol: int = 38) -> Path:
    """Fallback when SAM finds nothing: key out the plain background colour sampled at the corners."""
    im = Image.open(image_path).convert("RGBA")
    arr = np.array(im).astype(np.int16)
    h, w = arr.shape[:2]
    corners = np.concatenate([arr[:8, :8, :3].reshape(-1, 3), arr[:8, -8:, :3].reshape(-1, 3),
                              arr[-8:, :8, :3].reshape(-1, 3), arr[-8:, -8:, :3].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    dist = np.abs(arr[:, :, :3] - bg).sum(axis=2)
    alpha = np.clip((dist - tol) * 6, 0, 255).astype(np.uint8)
    im.putalpha(Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.8)))
    _trim(im).save(out)
    return out


def _trim(im: Image.Image, pad: int = 6) -> Image.Image:
    bbox = im.split()[-1].point(lambda v: 255 if v > 20 else 0).getbbox()
    if not bbox:
        return im
    left, top, right, bottom = bbox
    return im.crop((max(0, left - pad), max(0, top - pad), min(im.width, right + pad), min(im.height, bottom + pad)))
