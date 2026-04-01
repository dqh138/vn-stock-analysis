"""
Vercel serverless entry point for the FastAPI app.

Vercel's @vercel/python runtime looks for an ASGI app called `app` in this file.
"""
from webapp.app import app  # noqa: F401 — re-exported as the ASGI app

# Vercel requires the variable to be named `app` at module level.
__all__ = ["app"]
