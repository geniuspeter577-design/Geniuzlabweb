"""AI Hub Chat provider — streams a reply from OpenAI's Chat Completions
API one token-chunk at a time.

Same seam as providers.py / video_providers.py: views.py never talks to
OpenAI directly, it only calls stream_chat_reply(messages). No key is
ever hardcoded — everything reads from OPENAI_API_KEY, the one shared
key used for chat, images, and any future OpenAI feature (per project
policy, see settings.py / .env.example).

    OPENAI_API_KEY=sk-...          # required
    OPENAI_CHAT_MODEL=gpt-4o-mini  # optional, has a sane default
    OPENAI_API_BASE=...            # optional, for a proxy/compatible endpoint

is_chat_configured() lets views.py show a friendly "not set up yet"
message instead of ever letting a missing key surface as a 500.

stream_chat_reply() is a generator that yields plain-text chunks as
they arrive over the wire (Server-Sent Events under the hood), so the
view can forward each chunk to the browser immediately instead of
waiting for the full reply — this is what makes the UI feel like a
premium, live-typing assistant rather than a spinner-then-dump chatbot.
"""

import json
import logging
import os

import requests

logger = logging.getLogger("ai_hub")

DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are the GeniuzLab AI Hub assistant, built into a platform for "
    "creatives to learn, build portfolios, get hired, collaborate, and "
    "sell services. Help with creative writing, business advice, graphic "
    "design direction, video editing guidance, coding, branding, and "
    "prompt engineering. Use Markdown formatting, including fenced code "
    "blocks with a language tag for any code. Be concise and practical."
)


class ChatProviderNotConfigured(Exception):
    """OPENAI_API_KEY is not set."""


class ChatGenerationError(Exception):
    """The provider is configured, but the request itself failed."""


def is_chat_configured():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def stream_chat_reply(messages):
    """messages: list of {"role": "user"|"assistant", "content": str},
    oldest first — the full thread history, giving the model real
    conversation memory on every turn.

    Yields str chunks of the assistant's reply as they stream in.
    Raises ChatProviderNotConfigured / ChatGenerationError on failure.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ChatProviderNotConfigured("OPENAI_API_KEY is not set.")

    model = os.environ.get("OPENAI_CHAT_MODEL", DEFAULT_MODEL).strip()
    base_url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")

    payload_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": payload_messages,
                "stream": True,
            },
            stream=True,
            timeout=60,
        )
    except requests.RequestException as exc:
        logger.exception("OpenAI chat request failed to send")
        raise ChatGenerationError(f"Could not reach OpenAI: {exc}") from exc

    if resp.status_code != 200:
        body = ""
        try:
            body = resp.text[:500]
        except Exception:
            pass
        logger.error("OpenAI chat API error %s: %s", resp.status_code, body)
        raise ChatGenerationError(f"OpenAI API returned HTTP {resp.status_code}")

    try:
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            if not raw_line.startswith("data:"):
                continue
            data = raw_line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            piece = delta.get("content")
            if piece:
                yield piece
    except requests.RequestException as exc:
        logger.exception("OpenAI chat stream interrupted")
        raise ChatGenerationError(f"Connection to OpenAI was interrupted: {exc}") from exc
