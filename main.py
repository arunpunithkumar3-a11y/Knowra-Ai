"""Knowra Application Entrypoint.

Allows running directly with:
    uvicorn main:app --reload --port 8000
"""

from src.main import app

__all__ = ["app"]
