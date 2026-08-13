from redis.asyncio import Redis
from src.config import configure

redis_client = Redis.from_url(configure.REDIS_URL)


JTI_EXPIRY=3600

async def add_jti_to_blacklist(jti:str) ->None:
    await redis_client.setex(
        name=jti,
        time=JTI_EXPIRY,
        value="true"
    )


async def token_in_blaclist(jti:str)->bool:
    exists = await redis_client.exists(jti)
    return exists==1    