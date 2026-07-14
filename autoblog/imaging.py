"""Image post-processing before upload.

Re-encodes every featured image to a clean, web-optimized JPEG:
* strips EXIF/metadata (which can trigger PHP exif warnings on some hosts and
  garble the WordPress REST response),
* converts to RGB JPEG,
* caps the width for faster page loads (better Core Web Vitals / SEO).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("autoblog")

MAX_WIDTH = 1280
JPEG_QUALITY = 85


def normalize_image(path: Path) -> Path:
    """Return a cleaned .jpg version of the image (or the original on failure)."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            img = img.convert("RGB")  # drops alpha + EXIF
            if img.width > MAX_WIDTH:
                ratio = MAX_WIDTH / img.width
                img = img.resize((MAX_WIDTH, round(img.height * ratio)))
            out = path.with_suffix(".jpg")
            # save with no exif; optimize for size
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        if out != path:
            try:
                path.unlink()
            except OSError:
                pass
        return out
    except Exception as err:  # noqa: BLE001 - never block on optimisation
        logger.warning("Image normalization failed (%s); using original.", err)
        return path
