from __future__ import annotations

import logging
from typing import Optional

import asyncpg

from core.settings import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def create_pool() -> asyncpg.Pool:
    """Create and return the global asyncpg connection pool.

    Uses statement_cache_size=0 because PgBouncer in transaction mode
    does not support named prepared statements.
    """
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        statement_cache_size=0,
        command_timeout=30,
        max_inactive_connection_lifetime=300,
    )
    logger.info("Database pool created (min=2, max=10)")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised — call create_pool() first")
    return _pool
