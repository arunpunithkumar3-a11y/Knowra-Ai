import logging
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.config import configure

logger = logging.getLogger(__name__)

_pg_conninfo = configure.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

_pool: AsyncConnectionPool | None = None
_checkpointer = None


async def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=_pg_conninfo,
            min_size=1,
            max_size=10,
            open=False,
            kwargs={"autocommit": True},
        )
        await _pool.open()
    return _pool


async def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        try:
            pool = await _get_pool()
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            _checkpointer = saver
        except Exception as e:
            logger.warning(
                "PostgreSQL checkpointer initialization failed (%s); falling back to MemorySaver.", e
            )
            from langgraph.checkpoint.memory import MemorySaver
            _checkpointer = MemorySaver()

    return _checkpointer
