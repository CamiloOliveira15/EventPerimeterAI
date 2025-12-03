import redis.asyncio as redis
from src.core.config import get_settings

settings = get_settings()

class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=False # Keep as bytes for image data
            )
        return cls._instance

async def get_redis_client():
    return RedisClient.get_instance()
