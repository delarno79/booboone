"""Free AI image generation via Pollinations.ai (no API key, no billing).

Generates a unique image from the article's image prompt. This is the free path
to *AI-generated* featured images (as opposed to stock photos), and unlike the
Gemini/Imagen image API it does not require a paid Google account.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from pathlib import Path

import requests

logger = logging.getLogger("autoblog")

_BASE = "https://image.pollinations.ai/prompt/"


class PollinationsImageGenerator:
    def __init__(self, output_dir: Path, *, width: int = 1024, height: int = 576):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height

    def generate(self, prompt: str, *, slug: str, timeout: int = 120) -> Path | None:
        full_prompt = (
            f"{prompt}. Photorealistic, editorial, high quality. "
            "No text anywhere: no words, letters, numbers, captions, logos, "
            "watermarks, signage, or readable screens/documents."
        )
        url = _BASE + urllib.parse.quote(full_prompt)
        params = {
            "width": self.width,
            "height": self.height,
            "nologo": "true",
            "safe": "true",
        }
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            if not ctype.startswith("image/"):
                logger.warning("Pollinations returned non-image (%s).", ctype)
                return None
            ext = ".jpg" if "jpeg" in ctype or "jpg" in ctype else ".png"
            path = self.output_dir / f"{_safe_slug(slug)}{ext}"
            path.write_bytes(resp.content)
            logger.info("Generated free AI image (pollinations) -> %s", path.name)
            return path
        except requests.RequestException as err:
            logger.warning("Free AI image generation failed (%s).", repr(err)[:150])
            return None


def _safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "featured"
