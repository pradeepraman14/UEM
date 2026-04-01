from redis.asyncio import Redis, ConnectionPool
from app.config import settings

_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> Redis:
    return Redis(connection_pool=get_redis_pool())


async def close_redis_pool() -> None:
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None
