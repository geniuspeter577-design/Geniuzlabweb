"""Video-generation provider abstraction.

Same seam as providers.py, but for video: views.py only ever calls
get_video_provider(). Video generation is asynchronous everywhere (you
submit a prompt and get a job id back, then poll for completion), so
each provider exposes start_generation() + check_status() rather than
a single generate() call.

    AI_VIDEO_PROVIDER=runway     # which provider is active (default: runway)
    RUNWAY_API_KEY=...           # required for the runway provider
    RUNWAY_MODEL=gen3a_turbo     # optional
    LUMA_API_KEY=...             # required for the luma provider

No key is ever hardcoded. If the active provider has no key,
is_configured() returns False and the view shows a friendly
"not set up yet" message.

IMPORTANT: Runway's and Luma's HTTP APIs are not something this
environment can call to verify live, and third-party API contracts do
shift over time. The endpoint paths, payload shapes, and status field
names below reflect each provider's documented API as of this writing
— treat them as a solid starting structure, but check the provider's
current API reference before relying on this in production, and adjust
the small number of marked spots if a field name has changed.

To add a provider (Pika, Kling, etc.): subclass VideoProvider,
implement is_configured()/start_generation()/check_status(), and add
one line to VIDEO_PROVIDERS.
"""

import logging
import os

import requests

logger = logging.getLogger("ai_hub")


class VideoProviderNotConfigured(Exception):
    """The active provider is missing its required API key/config."""


class VideoGenerationError(Exception):
    """The provider is configured, but the request itself failed."""


class VideoProvider:
    name = "base"

    def is_configured(self):
        raise NotImplementedError

    def start_generation(self, prompt):
        """Submits the job. Returns an external job id (str)."""
        raise NotImplementedError

    def check_status(self, job_id):
        """Returns {"status": "queued"|"processing"|"done"|"failed",
        "video_url": str or None}."""
        raise NotImplementedError


class RunwayVideoProvider(VideoProvider):
    """Runway's text-to-video API (Gen-3 family). See
    https://docs.dev.runwayml.com for current endpoint/version details."""

    name = "runway"

    def __init__(self):
        self.api_key = os.environ.get("RUNWAY_API_KEY", "").strip()
        self.base_url = os.environ.get("RUNWAY_API_BASE", "https://api.dev.runwayml.com/v1").rstrip("/")
        self.model = os.environ.get("RUNWAY_MODEL", "gen3a_turbo").strip()
        self.api_version = os.environ.get("RUNWAY_API_VERSION", "2024-11-06").strip()

    def is_configured(self):
        return bool(self.api_key)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": self.api_version,
        }

    def start_generation(self, prompt):
        if not self.is_configured():
            raise VideoProviderNotConfigured("RUNWAY_API_KEY is not set.")
        try:
            resp = requests.post(
                f"{self.base_url}/text_to_video",
                headers=self._headers(),
                json={"promptText": prompt, "model": self.model},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.exception("Runway request failed to send")
            raise VideoGenerationError(f"Could not reach Runway: {exc}") from exc

        if resp.status_code not in (200, 201, 202):
            logger.error("Runway API error %s: %s", resp.status_code, resp.text[:500])
            raise VideoGenerationError(f"Runway API returned HTTP {resp.status_code}")

        job_id = (resp.json() or {}).get("id")
        if not job_id:
            raise VideoGenerationError("Runway API response had no job id.")
        return job_id

    def check_status(self, job_id):
        try:
            resp = requests.get(
                f"{self.base_url}/tasks/{job_id}",
                headers=self._headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise VideoGenerationError(f"Could not reach Runway: {exc}") from exc

        if resp.status_code != 200:
            raise VideoGenerationError(f"Runway API returned HTTP {resp.status_code}")

        data = resp.json() or {}
        raw_status = (data.get("status") or "").lower()
        mapped = {
            "pending": "queued",
            "running": "processing",
            "succeeded": "done",
            "failed": "failed",
        }.get(raw_status, "processing")

        video_url = None
        output = data.get("output") or []
        if output:
            video_url = output[0]

        return {"status": mapped, "video_url": video_url}


class LumaVideoProvider(VideoProvider):
    """Luma AI's Dream Machine API. See
    https://docs.lumalabs.ai for current endpoint details."""

    name = "luma"

    def __init__(self):
        self.api_key = os.environ.get("LUMA_API_KEY", "").strip()
        self.base_url = os.environ.get("LUMA_API_BASE", "https://api.lumalabs.ai/dream-machine/v1").rstrip("/")

    def is_configured(self):
        return bool(self.api_key)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def start_generation(self, prompt):
        if not self.is_configured():
            raise VideoProviderNotConfigured("LUMA_API_KEY is not set.")
        try:
            resp = requests.post(
                f"{self.base_url}/generations",
                headers=self._headers(),
                json={"prompt": prompt},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.exception("Luma request failed to send")
            raise VideoGenerationError(f"Could not reach Luma: {exc}") from exc

        if resp.status_code not in (200, 201, 202):
            logger.error("Luma API error %s: %s", resp.status_code, resp.text[:500])
            raise VideoGenerationError(f"Luma API returned HTTP {resp.status_code}")

        job_id = (resp.json() or {}).get("id")
        if not job_id:
            raise VideoGenerationError("Luma API response had no generation id.")
        return job_id

    def check_status(self, job_id):
        try:
            resp = requests.get(
                f"{self.base_url}/generations/{job_id}",
                headers=self._headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise VideoGenerationError(f"Could not reach Luma: {exc}") from exc

        if resp.status_code != 200:
            raise VideoGenerationError(f"Luma API returned HTTP {resp.status_code}")

        data = resp.json() or {}
        raw_state = (data.get("state") or "").lower()
        mapped = {
            "queued": "queued",
            "dreaming": "processing",
            "completed": "done",
            "failed": "failed",
        }.get(raw_state, "processing")

        video_url = None
        assets = data.get("assets") or {}
        if assets.get("video"):
            video_url = assets["video"]

        return {"status": mapped, "video_url": video_url}


# Registry: env var value -> provider class. Add new providers here.
VIDEO_PROVIDERS = {
    "runway": RunwayVideoProvider,
    "luma": LumaVideoProvider,
}


def get_video_provider():
    """Reads AI_VIDEO_PROVIDER from the environment and returns an
    instance of the matching provider. Defaults to Runway, including
    when the configured value doesn't match anything registered."""
    key = os.environ.get("AI_VIDEO_PROVIDER", "runway").strip().lower()
    provider_cls = VIDEO_PROVIDERS.get(key, RunwayVideoProvider)
    return provider_cls()
