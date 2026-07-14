"""Image generation via the OpenAI Images API.

Defaults to ``gpt-image-1-mini`` at low quality — the most cost-effective
option (roughly $0.002/image, i.e. a few dollars a month at 39 posts/day).
Model, size and quality are all configurable from .env.
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger("autoblog")


class OpenAIImageGenerator:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-image-1-mini",
        output_dir: Path | None = None,
        *,
        size: str = "1536x1024",  # landscape, good for featured images
        quality: str = "low",  # low | medium | high  (low = cheapest)
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.size = size
        self.quality = quality
        self.output_dir = output_dir or Path("generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, *, slug: str) -> Path | None:
        full_prompt = (
            f"{prompt}. Photorealistic, editorial blog featured image, high quality, "
            "natural lighting. Absolutely no text anywhere in the image: no words, "
            "letters, numbers, captions, logos, watermarks, signage, or labels. "
            "Do not show readable screens, documents, papers, or charts."
        )
        try:
            result = self.client.images.generate(
                model=self.model,
                prompt=full_prompt,
                size=self.size,
                quality=self.quality,
                n=1,
            )
            usage = getattr(result, "usage", None)
            if usage is not None:
                logger.info("OpenAI image usage: %s", usage)
            data = result.data[0]
            raw = getattr(data, "b64_json", None)
            if raw:
                image_bytes = base64.b64decode(raw)
            else:
                # Some models return a URL instead of base64.
                import requests

                url = getattr(data, "url", None)
                if not url:
                    logger.warning("OpenAI returned no image data for '%s'.", slug)
                    return None
                image_bytes = requests.get(url, timeout=90).content

            path = self.output_dir / f"{_safe_slug(slug)}.png"
            path.write_bytes(image_bytes)
            logger.info(
                "Generated AI image (%s, %s) -> %s",
                self.model,
                self.quality,
                path.name,
            )
            return path
        except Exception as err:  # noqa: BLE001 - never block publishing
            logger.warning("OpenAI image generation failed (%s).", repr(err)[:180])
            return None


def _safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "featured"
