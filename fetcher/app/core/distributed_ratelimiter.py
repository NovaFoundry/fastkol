import asyncio
import time
import redis.asyncio as aioredis
from app.settings import settings

class DistributedRateLimiter:
    def __init__(self, key: str, rate_per_sec: float = 1.0):
        cfg = settings.get_config('ratelimiter')
        self.redis_url = cfg['redis_url']
        self.key = f"fetcher:ratelimit:{key}"
        self.rate_per_sec = rate_per_sec
        self.min_interval = 1.0 / rate_per_sec
        self.lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local interval = tonumber(ARGV[2])
        local last = tonumber(redis.call('get', key) or '0')
        if now - last >= interval then
            redis.call('set', key, now)
            redis.call('pexpire', key, interval * 2)
            return 1
        else
            return 0
        end
        """
        self.redis = None
        self.script_sha = None

    async def _init_redis(self):
        if self.redis is None:
            self.redis = aioredis.from_url(self.redis_url)
            self.script_sha = await self.redis.script_load(self.lua_script)

    async def acquire(self):
        await self._init_redis()
        while True:
            now = int(time.time() * 1000)
            interval = int(self.min_interval * 1000)
            allowed = await self.redis.evalsha(self.script_sha, 1, self.key, now, interval)
            if allowed == 1:
                return
            await asyncio.sleep(self.min_interval / 2)

    async def close(self):
        if self.redis:
            await self.redis.close() 