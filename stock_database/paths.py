from __future__ import annotations
from pathlib import Path


def default_db_path() -> Path:
    """Stub - not used in Supabase mode."""
    return Path("/dev/null")
