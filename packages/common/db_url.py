from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResolvedDbUrl:
    url: str
    source: str  # "DATABASE_URL" | "DB_URL"


class DbUrlMismatchError(RuntimeError):
    pass


def resolve_db_url(
    *,
    database_url: Optional[str] = None,
    db_url: Optional[str] = None,
    allow_fallback: bool = True,
) -> ResolvedDbUrl:
    """
    Resolve the canonical DB URL for runtime services.

    Decision:
    - Prefer DATABASE_URL
    - Allow DB_URL only as a fallback (Phase 1 bridge)
    - If both are set and differ, raise to prevent split-brain persistence.
    """
    database_url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
    db_url = db_url if db_url is not None else os.environ.get("DB_URL")

    if database_url and db_url and database_url != db_url:
        raise DbUrlMismatchError("DATABASE_URL and DB_URL are both set but differ")

    if database_url:
        return ResolvedDbUrl(url=database_url, source="DATABASE_URL")

    if allow_fallback and db_url:
        return ResolvedDbUrl(url=db_url, source="DB_URL")

    raise RuntimeError("Database URL not configured (set DATABASE_URL)")

