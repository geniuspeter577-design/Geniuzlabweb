"""Compatibility WSGI entry point for the extracted backend package."""
from backend.wsgi import application

__all__ = ["application"]
