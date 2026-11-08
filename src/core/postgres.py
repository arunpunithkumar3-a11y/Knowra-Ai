import asyncio
import logging
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.config import configure

logger = logging.getLogger(__name__)


def _get_pg_conninfo() -> str:
    url = configure.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    if "sslmode=" not in url and ("render.com" in url or "supabase" in url or "aws" in url):
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


_pg_conninfo = _get_pg_conninfo()

_pool: AsyncConnectionPool | None = None
_checkpointer = None


async def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=_pg_conninfo,
            min_size=1,
            max_size=5,
            open=False,
            timeout=3.0,
            kwargs={"autocommit": True},
        )
        await asyncio.wait_for(_pool.open(), timeout=3.0)
    return _pool


async def get_checkpointer():
    global _checkpointer, _pool
    if _checkpointer is None:
        try:
            pool = await asyncio.wait_for(_get_pool(), timeout=3.0)
            saver = AsyncPostgresSaver(pool)
            await asyncio.wait_for(saver.setup(), timeout=3.0)
            _checkpointer = saver
            logger.info("Initialized AsyncPostgresSaver checkpointer.")
        except Exception as e:
            logger.warning(
                "PostgreSQL checkpointer initialization failed (%s); falling back to MemorySaver.", e
            )
            if _pool is not None:
                try:
                    await _pool.close()
                except Exception:
                    pass
                _pool = None
            from langgraph.checkpoint.memory import MemorySaver
            _checkpointer = MemorySaver()

    return _checkpointer
