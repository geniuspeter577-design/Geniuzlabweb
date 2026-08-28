"""Compatibility ASGI entry point for the extracted backend package."""
from backend.asgi import application

__all__ = ["application"]
