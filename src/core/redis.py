from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis

from src.config import configure

checkpointer = AsyncRedisSaver(
    redis_url=configure.REDIS_URL,
    ttl={
        "default_ttl": 30,
        "refresh_on_read": True,
    },
)

redis_client = Redis.from_url(
    configure.REDIS_URL,
    max_connections=50,
    decode_responses=True,
)


# JTI blacklist expiry should be longer than the longest token (refresh token = 2 days)
JTI_EXPIRY = 60 * 60 * 24 * 2  # 2 days in seconds


async def add_jti_to_blacklist(jti: str) -> None:
    await redis_client.setex(
        name=jti,
        time=JTI_EXPIRY,
        value="true",
    )


async def token_in_blacklist(jti: str) -> bool:
    exists = await redis_client.exists(jti)
    return exists == 1


async def setup_memory() -> None:
    await checkpointer.setup()
