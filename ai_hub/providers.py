"""Image-generation provider abstraction.

Design goal: views.py never talks to OpenAI (or anything else)
directly — it only calls get_image_provider().generate(prompt). Which
provider is active, and every credential it needs, is controlled
entirely by environment variables:

    AI_IMAGE_PROVIDER=openai        # which provider is active (default: openai)
    OPENAI_API_KEY=sk-...           # required for the openai provider
    OPENAI_IMAGE_MODEL=gpt-image-1  # optional, has a sane default
    OPENAI_API_BASE=...             # optional, for a proxy/compatible endpoint

No key is ever hardcoded here. If a provider's key is missing,
is_configured() returns False and the view shows a friendly
"not set up yet" message instead of crashing — it never lets a missing
key surface as a 500 error.

To add a new provider (Stability, etc.): subclass ImageProvider,
implement is_configured()/generate(), and add one line to
IMAGE_PROVIDERS. Nothing else in the app needs to change.
"""

import logging
import os

import requests

logger = logging.getLogger("ai_hub")


class ProviderNotConfigured(Exception):
    """The active provider is missing its required API key/config."""


class ImageGenerationError(Exception):
    """The provider is configured, but the generation call itself failed."""


class ImageProvider:
    name = "base"

    def is_configured(self):
        raise NotImplementedError

    def generate(self, prompt, size="1024x1024"):
        """Returns {"url": str} or {"b64": str}. Raises
        ProviderNotConfigured or ImageGenerationError on failure."""
        raise NotImplementedError


class OpenAIImageProvider(ImageProvider):
    """Default provider. Uses OpenAI's Images API
    (POST /v1/images/generations)."""

    name = "openai"

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1").strip()
        self.base_url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")

    def is_configured(self):
        return bool(self.api_key)

    def generate(self, prompt, size="1024x1024"):
        if not self.is_configured():
            raise ProviderNotConfigured("OPENAI_API_KEY is not set.")

        try:
            resp = requests.post(
                f"{self.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "prompt": prompt, "size": size, "n": 1},
                timeout=60,
            )
        except requests.RequestException as exc:
            logger.exception("OpenAI image request failed to send")
            raise ImageGenerationError(f"Could not reach OpenAI: {exc}") from exc

        if resp.status_code != 200:
            logger.error("OpenAI image API error %s: %s", resp.status_code, resp.text[:500])
            raise ImageGenerationError(f"OpenAI API returned HTTP {resp.status_code}")

        try:
            data = resp.json().get("data") or []
        except ValueError as exc:
            raise ImageGenerationError("OpenAI API returned an unreadable response.") from exc

        if not data:
            raise ImageGenerationError("OpenAI API returned no image data.")

        item = data[0]
        if item.get("url"):
            return {"url": item["url"]}
        if item.get("b64_json"):
            return {"b64": item["b64_json"]}
        raise ImageGenerationError("OpenAI API response had neither a url nor b64_json field.")


class StabilityImageProvider(ImageProvider):
    """Placeholder second provider. Demonstrates the seam for adding
    more providers later — not wired to a real endpoint yet, so it
    reports itself as configured (if a key is present) but raises a
    clear error on generate() rather than pretending to work."""

    name = "stability"

    def __init__(self):
        self.api_key = os.environ.get("STABILITY_API_KEY", "").strip()

    def is_configured(self):
        return bool(self.api_key)

    def generate(self, prompt, size="1024x1024"):
        raise ImageGenerationError(
            "The 'stability' provider is registered but not implemented yet. "
            "Add its API call in ai_hub/providers.py:StabilityImageProvider.generate()."
        )


# Registry: env var value -> provider class. Add new providers here.
IMAGE_PROVIDERS = {
    "openai": OpenAIImageProvider,
    "stability": StabilityImageProvider,
}


def get_image_provider():
    """Reads AI_IMAGE_PROVIDER from the environment and returns an
    instance of the matching provider. Defaults to OpenAI, including
    when the configured value doesn't match anything registered."""
    key = os.environ.get("AI_IMAGE_PROVIDER", "openai").strip().lower()
    provider_cls = IMAGE_PROVIDERS.get(key, OpenAIImageProvider)
    return provider_cls()
