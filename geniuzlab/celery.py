"""Compatibility Celery entry point for the extracted backend package."""
from backend.geniuzlab.celery import app

__all__ = ["app"]
