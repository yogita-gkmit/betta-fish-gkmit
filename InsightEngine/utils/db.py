"""
Generic Database Tools (Async)

This module provides database access wrappers based on SQLAlchemy 2.x async engine, supporting MySQL and PostgreSQL.
Data model definition location:
- None (This module only provides connection and query tools, does not define data models)
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Iterable, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy import text
from InsightEngine.utils.config import settings

__all__ = [
    "get_async_engine",
    "fetch_all",
]


_engine: Optional[AsyncEngine] = None


def _build_database_url() -> str:
    dialect: str = (settings.DB_DIALECT or "mysql").lower()
    host: str = settings.DB_HOST or ""
    port: str = str(settings.DB_PORT or "")
    user: str = settings.DB_USER or ""
    password: str = settings.DB_PASSWORD or ""
    db_name: str = settings.DB_NAME or ""

    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")  # Use complete URL provided externally if available

    if dialect in ("postgresql", "postgres"):
        # PostgreSQL uses asyncpg driver
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"

    # Default MySQL uses aiomysql driver
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{db_name}"


def get_async_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        database_url: str = _build_database_url()
        _engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return _engine


async def fetch_all(query: str, params: Optional[Union[Iterable[Any], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Execute read-only query and return list of dictionaries.
    """
    # Ensure we use an engine bound to the current context if needed, or just standard pattern
    # For safety in mixed sync/async environments (like Flask + asyncio), we should make sure the engine is disposed or compatible.
    # But usually, keeping a global engine is fine IF the loop is consistent.
    # If Flask is creating a new loop for each request (via something like asyncio.run), the global _engine created in a different loop will fail.
    
    # Simple fix: Create a local engine for the operation if we suspect loop mismatch, OR (better) check loop.
    # Given the traceback likely points to loop mismatch with the global _engine.
    
    # Let's recreate engine if loop seems different or just create a fresh one for now to be safe against loop boundaries.
    # NOTE: Creating engine per request is expensive but safe. Optimally we'd bond it to the loop.
    
    database_url: str = _build_database_url()
    # disposable engine for this call to avoid "Future attached to a different loop"
    engine = create_async_engine(database_url, pool_pre_ping=True)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params or {})
            rows = result.mappings().all()
            return [dict(row) for row in rows]
    finally:
        await engine.dispose()


