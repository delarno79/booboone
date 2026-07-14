"""Free stock-image fallback via the Openverse API (no API key required).

Prefers public-domain / CC0 images so the client's commercial blog has no
attribution obligations. Falls back to broader commercial-use licences only if
no public-domain match is found.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("autoblog")

_API = "https://api.openverse.org/v1/images/"
_UA = {"User-Agent": "booboone-autoblog/1.0 (+https://booboone.com)"}


class StockImageProvider:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, query: str, *, slug: str) -> Path | None:
        # Try progressively broader queries so abstract keywords still match:
        #   1) full keyword, public domain (no attribution)
        #   2) full keyword, any commercial-use licence
        #   3) first two words, commercial-use (broader net)
        short = " ".join(query.split()[:2])
        attempts = [
            {"q": query, "license": "cc0,pdm", "page_size": 15},
            {"q": query, "license_type": "commercial", "page_size": 15},
        ]
        if short.lower() != query.lower():
            attempts.append(
                {"q": short, "license_type": "commercial", "page_size": 15}
            )

        for params in attempts:
            hit = self._search_and_download(params, slug=slug)
            if hit is not None:
                return hit
        logger.warning("No free stock image found for '%s'.", query)
        return None

    def _search_and_download(self, params: dict, *, slug: str) -> Path | None:
        try:
            resp = requests.get(_API, params=params, headers=_UA, timeout=30)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except requests.RequestException as err:
            logger.warning("Openverse search failed: %s", err)
            return None

        for item in results:
            url = item.get("url")
            if not url:
                continue
            try:
                img = requests.get(url, headers=_UA, timeout=60)
                img.raise_for_status()
                content_type = img.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    continue
                ext = ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".png"
                path = self.output_dir / f"{_safe_slug(slug)}{ext}"
                path.write_bytes(img.content)
                logger.info(
                    "Using free stock image (%s) -> %s",
                    item.get("license", "?"),
                    path.name,
                )
                return path
            except requests.RequestException:
                continue
        return None


def _safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "featured"
