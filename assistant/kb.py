"""Loader for the assistant's centralized knowledge base.

Company info, founder info, services, pricing notes, FAQs, customer
care contacts, business hours, and policies all live in
`knowledge_base.json` — this is the ONLY file that should need editing
to update what the chatbot knows about GeniuzLab. Nothing in engine.py
should hardcode company/founder/contact facts; it should read them
from here instead.

To swap this for a database table later (e.g. so staff can edit the
knowledge base from the Django admin instead of a JSON file), replace
get_kb() with a query and keep the same dict shape — nothing else in
the assistant app needs to change.
"""

import json
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent / "knowledge_base.json"


@lru_cache(maxsize=1)
def get_kb():
    """Returns the parsed knowledge base dict. Cached for the life of
    the process — restart the app (or call get_kb.cache_clear()) after
    editing knowledge_base.json for changes to take effect."""
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
